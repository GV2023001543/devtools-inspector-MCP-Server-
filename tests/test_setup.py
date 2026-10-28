import json
from pathlib import Path

import pytest

from devtools_inspector.setup import SERVER_NAME, SetupError, configure_vscode, merge_vscode_configuration, vscode_server_definition


def test_vscode_merge_preserves_existing_servers_and_is_idempotent():
    existing = {"servers": {"other": {"type": "stdio", "command": "other-server"}}, "inputs": []}
    merged, changed = merge_vscode_configuration(existing)
    assert changed is True
    assert merged["servers"]["other"]["command"] == "other-server"
    assert merged["servers"][SERVER_NAME] == vscode_server_definition()
    repeated, changed = merge_vscode_configuration(merged)
    assert repeated == merged
    assert changed is False


def test_vscode_merge_refuses_to_overwrite_conflicting_server():
    with pytest.raises(SetupError, match="different configuration"):
        merge_vscode_configuration({"servers": {SERVER_NAME: {"type": "stdio", "command": "other"}}})


def test_vscode_configure_creates_backup_and_preserves_other_servers(tmp_path: Path):
    config = tmp_path / ".vscode" / "mcp.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"servers": {"other": {"type": "stdio", "command": "other"}}}), encoding="utf-8")
    assert configure_vscode(tmp_path) == config
    saved = json.loads(config.read_text(encoding="utf-8"))
    assert saved["servers"]["other"]["command"] == "other"
    assert saved["servers"][SERVER_NAME] == vscode_server_definition()
    assert list(config.parent.glob("mcp.json.devtools-inspector.*.bak"))
    configure_vscode(tmp_path)
    assert len(list(config.parent.glob("mcp.json.devtools-inspector.*.bak"))) == 1
