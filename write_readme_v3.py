#!/usr/bin/env python3
"""Append MCP client configuration and first-time usage sections."""

readme_path = "c:\\Users\\yedur\\Downloads\\projetcs\\mcp_server\\README.md"

content = """## MCP Client Configuration

### Cline

If you're using Cline (VS Code extension), add the following to your VS Code settings or `.vscode/mcp.json`:

```json
{
  "mcp.servers": {
    "live-devtools-inspector": {
      "type": "stdio",
      "command": "live-devtools-mcp",
      "env": {
        "DEVTOOLS_PROJECT_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

After adding, reload VS Code and use **MCP: List Servers** to confirm the server is running.

### VS Code (native MCP support)

If your MCP client uses `.vscode/mcp.json`:

```json
{
  "servers": {
    "live-devtools-inspector": {
      "type": "stdio",
      "command": "live-devtools-mcp",
      "env": {
        "DEVTOOLS_PROJECT_ROOT": "${workspaceFolder}"
      }
    }
  }
}
```

### Codex CLI/IDE

For Codex, configure the MCP server in your Codex settings or `codex_mcp.json`:

```json
{
  "servers": {
    "live-devtools-inspector": {
      "type": "stdio",
      "command": "live-devtools-mcp"
    }
  }
}
```

Then run `codex mcp refresh` to discover the tools.

### Finding the executable path

| OS | Path |
|---|---|
| **Windows** | Installed via `uv tool install` to the local bin directory, or `\\.venv\\Scripts\\live-devtools-mcp.exe` inside your venv |
| **macOS** | `~/\\.local\\/share\\/uv\\/tools\\/devtools-inspector-mcp\\/live-devtools-mcp` |
| **Linux** | `~/\\.local\\/share\\/uv\\/tools\\/devtools-inspector-mcp\\/live-devtools-mcp` |
"""

with open(readme_path, "a", encoding="utf-8") as f:
    f.write(content)

print("MCP client configuration appended")