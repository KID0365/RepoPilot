"""Tool registry."""

from .bash import BashTool
from .read import ReadFileTool
from .write import WriteFileTool
from .edit import EditFileTool
from .glob_tool import GlobTool
from .grep import GrepTool
from .agent import AgentTool
from .repo_map import RepoMapTool
from .entry_detector import EntryDetectorTool
from .env_checker import EnvCheckerTool
from .smoke_test_planner import SmokeTestPlannerTool

ALL_TOOLS = [
    BashTool(),
    ReadFileTool(),
    WriteFileTool(),
    EditFileTool(),
    GlobTool(),
    GrepTool(),
    AgentTool(),
    RepoMapTool(),
    EntryDetectorTool(),
    EnvCheckerTool(),
    SmokeTestPlannerTool(),
]


def get_tool(name: str):
    """Look up a tool by name."""
    for t in ALL_TOOLS:
        if t.name == name:
            return t
    return None
