# Personal Workflow Agent 面试项目说明与开发逻辑

## 为什么推荐做 Personal Workflow Agent

Personal Workflow Agent 很适合作为 agent 开发岗位的面试项目，因为它不是一个普通聊天机器人，而是一个更接近真实产品的个人 AI 助手原型。

目标岗位要求里强调的是新一代个人 AI 助手，尤其是帮助用户处理日常沟通和工作事务，并协调 Email、Chat、Calendar 和其他生产力工具。因此，Personal Workflow Agent 可以直接对应目标产品方向。

你在面试中可以这样解释：

> 我看到这个方向需要构建面向全球用户的个人 AI 助手，所以我做了一个 mini version，用来验证 Email、Calendar、Todo 和 Memory 之间的 agent 协同能力。

这比泛泛地说“我对 agent 感兴趣”更有说服力，因为它展示了你能根据业务目标设计技术原型。

## 这个项目能展示什么能力

这个项目可以展示以下能力：

- Agent 产品理解：知道 agent 不只是聊天，而是要完成任务。
- Tool calling 设计：把邮件、日程、任务、回复草稿封装成可调用工具。
- Workflow orchestration：能把多个工具串联成一个完整工作流。
- 状态管理：能维护 todos、calendar、memory、tool trace。
- 可解释性：通过 tool trace 展示 agent 的执行过程。
- 测试意识：用单元测试验证工具和 agent 行为。
- 工程表达：README、项目结构和 demo 都能服务于面试展示。

## 为什么不建议只做普通 RAG 或聊天机器人

普通 RAG 项目常见结构是：

```text
用户问题 -> 检索文档 -> LLM 回答
```

这种项目当然有价值，但对于个人 AI 助手岗位来说，它展示的能力不够完整。

Personal Workflow Agent 的结构更接近真实助手：

```text
用户目标 -> 读取上下文 -> 调用工具 -> 判断冲突 -> 创建行动 -> 生成总结
```

它不只是回答问题，而是能把信息转化为行动。

## 项目核心定位

Personal Workflow Agent 的核心定位是：

> 一个能理解用户目标，并在 Email、Calendar、Todo、Memory 等工具之间协调行动的个人工作流 Agent。

它需要做到：

- 读邮件
- 看日历
- 找冲突
- 判断优先级
- 创建待办
- 草拟回复
- 输出 daily brief
- 记录每一步工具调用

## 推荐技术栈

### 主语言

推荐使用 Python。

原因：

- Python 的 AI 和 agent 生态最好。
- FastAPI、Pydantic、SQLite、OpenAI SDK 等工具成熟。
- 面试中更容易快速展示原型。
- 适合从规则版 agent 平滑升级到 LLM agent。

### 后端

```text
Python
FastAPI
Pydantic
SQLite
pytest / unittest
```

### Agent 层

```text
OpenAI API 或其他 LLM API
Tool calling / function calling
Planner
Memory
Workflow state
Tool trace
```

### 数据层

早期：

```text
JSON mock data
```

升级后：

```text
SQLite
```

可选长期记忆：

```text
Chroma / FAISS
```

### 前端

第一版可以用：

```text
HTML / CSS / JavaScript
```

如果想做成更正式的产品展示，可以用：

```text
React + Vite
```

### 部署和工程化

```text
GitHub
GitHub Actions
Docker
Render / Railway / Fly.io
```

## 项目分层设计

### 1. 数据层

数据层负责存储用户上下文。

包括：

```text
emails
calendar_events
todos
user_memory
tool_calls
agent_runs
```

当前项目使用 JSON 文件作为 mock 数据。后续可以替换成 SQLite。

### 2. 工具层

工具层是 agent 能安全行动的边界。

每个工具都是一个明确的函数：

```python
search_email()
list_calendar_events()
detect_calendar_conflicts()
add_todo()
draft_reply()
```

Agent 不应该直接修改数据，而应该通过工具完成动作。

这样有三个好处：

- 行为可控
- 容易测试
- 方便记录 trace

### 3. Agent 决策层

Agent 决策层负责决定下一步做什么。

它需要处理：

```text
理解用户目标
决定调用哪些工具
读取工具结果
判断是否需要继续行动
生成最终回复
```

当前项目可以先使用规则 planner。

例如：

```python
if goal contains "today" or "brief":
    search important emails
    list calendar events
    detect conflicts
    create todos
    draft replies
```

后续可以升级成 LLM planner，让模型根据工具 schema 自己选择工具。

### 4. API 层

API 层用于把项目从 CLI demo 变成产品后端。

推荐接口：

```text
POST /agent/run
GET /agent/runs
GET /agent/runs/{id}
GET /emails
GET /calendar
GET /todos
```

### 5. UI 层

UI 层用于展示 agent 的结果和过程。

建议页面布局：

```text
左侧：用户输入目标
中间：Daily Brief / Agent Result
右侧：Tool Trace
下方：Emails / Calendar / Todos
```

面试时，tool trace 的展示非常重要。它能证明 agent 是一步步完成任务，而不是黑箱回答。

## 底层逻辑

Agent 的底层逻辑可以概括成：

```text
Goal -> Plan -> Tool Call -> Observation -> Next Action -> Final Answer
```

更具体：

```text
用户目标
  ↓
Planner 判断需要哪些信息
  ↓
调用工具读取邮件 / 日程 / 任务
  ↓
获得 Observation
  ↓
判断优先级、冲突和下一步行动
  ↓
调用工具创建 todo / 草拟回复
  ↓
生成最终 daily brief
  ↓
记录 tool trace
```

## 一个典型执行流程

用户输入：

```text
帮我看看今天有什么重要事情。
```

Agent 执行：

```text
1. load_memory
2. search_email(unread_only=True, priority="high")
3. list_calendar_events(today)
4. detect_calendar_conflicts(today)
5. add_todo("Review A1 product proposal")
6. draft_reply(email)
7. return daily brief
```

输出：

```text
Daily Brief
1. Important email from Alex Chen: Confirm A1 product proposal by 15:00.
2. Todo created: Review A1 product proposal due 15:00.
3. Reply draft prepared to Alex Chen.
4. Calendar conflict detected: Deep Work overlaps with Proposal Review.
5. Today's calendar: Deep Work, Proposal Review, Evening Study.
```

## 为什么 tool trace 很重要

Agent 项目的一个核心问题是可解释性。

如果只输出结果，面试官无法判断 agent 是怎么工作的。

Tool trace 可以展示：

```text
调用了什么工具
传入了什么参数
拿到了什么结果
为什么产生下一步动作
```

这能体现你理解 agent 的工程化问题：

- 可调试
- 可审计
- 可测试
- 可复现

## 开发路线

### 第一阶段：规则版 CLI Agent

目标：

```text
让项目能跑起来，并展示完整 agent loop。
```

要做：

- JSON mock 数据
- 工具层
- 规则 planner
- CLI demo
- 单元测试

当前项目已经完成这一阶段的基础版本。

### 第二阶段：SQLite 数据层

目标：

```text
让项目更像真实后端服务。
```

要做：

- 设计 SQLite schema
- 迁移 emails、calendar、todos、memory
- 保存 agent runs
- 保存 tool calls
- 增加数据访问层

### 第三阶段：FastAPI 后端

目标：

```text
把 CLI demo 变成可调用 API。
```

要做：

```text
POST /agent/run
GET /agent/runs/{id}
GET /emails
GET /calendar
GET /todos
```

### 第四阶段：Web Dashboard

目标：

```text
做出面试时能直接演示的产品界面。
```

要做：

- 用户目标输入框
- daily brief 展示
- tool trace 展示
- email/calendar/todo 三栏
- 一键运行 demo

### 第五阶段：LLM Tool Calling

目标：

```text
从规则 agent 升级到 LLM agent。
```

要做：

- 定义工具 schema
- 接入 OpenAI tool calling
- 保留规则 planner 作为 fallback
- 对 LLM 决策结果做安全校验
- 记录 LLM message 和 tool call

## 面试表达方式

你可以这样介绍项目：

> 这个项目是一个个人工作流 Agent 原型。我没有只做普通聊天框，而是把 Email、Calendar、Todo 和 Memory 抽象成工具，让 agent 可以根据用户目标调用工具、读取上下文、发现日程冲突、创建待办、草拟回复，并输出可追踪的 daily brief。

如果面试官问底层逻辑：

> 底层是一个 Goal -> Plan -> Tool Call -> Observation -> Action -> Final Answer 的循环。当前版本 planner 是规则版，优点是稳定、可测试；下一步可以替换为 LLM tool-calling planner，但工具层和 trace 机制保持不变。

如果面试官问为什么不用纯 LLM：

> 因为个人助手需要可靠地操作用户数据，不能只依赖模型自由生成。工具层提供了安全边界，trace 提供了可解释性，测试保证关键行为可复现。

## 项目最终目标

这个项目最终应该展示：

- 你理解 agent 产品不是聊天，而是工作流自动化。
- 你会设计工具和状态。
- 你能写可运行、可测试、可解释的 agent。
- 你能根据岗位方向做有针对性的作品集项目。

