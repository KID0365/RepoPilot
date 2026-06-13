# RepoPilot Project Walkthrough

## 项目定位

RepoPilot 是基于 CoreCoder 二次开发的 AI/ML 开源仓库复现前诊断 Agent。它不尝试自动训练模型，而是先回答四个问题：

1. 仓库中有哪些关键代码和配置？
2. 训练、评估、推理和 Demo 从哪里启动？
3. Python、PyTorch、CUDA、数据集和 checkpoint 条件是否清楚？
4. 在正式运行前，可以建议哪些低成本检查？

输出是一份带证据的 Markdown 诊断报告。静态分析不能替代运行验证，因此报告始终保留 `Full Reproduction: Unverified`。

## 架构概览

```text
CLI
  -> Agent Loop
  -> LLM chooses tools
  -> Static diagnosis tools
  -> Tool evidence returns to conversation
  -> LLM produces Markdown report
```

RepoPilot 的通用 Agent 骨架来自 CoreCoder。项目重点不是重新实现 LLM 客户端或 Agent loop，而是把 AI/ML 仓库复现前检查拆成稳定的领域工具，并规定证据与结论的边界。

## 核心模块

### Agent 与 LLM

`corecoder/agent.py` 负责多轮循环：调用 LLM、执行工具、回填结果，直到模型返回普通文本。`corecoder/llm.py` 负责流式响应、tool call 参数重组和重试。

V0.2 增加实例级 `tool_map`，使 Agent 真正能够执行构造时传入的工具集合。

### `repo_map`

扫描有限深度的目录树，跳过版本库、虚拟环境和缓存目录。对 Python 文件使用 AST 提取顶层类、函数和 import，并用 ASCII tree 输出目录结构。

### `entry_detector`

综合常见文件名、README 命令、`__main__.py`、console scripts、main guard、CLI 框架和入口式函数，输出多标签入口及置信度证据。

### `env_checker`

使用标准库解析 `pyproject.toml`、`setup.cfg`、requirements 等环境信息，并将风险表示为包含 evidence、impact 和 remediation 的统一结构。

### `smoke_test_planner`

根据 import、CLI、CUDA、下载、checkpoint 和长训练线索生成建议计划。它不运行目标代码，也不会生成下载或完整训练命令作为 smoke test。

## 设计取舍

### 复用 CoreCoder，而不是从零开始

CoreCoder 已经提供了可读的 Agent loop、工具协议、上下文管理和会话能力。复用这些基础设施，可以把开发重点放在垂直领域问题上，也能清楚说明哪些来自上游、哪些属于 RepoPilot。

### 静态工具优先，而不是完全依赖 LLM

目录遍历、AST 和配置解析属于确定性任务。将这些工作放进工具，通常比让 LLM 反复调用 `grep` 和 `read_file` 更稳定、更节省上下文，也更容易测试。

### Markdown 外部接口，结构化内部风险

工具继续返回 Markdown，兼容 CoreCoder 的字符串工具协议；风险在内部先使用统一字典构建，再格式化输出。这样避免大规模改动，同时提高报告一致性。

### 计划与执行分离

外部 AI/ML 仓库可能包含下载、GPU 初始化、长训练和平台专属命令。V0.3 仍坚持只生成 Smoke Test Plan，不执行建议命令。

## 项目边界

RepoPilot 能提供静态证据和复现前计划，但不能证明：

- 依赖一定可以安装；
- CUDA 与驱动一定兼容；
- 数据和权重一定可访问；
- 训练一定能够收敛；
- README 指标一定能够复现。

报告中的 high/medium/low 和 confidence 是规则化静态判断，不是运行成功概率。

## 后续计划

V1.0 前更重要的是提高工程可信度，而不是继续堆工具：

- 建立代表性仓库回归样本；
- 增加误报和边界测试；
- 定义可选机器可读报告；
- 统一发布说明、版本记录和文档；
- 继续保留上游 CoreCoder attribution。
