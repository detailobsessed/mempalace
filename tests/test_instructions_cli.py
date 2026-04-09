"""Tests for mempalace.instructions_cli — instruction output for skills."""

from unittest.mock import patch

import pytest

from mempalace.instructions_cli import AVAILABLE, INSTRUCTIONS_DIR, run_instructions


class TestRunInstructions:
    @pytest.mark.parametrize("name", AVAILABLE)
    def test_prints_instruction_content(self, name, capsys):
        run_instructions(name)
        out = capsys.readouterr().out
        assert len(out) > 0
        # Each instruction file should start with a markdown heading
        assert out.strip().startswith("#")

    def test_unknown_name_exits(self):
        with pytest.raises(SystemExit) as exc_info:
            run_instructions("nonexistent")
        assert exc_info.value.code == 1

    def test_all_instruction_files_exist(self):
        for name in AVAILABLE:
            md_path = INSTRUCTIONS_DIR / f"{name}.md"
            assert md_path.is_file(), f"Missing instruction file: {md_path}"

    def test_missing_file_exits(self, tmp_path):
        """If the instruction file is missing on disk, exits with code 1."""
        with patch("mempalace.instructions_cli.INSTRUCTIONS_DIR", tmp_path):
            with pytest.raises(SystemExit) as exc_info:
                run_instructions("init")
            assert exc_info.value.code == 1
