readme_path = "c:\\Users\\yedur\\Downloads\\projetcs\\mcp_server\\README.md"

lines = []
lines.append("# Live DevTools Inspector MCP")
lines.append("")
lines.append("A local Python MCP server for diagnosing an explicitly selected Chrome page.")
lines.append("It collects normalized console/runtime issues, failed network requests, and main-thread performance findings.")
lines.append("It can prepare an exact, reviewed source patch for an authorized local repository and run its test suite;")
lines.append("it does not gain source access from a public website URL.")
lines.append("")
lines.append("The package is named `devtools-inspector-mcp`. Verify this name is available on PyPI before publishing.")
lines.append("")
lines.append("---")
lines.append("")

with open(readme_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("First chunk written successfully")