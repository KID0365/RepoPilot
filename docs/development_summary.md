# RepoPilot Development Summary

## 版本演进

| 版本 | 定位 | 主要工作 |
|---|---|---|
| V0.1 | AI/ML 仓库复现前静态诊断原型 | 领域 prompt；`repo_map`、`entry_detector`、`env_checker`；Demo prompt 与样例报告 |
| V0.2 | 有结构化证据链的诊断 + Smoke Test Plan | Evidence/Risk helper；环境文件解析；多来源入口；`smoke_test_planner`；Agent 实例级 `tool_map` |
| V0.3 | Portfolio Polish Release | 文档体系、报告索引、项目边界、公开技术导览和本地面试复习材料 |

V0.3 不扩展诊断能力，也不改变 Agent loop、LLM 层、CLI 命令或 Python 包名。

## 上游 CoreCoder 与 RepoPilot 的边界

**来自 CoreCoder：**

- CLI 与交互式 REPL；
- Agent loop；
- OpenAI-compatible 和 LiteLLM 适配；
- function calling 工具协议；
- 多工具并行执行；
- 上下文压缩；
- 会话保存和恢复；
- 读写、编辑、搜索、Shell 和子 Agent 等基础工具。

**RepoPilot 新增或修改：**

- AI/ML 仓库诊断 system prompt；
- `repo_map`、`entry_detector`、`env_checker`、`smoke_test_planner`；
- `diagnosis.py` 中的 Evidence/Risk helper；
- Agent 实例级工具映射的小修复；
- Demo prompt、样例报告和测试；
- V0.3 的设计、工具、开发复盘、技术导览与报告索引。

项目不宣称 Agent 总体架构完全原创。

## 文件级复盘

| 文件 | 作用 | 来源 | 本项目改动 | 面试中怎么讲 |
|---|---|---|---|---|
| `corecoder/cli.py` | CLI、one-shot、REPL、会话命令 | CoreCoder | 基本沿用 | 我复用了成熟 CLI，没有重写入口层 |
| `corecoder/agent.py` | Agent loop、工具调用、并行执行 | CoreCoder | V0.2 增加实例级 `tool_map` | 修复了自定义工具 schema 可见但执行仍依赖全局注册的问题 |
| `corecoder/llm.py` | 流式 LLM、tool call 重组、重试 | CoreCoder | 基本沿用 | 模型适配不是本项目主要原创点 |
| `corecoder/context.py` | 上下文估算与多层压缩 | CoreCoder | 基本沿用 | 长工具输出由上游压缩机制控制 |
| `corecoder/prompt.py` | 动态 system prompt | CoreCoder 基础 | 改造成 RepoPilot 诊断角色并增加事实边界 | Prompt 决定 Agent 应如何使用工具和表述结论 |
| `corecoder/tools/base.py` | Tool 抽象和 schema | CoreCoder | 沿用 | 新工具通过同一 function-calling 接口接入 |
| `corecoder/tools/repo_map.py` | 仓库地图与 AST 符号概览 | RepoPilot | V0.1 新增，后续改为 ASCII tree | 用确定性扫描替代 LLM 逐文件盲读 |
| `corecoder/tools/entry_detector.py` | 多来源入口识别 | RepoPilot | V0.1 新增，V0.2 增强 README/console scripts/多标签 | 置信度表示静态证据强弱，不代表运行成功 |
| `corecoder/tools/env_checker.py` | 环境解析和风险诊断 | RepoPilot | V0.1 新增，V0.2 增加标准库解析和误报过滤 | 把关键词扫描升级为 evidence-based diagnosis |
| `corecoder/tools/smoke_test_planner.py` | 生成安全验证计划 | RepoPilot | V0.2 新增 | 只生成计划，避免外部代码、下载和训练副作用 |
| `corecoder/diagnosis.py` | Evidence/Risk 统一结构 | RepoPilot | V0.2 新增 | 内部结构化，外部继续返回 Markdown，保持上游 API |
| `tests/test_core.py` | 核心模块测试 | CoreCoder 基础 | 更新工具数量并测试实例工具映射 | 用测试保证二次开发没有破坏默认行为 |
| `tests/test_tools.py` | 工具测试 | CoreCoder 基础 | 增加四个诊断工具相关断言 | 当前覆盖主要是 happy path，边界评测仍可加强 |

## 核心工程改动

### 1. 垂直场景化

保留通用 Agent 框架，将目标从“通用代码编辑”收窄为“AI/ML 仓库复现前诊断”，并通过 prompt 约束不训练、不下载、不夸大复现状态。

### 2. 确定性工具下沉

目录扫描、AST、配置解析、入口证据和风险字段由 Python 工具处理，LLM 负责选择工具、综合证据和生成报告，减少模型临时发明分析流程。

### 3. 证据与推断分层

风险包含类型、类别、严重程度、置信度、证据、影响和修复建议。最终报告要求区分 confirmed facts、inferred assumptions、static risks、suggested smoke tests 和 unverified status。

### 4. 安全的验证规划

Smoke Test Planner 不执行任何命令。它只建议 preflight、import 和 CLI 检查，并在发现下载或长训练信号时明确阻止把默认入口当作 smoke test。

## 当前项目边界

RepoPilot 当前适合：

- 快速了解陌生 Python AI/ML 仓库；
- 发现常见入口和调用命令；
- 检查环境描述是否充分；
- 汇总数据、checkpoint、CUDA 和平台风险；
- 在实际运行前生成低成本检查建议。

RepoPilot 当前不负责：

- 安装并求解所有依赖；
- 执行目标仓库代码；
- 自动下载数据集或模型权重；
- 自动训练、评估或复现论文指标；
- 对所有语言、Notebook 和自定义构建系统进行完整分析；
- 保证 LLM 总结完全无误。

## 仍然存在的限制

- 静态规则仍可能误报或漏报；
- 入口分析不是完整跨文件调用图；
- 环境文件解析覆盖有限，锁文件主要识别存在；
- 没有稳定的 JSON 报告协议；
- 没有在真实仓库基准集上量化准确率；
- Smoke Test Plan 未执行，运行时兼容性仍需人工验证；
- 包名和 CLI 保持 `corecoder`，对外品牌与内部兼容名称并存。

## V1.0 封版前建议

V1.0 不一定需要增加更多工具，优先完成：

1. 建立少量代表性仓库的人工标注回归集。
2. 补充入口误判、环境解析和风险证据的边界测试。
3. 定义稳定的可选 JSON 报告格式。
4. 完成安装、CLI 和文档的一致性验收。
5. 明确版本发布、变更记录和许可证/上游署名。
6. 在隔离与显式授权前提下，再评估是否需要可执行 smoke-test 模式。
