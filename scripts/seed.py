"""Database seed and setup script.

Usage:
    python -m scripts.seed [--schema] [--seed] [--all]
"""

import sys
import asyncio
from pathlib import Path
from sqlalchemy import text
from app.config import settings
from app.database import engine
from app.observability.logging import get_logger

logger = get_logger(__name__)

DB_DIR = Path(__file__).parent.parent / "db"


async def run_sql_file(filepath: Path):
    """Execute SQL statements from a file using the async database engine."""
    if not filepath.exists():
        logger.error(f"SQL file not found: {filepath}")
        return False

    logger.info(f"Executing {filepath.name}...")
    content = filepath.read_text(encoding="utf-8")

    # Adapt embedding dimension in schema.sql to match settings.EMBEDDING_DIM if needed
    if filepath.name == "schema.sql" and settings.EMBEDDING_DIM != 1536:
        content = content.replace("vector(1536)", f"vector({settings.EMBEDDING_DIM})")
        logger.info(f"Adjusted vector dimension in schema to {settings.EMBEDDING_DIM}")

    # Remove comments and empty lines for clean execution
    statements = []
    current_stmt = []
    in_function = False

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        if "$$" in line:
            in_function = not in_function

        current_stmt.append(line)

        if not in_function and stripped.endswith(";"):
            stmt_text = "\n".join(current_stmt).strip()
            if stmt_text:
                statements.append(stmt_text)
            current_stmt = []

    if current_stmt:
        stmt_text = "\n".join(current_stmt).strip()
        if stmt_text:
            statements.append(stmt_text)

    async with engine.begin() as conn:
        for stmt in statements:
            try:
                await conn.execute(text(stmt))
            except Exception as e:
                logger.warning(f"Notice on statement: {e}")

    logger.info(f"Successfully processed {filepath.name} ({len(statements)} statements)")
    return True


async def main():
    args = sys.argv[1:]
    run_schema = "--schema" in args or "--all" in args or len(args) == 0
    run_seed = "--seed" in args or "--all" in args or len(args) == 0

    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    try:
        if run_schema:
            schema_file = DB_DIR / "schema.sql"
            print(f"Running schema from {schema_file.name}...")
            await run_sql_file(schema_file)
            print("Schema initialized.")

        if run_seed:
            seed_file = DB_DIR / "seed.sql"
            print(f"Running seed from {seed_file.name}...")
            await run_sql_file(seed_file)
            print("Seed data inserted.")

        print("Database setup complete.")
    except Exception as e:
        print(f"Database error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
