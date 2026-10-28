# Live DevTools Inspector MCP

Live DevTools Inspector is a local Python MCP server for diagnosing an explicitly selected Chrome page. It collects normalized console/runtime issues, failed network requests, and main-thread performance findings. It can prepare an exact, reviewed source patch for an authorized local repository and run its test suite; it does not gain source access from a public website URL.

## Prerequisites

- Python 3.11 or newer.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for the release installer.
- Chrome or Chromium launched with a loopback-only DevTools debugging endpoint.
- VS Code with an MCP-capable agent, Codex CLI/IDE, or another coding agent that supports local stdio MCP servers.

The package is named `live-devtools-inspector-mcp`. Before publication, verify this name is still available on PyPI and replace the example installer host below with a domain you control.

## Install

The installer is not hosted yet. These are the final public commands only after you publish the package to PyPI and host the matching scripts at a trusted HTTPS URL.

### Windows PowerShell

```powershell
irm https://YOUR-TRUSTED-DOMAIN/install.ps1 | iex
```

To avoid executing a remote script directly, download it, review it, then run it:

```powershell
irm https://YOUR-TRUSTED-DOMAIN/install.ps1 -OutFile install.ps1
Get-FileHash .\install.ps1 -Algorithm SHA256
.\install.ps1 -Agent vscode -ProjectRoot .
```

### macOS and Linux

```sh
curl --fail --location --proto '=https' --tlsv1.2 https://YOUR-TRUSTED-DOMAIN/install.sh | sh
```

The safer reviewed form is:

```sh
curl --fail --location --proto '=https' --tlsv1.2 https://YOUR-TRUSTED-DOMAIN/install.sh -o install.sh
shasum -a 256 install.sh
sh install.sh --agent vscode --project-root .
```

The installer asks for `vscode`, `codex`, or `manual` unless `--agent` is supplied. It requires `uv`, runs `uv tool install --upgrade live-devtools-inspector-mcp`, verifies `live-devtools-mcp` remains running as a stdio server, and configures only the chosen agent.

For development from this checkout:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
```

## VS Code configuration

Run the setup command from the repository you authorize for potential repair:

```sh
live-devtools-mcp-setup --agent vscode --project-root .
```

It safely merges the following entry into `.vscode/mcp.json`, preserving unrelated servers and making a timestamped backup before a change:

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

Open that folder in VS Code, trust the workspace only after reviewing the MCP configuration, then use **MCP: List Servers** to start or inspect the server. Use **MCP: Reset Cached Tools** after upgrades if the new tools do not appear. VS Code uses a top-level `servers` object for `.vscode/mcp.json`; see the [VS Code MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

## Codex configuration

Run setup from the authorized repository:

```sh
live-devtools-mcp-setup --agent codex --project-root .
```

The setup command uses the Codex CLI rather than editing TOML directly:

```sh
codex mcp add live-devtools-inspector --env DEVTOOLS_PROJECT_ROOT="/your/authorized/repository" -- live-devtools-mcp
```

It first runs `codex mcp get live-devtools-inspector`; a matching existing entry is left unchanged. Restart the Codex CLI or IDE extension after setup and use `codex mcp list` or `/mcp` to verify it is available. Codex supports local stdio MCP servers through `codex mcp add`, `~/.codex/config.toml`, or project `.codex/config.toml`; see the [official Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp).

## Other MCP clients

Run the installer with `--agent manual` to print this portable configuration. Add it only to the configuration location documented by your coding agent:

```json
{
  "mcpServers": {
    "live-devtools-inspector": {
      "command": "live-devtools-mcp",
      "args": []
    }
  }
}
```

Agents do not share a universal local configuration path or schema, so the installer intentionally does not guess or overwrite another agent's settings.

## Chrome setup and security

Use a dedicated profile and keep the debugging endpoint bound to loopback. Never expose or forward this port.

### Windows

```powershell
& "$env:ProgramFiles\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-address=127.0.0.1 `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:TEMP\devtools-inspector-chrome"
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

Use a different local port if required, then provide that endpoint to `list_browser_targets`. The server permits only unauthenticated HTTP loopback endpoints and page WebSockets from the selected endpoint. It redacts common secrets and query-string credentials, and it does not collect request/response bodies or headers.

## First scan

1. Open your website in the dedicated debug Chrome profile.
2. Call `list_browser_targets` with `http://127.0.0.1:9222`.
3. Call `connect_browser` using the selected page target ID.
4. Exercise the page, then call `get_live_diagnostics`, `inspect_console`, `inspect_network`, and `inspect_performance`.
5. Use the evidence, severity, and source metadata in the returned findings to investigate. A clean result covers only events observed while monitoring.

`inspect_performance` reports long main-thread tasks from the Long Tasks API when Chrome produces entries. It can also return an explicitly labeled `CDP Tracing fallback` finding. An action is labeled `timing_correlated` only when browser timing intervals overlap; that label is not a causation claim.

## Safe repair workflow

1. Open or explicitly authorize the local source repository first and set `DEVTOOLS_PROJECT_ROOT` to it.
2. Inspect diagnostics and source evidence.
3. Call `propose_fix` with a project-relative path, the current SHA-256, and one unique old/new snippet.
4. Review the proposal. Call `apply_patch` only with `approved=true`.
5. Run `run_project_checks` and rescan the browser page.
6. Report failed checks, incomplete browser verification, and unresolved diagnostics accurately.

The server never treats a public URL as repository authorization, never edits a production deployment, and refuses patch paths outside the authorized project root.

## Troubleshooting

- **`uv` not found:** install uv, then rerun the installer.
- **Server is missing from the agent:** restart or reload the agent, then inspect its MCP server list and logs.
- **Chrome cannot be found:** start Chrome with the loopback command above, open the target page, and call `list_browser_targets` again.
- **No performance finding:** exercise the page after connecting. If neither the Long Tasks API nor the collected trace yields evidence, `inspect_performance` returns an empty list.
- **A configuration conflict:** the setup tool refuses to replace a different server with the same name. Review the existing entry manually.

## Uninstall

Remove the agent configuration first, then uninstall the isolated tool:

```sh
uv tool uninstall live-devtools-inspector-mcp
```

For Codex, run `codex mcp remove live-devtools-inspector`. For VS Code, remove only the `live-devtools-inspector` entry from `.vscode/mcp.json` after reviewing that file's other servers.

## Release preparation

1. Recheck the PyPI package name immediately before upload.
2. Build and inspect artifacts: `uv build`.
3. Test the wheel in a clean virtual environment on each supported platform.
4. Publish only after review: `uv publish`.
5. Host `scripts/install.ps1` and `scripts/install.sh` on a versioned HTTPS release URL you control.
6. Publish SHA-256 checksums and replace `YOUR-TRUSTED-DOMAIN` in the release instructions.

Do not publish the package or installer scripts until the artifacts, URLs, checksums, and release version have been reviewed.
