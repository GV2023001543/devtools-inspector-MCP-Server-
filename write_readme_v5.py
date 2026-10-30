#!/usr/bin/env python3
"""Append tool reference and example prompts sections."""

readme_path = "c:\\Users\\yedur\\Downloads\\projetcs\\mcp_server\\README.md"

content = """## Complete MCP Tool Reference

| Tool | Purpose | Key Arguments |
|------|---------|-------------|
| `list_browser_targets` | List open Chrome pages from a CDP endpoint | `endpoint` (default: `http://127.0.0.1:9222`) |
| `connect_browser` | Connect CDP session to a selected page target | `endpoint`, `target_id` |
| `select_browser_target` | Switch active CDP session to a selected page target | `endpoint`, `target_id` (same as `connect_browser`) |
| `disconnect_browser` | Close the active page connection and remove event handlers | none |
| `get_connection_status` | Report browser connection and monitoring state | none |
| `start_live_inspection` | Resume bounded event-driven Console and Network collection | none |
| `stop_live_inspection` | Pause diagnostic collection without disconnecting | none |
| `get_live_diagnostics` | Return normalized, deduplicated diagnostics for the active page | optional `category` filter: `console`, `runtime`, `network`, `performance`, `security`, `accessibility` |
| `inspect_console` | Return captured console warnings, errors, and runtime exceptions | none |
| `inspect_network` | Return captured HTTP errors and failed/aborted requests | none |
| `inspect_performance` | Return observed long tasks from CDP tracing | none |
| `propose_fix` | Prepare a minimal exact-snippet patch without changing files | `relative_path`, `expected_sha256`, `old_text`, `new_text`, `rationale` |
| `apply_patch` | Apply a reviewed patch only after explicit approval and save a recovery point | `patch_id`, `approved` (must be `true`) |
| `run_project_checks` | Run the fixed pytest command; roll back the linked patch if checks fail | optional `patch_id` |
| `rollback_patch` | Restore a patch recovery point if the file has not changed since application | `patch_id` |
"""
with open(readme_path, "a", encoding="utf-8") as f:
    f.write(content)

print("Tool reference appended")