# ReproCoder One-shot Demo Prompts

## Demo A：分析当前仓库

```text
请仅做本地静态分析，使用 repo_map、entry_detector、env_checker 分析当前仓库，并生成 ReproCoder 科研代码复现诊断报告。

报告包括 Repository Overview、Entry Points、Environment Check、Reproduction Plan、Reproduction Risks、Suggested Fixes。

请明确区分 confirmed facts、inferred assumptions 和 unresolved risks，优先引用具体文件路径、建议命令和风险证据。不要执行训练，不要运行目标仓库代码，不要下载数据集、checkpoint 或模型权重。
```

## Demo B：分析指定 AI/ML 仓库

将路径替换为本地目标仓库的实际路径：

```text
请仅做本地静态分析，使用 repo_map、entry_detector、env_checker 分析仓库 D:/repos/example-paper。

请生成 ReproCoder 科研代码复现诊断报告，包含 Repository Overview、Entry Points、Environment Check、Reproduction Plan、Reproduction Risks、Suggested Fixes。

请明确区分 confirmed facts、inferred assumptions 和 unresolved risks。不要执行训练、推理或数据预处理，不要运行危险命令，不要下载任何大文件，只根据仓库中的代码、配置和文档进行静态分析。
```
