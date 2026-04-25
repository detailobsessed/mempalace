# detailobsessed/local-patches

This branch tracks local patches applied on top of upstream `main` that have not yet been merged upstream.

## Why this branch exists

The `mempalace` CLI is installed as a uv editable tool pointing at this repo:

```
uv tool install --editable /Users/ismar/repos/mempalace
```

This means the installed binary at `~/.local/bin/mempalace` (used by the Claude Code plugin hooks) runs code directly from this repo. Keeping patches on this branch lets us:

- Stay safe when running `git pull upstream main` (rebase our patches on top)
- Know exactly what we've diverged from upstream
- Eventually stop using this branch once all patches are merged upstream

## Upgrading

When upstream releases a new version:

```sh
cd ~/repos/mempalace
git fetch upstream
git rebase upstream/main
# resolve any conflicts, then push
git push origin detailobsessed/local-patches --force-with-lease
```

Then reinstall to pick up the new upstream Python deps (if any):

```sh
uv tool install --editable /Users/ismar/repos/mempalace --reinstall
```

## Verifying the install uses this repo (not PyPI)

Three layers of proof:

**1. `uv-receipt.toml`** records the editable path:
```
~/.local/share/uv/tools/mempalace/uv-receipt.toml
→ requirements = [{ name = "mempalace", editable = "/Users/ismar/repos/mempalace" }]
```

**2. The `.pth` file** is what Python actually reads at import time:
```
~/.local/share/uv/tools/mempalace/lib/python3.14/site-packages/_editable_impl_mempalace.pth
→ /Users/ismar/repos/mempalace
```

**3. Smoke-test** — inspect a signature that only exists in our patched code:
```sh
/Users/ismar/.local/share/uv/tools/mempalace/bin/python3 -c \
  "from mempalace.backends.chroma import quarantine_stale_hnsw; import inspect; print(inspect.signature(quarantine_stale_hnsw))"
# Expected: (..., max_link_lists_bytes: int = 5368709120) — not present in PyPI 3.3.3
```

## Patches

### fix: quarantine bloated/stale HNSW segments before opening PersistentClient

**Files:** `mempalace/backends/chroma.py`, `mempalace/repair.py`

**Problem:** ChromaDB's HNSW index accumulates duplicate neighbor entries in `link_lists.bin` when the same document IDs are upserted repeatedly. The file grows to terabytes (sparse on disk but still traversed by the Rust graph walker), causing a SIGSEGV in the ChromaDB Rust extension when `PersistentClient` opens the palace.

The existing `quarantine_stale_hnsw()` function in `chroma.py` was never called in production code — only in tests.

**Fix:**
1. Added `max_link_lists_bytes` parameter (default 5 GB) to `quarantine_stale_hnsw()` — quarantines bloated segments regardless of mtime staleness.
2. Called `quarantine_stale_hnsw()` in `ChromaBackend._client()` before every `PersistentClient` construction — auto-heals on next open.
3. Called `quarantine_stale_hnsw()` at the top of `rebuild_index()` in `repair.py` — prevents `col.count()` segfault when running `mempalace repair`.

**Upstream PR:** _not yet submitted_ — consider opening one against `MemPalace/mempalace`.
