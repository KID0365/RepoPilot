"""Static repository structure and Python symbol inspection."""

import ast
import os
from pathlib import Path

from .base import Tool


_SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}

_PROJECT_MARKERS = (
    "README",
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "setup.py",
    "Dockerfile",
    "configs",
)


class RepoMapTool(Tool):
    name = "repo_map"
    description = (
        "Statically inspect a repository tree, project metadata, and Python "
        "classes, functions, and imports. Does not execute repository code."
    )
    parameters = {
        "type": "object",
        "properties": {
            "root_path": {
                "type": "string",
                "description": "Repository root path (default: current directory)",
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum directory depth to scan (default: 3)",
            },
            "max_files": {
                "type": "integer",
                "description": "Maximum files to inspect and display (default: 80)",
            },
        },
        "required": [],
    }

    def execute(
        self,
        root_path: str = ".",
        max_depth: int = 3,
        max_files: int = 80,
    ) -> str:
        root = Path(root_path).expanduser().resolve()
        if not root.is_dir():
            return f"Error: {root_path} is not a directory"

        max_depth = max(0, min(max_depth, 10))
        max_files = max(1, min(max_files, 500))

        try:
            files, dirs, python_count, truncated = _scan_tree(
                root, max_depth, max_files
            )
        except OSError as e:
            return f"Error scanning {root}: {e}"

        python_files = [path for path in files if path.suffix.lower() == ".py"]
        markers = _find_markers(root)

        lines = [
            "# Repository Map",
            "",
            f"- Root: `{root}`",
            f"- Scan depth: `{max_depth}`",
            f"- Files inspected: `{len(files)}`"
            + (" (limit reached)" if truncated else ""),
            f"- Python files found: `{python_count}`",
            f"- Python files inspected: `{len(python_files)}`",
            "",
            "## Project Markers",
        ]
        for marker in _PROJECT_MARKERS:
            found = markers.get(marker)
            lines.append(f"- {marker}: " + (f"`{found}`" if found else "not found"))

        lines.extend(["", "## Directory Tree"])
        if not files and not dirs:
            lines.append("- (empty directory)")
        else:
            entries = [(path, True) for path in dirs] + [(path, False) for path in files]
            for path, is_dir in sorted(entries, key=lambda item: item[0].as_posix().lower()):
                depth = len(path.parts) - 1
                indent = "  " * depth
                suffix = "/" if is_dir else ""
                lines.append(f"{indent}- `{path.as_posix()}{suffix}`")

        lines.extend(["", "## Python Overview"])
        if not python_files:
            lines.append("- No Python files found within the scan limits.")
        else:
            for relative in python_files:
                summary = _python_summary(root / relative)
                lines.append(f"### `{relative.as_posix()}`")
                lines.append(f"- Classes: {_format_items(summary['classes'])}")
                lines.append(f"- Functions: {_format_items(summary['functions'])}")
                lines.append(f"- Imports: {_format_items(summary['imports'])}")
                if summary["error"]:
                    lines.append(f"- Parse warning: {summary['error']}")

        return "\n".join(lines)


def _scan_tree(
    root: Path,
    max_depth: int,
    max_files: int,
) -> tuple[list[Path], list[Path], int, bool]:
    files: list[Path] = []
    dirs: list[Path] = []
    python_count = 0
    truncated = False

    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root)
        depth = 0 if relative_dir == Path(".") else len(relative_dir.parts)

        dirnames[:] = sorted(
            name for name in dirnames
            if name not in _SKIP_DIRS and not (current_path / name).is_symlink()
        )
        if depth >= max_depth:
            dirnames[:] = []
        else:
            dirs.extend(relative_dir / name for name in dirnames)

        for filename in sorted(filenames):
            path = current_path / filename
            if path.is_symlink():
                continue
            if path.suffix.lower() == ".py":
                python_count += 1
            if len(files) >= max_files:
                truncated = True
            else:
                files.append(path.relative_to(root))

    return files, dirs, python_count, truncated


def _find_markers(root: Path) -> dict[str, str | None]:
    children = {path.name.lower(): path.name for path in root.iterdir()}
    result: dict[str, str | None] = {}
    for marker in _PROJECT_MARKERS:
        if marker == "README":
            readmes = sorted(
                name for lower, name in children.items()
                if lower.startswith("readme")
            )
            result[marker] = readmes[0] if readmes else None
        else:
            result[marker] = children.get(marker.lower())
    return result


def _python_summary(path: Path) -> dict[str, list[str] | str | None]:
    try:
        source = path.read_text(errors="replace")
        tree = ast.parse(source)
    except (OSError, SyntaxError) as e:
        return {"classes": [], "functions": [], "imports": [], "error": str(e)}

    classes: list[str] = []
    functions: list[str] = []
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or "."
            imports.append(module)

    return {
        "classes": classes[:20],
        "functions": functions[:30],
        "imports": list(dict.fromkeys(imports))[:30],
        "error": None,
    }


def _format_items(items: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) if items else "none detected"
