# Git 提交规范

## 总体原则

- **语义化提交**：每次提交只做一件事，描述改动意图，而非描述代码本身。
- **粒度控制**：每完成一个逻辑独立的功能点或修复即提交，避免一个提交包含多个无关改动。
- **语言**：提交标题用英文，正文可用中文描述详情。
- **使用 Agent 时**：Agent 提交前阅读本规范，生成符合规范的提交信息。

## 提交信息格式

```
<type>(<scope>): <subject>

<body>
```

### type（必填）

| type | 说明 | 示例 |
|---|---|---|
| `feat` | 新功能 | `feat(agent): add buyer-requirement-intake slot extraction` |
| `fix` | 修复 bug | `fix(search): handle empty skin list crash` |
| `docs` | 文档变更 | `docs(api): update guide/chat response schema` |
| `refactor` | 重构 | `refactor(agent): extract skill modules from agent.py` |
| `test` | 测试 | `test(agent): add intake edge case tests` |
| `chore` | 杂项 | `chore: add git-commit-convention.md` |
| `style` | 代码格式 | `style: remove unused imports` |

### scope（可选）

表示变更范围，推荐使用以下值：

- `agent` — Agent 编排服务
- `api` — API 服务
- `frontend` — 前端
- `search` — 搜索/数据查询
- `data` — JSON 数据
- `docs` — 文档
- `config` — 配置文件
- `deps` — 依赖管理

### subject（必填）

- 不超过 72 个字符
- 英文，首字母小写
- 不要句号结尾
- 用祈使句（"add" 而非 "added" 或 "adds"）

### body（可选）

- 与 subject 之间空一行
- 说明为什么要改、怎么改的
- 每行不超过 72 个字符

## 提交示例

```
feat(agent): add buyer-requirement-intake skill module

Implement slot extraction for budget, platform, rank, heroes,
skins, and risk preference from user natural language input.
```

```
docs(api): update guide/chat response with intake field

Add intake debug field to agent response for transparency.
Update the response example to match actual format_card output.
```

```
fix(search): normalize price unit from yuan to fen

Search was comparing yuan with fen values stored in JSON,
causing incorrect budget filter results.
```

## AI Agent 提交规则

当 AI Agent 在本仓库创建提交时，必须遵守以下规则：

1. **提交前**：阅读本文件。
2. **提交标题**：必须符合 `<type>(<scope>): <subject>` 格式。
3. **提交范围**：一个提交只允许一种 type，scope 应与实际改动文件保持一致。
4. **混合文件处理**：
   - 如果同时改动了代码和文档，主 type 按代码类型走，文档部分在 body 中说明。
   - 不相关的改动（如改 A 功能时顺手修了 B 功能的拼写）应拆成独立提交。
5. **不得创建空提交或无意义提交**（如 "fix typo"、"update"、"wip"）。

## 工作流程建议

1. 开发前：`git pull --rebase` 拉取最新。
2. 开发中：小步提交，频繁 `git commit`。
3. 开发完：`git rebase -i` 整理提交历史（如有需要）。
4. 推送前：确保没有调试代码和多余 `print`。
5. 推送后：创建 Pull Request，PR 标题也遵循本规范。