"""Safe local setup helpers for the packaged DevTools Inspector MCP server."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SERVER_NAME = "live-devtools-inspector"
SERVER_COMMAND = "live-devtools-mcp"


class SetupError(RuntimeError):
    """A local MCP configuration could not be completed safely."""


def vscode_server_definition() -> dict[str, Any]:
    return {
        "type": "stdio",
        "command": SERVER_COMMAND,
        "env": {"DEVTOOLS_PROJECT_ROOT": "${workspaceFolder}"},
    }


def merge_vscode_configuration(existing: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Merge this server into a VS Code-format document without changing other servers."""
    if not isinstance(existing, dict):
        raise SetupError("The VS Code MCP configuration must contain a JSON object.")
    servers = existing.get("servers", {})
    if not isinstance(servers, dict):
        raise SetupError("The VS Code MCP configuration has a non-object 'servers' field.")
    desired = vscode_server_definition()
    current = servers.get(SERVER_NAME)
    if current is not None:
        if current == desired:
            return existing, False
        raise SetupError(
            f"{SERVER_NAME!r} already exists with a different configuration. "
            "Review it manually; no changes were made."
        )
    merged = dict(existing)
    merged_servers = dict(servers)
    merged_servers[SERVER_NAME] = desired
    merged["servers"] = merged_servers
    return merged, True


def configure_vscode(project_root: Path) -> Path:
    config_path = project_root / ".vscode" / "mcp.json"
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SetupError(f"Cannot merge invalid JSON in {config_path}: {error}") from error
    else:
        existing = {}
    merged, changed = merge_vscode_configuration(existing)
    if not changed:
        return config_path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        backup = config_path.with_name(f"mcp.json.devtools-inspector.{int(time.time())}.bak")
        shutil.copy2(config_path, backup)
    temporary = config_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    temporary.replace(config_path)
    return config_path


def verify_server_startup(command: str = SERVER_COMMAND) -> None:
    executable = shutil.which(command)
    if executable is None:
        scripts_dir = Path(sys.executable).parent
        candidate = scripts_dir / (f"{command}.exe" if sys.platform == "win32" else command)
        executable = str(candidate) if candidate.is_file() else None
    if executable is None:
        raise SetupError(f"Could not find {command!r} on PATH after installation.")
    process = subprocess.Popen(
        [executable], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    try:
        time.sleep(0.5)
        if process.poll() is not None:
            stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
            raise SetupError(f"{command} exited during its startup check: {stderr.strip()}")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


def configure_codex(project_root: Path) -> None:
    codex = shutil.which("codex")
    if codex is None:
        raise SetupError("Codex CLI was not found on PATH. Install Codex, then rerun setup with --agent codex.")
    existing = subprocess.run([codex, "mcp", "get", SERVER_NAME], capture_output=True, text=True)
    if existing.returncode == 0:
        return
    result = subprocess.run(
        [
            codex,
            "mcp",
            "add",
            SERVER_NAME,
            "--env",
            f"DEVTOOLS_PROJECT_ROOT={project_root}",
            "--",
            SERVER_COMMAND,
        ],
        text=True,
    )
    if result.returncode != 0:
        raise SetupError("Codex rejected the MCP configuration; no fallback file was edited.")


def portable_configuration() -> str:
    return json.dumps(
        {"mcpServers": {SERVER_NAME: {"command": SERVER_COMMAND, "args": []}}}, indent=2
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Configure DevTools Inspector for a local coding agent.")
    parser.add_argument("--agent", choices=("vscode", "codex", "manual"), help="Agent to configure.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Authorized source repository for repair tools.")
    args = parser.parse_args(argv)
    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        raise SystemExit(f"Project root does not exist: {project_root}")
    try:
        verify_server_startup()
        if args.agent is None:
            args.agent = input("Configure which agent? [vscode/codex/manual] ").strip().lower()
        if args.agent == "vscode":
            print(f"Configured VS Code workspace MCP server: {configure_vscode(project_root)}")
        elif args.agent == "codex":
            configure_codex(project_root)
            print("Configured Codex MCP server. Existing matching configuration was left unchanged.")
        elif args.agent == "manual":
            print("Copy this portable MCP configuration into your agent's documented configuration location:")
            print(portable_configuration())
        else:
            raise SetupError("Choose vscode, codex, or manual.")
    except SetupError as error:
        raise SystemExit(f"Setup failed: {error}") from error


if __name__ == "__main__":
    main()
