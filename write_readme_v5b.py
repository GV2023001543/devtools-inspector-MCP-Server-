#!/usr/bin/env python3
"""Append example prompts, troubleshooting, and closing sections."""

readme_path = "c:\\Users\\yedur\\Downloads\\projetcs\\mcp_server\\README.md"

content = """## Example AI Assistant Prompts

You can now give these prompts to your AI coding assistant (Cline, Codex, etc.):

| Prompt | Tool(s) involved |
|--------|------------------|
| "Inspect the console errors on the active Chrome tab" | `inspect_console` |
| "Check for failed network requests on the page" | `inspect_network` |
| "Look for long-running tasks that are slowing down the page" | `inspect_performance` |
| "Get a summary of all live diagnostics for the current page" | `get_live_diagnostics` |
| "Prepare a patch to change `return 1` to `return 2` in `src/calc.py`" | `propose_fix` |
| "Apply the patch with ID `abc123` that I just reviewed" | `apply_patch` (with `approved=true`) |
| "Run the project tests and roll back the patch if they fail" | `run_project_checks` |
| "Roll back the patch I just applied" | `rollback_patch` |
| "List all available browser targets" | `list_browser_targets` |
"""

with open(readme_path, "a", encoding="utf-8") as f:
    f.write(content)

print("Example prompts appended")