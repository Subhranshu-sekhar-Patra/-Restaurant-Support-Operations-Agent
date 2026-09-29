"""KB ingest - splits markdown documents and upserts embeddings into pgvector."""

import re
import asyncio
from pathlib import Path
from datetime import date
from typing import List, Tuple

from sqlalchemy import text

from app.config import settings
from app.database import async_session
from app.rag.embedder import embed_texts
from app.observability.logging import get_logger

logger = get_logger(__name__)

KB_DIR = Path(__file__).parent.parent.parent / "data" / "knowledge_base"


def parse_frontmatter(content: str) -> Tuple[dict, str]:
    """Extract YAML-like frontmatter from markdown content."""
    meta = {"effective_date": str(date.today()), "version": 1}

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            body = parts[2].strip()

            for line in frontmatter.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "effective_date":
                        meta["effective_date"] = value
                    elif key == "version":
                        meta["version"] = int(value)
                    elif key == "title":
                        meta["title"] = value

            return meta, body

    return meta, content


def split_by_heading(content: str, max_tokens: int = 400, overlap: int = 50) -> List[dict]:
    """
    Split markdown content by headings.
    Each section becomes a chunk, with overlap for context.
    """
    # Split by markdown headings
    sections = re.split(r'\n(?=#{1,3}\s)', content)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Extract section heading
        heading_match = re.match(r'^(#{1,3})\s+(.+)', section)
        heading = heading_match.group(2) if heading_match else None

        # Simple token estimation (words / 0.75)
        words = section.split()
        estimated_tokens = len(words) / 0.75

        if estimated_tokens <= max_tokens:
            chunks.append({"section": heading, "content": section})
        else:
            # Split large sections into smaller chunks
            sentences = re.split(r'(?<=[.!?])\s+', section)
            current_chunk = []
            current_tokens = 0

            for sentence in sentences:
                sent_tokens = len(sentence.split()) / 0.75
                if current_tokens + sent_tokens > max_tokens and current_chunk:
                    chunks.append({
                        "section": heading,
                        "content": " ".join(current_chunk),
                    })
                    # Keep overlap
                    overlap_words = " ".join(current_chunk).split()[-overlap:]
                    current_chunk = [" ".join(overlap_words), sentence]
                    current_tokens = len(" ".join(current_chunk).split()) / 0.75
                else:
                    current_chunk.append(sentence)
                    current_tokens += sent_tokens

            if current_chunk:
                chunks.append({
                    "section": heading,
                    "content": " ".join(current_chunk),
                })

    return chunks


async def ingest_file(filepath: Path):
    """Ingest a single KB markdown file."""
    content = filepath.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    source = filepath.name
    title = meta.get("title", filepath.stem.replace("_", " ").title())
    effective_date = meta["effective_date"]
    version = meta["version"]

    # Split into chunks
    chunks = split_by_heading(body)
    if not chunks:
        logger.warning(f"No chunks from {source}")
        return

    logger.info(f"Ingesting {source}: {len(chunks)} chunks")

    # Generate embeddings for all chunks
    texts = [c["content"] for c in chunks]
    embeddings = await embed_texts(texts)

    async with async_session() as db:
        # Upsert document (keyed on source)
        result = await db.execute(
            text("""
                INSERT INTO kb_documents (title, source, effective_date, version, content)
                VALUES (:title, :source, :effective_date, :version, :content)
                ON CONFLICT (source) DO UPDATE SET
                    title = EXCLUDED.title,
                    effective_date = EXCLUDED.effective_date,
                    version = EXCLUDED.version,
                    content = EXCLUDED.content
                RETURNING id
            """),
            {
                "title": title,
                "source": source,
                "effective_date": effective_date,
                "version": version,
                "content": body,
            },
        )
        doc_id = str(result.scalar_one())

        # Delete old chunks for this document
        await db.execute(
            text("DELETE FROM kb_chunks WHERE document_id = :doc_id"),
            {"doc_id": doc_id},
        )

        # Insert new chunks
        for chunk, embedding in zip(chunks, embeddings):
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await db.execute(
                text("""
                    INSERT INTO kb_chunks (document_id, section, content, embedding)
                    VALUES (:doc_id, :section, :content, :embedding::vector)
                """),
                {
                    "doc_id": doc_id,
                    "section": chunk["section"],
                    "content": chunk["content"],
                    "embedding": embedding_str,
                },
            )

        await db.commit()
        logger.info(f"Ingested {source}: {len(chunks)} chunks with embeddings")


async def ingest_all():
    """Ingest all markdown files from the knowledge base directory."""
    if not KB_DIR.exists():
        logger.error(f"Knowledge base directory not found: {KB_DIR}")
        return

    md_files = sorted(KB_DIR.glob("*.md"))
    if not md_files:
        logger.error(f"No markdown files in {KB_DIR}")
        return

    logger.info(f"Ingesting {len(md_files)} KB files from {KB_DIR}")
    for filepath in md_files:
        try:
            await ingest_file(filepath)
        except Exception as e:
            logger.error(f"Failed to ingest {filepath.name}: {e}")


if __name__ == "__main__":
    asyncio.run(ingest_all())
