#!/usr/bin/env bash
# Ingest knowledge base documents into pgvector
set -e
python -m app.rag.ingest
