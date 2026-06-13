# RepoPilot V0.2

*A lightweight agent for AI/ML codebase diagnosis and reproduction planning.*

RepoPilot 是面向 AI/ML 开源代码仓库的诊断与复现规划 Agent。它通过本地静态分析识别仓库结构、运行入口、依赖环境以及数据集、权重、CUDA 和配置风险，并由 LLM 整理为可执行的复现计划与诊断报告。

> **Fork 说明：** 本项目基于 [CoreCoder](https://github.com/he-yufeng/CoreCoder) fork 二次开发。CoreCoder 由 [Yufeng He（何宇峰）](https://github.com/he-yufeng) 创建，提供了 Agent loop、LLM 适配、工具系统、上下文压缩和会话机制等核心架构。RepoPilot 在此基础上增加 AI/ML 开源仓库诊断与复现规划场景的 prompt、静态分析工具和项目文档，不宣称整体架构完全原创。

上游 CoreCoder 的原始 README 已保存在 [`README_CORECODER.md`](README_CORECODER.md)。

## 项目定位

RepoPilot 的目标不是自动完成昂贵训练，而是在复现前回答：

- 仓库包含哪些关键模块和配置？
- 训练、推理、评估和 Demo 从哪里启动？
- Python、PyTorch、CUDA 和依赖版本是否明确？
- 数据集、checkpoint 和预训练权重需要如何准备？
- 当前证据能否支持“可复现”，还存在哪些未验证风险？

RepoPilot 默认只做本地静态诊断，不自动下载大文件，也不执行真实训练。

## Quick Start

推荐先创建并激活虚拟环境：

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

复制 `.env.example` 为 `.env`，并填写自己的 OpenAI-compatible API Key。如果当前运行方式没有自动加载 `.env`，请手动设置环境变量。

Linux/macOS bash：

```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://api.deepseek.com"
export CORECODER_MODEL="deepseek-chat"
```

Windows PowerShell：

```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
$env:OPENAI_BASE_URL = "https://api.deepseek.com"
$env:CORECODER_MODEL = "deepseek-chat"
```

启动交互模式：

```bash
corecoder -m deepseek-chat
```

API Key 只应保存在本地 `.env` 或当前终端环境变量中，不要提交到 Git。

## 为什么基于 CoreCoder

CoreCoder 提供了一个简洁、可读的 Agent 核心，包括：

- CLI 和多轮 Agent loop
- OpenAI-compatible 与 LiteLLM 调用
- Function calling 工具系统
- 并行工具执行
- 上下文压缩
- 会话保存和恢复

RepoPilot 保留这些能力，在其上增加 AI/ML 开源仓库诊断与复现规划领域的 prompt 和静态分析工具，避免重写通用 Agent 基础设施。

## V0.2 新增内容

- 新增轻量 Evidence / Risk 结构化诊断模型。
- `entry_detector` 支持 README 命令、声明式入口、多标签类型和浅层可达性证据。
- `env_checker` 支持标准库解析环境文件，并输出带文件、行号、影响和修复建议的结构化风险。
- 新增只生成建议、不执行命令的 `smoke_test_planner`。
- Agent 支持通过实例工具映射执行外部动态工具。
- 保留 CoreCoder 原有读写、搜索、Shell、子 Agent 和会话功能。

V0.2 聚焦“有结构化证据链的复现前诊断 + Smoke Test Plan 生成”。诊断工具只读取本地仓库，`smoke_test_planner` 不执行它建议的命令。

## Architecture

```text
User Request
    -> RepoPilot Prompt
    -> CoreCoder Agent Loop
    -> repo_map / entry_detector / env_checker / smoke_test_planner
    -> LLM Summary
    -> Evidence-based Diagnosis + Smoke Test Plan
```

## 四个诊断工具

### `repo_map`

扫描有限深度的目录树，统计 Python 文件，并通过 AST 提取顶层 class、function 和 import。它还会检测 README、依赖文件、Dockerfile 和 `configs` 目录。

主要参数：

- `root_path`：仓库路径，默认当前目录。
- `max_depth`：扫描深度，默认 3。
- `max_files`：最多分析的文件数，默认 80。

### `entry_detector`

扫描常见入口文件以及 `scripts/*.py`、`tools/*.py`，检查：

- `if __name__ == "__main__"`
- `argparse`、`click`、`typer`
- `train`、`evaluate`、`eval`、`infer`、`inference`、`demo`、`main` 等函数

同时读取 README 命令、`pyproject.toml` scripts 和 console scripts，输出多标签入口、建议调用命令、置信度和判断证据。

### `env_checker`

检查 requirements、pyproject、conda、setup、Docker、README、锁文件等，使用标准库尽量结构化解析并提取：

- Python 版本声明
- PyTorch 和常见 AI/ML 依赖
- CUDA/GPU 提示
- 数据集、checkpoint、预训练权重和 model zoo 线索
- 带 category、severity、confidence、文件、行号、影响和修复建议的结构化风险

### `smoke_test_planner`

根据入口、依赖、import、CUDA、数据下载、checkpoint 和长训练线索生成低成本验证计划，包括 Preflight、Import、CLI、Safe Runtime 和 Expected Failures。

该工具只生成标注为 “Suggested only, not executed” 的命令建议，不运行目标代码、不训练、不联网、不下载和不修改目标仓库。

## CLI Usage

```text
corecoder [-m MODEL] [--base-url BASE_URL] [--api-key API_KEY]
          [-p PROMPT] [-r SESSION_ID]
```

- `-m, --model`：指定模型名称。
- `--base-url`：指定 OpenAI-compatible API 地址。
- `--api-key`：临时指定 API Key；优先使用环境变量或本地 `.env`。
- `-p, --prompt`：执行 one-shot 诊断任务。
- `-r, --resume`：恢复已保存的会话。

CLI 命令名和 Python 包名仍保持为 `corecoder`，以维持与上游项目的兼容性。

## Demo 命令

在待分析仓库根目录运行：

```bash
corecoder -m deepseek-chat -p "请使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析当前仓库，并生成 RepoPilot V0.2 诊断报告。报告包括 Repository Overview、Entry Points、Environment Check、Structured Risks、Reproduction Plan、Smoke Test Plan、Suggested Fixes。不要执行 smoke tests。"
```

完整提示词见 `examples/repopilot_demo_prompt.md`。

分析指定仓库：

```bash
corecoder -m deepseek-chat -p "请仅做静态分析，使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析 D:/repos/example-paper，并生成复现诊断报告。不要执行训练、smoke tests，也不要下载数据集或模型权重。"
```

将外部仓库诊断报告保存为文件：

```bash
corecoder -m deepseek-chat -p "请使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析 D:/repos/example-paper，并将最终报告写入 reports/sample_external_report.md。只生成计划，不执行训练或 smoke tests，不下载数据集或模型权重。"
```

## 报告样例

```markdown
# RepoPilot Reproducibility Diagnosis

## Repository Overview
- Confirmed: `train.py`、`configs/` 和 `requirements.txt` 存在。
- Inferred: 项目可能使用配置驱动训练。

## Entry Points
- Training: `train.py`，high confidence。
- Inference: `demo.py`，medium confidence。

## Environment Check
- `torch` 已声明，但未固定版本。
- README 提到 CUDA，未给出明确 CUDA/PyTorch 对应关系。

## Reproduction Plan
1. 创建隔离 Python 环境。
2. 安装固定版本依赖。
3. 按 README 准备数据集和 checkpoint。
4. 先运行帮助命令或轻量推理验证入口。

## Reproduction Risks
- High: 数据集下载地址和目录结构未确认。
- Medium: PyTorch/CUDA 版本未固定。

## Smoke Test Plan
- Suggested only, not executed.
- `python --version`
- `python train.py --help`
- Smoke-test verified: not executed.
- Full reproduction: unverified.

## Suggested Fixes
- 增加带版本约束的环境文件。
- 补充数据目录、权重校验值和最小推理命令。
```

静态报告只能说明仓库中可确认的证据，不能替代实际运行验证。

## 当前限制

- 主要分析 Python 和常见 AI/ML 项目文件，无法覆盖所有语言与自定义构建系统。
- 入口类型和风险等级来自静态规则，可能需要人工复核。
- 不验证依赖是否真的可安装，也不验证 CUDA、GPU 和驱动的运行时兼容性。
- 不执行训练、推理或数据预处理，因此不宣称目标仓库已经成功复现。
- 不自动下载数据集、checkpoint 或预训练权重。
- Smoke Test Plan 只是静态生成的建议，不代表命令已经执行或通过。

## 测试结果

在当前开发环境下测试通过：`python -m pytest`，`71 passed`。

基础语法检查：

```bash
python -m compileall corecoder
```

## 后续计划

- 支持更完整的配置继承分析。
- 识别更深的数据目录约定和 checkpoint 加载链路。
- 在明确授权和隔离条件下执行可控 smoke test。
- 增加常见论文仓库的诊断测试集。
- 支持输出机器可读的 JSON 报告。

## 项目亮点总结

RepoPilot 基于 CoreCoder Agent 架构二次开发，面向 AI/ML 开源代码仓库提供复现前静态诊断与规划能力。项目通过自定义 Tool 接入仓库结构映射、多来源入口识别、结构化环境风险和 Smoke Test Plan，并由 LLM 汇总为可追溯的诊断报告。

## 上游说明与致谢

本项目基于 [CoreCoder](https://github.com/he-yufeng/CoreCoder) fork 改造，复用了其 Agent loop、LLM 适配、工具系统、上下文压缩、会话机制以及基础 CLI 能力。RepoPilot 的领域 prompt、诊断数据模型、`repo_map`、`entry_detector`、`env_checker`、`smoke_test_planner` 和仓库诊断文档属于本次扩展，但本项目不宣称整体架构完全原创。

感谢 CoreCoder 原作者 [Yufeng He（何宇峰）](https://github.com/he-yufeng) 开源这一简洁、易读的 Agent 基础项目。请同时参考 [`README_CORECODER.md`](README_CORECODER.md)，并遵守仓库中的 MIT License、原始版权声明和署名要求。
