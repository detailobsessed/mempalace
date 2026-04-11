# Development Commands

```bash
poe test          # Run tests (excluding slow)
poe test-cov      # Tests with coverage
poe lint          # Ruff check
poe format        # Ruff format
poe typecheck     # ty type checking
poe check         # Lint + typecheck in parallel
poe fix           # Auto-fix + format

uv run pytest tests/ -v                # All tests
uv run pytest tests/test_file.py -v    # Single file
uv run pytest -k "pattern" -v          # Pattern match
```

## System commands (Darwin)

- `git`, `ls`, `grep`, `find` - standard unix
- `which`, `uv`, `poe` available on PATH
