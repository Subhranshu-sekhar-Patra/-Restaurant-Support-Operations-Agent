"""Run knowledge base ingestion.

Usage:
    python -m scripts.ingest_kb
"""

import asyncio
from app.rag.ingest import ingest_all

if __name__ == "__main__":
    asyncio.run(ingest_all())
