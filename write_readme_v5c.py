#!/usr/bin/env python3
"""Append troubleshooting, license, contribution, and support sections."""

readme_path = "c:\\Users\\yedur\\Downloads\\projetcs\\mcp_server\\README.md"

content = """## Troubleshooting

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
$env:DEVTOOLS_PROJECT_ROOT="C:\\path\\to\\your\\project"
```

Or using the setup tool:

```sh
live-devtools-mcp-setup --project-root .
```
"""
with open(readme_path, "a", encoding="utf-8") as f:
    f.write(content)

print("Troubleshooting, license, and closing sections appended")