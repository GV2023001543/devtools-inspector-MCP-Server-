#!/usr/bin/env python3
"""Write the beginning of README.md - title, intro, features."""

readme_path = "c:\\Users\\yedur\\Downloads\\projetcs\\mcp_server\\README.md"

content = """# Live DevTools Inspector MCP

A local Python MCP server for diagnosing an explicitly selected Chrome page. It collects normalized console/runtime issues, failed network requests, and main-thread performance findings. It can prepare an exact, reviewed source patch for an authorized local repository and run its test suite; it does not gain source access from a public website URL.

The package is named `devtools-inspector-mcp`. Verify this name is available on PyPI before publishing.

---
"""

content += """## Features

- Browser target discovery via CDP WebSocket endpoint
- Live Console, Network, and Performance monitoring
- Normalized and deduplicated diagnostics
- SHA-256 verified patch proposals with CRLF preservation
- Path traversal blocking and project root enforcement
- `propose_fix` → `apply_patch` (`approved=true`) → `run_project_checks` → `rollback_patch` workflow
"""

content += """## Prerequisites

- Python 3.11 or newer
- `uv` package manager recommended for installation
- Google Chrome or Chromium with remote debugging enabled
- MCP-compatible client (Cline, VS Code, Codex CLI/IDE, or other stdio MCP supporter)
- Supported OS: Windows PowerShell, macOS Terminal, or Linux shell
"""

with open(readme_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Beginning README written")