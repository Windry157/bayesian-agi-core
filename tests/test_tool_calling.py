"""
Tool calling end-to-end test with Ollama
"""
import sys, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.uncertainty.text_generator import TextGenerator
from src.core.tools import register_all

register_all()

async def main():
    gen = TextGenerator(
        ollama_url="http://192.168.3.105:11434",
        default_model="gemma4:e4b"
    )

    test_file = Path(__file__).parent / "test_models_smoke.py"
    content = test_file.read_text()[:100]

    prompt = f"请用 read 工具读取文件 {test_file}，然后告诉我文件里有没有 import asyncio"

    print(f"=== 测试 Tool Calling ===")
    print(f"Prompt: {prompt[:80]}...")

    result = await gen.generate_with_tools(
        prompt=prompt,
        model="gemma4:e4b",
    )

    print(f"\nResponse: {result['text'][:300]}")
    print(f"Tool rounds: {len(result.get('tool_rounds', []))}")
    for r in result.get('tool_rounds', []):
        print(f"  Tool: {r.get('tool')}, args: {str(r.get('args', {}))[:80]}")
        print(f"  Output: {r.get('output', '')[:120]}...")

    print(f"\n{'PASS' if result['tool_count'] > 0 else 'NO TOOLS'}")

if __name__ == "__main__":
    asyncio.run(main())
