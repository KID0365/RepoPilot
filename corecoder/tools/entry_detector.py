"""Static detection of likely training, inference, evaluation, and demo entries."""

import ast
import os
from pathlib import Path

from .base import Tool
from .repo_map import _SKIP_DIRS


_ENTRY_NAMES = {
    "train.py",
    "main.py",
    "demo.py",
    "infer.py",
    "inference.py",
    "eval.py",
    "test.py",
    "run.py",
    "app.py",
}

_FUNCTION_TYPES = {
    "train": "training",
    "evaluate": "evaluation",
    "eval": "evaluation",
    "infer": "inference",
    "inference": "inference",
    "demo": "demo",
}


class EntryDetectorTool(Tool):
    name = "entry_detector"
    description = (
        "Statically find likely training, inference, evaluation, and demo "
        "entry points in an AI/ML repository."
    )
    parameters = {
        "type": "object",
        "properties": {
            "root_path": {
                "type": "string",
                "description": "Repository root path (default: current directory)",
            },
        },
        "required": [],
    }

    def execute(self, root_path: str = ".") -> str:
        root = Path(root_path).expanduser().resolve()
        if not root.is_dir():
            return f"Error: {root_path} is not a directory"

        candidates = _candidate_files(root)
        results = [_inspect_candidate(root, path) for path in candidates]

        lines = [
            "# Entry Point Detection",
            "",
            f"- Root: `{root}`",
            f"- Candidate files: `{len(results)}`",
            "",
            "## Candidates",
        ]
        if not results:
            lines.append("- No conventional Python entry points were found.")
            return "\n".join(lines)

        for result in results:
            lines.extend([
                f"### `{result['path']}`",
                f"- Type: **{result['type']}**",
                f"- Confidence: **{result['confidence']}**",
                f"- Reasons: {'; '.join(result['reasons'])}",
            ])
        return "\n".join(lines)


def _candidate_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root)
        dirnames[:] = sorted(
            name for name in dirnames
            if name not in _SKIP_DIRS and not (current_path / name).is_symlink()
        )

        in_special_dir = bool(relative_dir.parts) and relative_dir.parts[0] in {
            "scripts",
            "tools",
        }
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            if filename.lower() in _ENTRY_NAMES or in_special_dir:
                path = current_path / filename
                if not path.is_symlink():
                    candidates.append(path)
        if len(candidates) >= 200:
            break
    return sorted(set(candidates), key=lambda path: path.as_posix().lower())[:200]


def _inspect_candidate(root: Path, path: Path) -> dict:
    relative = path.relative_to(root).as_posix()
    filename = path.name.lower()
    if filename in _ENTRY_NAMES:
        reasons: list[str] = [f"conventional filename `{path.name}`"]
    else:
        reasons = [f"Python script under `{path.relative_to(root).parts[0]}/`"]
    function_names: set[str] = set()
    has_main_guard = False
    cli_frameworks: set[str] = set()

    try:
        tree = ast.parse(path.read_text(errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_names.add(node.name.lower())
            elif isinstance(node, ast.If) and _is_main_guard(node.test):
                has_main_guard = True
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = _import_names(node)
                cli_frameworks.update(names & {"argparse", "click", "typer"})
    except (OSError, SyntaxError) as e:
        return {
            "path": relative,
            "type": _type_from_filename(filename),
            "confidence": "low",
            "reasons": reasons + [f"could not parse AST: {e}"],
        }

    detected_types = [
        entry_type
        for name, entry_type in _FUNCTION_TYPES.items()
        if name in function_names
    ]
    entry_type = _choose_type(filename, detected_types)

    if has_main_guard:
        reasons.append("contains `if __name__ == \"__main__\"`")
    if cli_frameworks:
        reasons.append("uses CLI framework: " + ", ".join(sorted(cli_frameworks)))
    matched_functions = sorted(
        name for name in function_names
        if name in _FUNCTION_TYPES or name == "main"
    )
    if matched_functions:
        reasons.append("entry-like functions: " + ", ".join(matched_functions))

    evidence = int(has_main_guard) + int(bool(cli_frameworks)) + int(bool(matched_functions))
    confidence = "high" if evidence >= 2 else "medium" if evidence == 1 else "low"
    return {
        "path": relative,
        "type": entry_type,
        "confidence": confidence,
        "reasons": reasons,
    }


def _is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare) or len(node.ops) != 1:
        return False
    if not isinstance(node.ops[0], ast.Eq) or len(node.comparators) != 1:
        return False
    left, right = node.left, node.comparators[0]
    return (
        isinstance(left, ast.Name)
        and left.id == "__name__"
        and isinstance(right, ast.Constant)
        and right.value == "__main__"
    ) or (
        isinstance(right, ast.Name)
        and right.id == "__name__"
        and isinstance(left, ast.Constant)
        and left.value == "__main__"
    )


def _import_names(node: ast.Import | ast.ImportFrom) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name.split(".")[0] for alias in node.names}
    return {(node.module or "").split(".")[0]}


def _type_from_filename(filename: str) -> str:
    if "train" in filename:
        return "training"
    if filename in {"infer.py", "inference.py"}:
        return "inference"
    if filename in {"eval.py", "test.py"}:
        return "evaluation"
    if filename in {"demo.py", "app.py"}:
        return "demo"
    return "unknown"


def _choose_type(filename: str, detected_types: list[str]) -> str:
    filename_type = _type_from_filename(filename)
    if filename_type != "unknown":
        return filename_type
    for entry_type in ("training", "inference", "evaluation", "demo"):
        if entry_type in detected_types:
            return entry_type
    return "unknown"
