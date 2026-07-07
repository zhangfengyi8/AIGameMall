# Agent 模块对接说明（给 API 侧）

本文档说明 API 服务如何调用 `services/agent-orchestrator`，包括非流式、流式、history 管理和返回字段约定。

## 对接边界

API 侧只负责：

1. 接收前端请求。
2. 根据 `session_id` 读取上一轮 `history`。
3. 调用 Agent 模块。
4. 将 Agent 返回内容包装成 HTTP JSON 或 SSE。
5. 保存 Agent 返回的新 `history`。

API 侧不要重复实现：

- 需求解析 `intake()`。
- 推荐策略 `build_query()`。
- JSON 搜索 `_do_search()`。
- LLM prompt 拼装。
- 推荐卡片 `format_card()`。

这些能力由 `app.agent.run_agent()` 和 `app.agent.run_agent_stream()` 统一封装。

## Python 导入方式

如果 API 服务和 Agent 服务保持当前目录关系：

```text
services/
├── api/
└── agent-orchestrator/
```

API 侧可在启动时加入导入路径：

```python
import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parents[2] / "agent-orchestrator"
sys.path.insert(0, str(AGENT_DIR))
```

然后按需导入：

```python
from app.agent import run_agent, run_agent_stream
```

如果 API 自身包名也叫 `app`，可能与 Agent 的 `app` 包冲突。建议 API 同学选择其中一种方式：

1. 在进程启动最早阶段加入 `agent-orchestrator` 路径，再导入 Agent。
2. 后续重命名 Agent 包名，例如 `agent_app` 或 `aigamemall_agent`。
3. 用独立适配层封装导入，避免业务路由里直接处理路径。

## 请求字段约定

前端到 API 建议请求体：

```json
{
  "session_id": "sess_001",
  "message": "安卓 QQ，500以内，皮肤多点"
}
```

API 传给 Agent 的参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_message` | `str` | 是 | 用户本轮输入，即前端传来的 `message` |
| `history` | `list \/ None` | 否 | 该 session 上一轮 Agent 返回的 history，第一轮可传 `None` 或 `[]` |

## History 职责划分

Agent 侧负责：

- 基于本轮输入和上一轮 `history` 生成模型上下文。
- 返回下一轮应继续使用的新 `history`。

API 侧负责：

- 根据 `session_id` 存取 `history`。
- 调用前传入旧 `history`。
- 调用后保存新 `history`。

第一版可使用内存字典：

```python
sessions: dict[str, list] = {}

history = sessions.get(session_id, [])
result = await run_agent(user_message=message, history=history)
sessions[session_id] = result["history"]
```

后续如果要多实例部署，再替换为 Redis 或数据库。

## 非流式调用

```python
from app.agent import run_agent

async def guide_chat(session_id: str, message: str):
    history = sessions.get(session_id, [])

    result = await run_agent(
        user_message=message,
        history=history,
    )

    sessions[session_id] = result["history"]
    return result
```

返回结构：

```json
{
  "reply": "自然语言推荐语或追问",
  "recommendations": [
    {
      "account_id": "listing_10019",
      "accountId": "acc_100019",
      "game_code": "WZ",
      "server_code": "ANDROID_QQ",
      "price": 399,
      "vip_level": 4,
      "rank_name": "钻石",
      "rank_stars": 0,
      "anti_addiction": "NONE",
      "secondary_real_name": "SUPPORTED",
      "change_bind": "FULL_SUPPORTED",
      "skin_count": 5,
      "hero_count": 5,
      "value_score": 101.55,
      "heroes": ["英雄名称"],
      "skins": ["皮肤名称"]
    }
  ],
  "history": [],
  "intake": {}
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `reply` | 展示给用户的导购文本 |
| `recommendations` | 前端可直接渲染的账号卡片；需求模糊时为空数组；最多 3 个 |
| `history` | API 必须保存，下一轮传回 Agent |
| `intake` | 需求解析结果，可用于日志和调试，前端可忽略 |

## 流式调用

```python
from app.agent import run_agent_stream

async for event in run_agent_stream(
    user_message=message,
    history=history,
):
    event_name = event["event"]
    data = event["data"]
```

事件类型：

| event | data | 说明 |
|---|---|---|
| `strategy` | `{ filters, weights, account_count, account_ids }` | 推荐策略和候选账号概览 |
| `message_delta` | `{ text }` | LLM 文本增量，用于打字机效果 |
| `recommendations` | `RecommendationCard[]` | 完整推荐卡片数组，命中多少返回多少，最多 3 个 |
| `done` | `{ reply, recommendations, history, intake }` | 本轮结束，API 在这里保存 `history` |

需求模糊时通常只会输出：

1. `message_delta`
2. `done`

需求明确时通常输出：

1. `strategy`
2. 多个 `message_delta`
3. `recommendations`（最多 3 个商品卡片 JSON）
4. `done`

## SSE 包装示例

```python
import json
from fastapi.responses import StreamingResponse
from app.agent import run_agent_stream


def sse(event: str, data: dict | list) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def guide_chat_stream(session_id: str, message: str):
    history = sessions.get(session_id, [])

    async def stream():
        async for event in run_agent_stream(message, history):
            if event["event"] == "done":
                sessions[session_id] = event["data"]["history"]
            yield sse(event["event"], event["data"])

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

## 错误处理建议

API 侧建议捕获 Agent 调用异常：

```python
try:
    result = await run_agent(message, history)
except Exception as exc:
    # 记录日志，返回统一错误结构
    ...
```

流式接口建议输出 `error` 事件：

```python
try:
    async for event in run_agent_stream(message, history):
        yield sse(event["event"], event["data"])
except Exception as exc:
    yield sse("error", {"message": str(exc)})
```

## 本地验证

Agent 侧本地交互测试：

```bash
cd services/agent-orchestrator
python test_agent.py
```

`test_agent.py` 已支持流式打印，并在本地变量中维护当前进程内的 `history`。

## 注意事项

- 当前 Agent 使用 OpenAI Agents SDK 的 Responses API，模型网关需要支持 `/responses`。
- `OPENAI_MODEL` 必须使用网关支持的模型别名，例如当前网关提示的 `auto`、`pro`、`flash` 等。
- API 侧不要从 `reply` 文本里解析账号卡片，应直接使用 `recommendations`。
- `history` 不建议由前端直接长期保存，第一版建议 API 内存保存；后续可换 Redis。
