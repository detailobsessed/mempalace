<div align="center">

<img src="assets/mempalace_logo.png" alt="MemPalace" width="280">

# MemPalace — `detailobsessed` fork

### Production-hardened fork of [milla-jovovich/mempalace](https://github.com/milla-jovovich/mempalace)

[![Python][python-shield]][python-link]
[![License][license-shield]][license-link]
[![CI][ci-shield]][ci-link]

</div>

---

## Table of contents

- [Why this fork?](#why-this-fork)
- [What changed](#what-changed)
- [Quick start](#quick-start)
- [Tips](#tips)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

---

## Why this fork?

Upstream MemPalace is awesome but a bit of a rough diamond at launch (as of early April 2026). I wanted more robustness and confidence, so I:

- Applied my [copier-uv-bleeding](https://github.com/detailobsessed/copier-uv-bleeding) template — modern Python boilerplate with comprehensive ruff rules, git hooks, formatting, type checking, CI, docs, the works
- Wrote a comprehensive test suite with coverage enforcement
- Fixed bugs and hardened the code as I went

Everything else — the palace architecture, AAAK dialect, MCP server, knowledge graph — is upstream's work. [Read the upstream README](https://github.com/milla-jovovich/mempalace#readme) for the full story.

---

## What changed

### Engineering infrastructure

- **`uv_build` + src layout** — proper packaging, editable installs, clean isolation
- **Test suite** with coverage enforcement in pre-push hooks
- **GitHub Actions CI** — lint + typecheck + test on every push, docs build
- **Pre-commit/pre-push hooks** via prek: ruff, ty, typos, pytest-testmon (incremental)
- **mkdocs-material docs** with API reference auto-generated from docstrings

### New features

- **`scripts/setup_claude.py`** — one-shot Claude Code integration: installs the fork as an editable uv tool, configures MCP server, sets up hooks
- **Auto-save hooks** (`hooks/`) — saves every 15 messages, emergency-saves before context compression
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
uv run scripts/setup_claude.py
```

For usage, commands, and architecture — see the [upstream README](https://github.com/milla-jovovich/mempalace#readme).

> **Tip:** Set `"autoMemoryEnabled": false` in `~/.claude/settings.json` to let MemPalace handle all memory instead of Claude's built-in system. See [Tips](#tips) for details.

> **Tip:** You can start using MemPalace immediately — `mempalace init` and `mempalace mine` enrich your palace but aren't required. See [Tips](#tips).

---

## Tips

### Disable Claude's built-in memory

Claude Code has a built-in memory system (`CLAUDE.md` auto-edits). When using MemPalace, this competes for the same job. Adding `"autoMemoryEnabled": false` to `~/.claude/settings.json` disables it, letting MemPalace be the single source of truth for long-term memory:

```json
{
  "autoMemoryEnabled": false
}
```

The installer script (`scripts/setup_claude.py`) already configures MCP and hooks — this setting is a recommended complement.

### No init or mine required

`mempalace init` and `mempalace mine` pre-populate the palace with project structure and file content, but they aren't prerequisites. The MCP tools — knowledge graph (`mempalace_kg_*`), diary (`mempalace_diary_*`), drawers, search — all work on an empty palace. MemPalace builds up organically as your agent stores facts and writes diary entries during sessions.

Running `init` and `mine` is still valuable when you want to seed the palace with existing project context upfront, but you can start getting value from MemPalace without them.

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
