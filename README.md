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

### Tooling & infrastructure

- **`uv_build` + src layout** — proper packaging with editable installs
- **prek** — pre-commit/pre-push hooks: ruff, ty, typos, pytest-testmon (incremental)
- **copier-uv-bleeding template** — opinionated boilerplate for modern Python projects
- **Python 3.14** — PEP 758 bare-except syntax, timezone-aware timestamps, type annotations
- **Independent versioning** — python-semantic-release for the CLI/library (from conventional commits), manual bumps for the Claude Code plugin. A prek hook guards against plugin content changes without a version bump.
- **Version reset** — this fork starts at `v0.0.1`, independent of upstream's version numbering

### Behavioral changes from upstream

- **Synchronous hook mining** — Stop hook runs transcript mining synchronously so Claude Code's `statusMessage` spinner is visible during saves (upstream used fire-and-forget background processes)
- **Auto-save opt-out** — Stop hook auto-save can be disabled via `~/.mempalace/config.json` (`stop_hook.auto_save: false`)
- **Hook log viewer** — `mempalace hook logs [-n N] [-f]` command to tail hook execution logs
- **Code quality** — extracted helpers, defensive config loading, hardened input validation

---

## Installation

MemPalace has two components: a **Python package** (the CLI and MCP server) and a **Claude Code plugin** (hooks, skills, commands).

### 1. Python package

```bash
# Install from this fork
uv tool install --from git+https://github.com/detailobsessed/mempalace mempalace

# Or clone and install locally for development
git clone https://github.com/detailobsessed/mempalace
cd mempalace
uv sync                                    # install dependencies
uv tool install --editable .               # install CLI as mempalace on PATH
```

### 2. Claude Code plugin

In Claude Code, add the marketplace and install:

```
/install-plugin detailobsessed/mempalace
```

This registers the plugin marketplace and installs hooks (Stop, PreCompact), skills, and the MCP server.

### Updating

Both components pull from the `bleeding` branch (this fork's trunk). Push your changes there first, then:

```bash
# Update the Python package
uv tool upgrade mempalace

# Update the Claude Code plugin (in Claude Code)
/plugin
```

The plugin has `autoUpdate: true` so it checks for updates on session start, but `/plugin` forces an immediate check.

### Verify

```bash
mempalace status          # Palace overview
mempalace hook logs -n 5  # Recent hook activity
```

For usage, commands, and architecture — see the [upstream README](https://github.com/milla-jovovich/mempalace#readme).

---

## Development

```bash
# Local setup — required to test CLI and MCP server changes
uv sync                              # install dependencies
uv tool install --editable . --force # point mempalace + mempalace-mcp-server at local source

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

After editing MCP server code, reload the plugin in Claude Code (`/reload-plugins`) to pick up changes.

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
