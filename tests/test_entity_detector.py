"""Tests for entity_detector.py — entity extraction and classification."""

import pytest

from mempalace.entity_detector import (
    classify_entity,
    detect_entities,
    extract_candidates,
    scan_for_detection,
    score_entity,
)


class TestExtractCandidates:
    def test_finds_repeated_names(self):
        text = "Alice went to the store. Alice bought milk. Alice came home."
        candidates = extract_candidates(text)
        assert "Alice" in candidates
        assert candidates["Alice"] == 3

    def test_ignores_stopwords(self):
        text = "The The The This This This That That That"
        candidates = extract_candidates(text)
        assert "The" not in candidates
        assert "This" not in candidates

    def test_frequency_threshold(self):
        text = "Bob went home. Charlie stayed."
        candidates = extract_candidates(text)
        # Each appears only once, below the 3x threshold
        assert "Bob" not in candidates
        assert "Charlie" not in candidates

    def test_multi_word_names(self):
        # "Memory" is in STOPWORDS, so multi-word "Memory Palace" won't match.
        # Single-word "Palace" appears 3x and passes the threshold.
        text = "Memory Palace is great. Memory Palace rocks. Memory Palace forever."
        candidates = extract_candidates(text)
        assert "Palace" in candidates

    def test_empty_text(self):
        candidates = extract_candidates("")
        assert len(candidates) == 0


class TestScoreEntity:
    def test_person_dialogue_signal(self):
        text = "Alice: hello there\nAlice: how are you"
        lines = text.split("\n")
        scores = score_entity("Alice", text, lines)
        assert scores["person_score"] > 0

    def test_person_verb_signal(self):
        text = "Alice said hello. Alice asked about the project. Alice laughed."
        lines = text.split("\n")
        scores = score_entity("Alice", text, lines)
        assert scores["person_score"] > 0

    def test_project_verb_signal(self):
        text = "We're building MemPalace. Deploy MemPalace today. import MemPalace"
        lines = text.split("\n")
        scores = score_entity("MemPalace", text, lines)
        assert scores["project_score"] > 0

    def test_code_reference(self):
        text = "Check out mempalace.py for details"
        lines = text.split("\n")
        scores = score_entity("mempalace", text, lines)
        assert scores["project_score"] > 0

    def test_no_signals(self):
        text = "The weather is nice today"
        lines = text.split("\n")
        scores = score_entity("Weather", text, lines)
        assert scores["person_score"] == 0
        assert scores["project_score"] == 0


class TestClassifyEntity:
    @pytest.mark.parametrize(
        ("name", "count", "scores", "expected_type"),
        [
            (
                "Alice",
                10,
                {
                    "person_score": 15,
                    "project_score": 0,
                    "person_signals": ["dialogue marker (3x)", "action (2x)", "pronoun nearby (1x)"],
                    "project_signals": [],
                },
                "person",
            ),
            (
                "MemPalace",
                8,
                {
                    "person_score": 0,
                    "project_score": 10,
                    "person_signals": [],
                    "project_signals": ["project verb (3x)", "code file reference (2x)"],
                },
                "project",
            ),
            (
                "Unknown",
                5,
                {"person_score": 0, "project_score": 0, "person_signals": [], "project_signals": []},
                "uncertain",
            ),
            (
                "Ambiguous",
                10,
                {
                    "person_score": 5,
                    "project_score": 5,
                    "person_signals": ["action (1x)"],
                    "project_signals": ["project verb (1x)"],
                },
                "uncertain",
            ),
        ],
        ids=["person", "project", "uncertain-no-signals", "uncertain-mixed"],
    )
    def test_classification(self, name, count, scores, expected_type):
        result = classify_entity(name, count, scores)
        assert result["type"] == expected_type

    def test_person_confidence_above_half(self):
        scores = {
            "person_score": 15,
            "project_score": 0,
            "person_signals": ["dialogue marker (3x)", "action (2x)", "pronoun nearby (1x)"],
            "project_signals": [],
        }
        result = classify_entity("Alice", 10, scores)
        assert result["confidence"] > 0.5

    def test_pronoun_only_downgraded(self):
        scores = {
            "person_score": 8,
            "project_score": 0,
            "person_signals": ["pronoun nearby (4x)"],
            "project_signals": [],
        }
        result = classify_entity("Grace", 5, scores)
        assert result["type"] == "uncertain"


class TestDetectEntitiesIntegration:
    def test_detect_entities_with_prose_files(self, tmp_path):
        f1 = tmp_path / "notes.txt"
        f1.write_text(
            "Alice said hello. Alice asked about it. Alice laughed.\n"
            "Alice told me the plan. Alice smiled at everyone.\n"
            "Bob: hey there\nBob: how are you\nBob: see you later\n" * 3,
            encoding="utf-8",
        )
        detected = detect_entities([f1])
        assert "people" in detected
        assert "projects" in detected
        assert "uncertain" in detected


class TestScanForDetectionIntegration:
    def test_scan_for_detection(self, tmp_path):
        (tmp_path / "notes.md").write_text("test content", encoding="utf-8")
        (tmp_path / "journal.txt").write_text("more content", encoding="utf-8")
        (tmp_path / "app.py").write_text("code here", encoding="utf-8")
        files = scan_for_detection(str(tmp_path))
        assert len(files) > 0
