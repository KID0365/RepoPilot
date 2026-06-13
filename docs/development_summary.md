# RepoPilot V1.0 开发总结

## 版本演进

| 版本 | 定位 | 主要工作 |
|---|---|---|
| V0.1 | AI/ML 仓库诊断 MVP | 领域 prompt；`repo_map`、`entry_detector`、`env_checker`；Demo 与样例报告 |
| V0.2 | evidence-based diagnosis | Evidence/Risk 结构；多来源 entry point；环境解析；`smoke_test_planner`；Agent `tool_map` |
| V0.3 | Portfolio Polish Release | docs 体系、reports 索引、项目边界和公开技术导览 |
| V1.0 | Stable Portfolio Release | 统一公开文档、版本、术语、Demo、报告边界、attribution 和验收结果 |

V1.0 不新增诊断能力，也不改变 Agent loop、LLM 层、CLI 命令或 Python 包名。

## CoreCoder 与 RepoPilot 的边界

### 来自 CoreCoder

- CLI 与交互式 REPL
- Agent loop
- OpenAI-compatible 与 LiteLLM 适配
- Tool Calling 协议
- 多 Tool 并行执行
- context compression
- session 保存和恢复
- 读写、编辑、搜索、Shell 和子 Agent 等基础 Tool

### RepoPilot 新增或修改

- AI/ML 仓库诊断 system prompt
- `repo_map`
- `entry_detector`
- `env_checker`
- `smoke_test_planner`
- `corecoder/diagnosis.py` 中的 Evidence/Risk 辅助结构
- Agent 实例级 `tool_map` 小修复
- 诊断 Tool 测试、Demo、样例报告和公开文档

项目不宣称 Agent 总体架构完全原创。

## 主要文件

| 文件 | 作用 | 来源 | RepoPilot 改动 |
|---|---|---|---|
| `corecoder/cli.py` | CLI、单次任务、REPL、session 命令 | CoreCoder | 基本沿用，命令名保持 `corecoder` |
| `corecoder/agent.py` | Agent loop、Tool Calling、并行执行 | CoreCoder | 增加实例级 `tool_map` |
| `corecoder/llm.py` | 流式 LLM、Tool Calling 参数重组、重试 | CoreCoder | 基本沿用 |
| `corecoder/context.py` | token 估算与 context compression | CoreCoder | 基本沿用 |
| `corecoder/prompt.py` | 动态 system prompt | CoreCoder 基础 | 改为 RepoPilot 诊断角色并增加事实边界 |
| `corecoder/tools/base.py` | Tool 抽象与 schema | CoreCoder | 沿用 |
| `corecoder/tools/repo_map.py` | 仓库地图与 AST 概览 | RepoPilot | 新增；后续统一 ASCII tree |
| `corecoder/tools/entry_detector.py` | 多来源 entry point 识别 | RepoPilot | 新增并增强 README、console scripts 和多标签证据 |
| `corecoder/tools/env_checker.py` | 环境解析与 structured risks | RepoPilot | 新增并增强标准库解析和误报过滤 |
| `corecoder/tools/smoke_test_planner.py` | 生成 smoke test plan | RepoPilot | 新增；只生成计划，不执行命令 |
| `corecoder/diagnosis.py` | Evidence/Risk 统一结构 | RepoPilot | 新增 |
| `tests/test_core.py` | 核心模块测试 | CoreCoder 基础 | 更新 Tool 数量、版本与 `tool_map` 测试 |
| `tests/test_tools.py` | Tool 测试 | CoreCoder 基础 | 增加四个诊断 Tool 的测试 |
| `docs/` | 设计、Tool 系统、开发总结和技术导览 | RepoPilot | V0.3 建立，V1.0 统一封版 |
| `reports/` | 当前仓库与外部仓库样例报告 | RepoPilot | 统一中文主体、static analysis 边界和 ASCII tree |

## 核心工程取舍

### 复用通用 Agent 框架

CoreCoder 已提供 Agent loop、LLM、Tool Calling、context compression 和 session。RepoPilot 将开发重点放在 AI/ML 仓库诊断，而不是重写基础设施。

### 确定性分析下沉到 Tool

目录遍历、AST、配置解析、entry point 证据和 structured risks 由 Python Tool 完成；LLM 负责选择 Tool、综合证据和生成 Markdown report。

### 证据、推断与风险分层

报告要求区分 confirmed facts、inferred assumptions、static risks、suggested smoke tests 和 full reproduction unverified，避免把启发式判断写成已验证事实。

### 计划与执行分离

`smoke_test_planner` 不执行任何命令。外部仓库可能包含下载、CUDA 初始化和长训练，执行需要隔离环境与明确授权。

## 当前能力边界

RepoPilot 适合：

- 快速了解陌生 Python AI/ML 仓库
- 识别常见 entry point 和调用命令
- 检查环境描述是否充分
- 汇总数据集、checkpoint、CUDA 和平台风险
- 在真实运行前生成 smoke test plan

RepoPilot 不负责：

- 安装和求解所有 dependency
- 执行目标仓库代码
- 下载数据集或模型权重
- 自动训练、评估或复现论文指标
- 完整支持所有语言、Notebook 和自定义构建系统
- 保证 LLM 汇总完全无误

## 当前限制

- static analysis 规则可能误报或漏报
- entry point 分析不是完整跨文件调用图
- 环境文件解析覆盖有限
- 尚无稳定的 JSON report 协议
- 尚未在大规模真实仓库基准集上量化准确率
- smoke test plan 未执行，runtime compatibility 仍需人工验证
- 对外品牌为 RepoPilot，兼容包名和 CLI 仍为 `corecoder`

## 可能扩展

- 建立人工标注的真实仓库回归集
- 增加边界测试和误报分析
- 定义可选 JSON report
- 完善正式 release 与 changelog
- 在隔离环境和显式授权下评估可执行 smoke test 模式
