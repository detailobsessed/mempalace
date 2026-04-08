<div align="center">

<img src="assets/mempalace_logo.png" alt="MemPalace" width="280">

# MemPalace — `detailobsessed` fork

### Production-hardened fork of [milla-jovovich/mempalace](https://github.com/milla-jovovich/mempalace)

[![Python][python-shield]][python-link]
[![License][license-shield]][license-link]
[![CI][ci-shield]][ci-link]

</div>

---

## Why this fork?

Upstream MemPalace is a great idea with a working prototype. This fork makes it **shippable**: tested, typed, packaged, and CI-enforced.

| &nbsp; | Upstream | This fork |
| --- | --- | --- |
| **Tests** | None | 568 tests, 86% coverage |
| **Type checking** | None | ty — 0 errors |
| **Packaging** | No `pyproject.toml` | uv + src layout, installable as editable tool |
| **CI** | None | GitHub Actions (lint, typecheck, test, docs, release) |
| **Pre-commit hooks** | None | ruff, ty, typos, pytest, secret detection |
| **Docs site** | None | mkdocs-material with API reference |
| **License** | Apache 2.0 | MIT |

Everything else — the palace architecture, AAAK dialect, MCP server, knowledge graph, benchmarks — is upstream's work. [Read the upstream README](https://github.com/milla-jovovich/mempalace#readme) for the full story.

---

## What we changed

### Engineering infrastructure (from zero)

- **`pyproject.toml`** — proper Python packaging with `uv_build`, dependency pinning (`chromadb>=1.5.6`), `py.typed` marker
- **src layout** — `mempalace/` → `src/mempalace/` for clean install isolation
- **568 tests** across 21 test files covering all modules: dialect, layers, searcher, miner, convo_miner, MCP server, knowledge graph, entity detection, normalize, spellcheck, CLI, split, config, onboarding, room detection
- **86% branch coverage** enforced in CI with `--cov-fail-under=85`
- **GitHub Actions CI** — lint + typecheck + test on every push, docs build, automated releases
- **Pre-commit/pre-push hooks** via prek: ruff check+format, ty type checking, typos, pytest-testmon (incremental), pytest-cov on push
- **mkdocs-material docs** with API reference auto-generated from docstrings
- **Issue templates**, PR template, dependabot, security policy, contributing guide, code of conduct

### Bug fixes

- **SQLite WAL mode** — enables concurrent reads on the knowledge graph
- **Bounded queries** — `LIMIT` caps on all unbounded ChromaDB `.get()` calls (prevents OOM on large palaces)
- **KG hardening** — entity timeline limits, consistent query caps
- **Error handling** — sanitized error responses, preserved CLI exit codes, logged tracebacks instead of crashing
- **Hook security** — sanitized `SESSION_ID` in save hook to prevent path traversal
- **Type safety** — all ChromaDB nullable returns properly guarded, kwargs dict-building replaced with explicit keyword args

### New features

- **`scripts/setup_claude.py`** — one-shot Claude Code integration: installs the fork as an editable uv tool, configures MCP server, sets up hooks
- **Auto-save hooks** (`hooks/`) — `mempal_save_hook.sh` saves every 15 messages, `mempal_precompact_hook.sh` emergency-saves before context compression
- **CLAUDE.md** — project instructions for Claude Code with dev commands, architecture overview, and CLI reference

---

## Quick start

```bash
# Install from this fork
uv tool install --editable --from git+https://github.com/detailobsessed/mempalace mempalace

# Or clone and install locally
git clone https://github.com/detailobsessed/mempalace
cd mempalace
uv sync

# One-shot Claude Code setup (MCP server + hooks)
uv run python scripts/setup_claude.py
```

For usage, commands, and architecture — see the [upstream README](https://github.com/milla-jovovich/mempalace#readme).

---

## Development

```bash
# Task runner (preferred)
poe test          # Run tests (excluding slow)
poe test-cov      # Tests with coverage report
poe lint          # Ruff check
poe format        # Ruff format
poe typecheck     # ty type checking
poe check         # Lint + typecheck in parallel
poe fix           # Auto-fix + format
poe docs          # Serve documentation locally

# Direct commands
uv run pytest tests/ -v
uv run ruff check .
uv run ty check
```

---

## Contributing

PRs welcome. All contributions must pass CI: ruff, ty (0 errors), pytest (86%+ coverage).

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT — see [LICENSE](LICENSE).

<!-- Link Definitions -->
[python-shield]: https://img.shields.io/badge/python-3.14+-7dd8f8?style=flat-square&labelColor=0a0e14&logo=python&logoColor=7dd8f8
[python-link]: https://www.python.org/
[license-shield]: https://img.shields.io/badge/license-MIT-b0e8ff?style=flat-square&labelColor=0a0e14
[license-link]: https://github.com/detailobsessed/mempalace/blob/bleeding/LICENSE
[ci-shield]: https://img.shields.io/github/actions/workflow/status/detailobsessed/mempalace/ci.yml?branch=bleeding&style=flat-square&labelColor=0a0e14&label=CI
[ci-link]: https://github.com/detailobsessed/mempalace/actions/workflows/ci.yml
