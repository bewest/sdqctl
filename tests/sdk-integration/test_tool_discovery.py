#!/usr/bin/env python3
"""
SDK Integration Test: Full tool and model discovery
"""
import asyncio
import sys
import json

sys.path.insert(0, '/home/bewest/src/copilot-sdk/python')

from copilot import CopilotClient
from copilot.types import SubprocessConfig
from copilot.generated.rpc import ToolsListParams

CLI_PATH = "/home/bewest/.local/bin/copilot"

async def main():
    config = SubprocessConfig(cli_path=CLI_PATH)
    client = CopilotClient(config)
    
    try:
        await client.start()
        
        # List models
        models = await client.rpc.models.list()
        print(f"# Available Models ({len(models.models)})")
        for m in models.models:
            reasoning = f" (reasoning: {m.default_reasoning_effort})" if m.default_reasoning_effort else ""
            billing = f" [x{m.billing.multiplier}]" if m.billing else ""
            print(f"  - {m.id}: {m.name}{billing}{reasoning}")
        print()
        
        # List tools
        result = await client.rpc.tools.list(ToolsListParams())
        print(f"# Default Tools ({len(result.tools)})")
        for tool in sorted(result.tools, key=lambda t: t.name):
            print(f"  - {tool.name}")
        print()
        
        # Output full tool details for docs
        print("# Tool Details")
        for t in sorted(result.tools, key=lambda t: t.name):
            print(f"\n## {t.name}")
            desc_lines = t.description.split('\n')
            print(f"Description: {desc_lines[0][:120]}")
            if t.namespaced_name:
                print(f"Namespaced: {t.namespaced_name}")
            if t.parameters:
                props = t.parameters.get("properties", {})
                required = t.parameters.get("required", [])
                print(f"Parameters ({len(props)}):")
                for p, spec in list(props.items())[:8]:
                    req = "*" if p in required else ""
                    ptype = spec.get("type", "")
                    print(f"  - {p}{req}: {ptype}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
