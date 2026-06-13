# RepoPilot V1.0 Demo Prompt

以下 Prompt 均要求只做本地 static analysis。代码、命令、参数、文件路径、Tool 名和配置文件名保持原样。

## Demo A：分析当前仓库

```text
请仅做本地 static analysis，使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析当前仓库，并生成中文的 RepoPilot V1.0 代码仓库诊断与 reproduction planning 报告。

报告包括仓库概览、entry point、环境检查、structured risks、复现计划、smoke test plan 和修复建议。

请明确区分 confirmed facts、inferred assumptions、static risks、suggested smoke tests 和 full reproduction unverified。优先引用具体文件路径、行号、命令和风险证据。

不要执行目标仓库代码、训练、推理、数据预处理或 smoke test；不要联网；不要下载数据集、checkpoint 或模型权重；不要修改目标仓库。不要生成或编造任何日期或时间元信息；除非 Tool 明确提供经过验证的当前日期，否则省略此类字段。
```

## Demo B：分析指定 AI/ML 仓库

将路径替换为目标仓库的实际本地路径：

```text
请仅做本地 static analysis，使用 repo_map、entry_detector、env_checker、smoke_test_planner 分析仓库 D:/repos/example-paper。

请生成中文的 RepoPilot V1.0 AI/ML 开源仓库复现前诊断报告，包含仓库概览、entry point、环境检查、structured risks、复现计划、smoke test plan 和修复建议。

报告必须区分 confirmed facts、inferred assumptions、static risks、suggested smoke tests 和 full reproduction unverified。

不要执行目标仓库代码、训练、推理、数据预处理或 smoke test；不要运行危险命令；不要联网或下载任何文件；不要修改目标仓库。smoke test plan 中的命令必须标记为 suggested only, not executed。不要生成或编造任何日期或时间元信息；除非 Tool 明确提供经过验证的当前日期，否则省略此类字段。
```

## Demo C：只生成 smoke test plan

```text
请使用 smoke_test_planner 为当前仓库生成中文的低成本 smoke test plan。

只生成建议，不执行任何命令，不运行目标代码，不训练，不联网，不下载数据集、checkpoint 或模型权重，不修改仓库。

请输出前置检查、import 检查、CLI 检查、安全运行建议、预期失败点和验证状态，并明确 suggested only, not executed 与 full reproduction unverified。不要生成或编造任何日期或时间元信息；除非 Tool 明确提供经过验证的当前日期，否则省略此类字段。
```
