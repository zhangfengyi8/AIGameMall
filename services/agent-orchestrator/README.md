# Agent Orchestrator Service

Python AI Agent 编排服务，基于 OpenAI Agents SDK。

## 职责

- 接收前端导购请求（通过 API 服务转发）
- 使用 GPT-4o-mini 理解用户自然语言需求
- 调用 search_accounts Tool 从 JSON 数据中筛选账号
- 大模型自行分析性价比（valuation 字段）和风险（risk 字段）
- 生成推荐理由和风险提示

## 架构

第一版采用单 Agent + 单 Tool 架构：

1. 用户输入 → Agent 理解需求 → Tool Call search_accounts → 结果返回大模型 → 最终回复
2. 整个 tool call 循环由 OpenAI Agents SDK 自动编排

## 目录

- `app/agent.py`: Agent 定义与 Runner 封装
- `app/instructions.py`: 系统提示词
- `app/tools/search.py`: search_accounts 工具函数
- `app/fallback/rule_engine.py`: 无模型时的规则降级
- `tests/`: 测试

## 降级策略

当模型调用失败或 API Key 不可用时，自动切换到规则模式，用关键词提取条件并返回模板推荐。


## 模块调用方式

API 服务不需要复制 Agent 内部流程，只需要把 `services/agent-orchestrator` 加入 Python 导入路径，然后调用 `app.agent` 暴露的入口。

### 非流式调用

```python
import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2] / "agent-orchestrator"
sys.path.insert(0, str(AGENT_DIR))

from app.agent import run_agent

result = await run_agent(
    user_message="安卓 QQ，500以内，皮肤多点",
    history=history,
)
```

返回结构：

```json
{
  "reply": "自然语言推荐语或追问",
  "recommendations": [],
  "history": [],
  "intake": {}
}
```

字段说明：

- `reply`: LLM 或规则生成的导购回复。
- `recommendations`: 前端可直接渲染的账号卡片数组；需求模糊时为空数组。
- `history`: 下一轮继续传回 `run_agent()` 或 `run_agent_stream()` 的上下文。
- `intake`: 规则引擎解析出的需求结构，主要用于调试、日志和透明度展示。

### 流式调用

```python
from app.agent import run_agent_stream

async for event in run_agent_stream(
    user_message="安卓 QQ，500以内，皮肤多点",
    history=history,
):
    event_name = event["event"]
    data = event["data"]
```

事件顺序：

1. `strategy`: 推荐策略和候选账号概览，仅在需求明确并开始搜索后输出。
2. `message_delta`: LLM 文本增量，可直接推给前端做打字机效果。
3. `recommendations`: 完整推荐卡片数组，和 LLM 看到的候选账号同源。
4. `done`: 本轮完整结果，包含 `reply`、`recommendations`、`history`、`intake`。

SSE 包装示例：

```python
import json
from fastapi.responses import StreamingResponse


def sse(event: str, data: dict | list) -> str:
    return f"event: {event}
data: {json.dumps(data, ensure_ascii=False)}

"


async def stream():
    async for event in run_agent_stream(message, history):
        yield sse(event["event"], event["data"])

return StreamingResponse(stream(), media_type="text/event-stream")
```

### History 规则

- API 服务负责按 `session_id` 保存 `history`。
- 每次调用前传入上一轮 `history`。
- 每次收到非流式结果或流式 `done` 事件后，用返回的 `history` 覆盖该 session 的历史。
- 第一版不要求持久化，内存保存即可。

### 注意事项

- `run_agent_stream()` 是 Agent 模块提供给 API 的推荐流式入口；API 侧不要重新实现 intake、brief、search 或 LLM 拼装逻辑。
- `recommendations` 由 Agent 规则搜索生成，前端卡片不要从 LLM 文本中解析。
- 使用 OpenAI Agents SDK 的 Responses API，模型网关需要支持 `/responses`。


## API 对接文档

- `docs/api/agent-module-integration.md`: 给 API 侧调用 Agent 模块的非流式、流式、history 和 SSE 对接说明。
