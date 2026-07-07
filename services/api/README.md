# AIGameMall API

API 是前端和 agent 之间的后端接口层。前端只依赖 API 返回的稳定结构，不直接依赖 agent 原始输出。

## 整体链路

```text
前端输入需求
  -> POST /api/v1/chat/stream
  -> API 调用 agent
  -> API 透传文本增量并判断最终内容类型
  -> 前端流式展示文本或账号卡片

前端点击账号卡片
  -> GET /api/v1/accounts/{account_id}
  -> API 返回账号详情
```

## 前端调用的接口

### 1. 用户对话，流式

```http
POST /api/v1/chat/stream
```

前端优先调用这个接口提交用户需求，响应类型是 `text/event-stream`。

请求字段：

```text
session_id  会话 ID
message     用户输入
history     上一次 done 事件返回的会话上下文，可为空
```

SSE 事件：

```text
message_delta    文本增量，前端用于打字机展示
recommendations  推荐账号卡片，前端展示卡片
done             本轮最终结果，包含 type/message/cards/history/intake
error            agent 调用失败
```

`done` 事件字段：

```text
type      返回内容类型：clarification 或 recommendations
message   展示给用户的文本
cards     推荐账号卡片，可能为空
history   会话上下文，下一轮继续透传
intake    agent 需求解析结果，前端按需使用
```

前端展示规则：

```text
type = clarification
  只展示 message，引导用户补充需求

type = recommendations
  展示 message 和 cards 账号卡片
```

### 2. 用户对话，非流式

```http
POST /api/v1/chat
```

非流式兼容接口。请求字段和 `/api/v1/chat/stream` 一样，直接返回完整 JSON：

```text
type
message
cards
history
intake
```

### 3. 账号详情

```http
GET /api/v1/accounts/{account_id}
```

前端点击推荐卡片后调用这个接口。

例如：

```http
GET /api/v1/accounts/listing_10019
```

返回账号标题、价格、区服、段位、资产、风险提示、购买提示等详情数据。

账号不存在时返回 `404`。

## API 调用 agent

`POST /api/v1/chat/stream` 和 `POST /api/v1/chat` 内部都会调用 agent。

当前调用方式：

```text
app.routers.chat
  -> app.services.agent_client.run_agent_stream(...)
  -> services/agent-orchestrator

app.routers.chat
  -> app.services.agent_client.run_agent(...)
  -> services/agent-orchestrator
```

agent 返回的核心字段：

```text
reply             agent 文本回复
recommendations   推荐账号列表，可能为空
history           会话上下文
intake            需求解析结果
```

## 如何区分 agent 返回内容

区分逻辑在 API 内部完成，前端不需要直接判断 agent 原始字段。

判断规则：

```text
recommendations 为空
  -> type = clarification
  -> 表示 agent 在引导用户补充需求

recommendations 不为空
  -> type = recommendations
  -> 表示 agent 返回了推荐账号
```

这层转换逻辑在：

```text
app/routers/agent_results.py
```

它不是前端直接调用的接口，只是 API 内部把 agent 结果转换成前端展示结构。

## 启动服务

在 `services/api` 目录下启动：

```bash
uv run --python 3.11 python -m app.server
```

默认监听：

```text
0.0.0.0:8000
```

当前局域网访问地址：

```text
http://192.168.10.132:8000
```

前端使用：

```text
POST http://192.168.10.132:8000/api/v1/chat/stream
POST http://192.168.10.132:8000/api/v1/chat
GET  http://192.168.10.132:8000/api/v1/accounts/{account_id}
```

如果网络切换，`192.168.10.132` 可能变化，需要重新用 `ipconfig` 查看 WLAN 的 IPv4 地址。

## 测试

```bash
uv run --python 3.11 pytest -q
```
