"""
query_sanitizer.py — Mitigate system prompt contamination in search queries.

Problem: AI agents sometimes prepend system prompts (2000+ chars) to search queries.
Embedding models represent the concatenated string as a single vector where the
system prompt overwhelms the actual question (typically 10-50 chars), causing
near-total retrieval failure (89.8% -> 1.0% R@10). See Issue #333.

Expected recovery:
  Step 1 passthrough (<=200 chars)     -> no degradation, ~89.8%
  Step 2 question extraction (? found) -> near-full recovery, ~85-89%
  Step 3 tail sentence extraction      -> moderate recovery, ~80-89%
  Step 4 tail truncation (fallback)    -> minimum viable, ~70-80%

  Without sanitizer: 1.0% (catastrophic silent failure)
  Worst case with sanitizer: ~70-80% (survivable)
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("mempalace_mcp")

# --- Constants ---
MAX_QUERY_LENGTH = 500  # Above this, system prompt almost certainly dominates
SAFE_QUERY_LENGTH = 200  # Below this, query is almost certainly clean
MIN_QUERY_LENGTH = 10  # Extracted result shorter than this = extraction failed

# Sentence splitter: capturing group retains the delimiter so we can reassemble
_SENTENCE_SPLIT = re.compile(r"([.!?\u3002\uff01\uff1f\n]+)")

# Question detector: ends with ? or fullwidth ? (possibly with trailing whitespace/quotes)
_QUESTION_MARK = re.compile(r"[?\uff1f]\s*[\"']?\s*$")


def _make_result(clean_query: str, *, was_sanitized: bool, original_length: int, method: str) -> dict:
    """Build a sanitizer result dict."""
    return {
        "clean_query": clean_query,
        "was_sanitized": was_sanitized,
        "original_length": original_length,
        "clean_length": len(clean_query),
        "method": method,
    }


def _clamp_and_log(candidate: str, original_length: int, method: str) -> dict:
    """Clamp candidate to MAX_QUERY_LENGTH, log, and return result."""
    if len(candidate) > MAX_QUERY_LENGTH:
        candidate = candidate[-MAX_QUERY_LENGTH:]
    logger.warning(
        "Query sanitized: %d -> %d chars (method=%s)",
        original_length,
        len(candidate),
        method,
    )
    return _make_result(candidate, was_sanitized=True, original_length=original_length, method=method)


def _reassemble_sentences(raw_query: str) -> list[str]:
    """Split on sentence-ending punctuation, reattach delimiters to each segment."""
    parts = _SENTENCE_SPLIT.split(raw_query)
    sentences: list[str] = []
    for i in range(0, len(parts) - 1, 2):
        sentence = (parts[i] + parts[i + 1]).strip()
        if sentence:
            sentences.append(sentence)
    if len(parts) % 2 == 1 and parts[-1].strip():
        sentences.append(parts[-1].strip())
    return sentences


def _find_questions(all_segments: list[str], raw_query: str) -> list[str]:
    """Find question sentences from segments and sentence splits."""
    questions = [seg for seg in reversed(all_segments) if _QUESTION_MARK.search(seg)]
    if not questions:
        sentences = _reassemble_sentences(raw_query)
        questions.extend(sent for sent in reversed(sentences) if _QUESTION_MARK.search(sent))
    return questions


def sanitize_query(raw_query: str | None) -> dict:
    """Extract the actual search intent from a potentially contaminated query.

    Returns dict with: clean_query, was_sanitized, original_length, clean_length, method.
    """
    if not raw_query or not raw_query.strip():
        return _make_result(raw_query or "", was_sanitized=False, original_length=len(raw_query or ""), method="passthrough")

    raw_query = raw_query.strip()
    original_length = len(raw_query)

    # --- Step 1: Short query passthrough ---
    if original_length <= SAFE_QUERY_LENGTH:
        return _make_result(raw_query, was_sanitized=False, original_length=original_length, method="passthrough")

    all_segments = [s.strip() for s in raw_query.split("\n") if s.strip()]

    # --- Step 2: Question extraction ---
    questions = _find_questions(all_segments, raw_query)
    if questions:
        candidate = questions[0].strip()
        if len(candidate) >= MIN_QUERY_LENGTH:
            return _clamp_and_log(candidate, original_length, "question_extraction")

    # --- Step 3: Tail sentence extraction ---
    for seg in reversed(all_segments):
        stripped = seg.strip()
        if len(stripped) >= MIN_QUERY_LENGTH:
            return _clamp_and_log(stripped, original_length, "tail_sentence")

    # --- Step 4: Tail truncation (fallback) ---
    candidate = raw_query[-MAX_QUERY_LENGTH:].strip()
    return _clamp_and_log(candidate, original_length, "tail_truncation")
