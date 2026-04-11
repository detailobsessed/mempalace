# MemPalace Project Overview

## Purpose

Local-first memory system for AI agents. Ingests project files or conversation exports into a ChromaDB-backed "palace" organized by wings (projects/domains) and rooms (topics). No API key required.

## Tech Stack

- Python 3.14, src layout (`src/mempalace/`)
- `uv` package manager, `ruff` linting/formatting, `ty` type checking, `pytest` testing
- `poethepoet` (poe) task runner
- ChromaDB for vector storage, PyYAML for config

## Repository

- Fork: `detailobsessed/mempalace`, Upstream: `milla-jovovich/mempalace`
- Trunk branch: `bleeding`, Main branch: `main` (clean for upstream PRs)

## Key Modules

- `cli.py` - CLI entry point (argparse)
- `hooks_cli.py` - Hook handlers (session-start, stop, precompact)
- `instructions_cli.py` - Skill instruction output
- `mcp_server.py` - JSON-RPC stdio MCP server
- `miner.py` / `convo_miner.py` - Project and conversation mining
- `layers.py` - 4-layer memory stack
- `knowledge_graph.py` - Subject-predicate-object triples
- `dialect.py` - AAAK compressed symbolic format
- `palace_graph.py` - Graph traversal
- `searcher.py` - Semantic search
