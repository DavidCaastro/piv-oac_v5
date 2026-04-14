"""Unit tests for sdk/engram/reader.py — EngramReader."""

import tempfile
from pathlib import Path

import pytest

from sdk.engram.reader import EngramAccessError, EngramReader


@pytest.mark.unit
class TestEngramReader:

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)
        # Create core/ subdir with a sample atom
        (self.root / "core").mkdir()
        (self.root / "core" / "decisions.md").write_text("# Decisions\nsome content")

    def test_authorized_read_succeeds(self):
        reader = EngramReader(self.root, role="orchestrator")
        content = reader.read("core/decisions.md")
        assert "# Decisions" in content

    def test_unauthorized_subdir_raises_access_error(self):
        reader = EngramReader(self.root, role="orchestrator")
        with pytest.raises(EngramAccessError, match="not allowed"):
            reader.read("security/alerts.md")

    def test_specialist_agent_has_no_access(self):
        reader = EngramReader(self.root, role="specialist_agent")
        with pytest.raises(EngramAccessError, match="isolation boundary"):
            reader.read("core/decisions.md")

    def test_exists_returns_false_for_missing_atom(self):
        reader = EngramReader(self.root, role="orchestrator")
        assert reader.exists("core/nonexistent.md") is False

    def test_exists_returns_true_for_present_atom(self):
        reader = EngramReader(self.root, role="orchestrator")
        assert reader.exists("core/decisions.md") is True

    def test_exists_returns_false_for_unauthorized_subdir(self):
        reader = EngramReader(self.root, role="orchestrator")
        assert reader.exists("security/alerts.md") is False

    def test_file_not_found_raises_error(self):
        reader = EngramReader(self.root, role="orchestrator")
        with pytest.raises(FileNotFoundError):
            reader.read("core/missing.md")
