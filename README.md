<div align="center">

<img src="assets/mempalace_logo.png" alt="MemPalace" width="280">

# MemPalace — `detailobsessed` fork

### Experimental fork of [milla-jovovich/mempalace](https://github.com/milla-jovovich/mempalace)

[![Python][python-shield]][python-link]
[![License][license-shield]][license-link]
[![CI][ci-shield]][ci-link]

</div>

---

## What is this?

This is an **experimental fork** of [milla-jovovich/mempalace](https://github.com/milla-jovovich/mempalace) — a local-first memory system for AI agents. All credit for the core architecture (palace metaphor, AAAK dialect, MCP server, knowledge graph) goes to the upstream project.

This fork is a learning playground where we:

- Experiment with modern Python tooling (uv, ruff, ty, prek)
- Try ideas like auto-save hooks, Claude Code plugin packaging, and Python 3.14 features
- Occasionally contribute improvements back upstream

**If you want MemPalace for real use, start with [upstream](https://github.com/milla-jovovich/mempalace).** This fork may diverge, break, or take experimental directions that don't suit general use.

---

## What's different here

### Tooling experiments

- **`uv_build` + src layout** — proper packaging with editable installs
- **prek** — pre-commit/pre-push hooks: ruff, ty, typos, pytest-testmon (incremental)
- **copier-uv-bleeding template** — opinionated boilerplate for modern Python projects

### Improvements to upstream

- **Hook enhancements** — silent background transcript mining instead of blocking (avoids MCP disconnects), config opt-out for auto-save, visible status messages during hook execution
- **Python 3.14** — PEP 758 bare-except syntax, timezone-aware timestamps, type annotations
- **Code quality** — extracted helpers, defensive config loading, hardened input validation

---

## Quick start

```bash
# Install from this fork
uv tool install --editable --from git+https://github.com/detailobsessed/mempalace mempalace

# Or clone and install locally
git clone https://github.com/detailobsessed/mempalace
cd mempalace
uv sync
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

PRs welcome. All contributions must pass CI: ruff, ty (0 errors), pytest with coverage threshold.

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
