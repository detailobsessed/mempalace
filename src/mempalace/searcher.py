"""
searcher.py — Find anything. Exact words.

Semantic search against the palace.
Returns verbatim text — the actual words, never summaries.
"""

import logging
from pathlib import Path

import chromadb

from .config import build_where as _build_where

logger = logging.getLogger("mempalace_mcp")


class SearchError(Exception):
    """Raised when search cannot proceed (e.g. no palace found)."""


def search(
    query: str,
    palace_path: str,
    wing: str | None = None,
    room: str | None = None,
    n_results: int = 5,
):
    """
    Search the palace. Returns verbatim drawer content.
    Optionally filter by wing (project) or room (aspect).
    """
    try:
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_collection("mempalace_drawers")
    except Exception:
        print(f"\n  No palace found at {palace_path}")
        print("  Run: mempalace init <dir> then mempalace mine <dir>")
        msg = f"No palace found at {palace_path}"
        raise SearchError(msg) from None

    # Build where filter
    where = _build_where(wing, room)

    try:
        results = col.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
            where=where,
        )

    except Exception as e:
        print(f"\n  Search error: {e}")
        msg = f"Search error: {e}"
        raise SearchError(msg) from e

    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    dists = results["distances"][0] if results["distances"] else []

    if not docs:
        print(f'\n  No results found for: "{query}"')
        return

    print(f"\n{'=' * 60}")
    print(f'  Results for: "{query}"')
    if wing:
        print(f"  Wing: {wing}")
    if room:
        print(f"  Room: {room}")
    print(f"{'=' * 60}\n")

    for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists, strict=False), 1):
        similarity = round(1 - dist, 3)
        source = Path(meta.get("source_file", "?")).name
        wing_name = meta.get("wing", "?")
        room_name = meta.get("room", "?")

        print(f"  [{i}] {wing_name} / {room_name}")
        print(f"      Source: {source}")
        print(f"      Match:  {similarity}")
        print()
        # Print the verbatim text, indented
        for line in doc.strip().split("\n"):
            print(f"      {line}")
        print()
        print(f"  {'─' * 56}")

    print()


def search_memories(query: str, palace_path: str, wing: str | None = None, room: str | None = None, n_results: int = 5) -> dict:
    """
    Programmatic search — returns a dict instead of printing.
    Used by the MCP server and other callers that need data.
    """
    try:
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_collection("mempalace_drawers")
    except Exception:
        logger.exception("No palace found at %s", palace_path)
        return {
            "error": "No palace found",
            "hint": "Run: mempalace init <dir> && mempalace mine <dir>",
        }

    # Build where filter
    where = _build_where(wing, room)

    try:
        results = col.query(
            query_texts=[query],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
            where=where,
        )
    except Exception as e:
        return {"error": f"Search error: {e}"}

    docs = results["documents"][0] if results["documents"] else []
    metas = results["metadatas"][0] if results["metadatas"] else []
    dists = results["distances"][0] if results["distances"] else []

    hits = []
    for doc, meta, dist in zip(docs, metas, dists, strict=False):
        hits.append({
            "text": doc,
            "wing": meta.get("wing", "unknown"),
            "room": meta.get("room", "unknown"),
            "source_file": Path(meta.get("source_file", "?")).name,
            "similarity": round(1 - dist, 3),
        })

    return {
        "query": query,
        "filters": {"wing": wing, "room": room},
        "results": hits,
    }
