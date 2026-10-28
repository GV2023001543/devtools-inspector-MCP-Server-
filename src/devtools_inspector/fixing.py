from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from .redaction import redact_text


_ALLOWED_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css"}
_BLOCKED_PARTS = {".git", ".venv", "venv", "node_modules", "site-packages", "dist", "build"}


class PatchError(ValueError):
    """A patch could not be safely prepared, applied, or rolled back."""


@dataclass
class ProposedPatch:
    patch_id: str
    path: Path
    expected_sha256: str
    old_text: str
    new_text: str
    rationale: str


class PatchManager:
    def __init__(self, project_root: Path):
        self.root = project_root.resolve()
        self._proposals: dict[str, ProposedPatch] = {}
        self._backup_root = self.root / ".devtools_mcp" / "rollback"

    def _ensure_state_dir(self) -> None:
        state_dir = self.root / ".devtools_mcp"
        try:
            state_dir.mkdir(exist_ok=True)
            if state_dir.is_symlink():
                raise PatchError("The patch state directory cannot be a symbolic link.")
            state_dir.resolve().relative_to(self.root)
            self._backup_root.mkdir(exist_ok=True)
            if self._backup_root.is_symlink():
                raise PatchError("The rollback directory cannot be a symbolic link.")
            self._backup_root.resolve().relative_to(self.root)
        except ValueError:
            raise PatchError("The patch state directory must remain inside the project root.") from None
        except OSError as error:
            raise PatchError(f"Could not prepare patch state: {error}") from error

    def _record(self, action: str, details: dict[str, str]) -> None:
        self._ensure_state_dir()
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            **details,
        }
        with (self.root / ".devtools_mcp" / "history.jsonl").open("a", encoding="utf-8") as history:
            history.write(json.dumps(record, ensure_ascii=True) + "\n")

    def _resolve_source(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if candidate.is_absolute() or not relative_path or ".." in candidate.parts:
            raise PatchError("Use a project-relative source path without '..'.")
        if candidate.suffix.lower() not in _ALLOWED_SUFFIXES or any(part.lower() in _BLOCKED_PARTS for part in candidate.parts):
            raise PatchError("This path is not an allowed source file; dependency, build, and environment paths are blocked.")
        path = (self.root / candidate).resolve()
        try:
            path.relative_to(self.root)
        except ValueError:
            raise PatchError("The source path resolves outside the configured project root.") from None
        if path.is_symlink() or not path.is_file():
            raise PatchError("The selected path must be an existing regular source file.")
        if path.stat().st_size > 250_000:
            raise PatchError("Files larger than 250 KB are not eligible for patching.")
        return path

    def propose(
        self,
        relative_path: str,
        expected_sha256: str,
        old_text: str,
        new_text: str,
        rationale: str,
    ) -> dict[str, str]:
        path = self._resolve_source(relative_path)
        original_bytes = path.read_bytes()
        content = original_bytes.decode("utf-8")
        actual_hash = hashlib.sha256(original_bytes).hexdigest()
        if actual_hash != expected_sha256:
            raise PatchError("The file changed since it was inspected. Read it again and propose against its current SHA-256.")
        if not old_text or len(old_text) > 20_000 or len(new_text) > 20_000:
            raise PatchError("Provide a non-empty old snippet and snippets no larger than 20 KB.")
        if content.count(old_text) != 1:
            raise PatchError("The old snippet must match exactly once; no file changes were made.")
        patch_id = uuid4().hex[:16]
        self._proposals[patch_id] = ProposedPatch(
            patch_id=patch_id,
            path=path,
            expected_sha256=actual_hash,
            old_text=old_text,
            new_text=new_text,
            rationale=redact_text(rationale, 500),
        )
        self._record(
            "proposed",
            {"patch_id": patch_id, "path": path.relative_to(self.root).as_posix(), "sha256": actual_hash},
        )
        return {"patch_id": patch_id, "path": path.relative_to(self.root).as_posix(), "rationale": redact_text(rationale, 500), "approval_required": True}

    def apply(self, patch_id: str, approved: bool) -> dict[str, str | bool]:
        if not approved:
            raise PatchError("Patch not applied. Set approved=true only after reviewing the proposed change.")
        proposal = self._proposals.get(patch_id)
        if proposal is None:
            raise PatchError("Proposal not found or expired with this server session; create it again.")
        current_bytes = proposal.path.read_bytes()
        current = current_bytes.decode("utf-8")
        if hashlib.sha256(current_bytes).hexdigest() != proposal.expected_sha256:
            raise PatchError("The file changed after the proposal. Patch refused; inspect and propose again.")
        if current.count(proposal.old_text) != 1:
            raise PatchError("The patch anchor is no longer unique. No file changes were made.")
        updated = current.replace(proposal.old_text, proposal.new_text, 1)
        updated_bytes = updated.encode("utf-8")
        applied_hash = hashlib.sha256(updated_bytes).hexdigest()
        self._ensure_state_dir()
        backup = {
            "patch_id": patch_id,
            "path": proposal.path.relative_to(self.root).as_posix(),
            "original": current,
            "original_sha256": proposal.expected_sha256,
            "applied_sha256": applied_hash,
            "rationale": proposal.rationale,
        }
        self._atomic_write(self._backup_root / f"{patch_id}.json", json.dumps(backup, ensure_ascii=True))
        self._atomic_write(proposal.path, updated_bytes)
        self._proposals.pop(patch_id, None)
        self._record(
            "applied",
            {"patch_id": patch_id, "path": proposal.path.relative_to(self.root).as_posix(), "sha256": applied_hash},
        )
        return {
            "patch_id": patch_id,
            "applied": True,
            "path": proposal.path.relative_to(self.root).as_posix(),
            "applied_sha256": applied_hash,
            "verification": "unverified",
        }

    def rollback(self, patch_id: str) -> dict[str, str | bool]:
        backup_path = self._backup_root / f"{patch_id}.json"
        if not backup_path.is_file():
            raise PatchError("No recovery point exists for this patch ID.")
        backup = json.loads(backup_path.read_text(encoding="utf-8"))
        path = self._resolve_source(backup["path"])
        current_bytes = path.read_bytes()
        current_hash = hashlib.sha256(current_bytes).hexdigest()
        if current_hash != backup["applied_sha256"]:
            raise PatchError("The file has changed since the patch was applied. Rollback refused to preserve newer edits.")
        self._atomic_write(path, backup["original"].encode("utf-8"))
        backup_path.unlink()
        self._record("rolled_back", {"patch_id": patch_id, "path": backup["path"]})
        return {"patch_id": patch_id, "rolled_back": True, "path": backup["path"]}

    async def run_project_checks(self, patch_id: str | None = None, timeout: float = 120) -> dict[str, object]:
        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pytest",
                "-q",
                cwd=self.root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
                exit_code = process.returncode
            except TimeoutError:
                process.kill()
                await process.wait()
                output = b"pytest exceeded the 120 second verification limit."
                exit_code = -1
            executed = True
        except OSError as error:
            output = str(error).encode("utf-8", errors="replace")
            exit_code = -1
            executed = False
        result: dict[str, object] = {
            "command": [sys.executable, "-m", "pytest", "-q"],
            "executed": executed,
            "passed": executed and exit_code == 0,
            "exit_code": exit_code,
            "output": redact_text(output.decode("utf-8", errors="replace")[-10_000:], 10_000),
            "browser_verification": "not_run",
        }
        self._record(
            "checks",
            {"patch_id": patch_id or "", "passed": str(result["passed"]), "exit_code": str(exit_code)},
        )
        if patch_id and not result["passed"]:
            try:
                result["rollback"] = self.rollback(patch_id)
            except PatchError as error:
                result["rollback"] = {"rolled_back": False, "error": str(error)}
        return result

    @staticmethod
    def _atomic_write(path: Path, content: str | bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = path.stat().st_mode if path.exists() else None
        if isinstance(content, bytes):
            with NamedTemporaryFile("wb", dir=path.parent, delete=False) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
        else:
            with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
                temporary.write(content)
                temporary_path = Path(temporary.name)
        if mode is not None:
            os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)