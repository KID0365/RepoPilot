# RepoPilot V1.0 技术导览

## 30 秒概览

RepoPilot 是基于 CoreCoder 二次开发的 AI/ML 仓库复现前诊断 Agent。它使用四个 static analysis Tool 分析仓库结构、entry point、dependency 和复现风险，再由 LLM 基于证据生成 reproduction planning 与 Markdown report。项目只提供诊断和 smoke test plan，不执行训练、下载或完整复现。

## 2 分钟技术导览

AI/ML 开源仓库常见的问题不是缺少模型代码，而是运行入口、dependency 版本、CUDA、数据集和 checkpoint 信息分散。直接执行入口可能触发长时间训练、下载或平台兼容问题。

RepoPilot 复用 CoreCoder 的 CLI、Agent loop、LLM 适配、Tool Calling、context compression 和 session，在此基础上增加四个领域 Tool：

- `repo_map` 使用目录扫描和 AST 建立仓库地图
- `entry_detector` 综合文件名、README 命令、main guard 和 CLI 框架识别 entry point
- `env_checker` 解析环境文件并生成 structured risks
- `smoke_test_planner` 只生成低成本 smoke test plan

Tool 提供确定性证据，LLM 负责选择 Tool、综合证据和组织报告。报告必须区分 confirmed facts、inferred assumptions、static risks、suggested smoke tests 和 full reproduction unverified。

## Agent 与 LLM

`corecoder/agent.py` 负责多轮 Agent loop：调用 LLM、解析 Tool Calling、执行 Tool、回填结果，直到模型返回普通文本。

`corecoder/llm.py` 负责流式响应、Tool Calling 参数重组和重试。该模块主要来自 CoreCoder，不是 RepoPilot 的核心新增能力。

Agent 使用实例级 `tool_map` 执行构造时传入的 Tool，同时保持默认 `ALL_TOOLS` 行为。

## 四个诊断 Tool

### `repo_map`

扫描有限深度目录树，跳过版本库、虚拟环境和缓存目录。对 Python 文件使用 AST 提取顶层 class、function 和 import，并使用 ASCII tree 输出结构。

### `entry_detector`

综合常见文件名、README 命令、`__main__.py`、console scripts、main guard、CLI 框架和入口式函数，输出多标签 entry point、建议命令和置信度证据。

置信度表示 static evidence 的强弱，不表示命令运行成功率。

### `env_checker`

使用标准库解析 `requirements.txt`、`pyproject.toml`、`setup.cfg`、`setup.py`、`environment.yml` 等文件，提取 Python、PyTorch、CUDA、数据集和 checkpoint 线索，并构建包含 evidence、impact 和 remediation 的 structured risks。

### `smoke_test_planner`

根据 import、CLI、CUDA、下载、checkpoint 和长训练信号生成 smoke test plan。它不运行目标代码，也不会把下载或完整训练命令作为默认 smoke test。

## 设计取舍

### 基于 CoreCoder 扩展

CoreCoder 已提供清晰的 Agent loop 和 Tool 协议。复用上游能力可以把项目范围集中在 AI/ML 仓库诊断，并清楚区分上游基础与 RepoPilot 新增部分。

### Tool 优先于纯 LLM 推断

目录遍历、AST 和配置解析属于确定性任务。将这些工作放入 Tool，比让 LLM 反复读取和搜索文件更稳定、更节省 context，也更容易测试。

### evidence-based diagnosis

报告结论尽量关联路径、行号、配置项和原始命令。LLM 负责表达，Tool 负责提供可复核证据。

### Markdown 外部接口

Tool 继续返回 Markdown，兼容 CoreCoder 的字符串 Tool 协议；structured risks 在内部先以统一 Evidence/Risk 结构构建，再格式化输出。

### 计划与执行分离

外部仓库可能包含下载、GPU 初始化、长训练和平台专属命令。RepoPilot V1.0 只生成 smoke test plan，不执行建议命令。

## 项目边界

RepoPilot 能提供 static evidence 和 reproduction planning，但不能证明：

- dependency 一定可以安装
- CUDA 与驱动一定兼容
- 数据集和 checkpoint 一定可访问
- 训练一定能够收敛
- README 指标一定能够复现

报告中的严重程度和 confidence 是规则化 static analysis 结果，不是运行成功概率。

## 当前限制与可能扩展

- static analysis 可能误报或漏报
- 非 Python 项目与复杂配置支持有限
- 尚未构建完整调用图
- 尚无稳定 JSON report
- 尚未在真实仓库基准集上量化准确率

后续可以增加真实仓库回归集、边界测试和可选机器可读输出，但这些不属于 V1.0 当前能力。
