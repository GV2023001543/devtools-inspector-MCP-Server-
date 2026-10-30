# Live DevTools Inspector MCP

A local Python MCP server for diagnosing an explicitly selected Chrome page. It collects normalized console/runtime issues, failed network requests, and main-thread performance findings. It can prepare an exact, reviewed source patch for an authorized local repository and run its test suite; it does not gain source access from a public website URL.

The package is named `devtools-inspector-mcp`. Verify this name is available on PyPI before publishing.

---
## Features

- Browser target discovery via CDP WebSocket endpoint
- Live Console, Network, and Performance monitoring
- Normalized and deduplicated diagnostics
- SHA-256 verified patch proposals with CRLF preservation
- Path traversal blocking and project root enforcement
- `propose_fix` → `apply_patch` (`approved=true`) → `run_project_checks` → `rollback_patch` workflow
## Prerequisites

- Python 3.11 or newer
- `uv` package manager recommended for installation
- Google Chrome or Chromium with remote debugging enabled
- MCP-compatible client (Cline, VS Code, Codex CLI/IDE, or other stdio MCP supporter)
- Supported OS: Windows PowerShell, macOS Terminal, or Linux shell
## Installation

### From PyPI (recommended)

```powershell
# Windows PowerShell
uv tool install --upgrade devtools-inspector-mcp
```

```sh
# macOS and Linux
uv tool install --upgrade devtools-inspector-mcp
```

### Verify installation

```powershell
# Windows PowerShell
live-devtools-mcp --help
```

```sh
# macOS and Linux
live-devtools-mcp --help
```

### From this checkout (development)

```powershell
# Windows PowerShell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
```

```sh
# macOS and Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install -q pytest pytest-asyncio
```

## Chrome Setup

The server connects to Chrome via the Chrome DevTools Protocol (CDP) WebSocket endpoint. You must launch Chrome with debugging enabled on `127.0.0.1:9222`.

### Windows PowerShell

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-address=127.0.0.1 `
  --remote-debugging-port=9222 `
  --user-data-dir "$env:TEMP\devtools-inspector-chrome"
```

### macOS

```sh
open -na "Google Chrome" --args   --remote-debugging-address=127.0.0.1   --remote-debugging-port=9222   --user-data-dir="${TMPDIR:-/tmp}/devtools-inspector-chrome"
```

### Linux

```sh
google-chrome   --remote-debugging-address=127.0.0.1   --remote-debugging-port=9222   --user-data-dir="${TMPDIR:-/tmp}/devtools-inspector-chrome"
```

### Open your website in Chrome

1. Launch Chrome using one of the commands above
2. Open `http://localhost:3000` (or your local development server) in the new Chrome window
3. The page must be open for `list_browser_targets` to discover it
## MCP Client Configuration

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
| **Windows** | Installed via `uv tool install` to the local bin directory, or `\.venv\Scripts\live-devtools-mcp.exe` inside your venv |
| **macOS** | `~/\.local\/share\/uv\/tools\/devtools-inspector-mcp\/live-devtools-mcp` |
| **Linux** | `~/\.local\/share\/uv\/tools\/devtools-inspector-mcp\/live-devtools-mcp` |
## First-Time Usage

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
## Complete MCP Tool Reference

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
## Example AI Assistant Prompts

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
## Troubleshooting

| Problem | Solution |
|---------|----------|
| **`uv` not found** | Install uv: `pip install uv` or download from https://docs.astral.sh/uv/getting-started/installation/ |
| **Server missing from agent** | Restart/reload your MCP agent, then use **MCP: List Servers** to refresh |
| **Chrome connection refused** | - Verify Chrome is running with the debugging commands above<br>- Ensure Chrome is on `127.0.0.1:9222`<br>- Check firewall allows loopback connections |
| **No browser targets found** | - Confirm Chrome is open with the debug profile<br>- Ensure the page is loaded in Chrome<br>- Run `list_browser_targets` again |
| **`list_browser_targets` returns empty list** | - Verify endpoint is `http://127.0.0.1:9222`<br>- Check Chrome process is still running<br>- Ensure no other process is using port 9222 |
| **MCP server not starting** | - Verify Python 3.11+ is installed<br>- Check `live-devtools-mcp` is in your PATH<br>- Try `python -m devtools_inspector.server` for debugging |
| **Executable not found** | - On Windows: ensure venv Scripts folder is in PATH<br>- On macOS/Linux: `uv tool install --upgrade devtools-inspector-mcp` installs to `~/.local/share/uv/tools/` |
| **Wrong project root** | - Set `DEVTOOLS_PROJECT_ROOT` environment variable<br>- Or run `live-devtools-mcp-setup --project-root .` to configure<br>- Or pass `--project-root .` via your MCP client's env vars |

## License

This project is licensed under the [MIT License](LICENSE.txt). See the LICENSE.txt file for full terms.

## Contribution

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, discuss what you would like to change via a GitHub Issue first.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/foo-bar`)
3. Commit your changes (`git commit -m 'Add some foo-bar'`)
4. Push to the branch (`git push origin feature/foo-bar`)
5. Open a Pull Request

## Support

- **GitHub Issues**: Report bugs and feature requests at the [GitHub repository](https://github.com/your-username/devtools-inspector-mcp/issues)
- **Discussions**: Ask questions and share use cases at [GitHub Discussions](https://github.com/your-username/devtools-inspector-mcp/discussions)
- **PyPI**: `uv tool info devtools-inspector-mcp` for installation info

## Release Preparation

1. Recheck the PyPI package name immediately before upload
2. Build and inspect artifacts: `uv build`
3. Test the wheel in a clean virtual environment on each supported platform
4. Publish only after review: `uv publish`
5. Host `scripts/install.ps1` and `scripts/install.sh` on a versioned HTTPS release URL you control
6. Publish SHA-256 checksums and replace example domains in the README

**Do not publish the package or installer scripts until the artifacts, URLs, checksums, and release version have been reviewed.**

## Automatic Workspace Detection

The server automatically detects the VS Code workspace root with the following priority:

1. **`DEVTOOLS_PROJECT_ROOT` environment variable** (explicit opt-in) — If set and points to an existing directory, it will be used as the project root
2. **VS Code workspace detection** — The server attempts to detect the workspace from the MCP client's roots notification. If Cline or another MCP client provides workspace folder information, the first workspace folder will be used
3. **Current working directory** — If neither of the above is available, the server falls back to `Path.cwd()` with a clear warning message

You can set the `DEVTOOLS_PROJECT_ROOT` environment variable explicitly if auto-detection doesn't work:

```powershell
# Windows PowerShell
$env:DEVTOOLS_PROJECT_ROOT="C:\path\to\your\project"
```

Or using the setup tool:

```sh
live-devtools-mcp-setup --project-root .
```
