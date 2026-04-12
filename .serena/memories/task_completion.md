# On Task Completion

1. Run `poe check` (lint + typecheck)
2. Run `poe test` (tests excluding slow)
3. Verify changes don't break existing functionality
4. Make changes first, then create branch with `git add -A && spice branch create <name> -m "<message>"`
5. Never stash before `spice bc` — just add and branch directly
6. Use `spice stack submit` to push; use `--force` if needed after restack
7. Linear issues are tracked — update status when starting/completing work
