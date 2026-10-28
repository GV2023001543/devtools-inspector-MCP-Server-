#!/usr/bin/env sh
# DevTools Inspector MCP - one-command installer (macOS / Linux)
set -eu

PACKAGE_NAME="${DEVTOOLS_INSPECTOR_PACKAGE:-live-devtools-inspector-mcp}"
AGENT=""
PROJECT_ROOT="$(pwd)"
SKIP_CHROME_CHECK=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --agent) AGENT="$2"; shift 2 ;;
    --project-root) PROJECT_ROOT="$2"; shift 2 ;;
    --skip-chrome-check) SKIP_CHROME_CHECK=1; shift ;;
    *) echo "Usage: install.sh [--agent vscode|codex|manual] [--project-root PATH] [--skip-chrome-check]" >&2; exit 2 ;;
  esac
done

echo "DevTools Inspector MCP - one-command installer"

# 1. Prerequisite: uv (required to install and run the packaged server).
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required but was not found on PATH." >&2
  echo "Install uv, then rerun this installer: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

# 2. Prerequisite: Chrome or Chromium (runtime, non-fatal). The MCP server itself
#    keeps the debugging endpoint bound to localhost; it never opens it to the internet.
if [ "$SKIP_CHROME_CHECK" -eq 0 ]; then
  CHROME_FOUND=0
  for candidate in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "$(command -v chromium 2>/dev/null)" \
    "$(command -v chromium-browser 2>/dev/null)" \
    "$(command -v google-chrome 2>/dev/null)" \
    "$(command -v google-chrome-stable 2>/dev/null)" \
  ; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      CHROME_FOUND=1
      break
    fi
  done
  if [ "$CHROME_FOUND" -eq 0 ]; then
    echo "Chrome/Chromium was not found in the default locations." >&2
    echo "DevTools Inspector needs Chrome launched with a loopback-only debugging endpoint (default 127.0.0.1:9222)." >&2
    echo "Example: google-chrome --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir=..." >&2
  fi
fi

# 3. Install DevTools Inspector from the package (idempotent: --force --upgrade).
echo "Installing $PACKAGE_NAME ..."
uv tool install --force --upgrade "$PACKAGE_NAME"

# 4. Configure the selected coding agent. The setup command verifies the server
#    executable starts, backs up and safely merges agent configuration, and is
#    safe to rerun (existing entries are left unchanged).
if [ -n "$AGENT" ]; then
  live-devtools-mcp-setup --agent "$AGENT" --project-root "$PROJECT_ROOT"
else
  live-devtools-mcp-setup --project-root "$PROJECT_ROOT"
fi

echo ""
echo "Installation complete."
echo "Next steps:"
echo "  1. Start Chrome with a dedicated loopback debugging profile (see README: Chrome setup and security)."
echo "  2. Open your website in that Chrome profile."
echo "  3. Use your coding agent to call list_browser_targets (http://127.0.0.1:9222), then connect_browser."
echo "  4. If you did not choose an agent, run: live-devtools-mcp-setup --agent <vscode|codex|manual> --project-root <path>"
echo "Server command: live-devtools-mcp   |   Troubleshooting: see the README Troubleshooting section."
