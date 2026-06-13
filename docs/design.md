# RepoPilot Design

## 一句话定位

RepoPilot 是一个面向 AI/ML 开源仓库的复现前诊断 Agent。它通过本地静态分析收集仓库结构、运行入口、环境依赖和复现风险证据，再由 LLM 整理为诊断报告与建议性的 Smoke Test Plan。

## 整体架构

```text
User Prompt
    -> CoreCoder CLI
    -> Agent Loop
    -> Tool Calling
    -> repo_map / entry_detector / env_checker / smoke_test_planner
    -> Evidence-based Diagnosis
    -> LLM Summary
    -> Markdown Report
```

RepoPilot 没有重写通用 Agent 基础设施。CLI、Agent loop、LLM 适配、function calling、并行工具执行、上下文压缩和会话机制来自上游 CoreCoder；RepoPilot 在此基础上增加领域 prompt、四个诊断工具、结构化风险辅助模块和项目文档。

## 完整执行流程

1. 用户通过 `corecoder` CLI 提交当前仓库或指定仓库的诊断任务。
2. CLI 从参数和环境变量加载模型、API Key、API 地址等配置，并创建 LLM 与 Agent。
3. Agent 将 RepoPilot system prompt、用户消息、对话历史和工具 schemas 一并发送给 LLM。
4. LLM 根据任务决定是否调用 `repo_map`、`entry_detector`、`env_checker` 或 `smoke_test_planner`。
5. Agent 执行工具，将返回文本作为 `tool` 消息加入对话，再次调用 LLM。
6. 多个独立工具在同一轮被请求时，可由 CoreCoder 的线程池并行执行。
7. LLM 根据工具证据继续读取文件、补充调查，或者生成最终 Markdown 报告。
8. 当 LLM 不再返回 tool calls 时，Agent loop 结束，普通文本成为最终回答。

项目没有独立的模板化报告引擎。报告结构由 RepoPilot prompt、demo prompt、工具输出和 LLM 综合生成。

## CoreCoder Agent Loop 的复用

CoreCoder 的核心循环可以概括为：

```text
user message
    -> LLM with tools
    -> tool calls?
        -> yes: execute tools -> append results -> call LLM again
        -> no: return final text
```

RepoPilot 保留了这一循环，没有为诊断场景另写调度器。领域能力通过工具注册进入同一 function-calling 协议，因此不会破坏上游的多轮对话、并行执行和上下文压缩机制。

V0.2 对 Agent 层做过一个小修复：Agent 初始化时为当前实例建立 `tool_map`，工具执行从该映射查找，而不是强制依赖全局 `ALL_TOOLS`。默认行为不变，同时真正支持传入自定义工具列表。

## RepoPilot 工具如何接入

每个工具继承 `Tool`，声明：

- `name`：LLM 调用时使用的函数名。
- `description`：告诉 LLM 工具解决什么问题。
- `parameters`：输入参数的 JSON Schema。
- `execute()`：执行静态分析并返回文本结果。

工具实例注册到 `ALL_TOOLS` 后，Agent 会自动：

1. 调用 `schema()` 生成 function-calling 描述；
2. 将 schema 发送给 LLM；
3. 接收模型返回的工具名和参数；
4. 调用对应工具；
5. 把工具结果放回对话。

四个诊断工具的职责如下：

```text
repo_map
    -> 仓库中有什么？

entry_detector
    -> 用户应从哪里启动训练、评估、推理或 Demo？

env_checker
    -> 运行环境和外部资源有哪些静态风险？

smoke_test_planner
    -> 正式运行前可以建议哪些低成本检查？
```

## Evidence-based Diagnosis

RepoPilot 不要求 LLM 直接凭文件名或经验下结论，而是尽量让工具返回可追溯证据，例如：

- 文件路径和行号；
- AST 中发现的函数、main guard 和 import；
- README 中的调用命令；
- 环境文件中解析出的依赖和版本约束；
- 风险类型、严重程度、置信度、影响和修复建议。

报告需要区分：

- **Confirmed facts**：工具或源码直接支持的事实。
- **Inferred assumptions**：基于静态证据做出的合理推断。
- **Static risks**：尚未通过运行验证的潜在风险。
- **Suggested smoke tests**：只建议、不执行的低成本检查。
- **Full reproduction unverified**：完整复现状态仍未验证。

这种设计不能消除 LLM 错误，但可以减少无依据推断，并让用户能够回到原文件复核。

## 为什么 Smoke Test Planner 只生成计划

AI/ML 仓库的入口可能在导入阶段就产生副作用，例如：

- 自动下载数据集或模型权重；
- 初始化 CUDA、分布式环境或多进程 DataLoader；
- 直接进入数百轮训练；
- 执行平台专属 Shell 命令；
- 加载本地不存在的 checkpoint。

因此 `smoke_test_planner` 只分析源码并生成建议命令，不调用 Bash 或 `subprocess`。计划必须明确标记为 `Suggested only, not executed`，避免把“建议运行”写成“已经通过”。

## 为什么不做自动训练和下载

RepoPilot 的目标是复现前诊断，而不是自动复现平台。自动训练或下载会引入：

- 不确定的 GPU、时间、网络和存储成本；
- 外部代码执行和供应链风险；
- 数据许可证与访问权限问题；
- 无法统一控制的运行环境；
- “命令启动成功”被误解为“论文结果复现成功”的风险。

因此项目默认：

- 不训练模型；
- 不下载数据集或 checkpoint；
- 不修改目标仓库；
- 不把静态分析或 Smoke Test Plan 表述为成功复现；
- 要求实际安装、运行、训练和指标复核由用户在受控环境中完成。
