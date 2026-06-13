# RepoPilot V1.0 示例报告

本目录收录 RepoPilot 的 static analysis 样例，用于展示 Tool evidence 如何被整理为复现前诊断与 reproduction planning 报告。

| 报告 | 分析对象 | 展示能力 |
|---|---|---|
| [`sample_repro_report.md`](sample_repro_report.md) | RepoPilot 当前仓库 | 项目结构、CLI entry point、环境声明、structured risks 和 smoke test plan |
| [`sample_external_pytorch_cifar_report.md`](sample_external_pytorch_cifar_report.md) | 外部 PyTorch CIFAR-10 示例仓库 | 训练与评估 entry point、dependency 缺失、CUDA/平台/数据/checkpoint 风险、ASCII tree 和安全验证计划 |

所有样例报告遵循以下边界：

- **Analysis Mode**：Static analysis only
- **Smoke Tests**：Suggested only, not executed
- **Full Reproduction**：Unverified
- 不执行目标仓库代码、训练或数据下载
- 不修改目标仓库

报告正文以中文为主，Tool 名、命令、路径、dependency、模型名和必要技术术语保留英文。Tool 输出与 LLM 汇总仍需人工复核，尤其是启发式 entry point 分类、风险严重程度和版本兼容性建议。
