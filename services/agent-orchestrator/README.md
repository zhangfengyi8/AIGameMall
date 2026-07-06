# Agent Orchestrator Service

Python AI Agent 编排服务。

建议职责：

- 理解用户自然语言/语音转文本需求
- 抽取游戏、预算、段位、皮肤、英雄、风险偏好等条件
- 调用 JSON 查询工具进行账号召回
- 对候选账号进行推荐排序
- 生成性价比、公允估价与风险提示

建议后续技术选型：LangGraph / OpenAI Agents SDK / 自研轻量工作流。
