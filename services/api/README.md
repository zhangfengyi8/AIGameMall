# API Service

Python 业务 API 服务。

建议职责：

- 接收前端导购请求
- 暴露账号查询、推荐结果、详情卡片等 API
- 调用 Agent 编排服务完成智能推荐
- 读取 `data` 目录下的 JSON 数据
- 返回前端可直接渲染的卡片结构

建议后续技术选型：FastAPI。
