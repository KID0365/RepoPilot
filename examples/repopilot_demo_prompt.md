# RepoPilot V0.2 One-shot Demo Prompts

## Demo A：分析当前仓库

```text
请仅做本地静态分析，使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析当前仓库，并生成 RepoPilot V0.2 代码仓库诊断与复现规划报告。

报告包括 Repository Overview、Entry Points、Environment Check、Structured Risks、Reproduction Plan、Smoke Test Plan、Suggested Fixes。

请明确区分 confirmed facts、inferred assumptions、static risks、suggested smoke tests 和 full reproduction status。优先引用具体文件路径、行号、命令和风险证据。不要执行训练、目标仓库代码或 smoke tests，不要下载数据集、checkpoint 或模型权重，不要修改目标仓库。不要生成或编造 Analysis Date / Generated at / 分析时间；除非工具明确提供当前日期，否则省略日期字段。
```

## Demo B：分析指定 AI/ML 仓库

将路径替换为目标仓库的实际本地路径：

```text
请仅做本地静态分析，使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析仓库 D:/repos/example-paper。

请生成 RepoPilot V0.2 AI/ML 开源仓库复现前诊断报告，包含 Repository Overview、Entry Points、Environment Check、Structured Risks、Reproduction Plan、Smoke Test Plan、Suggested Fixes。

不要执行训练、推理、数据预处理或 smoke tests，不要运行危险命令，不要下载任何文件，不要修改目标仓库。Smoke Test Plan 中的命令必须标记为 suggested only, not executed。不要生成或编造 Analysis Date / Generated at / 分析时间；除非工具明确提供当前日期，否则省略日期字段。
```

## Demo C：只生成 Smoke Test Plan

```text
请使用 smoke_test_planner 为当前仓库生成低成本 Smoke Test Plan。

只生成建议，不执行任何命令，不运行目标代码，不训练，不联网，不下载数据集或模型权重，不修改仓库。请输出 Preflight Checks、Import Checks、CLI Checks、Safe Runtime Checks、Expected Failures 和 Verification Status，并明确 full reproduction unverified。不要生成或编造 Analysis Date / Generated at / 分析时间；除非工具明确提供当前日期，否则省略日期字段。
```
