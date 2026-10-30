import asyncio
import sys
sys.path.insert(0, "src")
from devtools_inspector.server import mcp

async def main():
    tools = await mcp.list_tools()
    for t in tools:
        print(f'{t.name}:')
        # Call the schema method
        schema = t.schema() if callable(t.schema) else t.schema
        if isinstance(schema, dict):
            props = schema.get('properties', {})
            print(f'  Properties: {list(props.keys())}')
            for name, prop in props.items():
                print(f'    {name}: {prop}')
        else:
            print(f'  Schema: {schema}')

asyncio.run(main())