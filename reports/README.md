# RepoPilot Reports

本目录收录 RepoPilot 的静态诊断样例，用于展示工具证据如何被整理为复现前报告。报告不代表目标项目已经完成安装、训练、评估或指标复现。

报告默认跟随用户输入语言。当前公开 Demo 使用中文提示词，因此本目录的样例统一使用中文叙述；代码、命令、路径、工具名和必要的标准状态标识保持原样。

| 报告 | 分析对象 | 展示能力 |
|---|---|---|
| [`sample_repro_report.md`](sample_repro_report.md) | RepoPilot 当前仓库 | 项目自身结构、CLI 入口、环境声明、结构化风险和建议性 Smoke Test Plan |
| [`sample_external_pytorch_cifar_report.md`](sample_external_pytorch_cifar_report.md) | 外部 PyTorch CIFAR-10 示例仓库 | 训练/评估入口、依赖缺失、CUDA/平台/数据/checkpoint 风险、ASCII 目录树和安全验证计划 |

所有报告遵循以下边界：

- 分析模式：仅静态分析
- Smoke Tests：仅提供建议，未执行
- 完整复现：未验证
- 未执行训练、数据下载，也未修改目标仓库

工具输出和 LLM 总结可能需要人工复核，尤其是启发式入口分类、风险严重程度和版本兼容性建议。
