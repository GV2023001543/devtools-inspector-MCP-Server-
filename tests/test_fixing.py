import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from devtools_inspector.fixing import PatchError, PatchManager


def _proposal(manager: PatchManager, path: Path) -> str:
    content = path.read_bytes()
    return manager.propose(
        path.name,
        hashlib.sha256(content).hexdigest(),
        "return 1",
        "return 2",
        "Correct the result",
    )["patch_id"]


def test_patch_requires_approval_and_can_be_rolled_back(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text("def value():\n    return 1\n", encoding="utf-8")
    manager = PatchManager(tmp_path)
    patch_id = _proposal(manager, source)
    with pytest.raises(PatchError, match="approved=true"):
        manager.apply(patch_id, approved=False)
    result = manager.apply(patch_id, approved=True)
    assert result["verification"] == "unverified"
    assert "return 2" in source.read_text(encoding="utf-8")
    assert manager.rollback(patch_id)["rolled_back"] is True
    assert "return 1" in source.read_text(encoding="utf-8")
    history = [json.loads(line) for line in (tmp_path / ".devtools_mcp" / "history.jsonl").read_text().splitlines()]
    assert [entry["action"] for entry in history] == ["proposed", "applied", "rolled_back"]


def test_patch_rejects_stale_file_and_duplicate_anchor(tmp_path: Path):
    source = tmp_path / "app.js"
    source.write_text("return 1", encoding="utf-8")
    manager = PatchManager(tmp_path)
    patch_id = _proposal(manager, source)
    source.write_text("return 1;\n// new user edit", encoding="utf-8")
    with pytest.raises(PatchError, match="changed after the proposal"):
        manager.apply(patch_id, approved=True)


@pytest.mark.parametrize("relative_path", ["../outside.py", ".env", "node_modules/pkg/app.js", "package-lock.json"])
def test_patch_rejects_traversal_and_non_source_files(tmp_path: Path, relative_path: str):
    manager = PatchManager(tmp_path)
    with pytest.raises(PatchError):
        manager.propose(relative_path, "0" * 64, "a", "b", "test")


def test_rollback_preserves_changes_made_after_patch(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text("return 1", encoding="utf-8")
    manager = PatchManager(tmp_path)
    patch_id = _proposal(manager, source)
    manager.apply(patch_id, approved=True)
    source.write_text("return 2\n# user edit", encoding="utf-8")
    with pytest.raises(PatchError, match="preserve newer edits"):
        manager.rollback(patch_id)


def test_patch_preserves_crlf_line_endings(tmp_path: Path):
    source = tmp_path / "app.html"
    original = b"<p id=\"status\">Waiting</p>\r\n<button>Update</button>\r\n"
    source.write_bytes(original)
    manager = PatchManager(tmp_path)
    patch_id = manager.propose(
        source.name,
        hashlib.sha256(original).hexdigest(),
        "Waiting",
        "Updated",
        "Preserve the file's line endings",
    )["patch_id"]
    manager.apply(patch_id, approved=True)
    assert source.read_bytes() == b"<p id=\"status\">Updated</p>\r\n<button>Update</button>\r\n"


@pytest.mark.asyncio
async def test_failed_checks_roll_back_linked_patch(tmp_path: Path, monkeypatch):
    source = tmp_path / "app.py"
    source.write_text("return 1", encoding="utf-8")
    manager = PatchManager(tmp_path)
    patch_id = _proposal(manager, source)
    manager.apply(patch_id, approved=True)

    class FailedProcess:
        returncode = 1

        async def communicate(self):
            return b"1 failed", None

        def kill(self):
            pass

        async def wait(self):
            return 1

    async def create_failed_process(*args, **kwargs):
        return FailedProcess()

    monkeypatch.setattr("devtools_inspector.fixing.asyncio.create_subprocess_exec", create_failed_process)
    result = await manager.run_project_checks(patch_id)
    assert result["executed"] is True
    assert result["passed"] is False
    assert result["rollback"]["rolled_back"] is True
    assert "return 1" in source.read_text(encoding="utf-8")