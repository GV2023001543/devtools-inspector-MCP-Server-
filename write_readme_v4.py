#!/usr/bin/env python3
"""Append first-time usage and tool reference sections."""

readme_path = "c:\\Users\\yedur\\Downloads\\projetcs\\mcp_server\\README.md"

content = """## First-Time Usage

### 1. Start Chrome with debugging

Use the Chrome setup commands above to launch Chrome with remote debugging on port 9222.

### 2. Start the MCP server

```powershell
# Windows PowerShell
live-devtools-mcp
```

```sh
# macOS and Linux
live-devtools-mcp
```

The server will start as a stdio MCP server and report its status.

### 3. Discover Chrome targets

Call the `list_browser_targets` tool:

```json
{
  "name": "list_browser_targets",
  "arguments": {
    "endpoint": "http://127.0.0.1:9222"
  }
}
```

You'll see a list of open pages with their `target_id`, `title`, and `url`.

### 4. Connect to a browser target

Call `connect_browser` with the `target_id` you selected:

```json
{
  "name": "connect_browser",
  "arguments": {
    "endpoint": "http://127.0.0.1:9222",
    "target_id": "target_id_from_step_3"
  }
}
```

### 5. Start live inspection

Call `start_live_inspection` to begin collecting diagnostics:

```json
{
  "name": "start_live_inspection",
  "arguments": {}
}
```

### 6. Inspect diagnostics

- **Console errors**: `inspect_console`
- **Network failures**: `inspect_network`
- **Performance**: `inspect_performance`
- **All diagnostics**: `get_live_diagnostics`

### 7. Safe patch workflow (optional)

1. Inspect diagnostics and identify the file to fix
2. Call `propose_fix` with:
   - `relative_path`: project-relative path (e.g., `src/components/Button.py`)
   - `expected_sha256`: current file hash
   - `old_text`: current code snippet
   - `new_text`: proposed replacement
   - `rationale`: why this fix is needed
3. Review the `patch_id` returned
4. Call `apply_patch` with `approved=true` to apply
5. Run `run_project_checks` to verify
6. Use `rollback_patch` to revert if needed
"""

with open(readme_path, "a", encoding="utf-8") as f:
    f.write(content)

print("First-time usage appended")