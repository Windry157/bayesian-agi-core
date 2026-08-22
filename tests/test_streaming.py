"""
Streaming tool calling test
"""
import sys, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.tools import register_all
from src.core.uncertainty.text_generator import TextGenerator

register_all()

async def main():
    gen = TextGenerator(
        ollama_url="http://192.168.3.105:11434",
        default_model="gemma4:e4b"
    )

    prompt = "列出当前目录下tests文件夹里所有Python文件"

    print("=== Streaming Tool Calling ===")
    events = []
    async for event in gen.generate_with_tools_stream(
        prompt=prompt,
        model="gemma4:e4b",
    ):
        etype = event.get("type")
        if etype == "tool_call":
            print(f"[tool_call] {event['tool']}({str(event['args'])[:60]}...)")
        elif etype == "tool_result":
            print(f"[tool_result] {event['tool']}: {(event.get('output', '') or event.get('error', ''))[:80]}")
        elif etype == "text":
            print(f"[text] {event['content'][:200]}")
        events.append(event)

    print(f"\nTotal events: {len(events)}")
    print("PASS" if any(e["type"] == "tool_call" for e in events) else "NO TOOL CALLS")

if __name__ == "__main__":
    asyncio.run(main())
