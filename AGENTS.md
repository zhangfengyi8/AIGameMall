# AGENTS.md

本文件用于指导 AI Agent 在本仓库中进行开发、阅读代码与维护项目进度。

## 项目定位

AIGameMall 是一个面向游戏账号 C2C 交易场景的 AI 智能导购项目。

项目目标是让用户通过自然语言或语音描述需求，由 AI 理解预算、游戏偏好、段位、皮肤、英雄、换绑状态与风险偏好，并基于结构化账号 JSON 数据推荐匹配账号，同时输出性价比、公允估价与风险提示。

## 开发原则

- 开发必须围绕 `docs/PROGRESS.md` 中的进度清单逐步推进。
- 每完成一个阶段或任务，需要同步更新 `docs/PROGRESS.md` 的状态。
- 当前阶段不引入数据库，账号、标签和样例数据优先使用 JSON 文件管理。
- 当前阶段不处理部署能力，不需要 Docker、Nginx 或生产部署脚本。
- 当前阶段不包含管理端，前端只保留用户侧 `frontend`。
- 后端使用 Python 技术栈。
- 保持目录职责清晰，避免把业务代码混放到无关目录。
- 优先做最小可运行闭环，再逐步补充推荐策略和 Agent 能力。

## 目录概览

- `frontend`: 用户侧纯 HTML/JS 前端。
- `services/api`: Python 业务 API 服务。
- `services/agent-orchestrator`: Python Agent 编排服务（含 skills 模块）。
- `packages`: 后端共享 Python 包。
- `data`: JSON 数据目录，用于账号、标签与样例数据查询。
- `docs`: 产品、架构、API、Agent 设计文档与开发进度。
- `configs`: 仓库级配置。
- `scripts`: 本地开发辅助脚本。

## 重点文件

- `docs/git-commit-convention.md`: Git 提交规范，Agent 提交前必须阅读。
- `docs/product/mall-ai-guide.md`: 商城页与 AI 导购产品说明。
- `docs/architecture/json-data-schema.md`: JSON 数据结构设计。
- `docs/architecture/open-questions.md`: 待确认问题清单。
- `docs/api/api-design.md`: API 接口设计草案。
- `docs/api/frontend-integration.md`: 前后端对接说明。
- `docs/agents/2026-07-07-agent-orchestrator-design.md`: Agent 编排技术设计。
- `docs/PROGRESS.md`: 项目开发进度与阶段任务清单，开发时必须优先阅读。
- `README.md`: 项目总览与仓库结构说明。
- `services/api/README.md`: API 服务职责说明。
- `services/agent-orchestrator/README.md`: Agent 编排服务职责说明。
- `services/agent-orchestrator/app/skills/requirement_intake.py`: 买家需求理解技能（规则引擎）。
- `services/agent-orchestrator/app/skills/recommendation_brief.py`: 账号推荐简报技能（规则引擎）。
- `services/agent-orchestrator/skills/buyer-requirement-intake/SKILL.md`: 需求理解技能定义。
- `services/agent-orchestrator/skills/account-recommendation-brief/SKILL.md`: 推荐简报技能定义。
- `data/README.md`: JSON 数据目录说明。
- `packages/README.md`: 共享 Python 包说明。

## Agent 编排服务核心模块

### 技能模块（rules-based，先于 LLM 执行）

| 模块 | 文件 | 职责 |
|---|---|---|
| buyer-requirement-intake | `app/skills/requirement_intake.py` | 从用户消息提取预算、平台、段位、英雄/皮肤、风险偏好，输出结构化槽位 |
| account-recommendation-brief | `app/skills/recommendation_brief.py` | 将需求转为搜索过滤条件、排序权重、降级策略 |

### 执行流程

```
用户消息
  ↓
① intake() 规则解析 → 需求结构化
  ↓
② 需求模糊？→ 追问，不搜索
  ↓
③ build_query() 构建推荐策略
  ↓
④ _do_search() 规则搜索（只搜一次）
  ↓
⑤ 候选数据 + 策略注入 LLM → LLM 写推荐语
  ↓
⑥ 返回 { reply, recommendations, history, intake }
```

- 搜索只做一次，卡片数据和 LLM 看到的候选数据同源。
- 需求模糊时 `recommendations` 为空数组。

## Git 提交规范

Agent 创建提交时必须遵守 `docs/git-commit-convention.md`。关键规则：

- 标题格式 `<type>(<scope>): <subject>`。
- 一个提交只做一件事。
- 提交前 `git pull --rebase`。
- 不创建空提交或无意义提交。

## 开发顺序要求

Agent 开发项目时，应按照以下顺序推进：

1. 阅读 `docs/PROGRESS.md`，确认当前下一步任务。
2. 阅读与当前任务相关的 README 或设计文档。
3. 只修改当前任务必要的文件，避免无关重构。
4. 完成代码或文档变更后，更新 `docs/PROGRESS.md` 对应任务状态。
5. 如果任务涉及代码，尽量补充最小验证方式。
6. 在最终回复中说明修改了哪些文件，以及下一步建议执行什么。

## 当前技术约束

- 后端语言：Python。
- 前端技术：纯 HTML、CSS、JavaScript。
- 数据来源：本地 JSON 文件（关联表结构）。
- 数据库：当前阶段不使用。
- 部署：当前阶段不要求。
- 管理端：当前阶段不包含。

## 后端职责划分

### `services/api`

面向前端提供 HTTP API，建议承担：

- 健康检查接口。
- 账号列表查询接口。
- 账号详情查询接口。
- AI 导购推荐接口（调用 agent-orchestrator 模块）。
- 统一接口响应格式。

### `services/agent-orchestrator`

负责 AI 导购核心流程，采用规则引擎前置 + LLM 推荐的架构：

- **app/skills/requirement_intake.py**: 用户自然语言需求理解，预算/平台/段位/英雄/皮肤/风险偏好槽位抽取。
- **app/skills/recommendation_brief.py**: 搜索策略构建、排序权重、降级方案。
- **app/tools/search.py**: JSON 关联表查询工具。
- **app/agent.py**: Agent 编排主流程，组装技能模块 + LLM。
- **app/fallback/rule_engine.py**: 无模型时的规则降级兜底。

### `packages`

用于存放跨服务共享代码，建议承担：

- `packages/shared`: 通用工具、错误码、响应结构。
- `packages/types`: 共享数据结构、DTO、TypedDict 或 Pydantic 模型。
- `packages/config`: 配置读取与环境变量处理。
- `packages/ai-core`: LLM Client、Prompt 基础封装、AI 通用能力。

### `data`

用于存放 JSON 数据，建议承担：

- `data/accounts`: 游戏账号商品数据。
- `data/tags`: 标签、枚举、映射关系等结构化数据（关联表）。
- `data/samples`: 开发阶段样例数据。

## 进度维护规则

- 未开始任务使用 `[ ]`。
- 进行中任务使用 `[~]`。
- 已完成任务使用 `[x]`。
- 如果新增任务，应添加到 `docs/PROGRESS.md` 的合适阶段。
- 如果发现原计划不合理，应先调整 `docs/PROGRESS.md`，再继续开发。
- 不要跳过当前阶段直接做后续复杂功能，除非用户明确要求。

## 代码风格建议

- Python 代码优先保持清晰、简单、可测试。
- 命名应表达业务含义，避免缩写和单字母变量。
- 业务逻辑、数据读取、推荐策略、API 路由应分层放置。
- 不要提前引入复杂基础设施。
- 不要添加与当前任务无关的依赖。

## 第一版目标

第一版应优先完成以下闭环：

1. 用户在前端输入自然语言需求。
2. API 服务接收请求。
3. Agent 编排服务解析需求（intake → brief → search）。
4. 系统从 JSON 数据中筛选账号。
5. 系统返回推荐账号卡片（recommendations 数组）。
6. 前端展示 AI 推荐语 + 可点击的卡片。