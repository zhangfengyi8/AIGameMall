# AIGameMall API

API 目录只提供给前端使用的业务接口，不负责页面展示，也不直接实现 agent 能力。

当前 API 只做两件事：

1. 接收 agent 返回结果，转换成前端可渲染的数据。
2. 根据账号 ID 查询账号详情。

## 接口

### 渲染 agent 返回内容

```http
POST /api/v1/agent-results/render
```

前端把 agent 返回的 `reply`、`recommendations`、`history`、`intake` 传给这个接口。

API 会返回两种结果：

- `type: "clarification"`：没有推荐账号，只展示文本，引导用户补充需求。
- `type: "recommendations"`：有推荐账号，返回前端账号卡片列表。

前端主要使用返回字段：

```text
message   展示给用户的文本
cards     推荐账号卡片
history   会话上下文，继续对话时透传
intake    需求解析结果，按需使用
```

### 查询账号详情

```http
GET /api/v1/accounts/{account_id}
```

前端点击推荐卡片后，用卡片的 `id` 查询账号详情。

例如：

```http
GET /api/v1/accounts/listing_10019
```

返回账号标题、价格、区服、段位、资产、风险提示、购买提示等详情数据。

账号不存在时返回 `404`。

## 启动

在部署服务器的 `services/api` 目录下启动 API 服务：

```bash
uv run --python 3.11 aigamemall-api
```

默认监听：

```text
0.0.0.0:8000
```

前端请求时使用服务器地址：

```text
http://<api-server-host>:8000/api/v1/agent-results/render
http://<api-server-host>:8000/api/v1/accounts/{account_id}
```

如需修改监听地址或端口：

```bash
AIGAMEMALL_API_HOST=0.0.0.0 AIGAMEMALL_API_PORT=8080 uv run --python 3.11 aigamemall-api
```

本地开发需要热重载时再显式开启：

```bash
AIGAMEMALL_API_RELOAD=true uv run --python 3.11 aigamemall-api
```

## 测试

```bash
uv run --python 3.11 pytest -q
```

## 当前状态

API 单测已覆盖这两个接口。

当前前端还没有真正接入这些 API；完整链路需要前端调用 API 后才能完成联调。
