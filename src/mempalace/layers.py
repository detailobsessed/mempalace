"""
layers.py — 4-Layer Memory Stack for mempalace
===================================================

Load only what you need, when you need it.

    Layer 0: Identity       (~100 tokens)   — Always loaded. "Who am I?"
    Layer 1: Essential Story (~500-800)      — Always loaded. Top moments from the palace.
    Layer 2: On-Demand      (~200-500 each)  — Loaded when a topic/wing comes up.
    Layer 3: Deep Search    (unlimited)      — Full ChromaDB semantic search.

Wake-up cost: ~600-900 tokens (L0+L1). Leaves 95%+ of context free.

Reads directly from ChromaDB (mempalace_drawers)
and ~/.mempalace/identity.txt.
"""

import contextlib
import operator
import sys
from collections import defaultdict
from pathlib import Path

import chromadb

from .config import MempalaceConfig


def _build_where(wing: str | None, room: str | None) -> dict | None:
    """Build a ChromaDB where filter from optional wing/room."""
    if wing and room:
        return {"$and": [{"wing": wing}, {"room": room}]}
    if wing:
        return {"wing": wing}
    if room:
        return {"room": room}
    return None


# ---------------------------------------------------------------------------
# Layer 0 — Identity
# ---------------------------------------------------------------------------


class Layer0:
    """
    ~100 tokens. Always loaded.
    Reads from ~/.mempalace/identity.txt — a plain-text file the user writes.

    Example identity.txt:
        I am Atlas, a personal AI assistant for Alice.
        Traits: warm, direct, remembers everything.
        People: Alice (creator), Bob (Alice's partner).
        Project: A journaling app that helps people process emotions.
    """

    def __init__(self, identity_path: str | None = None):
        if identity_path is None:
            identity_path = str(Path("~/.mempalace/identity.txt").expanduser())
        self.path = identity_path
        self._text = None

    def render(self) -> str:
        """Return the identity text, or a sensible default."""
        if self._text is not None:
            return self._text

        if Path(self.path).exists():
            self._text = Path(self.path).read_text(encoding="utf-8").strip()
        else:
            self._text = "## L0 — IDENTITY\nNo identity configured. Create ~/.mempalace/identity.txt"

        return self._text

    def token_estimate(self) -> int:
        return len(self.render()) // 4


# ---------------------------------------------------------------------------
# Layer 1 — Essential Story (auto-generated from palace)
# ---------------------------------------------------------------------------


class Layer1:
    """
    ~500-800 tokens. Always loaded.
    Auto-generated from the highest-weight / most-recent drawers in the palace.
    Groups by room, picks the top N moments, compresses to a compact summary.
    """

    MAX_DRAWERS = 15  # at most 15 moments in wake-up
    MAX_CHARS = 3200  # hard cap on total L1 text (~800 tokens)

    def __init__(self, palace_path: str | None = None, wing: str | None = None):
        cfg = MempalaceConfig()
        self.palace_path = palace_path or cfg.palace_path
        self.wing = wing

    def generate(self) -> str:  # noqa: C901, PLR0912, PLR0915, PLR0914
        """Pull top drawers from ChromaDB and format as compact L1 text."""
        try:
            client = chromadb.PersistentClient(path=self.palace_path)
            col = client.get_collection("mempalace_drawers")
        except Exception:
            return "## L1 — No palace found. Run: mempalace mine <dir>"

        # Fetch all drawers in batches to avoid SQLite variable limit (~999)
        BATCH = 500
        docs, metas = [], []
        offset = 0
        while True:
            try:
                batch = col.get(
                    include=["documents", "metadatas"],
                    limit=BATCH,
                    offset=offset,
                    where={"wing": self.wing} if self.wing else None,
                )
            except Exception:
                break
            batch_docs = batch["documents"] or []
            batch_metas = batch["metadatas"] or []
            if not batch_docs:
                break
            docs.extend(batch_docs)
            metas.extend(batch_metas)
            offset += len(batch_docs)
            if len(batch_docs) < BATCH:
                break

        if not docs:
            return "## L1 — No memories yet."

        # Score each drawer: prefer high importance, recent filing
        scored = []
        for doc, meta in zip(docs, metas, strict=False):
            importance = 3
            # Try multiple metadata keys that might carry weight info
            for key in ("importance", "emotional_weight", "weight"):
                val = meta.get(key)
                if val is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        importance = float(val)
                    break
            scored.append((importance, meta, doc))

        # Sort by importance descending, take top N
        scored.sort(key=operator.itemgetter(0), reverse=True)
        top = scored[: self.MAX_DRAWERS]

        # Group by room for readability
        by_room = defaultdict(list)
        for imp, meta, doc in top:
            room = meta.get("room", "general")
            by_room[room].append((imp, meta, doc))

        # Build compact text
        lines = ["## L1 — ESSENTIAL STORY"]

        total_len = 0
        for room, entries in sorted(by_room.items()):
            room_line = f"\n[{room}]"
            lines.append(room_line)
            total_len += len(room_line)

            for _imp, meta, doc in entries:
                source = Path(meta.get("source_file", "")).name if meta.get("source_file") else ""

                # Truncate doc to keep L1 compact
                snippet = doc.strip().replace("\n", " ")
                if len(snippet) > 200:
                    snippet = snippet[:197] + "..."

                entry_line = f"  - {snippet}"
                if source:
                    entry_line += f"  ({source})"

                if total_len + len(entry_line) > self.MAX_CHARS:
                    lines.append("  ... (more in L3 search)")
                    return "\n".join(lines)

                lines.append(entry_line)
                total_len += len(entry_line)

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Layer 2 — On-Demand (wing/room filtered retrieval)
# ---------------------------------------------------------------------------


class Layer2:
    """
    ~200-500 tokens per retrieval.
    Loaded when a specific topic or wing comes up in conversation.
    Queries ChromaDB with a wing/room filter.
    """

    def __init__(self, palace_path: str | None = None):
        cfg = MempalaceConfig()
        self.palace_path = palace_path or cfg.palace_path

    def retrieve(
        self,
        wing: str | None = None,
        room: str | None = None,
        n_results: int = 10,
    ) -> str:
        """Retrieve drawers filtered by wing and/or room."""
        try:
            client = chromadb.PersistentClient(path=self.palace_path)
            col = client.get_collection("mempalace_drawers")
        except Exception:
            return "No palace found."

        where = _build_where(wing, room)

        try:
            results = col.get(
                include=["documents", "metadatas"],
                limit=n_results,
                where=where,
            )
        except Exception as e:
            return f"Retrieval error: {e}"

        docs = results["documents"] or []
        metas = results["metadatas"] or []

        if not docs:
            label = f"wing={wing}" if wing else ""
            if room:
                label += f" room={room}" if label else f"room={room}"
            return f"No drawers found for {label}."

        lines = [f"## L2 — ON-DEMAND ({len(docs)} drawers)"]
        for doc, meta in zip(docs[:n_results], metas[:n_results], strict=False):
            room_name = meta.get("room", "?")
            source = Path(meta.get("source_file", "")).name if meta.get("source_file") else ""
            snippet = doc.strip().replace("\n", " ")
            if len(snippet) > 300:
                snippet = snippet[:297] + "..."
            entry = f"  [{room_name}] {snippet}"
            if source:
                entry += f"  ({source})"
            lines.append(entry)

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Layer 3 — Deep Search (full semantic search via ChromaDB)
# ---------------------------------------------------------------------------


class Layer3:
    """
    Unlimited depth. Semantic search against the full palace.
    Reuses searcher.py logic against mempalace_drawers.
    """

    def __init__(self, palace_path: str | None = None):
        cfg = MempalaceConfig()
        self.palace_path = palace_path or cfg.palace_path

    def search(
        self,
        query: str,
        wing: str | None = None,
        room: str | None = None,
        n_results: int = 5,
    ) -> str:
        """Semantic search, returns compact result text."""
        try:
            client = chromadb.PersistentClient(path=self.palace_path)
            col = client.get_collection("mempalace_drawers")
        except Exception:
            return "No palace found."

        where = _build_where(wing, room)

        try:
            results = col.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
                where=where,
            )
        except Exception as e:
            return f"Search error: {e}"

        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        dists = results["distances"][0] if results["distances"] else []

        if not docs:
            return "No results found."

        lines = [f'## L3 — SEARCH RESULTS for "{query}"']
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists, strict=False), 1):
            similarity = round(1 - dist, 3)
            wing_name = meta.get("wing", "?")
            room_name = meta.get("room", "?")
            source = Path(meta.get("source_file", "")).name if meta.get("source_file") else ""

            snippet = doc.strip().replace("\n", " ")
            if len(snippet) > 300:
                snippet = snippet[:297] + "..."

            lines.extend((f"  [{i}] {wing_name}/{room_name} (sim={similarity})", f"      {snippet}"))
            if source:
                lines.append(f"      src: {source}")

        return "\n".join(lines)

    def search_raw(
        self,
        query: str,
        wing: str | None = None,
        room: str | None = None,
        n_results: int = 5,
    ) -> list:
        """Return raw dicts instead of formatted text."""
        try:
            client = chromadb.PersistentClient(path=self.palace_path)
            col = client.get_collection("mempalace_drawers")
        except Exception:
            return []

        where = _build_where(wing, room)

        try:
            results = col.query(
                query_texts=[query],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
                where=where,
            )
        except Exception:
            return []

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0] if results["documents"] else [],
            results["metadatas"][0] if results["metadatas"] else [],
            results["distances"][0] if results["distances"] else [],
            strict=False,
        ):
            hits.append({
                "text": doc,
                "wing": meta.get("wing", "unknown"),
                "room": meta.get("room", "unknown"),
                "source_file": Path(meta.get("source_file", "?")).name,
                "similarity": round(1 - dist, 3),
                "metadata": meta,
            })
        return hits


# ---------------------------------------------------------------------------
# MemoryStack — unified interface
# ---------------------------------------------------------------------------


class MemoryStack:
    """
    The full 4-layer stack. One class, one palace, everything works.

        stack = MemoryStack()
        print(stack.wake_up())                # L0 + L1 (~600-900 tokens)
        print(stack.recall(wing="my_app"))     # L2 on-demand
        print(stack.search("pricing change"))  # L3 deep search
    """

    def __init__(self, palace_path: str | None = None, identity_path: str | None = None):
        cfg = MempalaceConfig()
        self.palace_path = palace_path or cfg.palace_path
        self.identity_path = identity_path or str(Path("~/.mempalace/identity.txt").expanduser())

        self.l0 = Layer0(self.identity_path)
        self.l1 = Layer1(self.palace_path)
        self.l2 = Layer2(self.palace_path)
        self.l3 = Layer3(self.palace_path)

    def wake_up(self, wing: str | None = None) -> str:
        """
        Generate wake-up text: L0 (identity) + L1 (essential story).
        Typically ~600-900 tokens. Inject into system prompt or first message.

        Args:
            wing: Optional wing filter for L1 (project-specific wake-up).
        """
        parts = []
        parts.extend((self.l0.render(), ""))

        if wing:
            self.l1.wing = wing
        parts.append(self.l1.generate())

        return "\n".join(parts)

    def recall(self, wing: str | None = None, room: str | None = None, n_results: int = 10) -> str:
        """On-demand L2 retrieval filtered by wing/room."""
        return self.l2.retrieve(wing=wing, room=room, n_results=n_results)

    def search(self, query: str, wing: str | None = None, room: str | None = None, n_results: int = 5) -> str:
        """Deep L3 semantic search."""
        return self.l3.search(query, wing=wing, room=room, n_results=n_results)

    def status(self) -> dict:
        """Status of all layers."""
        result = {
            "palace_path": self.palace_path,
            "L0_identity": {
                "path": self.identity_path,
                "exists": Path(self.identity_path).exists(),
                "tokens": self.l0.token_estimate(),
            },
            "L1_essential": {
                "description": "Auto-generated from top palace drawers",
            },
            "L2_on_demand": {
                "description": "Wing/room filtered retrieval",
            },
            "L3_deep_search": {
                "description": "Full semantic search via ChromaDB",
            },
        }

        # Count drawers
        try:
            client = chromadb.PersistentClient(path=self.palace_path)
            col = client.get_collection("mempalace_drawers")
            count = col.count()
            result["total_drawers"] = count
        except Exception:
            result["total_drawers"] = 0

        return result


if __name__ == "__main__":
    import json

    def usage():
        print("layers.py — 4-Layer Memory Stack")
        print()
        print("Usage:")
        print("  python layers.py wake-up              Show L0 + L1")
        print("  python layers.py wake-up --wing=NAME  Wake-up for a specific project")
        print("  python layers.py recall --wing=NAME   On-demand L2 retrieval")
        print("  python layers.py search <query>       Deep L3 search")
        print("  python layers.py status               Show layer status")
        sys.exit(0)

    if len(sys.argv) < 2:
        usage()

    cmd = sys.argv[1]

    # Parse flags
    flags = {}
    positional = []
    for arg in sys.argv[2:]:
        if arg.startswith("--") and "=" in arg:
            key, val = arg.split("=", 1)
            flags[key.lstrip("-")] = val
        elif not arg.startswith("--"):
            positional.append(arg)

    palace_path = flags.get("palace")
    stack = MemoryStack(palace_path=palace_path)

    if cmd in {"wake-up", "wakeup"}:
        wing = flags.get("wing")
        text = stack.wake_up(wing=wing)
        tokens = len(text) // 4
        print(f"Wake-up text (~{tokens} tokens):")
        print("=" * 50)
        print(text)

    elif cmd == "recall":
        wing = flags.get("wing")
        room = flags.get("room")
        text = stack.recall(wing=wing, room=room)
        print(text)

    elif cmd == "search":
        query = " ".join(positional) if positional else ""
        if not query:
            print("Usage: python layers.py search <query>")
            sys.exit(1)
        wing = flags.get("wing")
        room = flags.get("room")
        text = stack.search(query, wing=wing, room=room)
        print(text)

    elif cmd == "status":
        s = stack.status()
        print(json.dumps(s, indent=2))

    else:
        usage()
