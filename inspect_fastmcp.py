#!/usr/bin/env python3
import sys
sys.path.insert(0, r'C:\Users\yedur\Downloads\projetcs\mcp_server\src')

# Read fastmcp.client.client module - look for Client class and active client tracking
with open(r'C:\Users\yedur\Downloads\projetcs\mcp_server\.venv-1\Lib\site-packages\fastmcp\client\client.py', 'r') as f:
    content = f.read()

# Print the full file
print(content)