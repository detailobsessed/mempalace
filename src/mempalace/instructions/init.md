# MemPalace Init

Guide the user through a complete MemPalace setup. Follow each step in order,
stopping to report errors and attempt remediation before proceeding.

## Step 1: Check if mempalace is already installed

Run `mempalace status` to see if the package is already present and working.
If it runs successfully, report the current state and skip to Step 4.

## Step 2: Check prerequisites

Run `uv --version` to confirm uv is available. If uv is not found, tell the
user to install it from <https://docs.astral.sh/uv/> and stop.

## Step 3: Install mempalace

Run `uv tool install mempalace`.

If installing from a local fork, use:
`uv tool install --editable /path/to/mempalace`

### Error handling -- install failures

If `uv tool install` fails, try these fallbacks in order:

1. If the error mentions compilation failures (commonly from chromadb or its
   native dependencies):
   - On macOS: suggest `xcode-select --install`
   - On Linux: suggest `sudo apt-get install build-essential python3-dev`
   - Then retry the install command
2. If all attempts fail, report the error clearly and stop.

## Step 4: Ask for project directory

Ask the user which project directory they want to initialize with MemPalace.
Offer the current working directory as the default. Wait for their response
before continuing.

## Step 5: Initialize the palace

Run `mempalace init <dir>` where `<dir>` is the directory from Step 4.

If this fails, report the error and stop.

## Step 6: Configure the plugin

If the plugin is not already registered, run:

    claude plugin add /path/to/mempalace/.claude-plugin

This registers the MCP server, hooks, and slash commands automatically.

If this fails, report the error but continue to the next step (plugin
configuration can be done manually later).

## Step 7: Verify installation

Run `mempalace status` and confirm the output shows a healthy palace.

If the command fails or reports errors, walk the user through troubleshooting
based on the output.

## Step 8: Show next steps

Tell the user setup is complete and suggest these next actions:

- Use /mempalace:mine to start adding data to their palace
- Use /mempalace:search to query their palace and retrieve stored knowledge
