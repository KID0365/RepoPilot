# RepoPilot V0.3 外部研究代码复现前诊断报告

**仓库**：ExternalDemo-pytorch-cifar
**路径**：`D:\AIProjects\ExternalDemo-pytorch-cifar`
**工具**：repo_map, entry_detector, env_checker, smoke_test_planner
**分析模式**：仅静态分析（Static analysis only）
**Smoke Tests**：仅提供建议，未执行（Suggested only, not executed）
**完整复现**：未验证（Unverified）

---

## 1. 仓库概览

| 项目 | 内容 |
|---|---|
| **用途** | 使用 PyTorch 在 CIFAR-10 上训练多种经典 CNN 的教学与演示项目 |
| **涉及模型** | VGG、ResNet、ResNeXt、DenseNet、MobileNetV2、DPN、DLA、PreActResNet、RegNet、ShuffleNet、SENet、EfficientNet、GoogLeNet、PNASNet、LeNet 等 |
| **代码规模** | 21 个 Python 文件、1 个 README、1 个 LICENSE |
| **目录结构** | `main.py`（主入口）+ `utils.py`（辅助函数）+ `models/`（18 个模型定义） |
| **许可证** | 存在 LICENSE 文件 |

### 目录树

```text
ExternalDemo-pytorch-cifar/
|-- LICENSE
|-- README.md
|-- main.py                  # 训练和测试主脚本
|-- utils.py                 # 初始化、进度条等辅助函数
`-- models/
    |-- __init__.py          # 统一导出模型
    |-- vgg.py
    |-- resnet.py
    |-- preact_resnet.py
    |-- resnext.py
    |-- densenet.py
    |-- mobilenet.py
    |-- mobilenetv2.py
    |-- dpn.py
    |-- senet.py
    |-- shufflenet.py
    |-- shufflenetv2.py
    |-- efficientnet.py
    |-- regnet.py
    |-- googlenet.py
    |-- lenet.py
    |-- pnasnet.py
    |-- dla.py
    `-- dla_simple.py
```

---

## 2. 入口识别

### 主入口：`main.py`（置信度：高）

| 属性 | 识别结果 |
|---|---|
| **入口类型** | 训练 + 评估 |
| **CLI 框架** | argparse |
| **默认模型** | `SimpleDLA()`（第 71 行） |
| **默认设备** | CUDA 可用时使用 GPU，否则使用 CPU |
| **默认学习率** | 0.1 |
| **默认优化器** | SGD（momentum=0.9, weight_decay=5e-4） |
| **默认调度器** | CosineAnnealingLR（T_max=200） |
| **默认训练轮数** | 200 |
| **默认 Batch Size** | 训练 128 / 测试 100 |
| **DataLoader Workers** | 2 |

### CLI 用法

```bash
# 从头训练，默认模型为 SimpleDLA
python main.py

# 从 checkpoint 恢复，并设置学习率
python main.py --resume --lr=0.01
```

以上是源码入口能力说明，不是建议立即执行的 Smoke Test。直接运行 `python main.py` 会进入默认 200 轮训练，并可能触发数据集下载。

### 模型选择方式

模型通过手动修改 `main.py` 第 57-71 行进行选择。当前启用 `SimpleDLA()`，其他模型行均被注释。

### 辅助函数：`utils.py`

- `get_mean_and_std(dataset)`：计算数据集均值和标准差。
- `init_params(net)`：初始化网络参数。
- `progress_bar(current, total, msg)`：显示训练进度。
- `format_time(seconds)`：格式化时间。

---

## 3. 环境检查

### 3.1 环境文件完整性

| 文件 | 是否存在 | 静态风险 |
|---|---|---|
| `requirements.txt` | 否 | **高**：没有依赖版本约束 |
| `pyproject.toml` | 否 | 中 |
| `environment.yml` | 否 | 中 |
| `setup.py` / `setup.cfg` | 否 | 低 |
| `Dockerfile` | 否 | 中 |
| `.env.example` | 否 | 低 |

### 3.2 依赖声明

**README 中的声明：**

- Python 3.6+
- PyTorch 1.0+

README 声明支持 Python 3.6+，但这是一个 PyTorch 1.0 时代的旧项目。Python 3.13 等现代 Python 版本可能产生依赖兼容问题，因为旧版 PyTorch 和 torchvision 不支持 Python 3.13。复现时优先考虑 Python 3.8-3.10 环境。

**源码中识别出的实际依赖：**

| 依赖 | 版本要求 | 证据 |
|---|---|---|
| Python | >= 3.6 | README 声明 |
| PyTorch | >= 1.0 | README；使用 `CosineAnnealingLR` |
| torchvision | 未声明 | 使用 `torchvision.datasets.CIFAR10` 和 `torchvision.transforms` |
| CUDA | 未声明 | 使用 `torch.nn.DataParallel` 和 `cudnn.benchmark` |

### 3.3 数据集

| 数据集 | 是否自动下载 | 存储路径 | 估计大小 |
|---|---|---|---|
| CIFAR-10 | 是（`download=True`） | `./data/` | 约 170 MB |

源码具有自动下载能力，但 RepoPilot 没有执行下载命令。

### 3.4 Checkpoint 机制

| 项目 | 内容 |
|---|---|
| 保存路径 | `./checkpoint/ckpt.pth` |
| 保存条件 | 测试准确率超过历史最佳值 |
| 保存内容 | `net`（state_dict）、`acc`、`epoch` |
| 恢复方式 | `--resume` 或 `-r` 参数 |

---

## 4. 建议的复现计划

以下步骤是后续人工复现建议，并未由 RepoPilot 执行。

### 第一步：创建环境

```bash
# 建议使用 Python 3.8-3.10
conda create -n cifar10 python=3.9
conda activate cifar10

# 根据实际 CUDA 版本选择 PyTorch
# CUDA 11.8 示例：
pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118

# CPU 环境示例：
pip install torch torchvision
```

具体 PyTorch、torchvision 与 CUDA 组合仍需根据目标机器和官方兼容矩阵确认。

### 第二步：准备代码与数据

```bash
cd D:\AIProjects\ExternalDemo-pytorch-cifar
```

源码已经存在。CIFAR-10 可能仍需手动准备或下载，但 RepoPilot 不执行下载命令。

### 第三步：选择模型

如需使用 ResNet18，可人工修改 `main.py`：

```python
# 取消第 58 行注释
net = ResNet18()

# 注释第 71 行
# net = SimpleDLA()
```

### 第四步：运行时验证

只有在环境、数据、平台兼容问题和训练成本均已确认后，才考虑人工执行训练或 checkpoint 恢复。RepoPilot 本次没有执行以下入口：

```bash
python main.py
python main.py --resume --lr=0.01
```

### 第五步：指标核对

README 给出了下列参考准确率。这些数值属于项目文档声明，不是 RepoPilot 的实测结果：

| 模型 | README 参考准确率 |
|---|---|
| SimpleDLA（默认） | 约 94.89% |
| ResNet18 | 约 93.02% |
| VGG16 | 约 92.64% |
| DenseNet121 | 约 95.04% |
| DLA | 约 95.47% |

---

## 5. 结构化复现风险

### 高风险

| ID | 风险描述 | 影响 | 证据 |
|---|---|---|---|
| **R1** | **缺少 requirements 或环境锁定文件** | 不同依赖版本可能导致安装、训练或结果不一致 | 未发现常见环境文件 |
| **R2** | **`utils.py` 第 45 行使用平台相关的 `stty size`** | Windows 上 `stty` 不可用或不返回终端尺寸时，导入 `utils.py` 或运行 `main.py` 可能失败 | `os.popen('stty size', 'r').read().split()` 偏向 Unix 环境 |
| **R3** | **`init.kaiming_normal` 已弃用** | 新版 PyTorch 将其改为 `kaiming_normal_`，可能产生警告或错误 | `utils.py` 第 33 行 |

### 中风险

| ID | 风险描述 | 影响 | 证据 |
|---|---|---|---|
| **R4** | **PyTorch 1.0 到 2.x 的版本跨度较大** | API 或行为差异需要实际验证 | README 声明 PyTorch 1.0+，现代环境通常使用 2.x |
| **R5** | **单 GPU 环境仍使用 `DataParallel`** | 通常不会直接报错，但会产生不必要开销 | `main.py` 第 74 行无条件包装 |
| **R6** | **`num_workers=2` 可能在 Windows 上引发多进程问题** | Windows DataLoader 多进程通常需要 main guard | `main.py` 第 45、50 行 |
| **R7** | **CIFAR-10 自动下载依赖网络** | 受限网络环境中可能无法准备数据 | `main.py` 第 43、48 行使用 `download=True` |

### 低风险

| ID | 风险描述 | 影响 | 证据 |
|---|---|---|---|
| **R8** | **没有固定随机种子** | 多次运行的结果可能波动 | `main.py` 未设置 `torch.manual_seed` |
| **R9** | **缺少实验配置管理** | 修改超参数需要直接编辑源码 | 参数集中硬编码于 `main.py` |
| **R10** | **没有独立测试或评估脚本** | 难以低成本自动核验结果 | 未发现独立 evaluation 脚本 |

---

## 6. 修复建议

### 修复 R2：跨平台终端宽度检测

**问题**：`utils.py` 使用 `os.popen('stty size', 'r').read().split()`。Windows 上可能因为 `stty` 不存在或没有返回终端尺寸而失败；可能的表现包括 Shell 命令失败或空输出解包错误。

**建议修改：**

```python
import shutil

term_width = shutil.get_terminal_size((80, 20)).columns
```

### 修复 R3：更新弃用 API

**问题**：`utils.py` 第 33 行使用旧 API。

```python
# 旧写法：
init.kaiming_normal(m.weight, mode='fan_out')

# 新写法：
init.kaiming_normal_(m.weight, mode='fan_out')
```

### 修复 R6：增加 Windows DataLoader 多进程保护

Windows 上使用 `num_workers > 0` 时，应将训练循环放入 main guard：

```python
if __name__ == '__main__':
    for epoch in range(start_epoch, start_epoch + 200):
        train(epoch)
        test(epoch)
        scheduler.step()
```

### 修复 R1：补充环境文件

建议增加经过实际验证的依赖文件。以下只表示需要约束 PyTorch 和 torchvision，不代表版本组合已经验证：

```text
torch
torchvision
```

最终版本应在真实安装和运行后固定，并记录对应 Python、CUDA 与操作系统信息。

### 修复 R8：固定随机种子

```python
import random
import numpy as np


def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
```

### 修复 R9：增加配置文件支持（可选）

可考虑使用简单的 YAML 或 JSON 配置管理模型、学习率、epoch 和数据路径，避免每次实验直接修改源码。

---

## 7. Smoke Test 计划

> 仅提供建议，未执行。RepoPilot 没有运行目标代码、训练、下载或任何 Smoke Test 命令。

### 前置检查

- `python --version`
- `python -c "import torch; print(torch.__version__)"`
- `python -c "import torch; print(torch.cuda.is_available())"`

### 导入检查

- `python -c "import models; print('models OK')"`

  预期：安装 PyTorch 后大概率可以通过。仅导入 `models` 不代表会导入 `utils.py`。

- `python -c "import utils"`

  预期：Windows 上可能因为 `utils.py` 在导入阶段执行 `stty size` 而失败。

### CLI 检查

- `python main.py --help`

执行前需要人工审查。`main.py` 会先导入 `utils.py`，并在参数解析前完成较多模块级初始化，因此可能尚未显示帮助信息就遇到 `stty` 问题。

### 安全运行建议

- 初次导入检查优先使用 CPU 环境。
- CIFAR-10 准备可能需要下载，但 RepoPilot 不执行下载命令。
- 不要直接把 `python main.py` 当作 Smoke Test，因为它会启动默认 200 轮训练，并可能触发数据集下载。
- 后续若要进行轻量运行检查，应先增加 `--epochs 1` 和 `--cpu` 等明确参数；当前代码尚未提供这些参数，因此本报告不把它们写成可直接执行的现有命令。
- 测试 `--resume` 前先确认 checkpoint 路径和文件格式。

### 预期失败点

- `python -c "import utils"`、`python main.py --help` 和 `python main.py` 在 Windows 上可能因为 `stty` 不可用或返回空输出而失败。
- 依赖版本没有锁定。
- Python、PyTorch、torchvision 与 CUDA 的兼容组合尚未确认；对该旧项目而言，Python 3.8-3.10 比 Python 3.13 更适合作为初始尝试范围。

### 验证状态

- 静态证据：已获得。
- Smoke Test：未执行。
- 完整复现：未验证。

---

## 8. 总结

| 维度 | 静态评估 |
|---|---|
| **代码完整性** | [OK] 包含主脚本和 18 个模型实现 |
| **文档清晰度** | [OK] README 提供基本用法和参考准确率 |
| **环境可复现性** | [FAIL] 缺少依赖锁定文件，并存在 Windows 兼容风险 |
| **开箱可用性** | [WARN] 静态分析提示 Windows `stty` 风险，实际行为尚未验证 |
| **结果可复现性** | [WARN] 未固定随机种子，结果可能波动 |
| **预计复现难度** | 静态分析推断 Linux/macOS 为低，Windows 为中；仍需运行时验证 |

**核心建议**：先处理 `stty size` 的 Windows 兼容问题、补充经过验证的依赖版本，并更新弃用的 PyTorch API。静态分析表明修复后项目可能具备复现条件，但必须通过实际安装、数据准备、运行和指标核对才能确认。

本报告未执行训练、数据下载、Smoke Test，也未修改目标仓库。完整复现状态仍为未验证。
