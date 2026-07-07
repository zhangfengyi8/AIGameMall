"""
Agent 交互式测试脚本。
可直接运行：python test_agent.py
输入消息进行对话，输入 quit 退出。
"""
import os
os.environ["AGENTS_TRACING_ENABLED"] = "false"

import sys
import asyncio
import io

from agents import set_tracing_disabled
set_tracing_disabled(True)

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    with open(str(_env_path), encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    print("=" * 60)
    print("[WARNING] 未设置 OPENAI_API_KEY，使用规则降级模式")
    print("=" * 60)

    from app.fallback.rule_engine import run_fallback

    print("\n=== 游戏账号导购助手（输入 quit 退出）===")
    try:
        while True:
            msg = input("\n[你] ")
            if msg.lower() in ("quit", "exit", "q"):
                break
            if not msg.strip():
                continue
            result = run_fallback(msg)
            print(f"\n[导购] {result['reply']}")
    except (EOFError, KeyboardInterrupt):
        print("\n再见！")

else:
    from app.agent import run_agent_stream

    async def main():
        history = None
        print("\n=== 游戏账号导购助手（输入 quit 退出）===")
        try:
            while True:
                msg = input("\n[你] ")
                if msg.lower() in ("quit", "exit", "q"):
                    break
                if not msg.strip():
                    continue
                print("\n[导购] ", end="", flush=True)
                final_result = None
                async for event in run_agent_stream(msg, history):
                    event_name = event["event"]
                    data = event["data"]
                    if event_name == "message_delta":
                        print(data["text"], end="", flush=True)
                    elif event_name == "done":
                        final_result = data
                print()
                if final_result:
                    history = final_result["history"]
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")

    asyncio.run(main())
