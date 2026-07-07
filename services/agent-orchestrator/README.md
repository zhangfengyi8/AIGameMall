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
