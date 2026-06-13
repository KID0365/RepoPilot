# RepoPilot V1.0 架构与设计

## 项目定位

RepoPilot 是面向 AI/ML 开源仓库的复现前诊断 Agent。它通过 static analysis 收集仓库结构、entry point、dependency 和复现风险证据，再由 LLM 整理为 reproduction planning 与 Markdown report。

项目定位是“运行前诊断”，不是自动复现平台。

## 整体架构

```text
用户 Prompt
    -> corecoder CLI
    -> CoreCoder Agent loop
    -> Tool Calling
    -> repo_map / entry_detector / env_checker / smoke_test_planner
    -> evidence-based diagnosis
    -> LLM 汇总
    -> Markdown report
```

RepoPilot 没有重新实现通用 Agent 基础设施。CLI、Agent loop、LLM 适配、Tool Calling、并行 Tool 执行、context compression 和 session 来自 CoreCoder；RepoPilot 增加领域 prompt、四个诊断 Tool、Evidence/Risk 辅助结构、测试和公开文档。

## 完整执行流程

1. 用户通过 `corecoder` CLI 提交当前仓库或指定仓库的诊断任务。
2. CLI 从参数和环境变量加载模型、API 和其他配置，并创建 LLM 与 Agent。
3. Agent 将 system prompt、用户消息、对话历史和 Tool schemas 发送给 LLM。
4. LLM 根据任务选择 `repo_map`、`entry_detector`、`env_checker` 或 `smoke_test_planner`。
5. Agent 解析 Tool Calling 参数并执行对应 Tool。
6. Tool 结果作为 `tool` message 返回对话，Agent 再次调用 LLM。
7. 同一轮中的多个独立 Tool 可以通过 CoreCoder 原有线程池并行执行。
8. 当 LLM 不再返回 Tool Calling 时，普通文本成为最终 Markdown report。

RepoPilot 没有独立的模板化报告引擎。报告结构由 system prompt、Demo Prompt、Tool 输出和 LLM 综合生成。

## CoreCoder Agent loop 的复用

```text
用户消息
    -> LLM + Tool schemas
    -> 是否返回 Tool Calling？
        -> 是：执行 Tool -> 回填结果 -> 再次调用 LLM
        -> 否：返回最终文本
```

RepoPilot 保留这一核心循环。领域能力通过 Tool 接口进入现有协议，因此没有破坏上游的多轮对话、并行执行、context compression 和 session 机制。

V0.2 曾对 Agent 做过一处小修复：Agent 初始化时建立实例级 `tool_map`，执行 Tool 时从当前实例映射查找，而不是只依赖全局 `ALL_TOOLS`。默认行为不变，但构造时传入的自定义 Tool 可以真正执行。

## Tool 接入方式

每个 Tool 继承 `Tool` 基类，并声明：

- `name`
- `description`
- `parameters`
- `execute()`

Tool 注册到 `ALL_TOOLS` 后，Agent 会调用 `schema()` 生成 Tool Calling schema，将其发送给 LLM，并根据返回的名称与参数执行对应 Tool。

四个诊断 Tool 的职责：

```text
repo_map
    -> 仓库中有什么？

entry_detector
    -> 训练、评估、推理和 Demo 从哪里启动？

env_checker
    -> dependency、CUDA、数据集和 checkpoint 有哪些 static risks？

smoke_test_planner
    -> 正式运行前可以建议哪些低成本检查？
```

## evidence-based diagnosis

RepoPilot 不要求 LLM 仅凭经验下结论，而是尽量让 Tool 返回可追溯证据：

- 文件路径与行号
- AST 中发现的 class、function、import 和 main guard
- README 中的调用命令
- 环境文件中的 dependency 与版本约束
- structured risks 的类别、严重程度、置信度、影响和修复建议

Markdown report 需要区分：

- **confirmed facts**：Tool 或源码直接支持的事实
- **inferred assumptions**：基于静态证据做出的推断
- **static risks**：尚未通过 runtime verification 的潜在风险
- **suggested smoke tests**：只建议、不执行的检查
- **full reproduction unverified**：完整复现仍未验证

这种设计不能完全消除 LLM 错误，但可以减少无依据推断，并让用户回到原始证据复核。

## smoke test plan 只生成不执行

AI/ML 仓库可能在 import 或 `--help` 阶段产生副作用：

- 下载数据集或模型权重
- 初始化 CUDA、分布式环境或多进程 DataLoader
- 直接进入长时间训练
- 执行平台专属 Shell 命令
- 加载不存在的 checkpoint

因此 `smoke_test_planner` 只分析源码并生成建议，不调用 Bash、`subprocess` 或目标仓库入口。报告必须明确 smoke test 未执行。

## 项目边界

RepoPilot 默认：

- 只做本地 static analysis
- 不执行目标仓库代码
- 不训练模型
- 不下载数据集或 checkpoint
- 不修改目标仓库
- 不把 smoke test plan 表述为运行结果
- 不把静态诊断表述为完整复现

实际安装、运行、训练、评估和指标核对需要用户在受控环境中完成。
