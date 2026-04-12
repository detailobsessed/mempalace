# Code Style

- Python 3.14 — PEP 758 `except A, B:` syntax is valid, don't parenthesize
- No explicit type hints convention enforced but present in some files
- `ruff` for linting and formatting
- `ty` for type checking
- Minimal docstrings, code is self-documenting
- argparse for CLI, no click/typer
- Private functions prefixed with `_`
- Fork of milla-jovovich/mempalace; trunk branch is `bleeding`
- Conventional commits required (feat:, fix:, chore:, etc.)
- chromadb PersistentClient instances must be `.close()`d after use in tests
