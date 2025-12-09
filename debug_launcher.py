"""
Safety launcher for debug_logic_flow.py to surface env/import errors.

Usage:
    python debug_launcher.py
"""

import asyncio
import os
import sys
import traceback

from dotenv import load_dotenv


def ensure_path() -> None:
    root = os.path.abspath(os.path.dirname(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)
    src_path = os.path.join(root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def check_env() -> None:
    required = ["OPENAI_API_KEY", "NEO4J_URI", "NEO4J_PASSWORD", "REDIS_URL"]
    for key in required:
        if not os.getenv(key):
            print(f"❌ MISSING ENV: {key}")
        else:
            print(f"✅ {key} loaded")


async def main():
    print("🔄 Loading .env ...")
    load_dotenv(override=True)
    ensure_path()
    check_env()

    print("🚀 Importing debug_logic_flow...")
    try:
        import scripts.debug_logic_flow as dlf  # type: ignore
    except Exception as e:
        print(f"❌ Import/Runtime error during import: {e}")
        traceback.print_exc()
        return

    print("✅ Imported. Running main()...")
    try:
        if hasattr(dlf, "main"):
            await dlf.main()
        else:
            print("⚠️ scripts.debug_logic_flow has no main(); nothing to run.")
    except Exception as e:
        print(f"❌ Runtime error in debug_logic_flow: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
