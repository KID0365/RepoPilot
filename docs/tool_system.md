# RepoPilot Tool System

## Tool 基类

所有工具都继承 `corecoder.tools.base.Tool`。接口刻意保持简单：

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

工具在 function calling 中的唯一名称，例如 `repo_map`。LLM 返回 tool call 时必须使用这个名称。

### `description`

工具能力的简短说明。它既是文档，也是 LLM 选择工具的重要上下文。描述应说明工具适合解决什么问题，并明确关键边界。

### `parameters`

输入参数的 JSON Schema，例如：

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

Schema 用于告诉模型参数名称、类型和是否必填。

### `execute()`

工具的实际执行入口。当前工具约定返回字符串：成功时返回 Markdown 或文本结果，常见错误也以 `Error: ...` 文本返回，由 Agent 重新交给 LLM 判断下一步。

## `schema()` 如何暴露工具

`Tool.schema()` 将类字段包装成 OpenAI function-calling 格式：

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

Agent 每轮调用 LLM 时，会把当前工具列表的 schemas 一并发送。模型可以返回工具名和 JSON 参数，Agent 再执行对应工具。

## `ALL_TOOLS` 与 `get_tool()`

`corecoder/tools/__init__.py` 是默认工具注册表。

- `ALL_TOOLS` 保存默认启用的工具实例。
- `get_tool(name)` 为兼容现有代码提供全局名称查找。
- `Agent()` 未显式传入工具时，默认使用 `ALL_TOOLS`。

RepoPilot 在这里注册四个诊断工具，因此无需修改 LLM 协议或 Agent loop。

## Agent `tool_map` 的意义

V0.1 中，Agent 虽然允许传入 `tools=[...]`，实际执行时却仍通过全局 `get_tool()` 查找。这会导致外部自定义工具能够出现在 schema 中，却可能无法执行。

V0.2 增加：

```python
self.tool_map = {tool.name: tool for tool in self.tools}
```

执行时改为：

```python
tool = self.tool_map.get(tool_name)
```

这样每个 Agent 真正使用自己的工具集合。默认 `ALL_TOOLS` 行为保持不变，同时为只读 Agent、测试工具或未来插件式扩展提供了基础。

## 四个 RepoPilot 工具

| 工具 | 主要职责 | 关键实现 |
|---|---|---|
| `repo_map` | 建立仓库结构和 Python 符号概览 | `os.walk`、深度/文件上限、跳过缓存目录、AST 顶层 class/function/import |
| `entry_detector` | 识别训练、评估、推理、Demo 和辅助入口 | 常见文件名、README 命令、main guard、CLI 框架、console scripts、多标签证据 |
| `env_checker` | 解析环境文件并输出结构化风险 | `tomllib`、`configparser`、requirements 行解析、setup.py AST、Evidence/Risk |
| `smoke_test_planner` | 生成低成本验证建议 | 静态检查 import、CLI、CUDA、下载、checkpoint 和长训练信号，不执行命令 |

## 如何新增静态分析工具

1. 在 `corecoder/tools/` 新建模块。
2. 继承 `Tool`。
3. 定义 `name`、`description` 和 `parameters`。
4. 实现只读、可控的 `execute()`。
5. 在 `corecoder/tools/__init__.py` 中导入并加入 `ALL_TOOLS`。
6. 为 schema、正常路径、错误路径和边界条件增加测试。
7. 更新 prompt 或文档，说明工具的适用场景和限制。

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

新增工具前应先判断是否真的需要新的领域能力，避免把可以由现有工具完成的简单搜索包装成过多抽象。

## 为什么外部输出保持 Markdown

Agent 和 LLM 最终需要消费工具结果。Markdown 有几个现实优势：

- 便于用户直接阅读；
- 可以作为 tool message 直接返回给 LLM；
- 不改变 CoreCoder 原有 `execute() -> str` 约定；
- 兼容现有报告生成流程。

V0.2 同时在工具内部引入轻量 Evidence/Risk 字典，使风险先以统一结构生成，再格式化为 Markdown。这样既保留上游工具 API，又提高证据字段的一致性。

当前版本尚未提供稳定的公共 JSON 输出协议。机器可读报告可以作为后续版本目标，但不属于 V0.3 的 Portfolio Polish 范围。
