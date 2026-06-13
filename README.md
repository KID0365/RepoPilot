# RepoPilot V1.0

*A lightweight agent for AI/ML codebase diagnosis and reproduction planning.*

RepoPilot 是一个基于 CoreCoder 二次开发的 AI Agent 项目。它通过 static analysis 分析本地 AI/ML 代码仓库，识别项目结构、entry point、dependency，以及数据集、checkpoint、CUDA 和平台风险，再由 LLM 将工具证据整理为 reproduction planning 与 Markdown report。

V1.0 是 **Stable Portfolio Release**。本版本不扩展诊断能力，重点完成项目边界、公开文档、可复现 Demo、样例报告和上游 attribution 的统一整理。

> **上游说明：** CLI、Agent loop、LLM 适配、Tool Calling、context compression、session 和基础 Tool 系统来自 [CoreCoder](https://github.com/he-yufeng/CoreCoder)。RepoPilot 在此基础上增加 AI/ML 仓库诊断 prompt、四个 static analysis Tool、结构化证据模型、测试和文档。本项目不宣称完整 Agent 架构为原创。

## 项目定位

很多 AI/ML 开源仓库包含模型代码，但缺少清晰的运行入口、dependency 版本、数据准备方式或 checkpoint 说明。直接运行可能触发长时间训练、数据下载、CUDA 初始化或平台兼容问题。

RepoPilot 的目标是在真实运行前回答：

- 仓库中有哪些关键代码、配置和环境文件？
- 训练、评估、推理和 Demo 的 entry point 在哪里？
- Python、PyTorch、CUDA 和 dependency 约束是否明确？
- 数据集、checkpoint 和预训练权重需要如何准备？
- 哪些结论是 confirmed facts，哪些只是 inferred assumptions 或 static risks？
- 可以建议哪些低成本 smoke test plan？

## RepoPilot 能做什么

- static codebase diagnosis
- entry point detection
- environment risk detection
- structured risks 与 evidence-based diagnosis
- smoke test plan 生成
- Markdown report 生成

## RepoPilot 不做什么

- 不训练模型
- 不执行目标仓库代码
- 不下载数据集、checkpoint 或模型权重
- 不修改目标仓库
- 不保证 dependency 一定可以安装
- 不保证完整复现成功
- 不用 static analysis 替代 runtime verification

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

RepoPilot 没有重写 Agent loop。四个诊断 Tool 通过 CoreCoder 原有的 Tool schema 和 Tool Calling 协议接入，工具结果作为 `tool` message 返回对话，LLM 再基于证据生成报告。

## 四个诊断 Tool

### `repo_map`

扫描有限深度的目录树，忽略版本库、虚拟环境和缓存目录；使用 AST 提取 Python 文件中的顶层 class、function 和 import，并输出 ASCII tree。

### `entry_detector`

综合常见文件名、README 命令、main guard、`argparse`、`click`、`typer`、console scripts 和入口式函数，识别训练、评估、推理、Demo 等 entry point，并给出置信度与证据。

### `env_checker`

检查 `requirements.txt`、`pyproject.toml`、`environment.yml`、`setup.py`、`setup.cfg`、Dockerfile 和 README，提取 Python、PyTorch、CUDA、数据集与 checkpoint 线索，并输出 structured risks。

### `smoke_test_planner`

根据 import、CLI、CUDA、下载、checkpoint 和长训练信号生成低成本 smoke test plan。该 Tool 只生成计划，不执行命令。

## 快速开始

创建并激活虚拟环境：

```bash
python -m venv .venv
```

Linux/macOS：

```bash
source .venv/bin/activate
pip install -e .
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .
```

根据 `.env.example` 配置 OpenAI-compatible API：

```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
$env:OPENAI_BASE_URL = "https://api.deepseek.com"
$env:CORECODER_MODEL = "deepseek-chat"
```

启动 CLI：

```bash
corecoder -m deepseek-chat
```

对外品牌为 RepoPilot，但为保持上游兼容，Python 包名和 CLI 命令仍为 `corecoder`。

## Demo 命令

分析当前仓库：

```bash
corecoder -m deepseek-chat -p "请仅做本地 static analysis，使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析当前仓库，并生成中文的 RepoPilot V1.0 诊断报告。不要执行训练、smoke test 或下载命令，不要修改目标仓库。"
```

分析指定仓库：

```bash
corecoder -m deepseek-chat -p "请仅做本地 static analysis，使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析 D:/repos/example-paper，并生成中文的 RepoPilot V1.0 复现前诊断报告。不要执行训练、smoke test 或下载命令，不要修改目标仓库。"
```

完整 Prompt 见 [`examples/repopilot_demo_prompt.md`](examples/repopilot_demo_prompt.md)。

## 文档

- [架构与设计](docs/design.md)
- [Tool 系统](docs/tool_system.md)
- [开发演进与工程复盘](docs/development_summary.md)
- [公开技术导览](docs/project_walkthrough.md)
- [样例报告索引](reports/README.md)

## 示例报告

- [RepoPilot 当前仓库诊断报告](reports/sample_repro_report.md)
- [外部 PyTorch CIFAR-10 仓库诊断报告](reports/sample_external_pytorch_cifar_report.md)

样例报告均为 static analysis 结果，并明确区分：

- confirmed facts
- inferred assumptions
- static risks
- suggested smoke tests
- full reproduction unverified

## 当前限制

- 主要面向 Python 和常见 AI/ML 仓库。
- entry point 与风险等级来自静态规则，可能存在误报或漏报。
- 不构建完整跨文件调用图。
- 不验证 dependency、CUDA、驱动或数据访问的 runtime compatibility。
- 不执行 smoke test，因此命令是否成功仍需人工验证。
- LLM 汇总仍可能出错，关键结论应回到源码证据复核。

## 测试

```bash
python -m compileall corecoder
python -m pytest
corecoder --help
```

当前测试集包含 71 项测试，覆盖核心模块、LiteLLM 适配、session 和主要 Tool 行为。

## 可能扩展

- 建立代表性外部仓库回归集。
- 增加 entry point 和环境解析的边界测试。
- 提供可选的机器可读 JSON report。
- 在隔离环境和显式授权下评估可执行 smoke test 模式。

这些方向不属于 V1.0 当前能力。

## 上游说明与致谢

本项目基于 [CoreCoder](https://github.com/he-yufeng/CoreCoder) fork 二次开发。CoreCoder 由 [Yufeng He（何宇峰）](https://github.com/he-yufeng) 创建，RepoPilot 复用了其 CLI、Agent loop、LLM 层、Tool 系统、context compression、session 和基础代码工具。

RepoPilot 新增或调整的部分主要包括：

- AI/ML 仓库诊断 prompt
- `repo_map`
- `entry_detector`
- `env_checker`
- `smoke_test_planner`
- Evidence/Risk 辅助结构
- Agent 实例级 `tool_map` 修复
- 测试、Demo、样例报告和公开文档

上游原始说明保存在 [`README_CORECODER.md`](README_CORECODER.md)。

## 许可证

项目遵循仓库中的 [MIT License](LICENSE)。使用和分发时请保留原始版权声明、许可证文本和 CoreCoder attribution。
