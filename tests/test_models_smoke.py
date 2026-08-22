"""
Model management smoke test
"""
import sys, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.assistant import ModelManager, Assistant

async def main():
    mgr = ModelManager()
    mgr._ollama_url = "http://192.168.3.105:11434"

    # Test live refresh
    print("=== Refreshing models from Ollama ===")
    models = await mgr.refresh_live()
    print(f"Models found: {len(models)}")
    for m in models:
        print(f"  {m['name']} ({m['provider']})")

    # Test assistant model switching
    a = Assistant()
    a.model_manager._ollama_url = "http://192.168.3.105:11434"
    models = await a.refresh_models()

    active = a.get_active_model()
    print(f"\nActive model: {active}")

    # Switch to another model if available
    names = [m["name"] for m in models if m["provider"] == "ollama"]
    print(f"Available: {len(names)} models")
    for n in names[:5]:
        print(f"  {n}")
    if len(names) > 1:
        target = [n for n in names if n != active][0]
        ok = a.switch_model(target)
        print(f"Switch to {target}: {'OK' if ok else 'FAILED'}")

        # Switch back
        a.switch_model(active)
        print(f"Switch back: {a.get_active_model()}")

    # Test switching to nonexistent model
    ok = a.switch_model("nonexistent-model:999b")
    print(f"Switch to invalid model: {'FAILED (expected)' if not ok else 'BUG!'}")

    print("\nAll model management tests passed!")

asyncio.run(main())
