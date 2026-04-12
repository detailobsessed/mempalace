# MemPalace Claude Code Plugin

A Claude Code plugin that gives your AI a persistent memory system. Mine projects and conversations into a searchable palace backed by ChromaDB, with 19 MCP tools, auto-save hooks, and 5 guided skills.

## Prerequisites

- Python 3.14+
- uv package manager

## Installation

### Local Clone

```bash
uv tool install --editable /path/to/mempalace
claude plugin add /path/to/mempalace/.claude-plugin
```

### Or use the setup script

```bash
python scripts/setup_claude.py
```

## Post-Install Setup

After installing the plugin, run the init command to complete setup:

```
/mempalace:init
```

## Available Slash Commands

| Command | Description |
| --- | --- |
| `/mempalace:help` | Show available tools, skills, and architecture |
| `/mempalace:init` | Set up MemPalace -- install, configure MCP, onboard |
| `/mempalace:search` | Search your memories across the palace |
| `/mempalace:mine` | Mine projects and conversations into the palace |
| `/mempalace:status` | Show palace overview -- wings, rooms, drawer counts |

## Hooks

MemPalace registers three hooks that run automatically:

- **SessionStart** -- Checks for missing identity and project config, surfacing setup hints.
- **Stop** -- Saves conversation context every 15 messages.
- **PreCompact** -- Preserves important memories before context compaction.

Set the `MEMPAL_DIR` environment variable to a directory path to automatically run `mempalace mine` on that directory during each save trigger.

## Local Development

When developing the plugin locally, use `--plugin-dir` to load it from your working tree instead of the installed cache:

```bash
claude --plugin-dir /path/to/mempalace/.claude-plugin
```

This takes precedence over the installed marketplace version. Changes are picked up on next session start. To pick up changes mid-session, run `/reload-plugins`.

The plugin version in `plugin.json` is only bumped on intentional plugin releases — not on every library version bump.

## Fork Divergences

This fork (detailobsessed/mempalace) differs from upstream (milla-jovovich/mempalace) in:

- **Source layout**: `src/mempalace/` (src layout) instead of `mempalace/` (flat layout)
- **MCP entry point**: `mempalace-mcp-server` (uv tool entry point) instead of `python3 -m mempalace.mcp_server`
- **Package manager**: `uv` instead of `pip`

## MCP Server

The plugin automatically configures a local MCP server with 19 tools for storing, searching, and managing memories. No manual MCP setup is required.
