# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is MemPalace

MemPalace is a local-first memory system for AI agents. It ingests project files or conversation exports into a ChromaDB-backed "palace" organized by wings (projects/domains) and rooms (topics within a wing). No API key required — all processing is local.

Key concepts:

- **Palace**: The ChromaDB database at `~/.mempalace/palace` (configurable)
- **Wings**: Top-level categories (project names or topic domains like `wing_code`, `wing_team`)
- **Rooms**: Named sub-topics within wings (e.g., `backend`, `decisions`, `planning`)
- **Drawers**: Individual content chunks stored in ChromaDB with metadata
- **Halls**: Corridor groupings (hall_facts, hall_events, hall_discoveries, etc.)
- **Tunnels**: Rooms that span multiple wings, connecting different domains
- **AAAK Dialect**: A compressed symbolic memory format (~30x compression) readable by any LLM without decoding

## Project Structure

Source code lives in `src/mempalace/` (src layout). Tests in `tests/`. Uses `uv` for package management, `ruff` for linting/formatting, `ty` for type checking, `pytest` for testing, and `poethepoet` (poe) as task runner.

## Architecture

### 4-Layer Memory Stack (`src/mempalace/layers.py`)

- **Layer 0** (~100 tokens): Identity from `~/.mempalace/identity.txt`
- **Layer 1** (~500-800 tokens): Auto-generated essential story from top palace drawers
- **Layer 2** (~200-500 tokens each): On-demand wing/room filtered retrieval
- **Layer 3** (unlimited): Full semantic search via ChromaDB

### Two Ingest Paths

1. **Project mining** (`miner.py`): Reads `mempalace.yaml` from project dir, routes files to rooms by folder path > filename > keyword scoring
2. **Conversation mining** (`convo_miner.py`): Normalizes chat exports (Claude, ChatGPT, Slack), chunks by exchange pairs (Q+A = one unit), routes by topic keywords

### MCP Server (`mcp_server.py`)

JSON-RPC stdio server providing read/write tools for Claude Code integration. Install with: `claude mcp add mempalace -- python /path/to/mcp_server.py`. Includes knowledge graph tools (`mempalace_kg_*`), diary tools (`mempalace_diary_*`), graph traversal (`mempalace_traverse`, `mempalace_find_tunnels`), and CRUD on drawers.

### Knowledge Graph (`knowledge_graph.py`)

Subject-predicate-object triples with temporal validity (valid_from/valid_to dates). Stored in `~/.mempalace/knowledge_graph.json`. Supports entity queries, timeline views, and fact invalidation.

### AAAK Dialect (`dialect.py`)

Compresses text into symbolic format: entity codes (3-letter uppercase), emotion markers, topic keywords, importance flags (ORIGIN, CORE, PIVOT, GENESIS, DECISION, TECHNICAL, SENSITIVE). Can compress from plain text or structured zettel JSON.

## Development Commands

```bash
# Task runner (preferred)
poe test                                # Run tests (excluding slow)
poe test-cov                            # Tests with coverage report
poe lint                                # Ruff check
poe format                              # Ruff format
poe typecheck                           # ty type checking
poe check                               # Lint + typecheck in parallel
poe fix                                 # Auto-fix + format
poe docs                                # Serve documentation locally

# Direct commands
uv run pytest tests/ -v                 # Run all tests
uv run pytest tests/test_dialect.py -v  # Run a single test file
uv run pytest -k "test_compress" -v     # Run tests matching a pattern
```

## CLI Commands

```bash
mempalace init <dir>                    # Detect rooms from folder structure + entities
mempalace mine <dir>                    # Mine project files into palace
mempalace mine <dir> --mode convos      # Mine conversation exports
mempalace search "query"                # Semantic search
mempalace wake-up                       # Show L0+L1 context (~600-900 tokens)
mempalace status                        # Show wing/room/drawer counts
mempalace compress --wing <name>        # Compress drawers with AAAK Dialect
mempalace split <dir>                   # Split mega-files into per-session files
mempalace hook run --hook <name> --harness <harness>  # Run a hook handler (stop, precompact)
mempalace instructions <name>           # Output skill instructions to stdout
mempalace mcp                           # Show MCP setup command for your AI client
```

## Configuration

Priority: env vars (`MEMPALACE_PALACE_PATH`) > config file (`~/.mempalace/config.json`) > defaults. Config manages palace path, collection name, topic wings, hall keywords, and people map.

## Dependencies

- `chromadb` — vector database for drawer storage and semantic search
- `pyyaml` — reading `mempalace.yaml` project configs

## Repository

- **Fork**: `detailobsessed/mempalace` (origin)
- **Upstream**: `milla-jovovich/mempalace` (upstream)
- **Trunk branch**: `bleeding` (template-enhanced development)
- **Main branch**: `main` (kept clean for upstream PRs)
