from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

from .cdp import BrowserConnectionError, BrowserSession
from .fixing import PatchError, PatchManager


mcp = FastMCP(
    "Live DevTools Inspector",
    instructions="Inspect an explicitly selected local Chrome tab. Browser debugging grants powerful access; keep its endpoint local and protected.",
)
browser = BrowserSession()
project_root = Path(os.environ.get("DEVTOOLS_PROJECT_ROOT", Path.cwd())).resolve()
patches = PatchManager(project_root)


@mcp.tool
async def list_browser_targets(endpoint: str = "http://127.0.0.1:9222") -> list[dict[str, str]]:
    """List page targets from a local Chrome debugging endpoint."""
    return await browser.list_targets(endpoint)


@mcp.tool
async def connect_browser(endpoint: str, target_id: str) -> dict[str, object]:
    """Connect to the explicitly selected page target and begin Console/Network monitoring."""
    return await browser.connect(endpoint, target_id)


@mcp.tool
async def select_browser_target(endpoint: str, target_id: str) -> dict[str, object]:
    """Switch the active CDP session to a selected page target."""
    return await browser.connect(endpoint, target_id)


@mcp.tool
async def disconnect_browser() -> dict[str, object]:
    """Close the active page connection and remove event handlers."""
    return await browser.disconnect()


@mcp.tool
def get_connection_status() -> dict[str, object]:
    """Report browser connection and monitoring state."""
    return browser.status()


@mcp.tool
def start_live_inspection() -> dict[str, object]:
    """Resume bounded event-driven Console and Network collection."""
    if browser.collector is None:
        raise BrowserConnectionError("Connect to a selected page target first.")
    browser.collector.monitoring = True
    return {"monitoring": True, "target": browser.target}


@mcp.tool
def stop_live_inspection() -> dict[str, object]:
    """Pause diagnostic collection without disconnecting the browser."""
    if browser.collector is None:
        raise BrowserConnectionError("Connect to a selected page target first.")
    browser.collector.monitoring = False
    return {"monitoring": False, "target": browser.target}


@mcp.tool
def get_live_diagnostics(category: Literal["console", "runtime", "network", "performance", "security", "accessibility"] | None = None) -> list[dict[str, object]]:
    """Return normalized, deduplicated diagnostics collected for the active page."""
    return [issue.model_dump(mode="json") for issue in browser.diagnostics(category)]


@mcp.tool
def inspect_console() -> list[dict[str, object]]:
    """Return captured console warnings, errors, and runtime exceptions."""
    return [issue.model_dump(mode="json") for issue in browser.diagnostics() if issue.category in ("console", "runtime")]


@mcp.tool
def inspect_network() -> list[dict[str, object]]:
    """Return captured HTTP errors and failed or aborted requests."""
    return [issue.model_dump(mode="json") for issue in browser.diagnostics("network")]


@mcp.tool
async def inspect_performance() -> list[dict[str, object]]:
    """Return observed long tasks, using explicitly labeled CDP tracing only when needed."""
    return [issue.model_dump(mode="json") for issue in await browser.performance_diagnostics()]


@mcp.tool
def propose_fix(relative_path: str, expected_sha256: str, old_text: str, new_text: str, rationale: str) -> dict[str, str | bool]:
    """Prepare a minimal exact-snippet patch without changing files."""
    return patches.propose(relative_path, expected_sha256, old_text, new_text, rationale)


@mcp.tool
def apply_patch(patch_id: str, approved: bool) -> dict[str, str | bool]:
    """Apply a reviewed patch only after explicit approval and save a recovery point."""
    return patches.apply(patch_id, approved)


@mcp.tool
async def run_project_checks(patch_id: str | None = None) -> dict[str, object]:
    """Run the fixed pytest command; roll back the linked patch if checks fail."""
    return await patches.run_project_checks(patch_id)


@mcp.tool
def rollback_patch(patch_id: str) -> dict[str, str | bool]:
    """Restore a patch recovery point if the file has not changed since application."""
    return patches.rollback(patch_id)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
