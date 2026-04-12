"""
repair.py — Scan, prune corrupt entries, and rebuild HNSW index.

When ChromaDB's HNSW index accumulates duplicate entries (from repeated
add() calls with the same ID), link_lists.bin can grow unbounded —
terabytes on large palaces — eventually causing segfaults.

Three operations:

  scan    — find every corrupt/unfetchable ID in the palace
  prune   — delete only the corrupt IDs (surgical)
  rebuild — extract all drawers, delete the collection, recreate with
            correct HNSW settings, and upsert everything back

Usage (standalone):
    python -m mempalace.repair scan [--wing X]
    python -m mempalace.repair prune --confirm
    python -m mempalace.repair rebuild

Usage (from CLI):
    mempalace repair scan [--wing X]
    mempalace repair prune --confirm
    mempalace repair rebuild
"""

from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

import chromadb

COLLECTION_NAME = "mempalace_drawers"


def _get_palace_path() -> str:
    """Resolve palace path from config."""
    try:
        from .config import MempalaceConfig

        return MempalaceConfig().palace_path
    except Exception:
        return str(Path.home() / ".mempalace" / "palace")


def _paginate_ids(col, where=None) -> list[str]:
    """Pull all IDs in a collection using pagination."""
    ids: list[str] = []
    page = 1000
    offset = 0
    while True:
        try:
            r = col.get(where=where, include=[], limit=page, offset=offset)
        except Exception:
            try:
                r = col.get(where=where, include=[], limit=page)
                new_ids = [i for i in r["ids"] if i not in set(ids)]
                if not new_ids:
                    break
                ids.extend(new_ids)
                offset += len(new_ids)
                continue
            except Exception:
                break
        n = len(r["ids"]) if r["ids"] else 0
        if n == 0:
            break
        ids.extend(r["ids"])
        offset += n
        if n < page:
            break
    return ids


def scan_palace(
    palace_path: str | None = None,
    only_wing: str | None = None,
) -> tuple[set[str], set[str]]:
    """Scan the palace for corrupt/unfetchable IDs.

    Probes in batches of 100, falls back to per-ID on failure.
    Writes corrupt_ids.txt to the palace directory for the prune step.

    Returns (good_set, bad_set).
    """
    palace_path = palace_path or _get_palace_path()
    print(f"\n  Palace: {palace_path}")
    print("  Loading...")

    client = chromadb.PersistentClient(path=palace_path)
    try:
        col = client.get_collection(COLLECTION_NAME)

        where = {"wing": only_wing} if only_wing else None
        total = col.count()
        print(f"  Collection: {COLLECTION_NAME}, total: {total:,}")
        if only_wing:
            print(f"  Scanning wing: {only_wing}")

        print("\n  Step 1: listing all IDs...")
        t0 = time.time()
        all_ids = _paginate_ids(col, where=where)
        print(f"  Found {len(all_ids):,} IDs in {time.time() - t0:.1f}s\n")

        if not all_ids:
            print("  Nothing to scan.")
            return set(), set()

        print("  Step 2: probing each ID (batches of 100)...")
        t0 = time.time()
        good_set, bad_set = _probe_ids(col, all_ids, t0)

        print(f"\n  Scan complete in {time.time() - t0:.1f}s")
        print(f"  GOOD: {len(good_set):,}")
        print(f"  BAD:  {len(bad_set):,}  ({len(bad_set) / max(len(all_ids), 1) * 100:.1f}%)")

        bad_file = Path(palace_path) / "corrupt_ids.txt"
        bad_file.write_text("\n".join(sorted(bad_set)) + "\n" if bad_set else "", encoding="utf-8")
        print(f"\n  Bad IDs written to: {bad_file}")
    finally:
        client.close()
    return good_set, bad_set


def _probe_ids(col, all_ids: list[str], t0: float) -> tuple[set[str], set[str]]:
    """Probe IDs in batches, falling back to per-ID on failure."""
    good_set: set[str] = set()
    bad_set: set[str] = set()
    batch = 100

    for i in range(0, len(all_ids), batch):
        chunk = all_ids[i : i + batch]
        try:
            r = col.get(ids=chunk, include=["documents"])
            good_set.update(r["ids"])
            for mid in chunk:
                if mid not in good_set:
                    bad_set.add(mid)
        except Exception:
            for sid in chunk:
                try:
                    r = col.get(ids=[sid], include=["documents"])
                    if r["ids"]:
                        good_set.add(sid)
                    else:
                        bad_set.add(sid)
                except Exception:
                    bad_set.add(sid)

        if (i // batch) % 50 == 0:
            elapsed = time.time() - t0
            rate = (i + batch) / max(elapsed, 0.01)
            eta = (len(all_ids) - i - batch) / max(rate, 0.01)
            print(f"    {i + batch:>6}/{len(all_ids):>6}  good={len(good_set):>6}  bad={len(bad_set):>6}  eta={eta:.0f}s")

    return good_set, bad_set


def prune_corrupt(palace_path: str | None = None, *, confirm: bool = False) -> None:
    """Delete corrupt IDs listed in corrupt_ids.txt."""
    palace_path = palace_path or _get_palace_path()
    bad_file = Path(palace_path) / "corrupt_ids.txt"

    if not bad_file.exists():
        print("  No corrupt_ids.txt found — run scan first.")
        return

    bad_ids = [line.strip() for line in bad_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"  {len(bad_ids):,} corrupt IDs queued for deletion")

    if not confirm:
        print("\n  DRY RUN — no deletions performed.")
        print("  Re-run with --confirm to actually delete.")
        return

    client = chromadb.PersistentClient(path=palace_path)
    try:
        col = client.get_collection(COLLECTION_NAME)
        before = col.count()
        print(f"  Collection size before: {before:,}")

        deleted, failed = _delete_ids(col, bad_ids)

        after = col.count()
        print(f"\n  Deleted: {deleted:,}")
        print(f"  Failed:  {failed:,}")
        print(f"  Collection size: {before:,} → {after:,}")
    finally:
        client.close()


def _delete_ids(col, bad_ids: list[str]) -> tuple[int, int]:
    """Delete IDs in batches, falling back to per-ID on failure."""
    batch = 100
    deleted = 0
    failed = 0
    for i in range(0, len(bad_ids), batch):
        chunk = bad_ids[i : i + batch]
        try:
            col.delete(ids=chunk)
            deleted += len(chunk)
        except Exception:
            for sid in chunk:
                try:
                    col.delete(ids=[sid])
                    deleted += 1
                except Exception:
                    failed += 1
        if (i // batch) % 20 == 0:
            print(f"    deleted {deleted}/{len(bad_ids)}  (failed: {failed})")
    return deleted, failed


def rebuild_index(palace_path: str | None = None) -> None:
    """Rebuild the HNSW index from scratch.

    1. Extract all drawers via ChromaDB get()
    2. Back up ONLY chroma.sqlite3 (not the bloated HNSW files)
    3. Delete and recreate the collection with hnsw:space=cosine
    4. Upsert all drawers back
    """
    palace_path = palace_path or _get_palace_path()
    palace = Path(palace_path)

    if not palace.is_dir():
        print(f"\n  No palace found at {palace_path}")
        return

    print(f"\n{'=' * 55}")
    print("  MemPalace Repair — Index Rebuild")
    print(f"{'=' * 55}\n")
    print(f"  Palace: {palace_path}")

    client = chromadb.PersistentClient(path=palace_path)
    try:
        col = client.get_collection(COLLECTION_NAME)
        total = col.count()
    except Exception as e:
        print(f"  Error reading palace: {e}")
        print("  Palace may need to be re-mined from source files.")
        client.close()
        return

    print(f"  Drawers found: {total}")

    if total == 0:
        print("  Nothing to repair.")
        client.close()
        return

    all_ids, all_docs, all_metas = _extract_all_drawers(col, total)

    _backup_sqlite(palace)

    _refile_drawers(client, all_ids, all_docs, all_metas)
    client.close()


def _extract_all_drawers(col, total: int) -> tuple[list[str], list[str], list[dict]]:
    """Extract all drawers from a collection in batches."""
    print("\n  Extracting drawers...")
    batch_size = 5000
    all_ids: list[str] = []
    all_docs: list[str] = []
    all_metas: list[dict] = []
    offset = 0
    while offset < total:
        batch = col.get(limit=batch_size, offset=offset, include=["documents", "metadatas"])
        if not batch["ids"]:
            break
        all_ids.extend(batch["ids"])
        all_docs.extend(batch["documents"])
        all_metas.extend(batch["metadatas"])
        offset += len(batch["ids"])
    print(f"  Extracted {len(all_ids)} drawers")
    return all_ids, all_docs, all_metas


def _backup_sqlite(palace: Path) -> None:
    """Back up chroma.sqlite3 (not the bloated HNSW files)."""
    sqlite_path = palace / "chroma.sqlite3"
    if sqlite_path.exists():
        backup_path = palace / "chroma.sqlite3.backup"
        print(f"  Backing up chroma.sqlite3 ({sqlite_path.stat().st_size / 1e6:.0f} MB)...")
        shutil.copy2(sqlite_path, backup_path)
        print(f"  Backup: {backup_path}")


def _refile_drawers(client, all_ids: list[str], all_docs: list[str], all_metas: list[dict]) -> None:
    """Delete and recreate the collection, then upsert all drawers back."""
    print("  Rebuilding collection with hnsw:space=cosine...")
    client.delete_collection(COLLECTION_NAME)
    new_col = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    batch_size = 5000
    filed = 0
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i : i + batch_size]
        batch_docs = all_docs[i : i + batch_size]
        batch_metas = all_metas[i : i + batch_size]
        new_col.upsert(documents=batch_docs, ids=batch_ids, metadatas=batch_metas)
        filed += len(batch_ids)
        print(f"  Re-filed {filed}/{len(all_ids)} drawers...")

    print(f"\n  Repair complete. {filed} drawers rebuilt.")
    print("  HNSW index is now clean with cosine distance metric.")
    print(f"\n{'=' * 55}\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="MemPalace repair tools")
    p.add_argument("command", choices=["scan", "prune", "rebuild"])
    p.add_argument("--palace", default=None, help="Palace directory path")
    p.add_argument("--wing", default=None, help="Scan only this wing")
    p.add_argument("--confirm", action="store_true", help="Actually delete corrupt IDs")
    args = p.parse_args()

    path = str(Path(args.palace).expanduser()) if args.palace else None

    if args.command == "scan":
        scan_palace(palace_path=path, only_wing=args.wing)
    elif args.command == "prune":
        prune_corrupt(palace_path=path, confirm=args.confirm)
    elif args.command == "rebuild":
        rebuild_index(palace_path=path)
