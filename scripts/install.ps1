param(
  [ValidateSet("vscode", "codex", "manual")]
  [string]$Agent,

  [string]$ProjectRoot = (Get-Location).Path,

  [string]$PackageName = "live-devtools-inspector-mcp",

  [switch]$SkipChromeCheck
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "DevTools Inspector MCP - one-command installer" -ForegroundColor Cyan

# 1. Prerequisite: uv (required to install and run the packaged server).
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv is required but was not found on PATH."
    Write-Host "Install uv, then rerun this installer: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Yellow
    exit 1
}

# 2. Prerequisite: Chrome or Chromium (runtime, non-fatal). The MCP server itself
#    keeps the debugging endpoint bound to localhost; it never opens it to the internet.
if (-not $SkipChromeCheck) {
    $chromePaths = @(
        "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
    )
    $chromeFound = $false
    foreach ($path in $chromePaths) {
        if (Test-Path -Path $path -PathType Leaf) {
            $chromeFound = $true
            break
        }
    }
    if (-not $chromeFound) {
        Write-Warning "Chrome/Chromium was not found in the default install locations."
        Write-Host "DevTools Inspector needs Chrome launched with a loopback-only debugging endpoint (default 127.0.0.1:9222)." -ForegroundColor Yellow
        Write-Host "Example: chrome.exe --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 --user-data-dir=`"$env:TEMP\devtools-inspector-chrome`"" -ForegroundColor Yellow
    }
}

# 3. Install DevTools Inspector from the package (idempotent: --force --upgrade).
Write-Host "Installing $PackageName ..."
uv tool install --force --upgrade $PackageName

# 4. Configure the selected coding agent. The setup command verifies the server
#    executable starts, backs up and safely merges agent configuration, and is
#    safe to rerun (existing entries are left unchanged).
if ($Agent) {
    live-devtools-mcp-setup --agent $Agent --project-root $ProjectRoot
} else {
    live-devtools-mcp-setup --project-root $ProjectRoot
}

Write-Host "`nInstallation complete." -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Start Chrome with a dedicated loopback debugging profile (see README: Chrome setup and security)."
Write-Host "  2. Open your website in that Chrome profile."
Write-Host "  3. Use your coding agent to call list_browser_targets (http://127.0.0.1:9222), then connect_browser."
Write-Host "  4. If you did not choose an agent, run: live-devtools-mcp-setup --agent <vscode|codex|manual> --project-root <path>"
Write-Host "Server command: live-devtools-mcp   |   Troubleshooting: see the README Troubleshooting section."
