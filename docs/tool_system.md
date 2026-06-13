# RepoPilot V1.0 Tool 系统

## Tool 基类

所有 Tool 都继承 `corecoder.tools.base.Tool`：

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict

    @abstractmethod
    def execute(self, **kwargs) -> str:
        ...
```

### `name`

Tool Calling 使用的唯一名称，例如 `repo_map`。LLM 返回 Tool Calling 时必须使用该名称。

### `description`

说明 Tool 解决什么问题，也是 LLM 选择 Tool 的重要上下文。描述需要明确能力和边界。

### `parameters`

Tool 输入参数的 JSON Schema：

```python
{
    "type": "object",
    "properties": {
        "root_path": {
            "type": "string",
            "description": "Repository root path",
        },
    },
    "required": [],
}
```

Schema 描述参数名称、类型和必填关系。

### `execute()`

Tool 的执行入口。当前约定为 `execute(**kwargs) -> str`：

- 成功时返回 Markdown 或普通文本
- 常见失败返回 `Error: ...`
- Agent 将结果作为 `tool` message 交还给 LLM

RepoPilot 诊断 Tool 默认只读取目标仓库。

## `schema()` 与 Tool Calling

`Tool.schema()` 将类字段包装成 OpenAI-compatible Tool Calling 格式：

```python
{
    "type": "function",
    "function": {
        "name": self.name,
        "description": self.description,
        "parameters": self.parameters,
    },
}
```

Agent 每轮调用 LLM 时发送当前 Tool schemas。LLM 返回 Tool 名称和 JSON 参数后，Agent 查找并执行对应实例。

## `ALL_TOOLS` 与 `get_tool()`

`corecoder/tools/__init__.py` 是默认 Tool 注册表：

- `ALL_TOOLS` 保存默认启用的 Tool 实例
- `get_tool(name)` 提供全局名称查找
- `Agent()` 未显式传入 Tool 时使用 `ALL_TOOLS`

RepoPilot 的四个诊断 Tool 在这里注册，因此不需要修改 LLM 协议。

## Agent `tool_map`

早期 Agent 虽然允许传入 `tools=[...]`，实际执行时仍通过全局 `get_tool()` 查找。这样可能出现 schema 已发送给 LLM，但自定义 Tool 无法执行的问题。

V0.2 增加实例级映射：

```python
self.tool_map = {tool.name: tool for tool in self.tools}
```

执行时使用：

```python
tool = self.tool_map.get(tool_name)
```

这样每个 Agent 使用自己的 Tool 集合，同时保持默认 `ALL_TOOLS` 行为不变。

## 四个 RepoPilot Tool

| Tool | 职责 | 关键实现 |
|---|---|---|
| `repo_map` | 建立仓库结构和 Python 符号概览 | `os.walk`、扫描上限、忽略目录、AST、ASCII tree |
| `entry_detector` | 识别训练、评估、推理、Demo 和辅助 entry point | 文件名、README 命令、main guard、CLI 框架、console scripts |
| `env_checker` | 解析环境文件并输出 structured risks | `tomllib`、`configparser`、requirements 解析、`setup.py` AST |
| `smoke_test_planner` | 生成低成本 smoke test plan | 检查 import、CLI、CUDA、下载、checkpoint 和长训练信号，不执行命令 |

## 新增 static analysis Tool

1. 在 `corecoder/tools/` 新建模块。
2. 继承 `Tool`。
3. 定义 `name`、`description` 和 `parameters`。
4. 实现只读、可控的 `execute()`。
5. 在 `corecoder/tools/__init__.py` 中导入并加入 `ALL_TOOLS`。
6. 为 schema、正常路径、错误路径和边界条件增加测试。
7. 更新 prompt 与公开文档。

最小示例：

```python
from .base import Tool


class ConfigSummaryTool(Tool):
    name = "config_summary"
    description = "Statically summarize repository configuration files."
    parameters = {
        "type": "object",
        "properties": {
            "root_path": {"type": "string"},
        },
        "required": [],
    }

    def execute(self, root_path: str = ".") -> str:
        return "# Config Summary\n\n- Static analysis only."
```

新增 Tool 前应先判断是否存在明确的新职责，避免把简单搜索包装成过多抽象。

## Markdown 输出与内部结构

Tool 对外继续返回 Markdown，原因包括：

- 用户可以直接阅读
- 可直接作为 `tool` message 返回 LLM
- 保持 CoreCoder 的 `execute() -> str` 接口
- 兼容现有报告生成流程

RepoPilot 内部使用轻量 Evidence/Risk 字典构建 structured risks，再格式化为 Markdown。这样既保留上游接口，又提高证据字段的一致性。

V1.0 尚未提供稳定的公共 JSON report 协议；机器可读输出属于可能扩展。
