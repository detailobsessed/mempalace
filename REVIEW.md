# Review Guidelines

This is an experimental fork of [milla-jovovich/mempalace](https://github.com/milla-jovovich/mempalace). These guidelines help reviewers distinguish intentional fork decisions from actual bugs.

## Critical Areas

- All changes to `src/mempalace/mcp_server.py` must be reviewed for input sanitization and ChromaDB interaction safety.
- Changes to `sanitize_name`, `sanitize_content`, `sanitize_kg_value` in `src/mempalace/config.py` are security-sensitive — these guard all user input.
- `src/mempalace/knowledge_graph.py` — JSON file I/O and data integrity for the knowledge graph.
- Hook scripts in `.claude-plugin/hooks/` and `src/mempalace/hooks_cli.py` — stdout protocol must output single-line JSON; any print/logging to stdout breaks Claude Code integration.
- **Markdown drift** — `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, and skill/command docs in `.claude-plugin/` go stale quickly as code changes. Flag any PR where code behavior changes but related documentation is not updated.

## Conventions

- Python >= 3.14 is required. PEP 758 unparenthesized except syntax (`except X, Y:` without parens) is valid and intentional. Do not flag as syntax error.
- `~/.mempalace/` is the metadata root (hook state, KG, identity, config). `palace_path` is only for ChromaDB data. This split is deliberate.
- `check_same_thread=False` on SQLite connections is safe — the MCP server is single-threaded stdio.
- Idempotent drawer IDs using content hashing are by design (dedup), not a bug.
- `uv` is the package manager (`uv run`, `uv sync`, `uv tool install`). Not pip.
- `poe` (poethepoet) is the task runner (`poe test`, `poe check`, `poe lint`).
- Hook scripts use `mempalace` (not `python3 -m mempalace`) because we install via `uv tool`.
- Stop hook blocks every 15 messages with an auto-save prompt. Auto-ingest (`MEMPAL_DIR`) runs in the background.

## Ignore

- Auto-generated files: `.copier-answers.yml`, `uv.lock`, `.python-version`
- Pyright `reportMissingImports` for `chromadb`, `pytest`, etc. — resolved at runtime via uv virtualenv.
- `_typos.toml` entries are false-positive overrides for the typos spell checker.
- Lock files and editor configs (`.editorconfig`, `.markdownlint.yaml`, `.lychee.toml`).

## Performance

- Precompact hook runs `subprocess.run` with `timeout=60` for MEMPAL_DIR mining. This is the maximum blocking time before the hook returns.
- ChromaDB `PersistentClient` is cached at module level in `mcp_server.py`. Do not create new clients per request.
- Stop hook's `_maybe_auto_ingest()` stays async (Popen) — fire-and-forget background mining of `MEMPAL_DIR`.
