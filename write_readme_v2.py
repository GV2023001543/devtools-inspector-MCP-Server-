#!/usr/bin/env python3
"""Append installation and Chrome setup sections to README.md."""

readme_path = "c:\\Users\\yedur\\Downloads\\projetcs\\mcp_server\\README.md"

content = """## Installation

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
.\\.venv\\Scripts\\Activate.ps1
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
& "$env:ProgramFiles\\Google\\Chrome\\Application\\chrome.exe" `
  --remote-debugging-address=127.0.0.1 `
  --remote-debugging-port=9222 `
  --user-data-dir "$env:TEMP\\devtools-inspector-chrome"
```

### macOS

```sh
open -na "Google Chrome" --args \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=9222 \
  --user-data-dir="${TMPDIR:-/tmp}/devtools-inspector-chrome"
```

### Linux

```sh
google-chrome \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=9222 \
  --user-data-dir="${TMPDIR:-/tmp}/devtools-inspector-chrome"
```

### Open your website in Chrome

1. Launch Chrome using one of the commands above
2. Open `http://localhost:3000` (or your local development server) in the new Chrome window
3. The page must be open for `list_browser_targets` to discover it
"""
with open(readme_path, "a", encoding="utf-8") as f:
    f.write(content)

print("Installation and Chrome setup appended")