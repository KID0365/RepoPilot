"""Static detection of likely repository entry points and invocations."""

import ast
import configparser
import os
import re
from pathlib import Path

from .base import Tool
from .repo_map import _SKIP_DIRS

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None


_ENTRY_NAMES = {
    "__main__.py",
    "train.py",
    "main.py",
    "demo.py",
    "infer.py",
    "inference.py",
    "eval.py",
    "evaluate.py",
    "test.py",
    "run.py",
    "app.py",
}

_FUNCTION_TYPES = {
    "train": "training",
    "fit": "training",
    "evaluate": "evaluation",
    "evaluation": "evaluation",
    "eval": "evaluation",
    "test": "evaluation",
    "infer": "inference",
    "inference": "inference",
    "predict": "inference",
    "demo": "demo",
}

_README_COMMAND_RE = re.compile(
    r"(?<![\w.-])("
    r"python(?:\d+(?:\.\d+)?)?\s+(?:-m\s+[\w.]+|[\w./\\-]+\.py)(?:\s+[^\r\n`|]*)?"
    r"|torchrun\s+[^\r\n`|]+"
    r"|accelerate\s+launch\s+[^\r\n`|]+"
    r"|bash\s+[\w./\\-]+\.sh(?:\s+[^\r\n`|]*)?"
    r")",
    re.IGNORECASE,
)


class EntryDetectorTool(Tool):
    name = "entry_detector"
    description = (
        "Statically find likely training, evaluation, inference, demo, and "
        "auxiliary entry points with invocation evidence."
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

        readme_commands = _readme_commands(root)
        candidates = _candidate_files(root)
        results = [
            _inspect_candidate(root, path, readme_commands)
            for path in candidates
        ]
        results.extend(_declared_script_entries(root, readme_commands))

        lines = [
            "# Entry Point Detection",
            "",
            f"- Root: `{root}`",
            f"- Candidate entry points: `{len(results)}`",
            "",
            "## Candidate Entry Points",
        ]
        if not results:
            lines.append("- No conventional or declared entry points were found.")
        for result in results:
            lines.extend([
                f"### `{result['path']}`",
                f"- Types: **{', '.join(result['types'])}**",
                f"- Confidence: **{result['confidence']}**",
                "- Invocations:",
            ])
            lines.extend(
                f"  - `{command}`"
                for command in result["invocations"]
            )
            if not result["invocations"]:
                lines.append("  - not detected")
            lines.append("- Evidence:")
            lines.extend(f"  - {item}" for item in result["evidence"])

        lines.extend(["", "## Invocation Commands"])
        lines.extend(
            f"- `{command}`"
            for command in readme_commands
        )
        if not readme_commands:
            lines.append("- No supported commands were extracted from README.md.")

        lines.extend([
            "",
            "## Possible Misclassification Risks",
            "- Conventional filenames may contain helper code rather than a runnable workflow.",
            "- README commands may be examples, outdated, or require omitted arguments.",
            "- Multi-label types are based on shallow AST evidence, not a full call graph.",
            "- Auxiliary shell, Makefile, and notebook entries are identified but not deeply parsed.",
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

        in_special_dir = bool(relative_dir.parts) and relative_dir.parts[0].lower() in {
            "scripts", "tools",
        }
        for filename in sorted(filenames):
            path = current_path / filename
            if path.is_symlink():
                continue
            lower = filename.lower()
            if lower.endswith(".py") and (lower in _ENTRY_NAMES or in_special_dir):
                candidates.append(path)
            elif (
                lower.endswith((".sh", ".ipynb"))
                and (in_special_dir or len(relative_dir.parts) == 0)
            ):
                candidates.append(path)
            elif lower == "makefile" and len(relative_dir.parts) == 0:
                candidates.append(path)
        if len(candidates) >= 200:
            break
    return sorted(set(candidates), key=lambda path: path.as_posix().lower())[:200]


def _inspect_candidate(
    root: Path,
    path: Path,
    readme_commands: list[str],
) -> dict:
    relative = path.relative_to(root).as_posix()
    if path.suffix.lower() != ".py":
        invocations = _commands_for_path(relative, readme_commands)
        return {
            "path": relative,
            "types": ["utility"],
            "invocations": invocations,
            "confidence": "medium" if invocations else "low",
            "evidence": [
                f"auxiliary `{path.suffix or path.name}` entry candidate",
                *([f"README invocation: `{command}`" for command in invocations]),
            ],
        }

    filename = path.name.lower()
    evidence: list[str] = []
    if filename in _ENTRY_NAMES:
        evidence.append(f"conventional filename `{path.name}`")
    else:
        evidence.append(f"Python script under `{path.relative_to(root).parts[0]}/`")

    function_names: set[str] = set()
    cli_frameworks: set[str] = set()
    cli_arguments: set[str] = set()
    main_guard_calls: set[str] = set()
    has_main_guard = False
    has_long_training_hint = False

    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_names.add(node.name.lower())
            elif isinstance(node, ast.If) and _is_main_guard(node.test):
                has_main_guard = True
                main_guard_calls.update(_called_names(node))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                cli_frameworks.update(_import_names(node) & {"argparse", "click", "typer"})
            elif isinstance(node, ast.Call):
                argument = _argparse_argument(node)
                if argument:
                    cli_arguments.add(argument)
            elif _long_training_hint(node):
                has_long_training_hint = True
    except (OSError, SyntaxError) as error:
        return {
            "path": relative,
            "types": _types_from_filename(filename),
            "invocations": _commands_for_path(relative, readme_commands),
            "confidence": "low",
            "evidence": evidence + [f"could not parse AST: {error}"],
        }

    types = set(_types_from_filename(filename))
    types.update(
        entry_type
        for name, entry_type in _FUNCTION_TYPES.items()
        if name in function_names
    )
    if len(types) > 1:
        types.discard("unknown")
    if not types:
        types.add("utility" if path.parent != root else "unknown")

    invocations = _commands_for_path(relative, readme_commands)
    if has_main_guard:
        evidence.append("contains `if __name__ == \"__main__\"`")
    if main_guard_calls:
        evidence.append("main guard calls: " + ", ".join(sorted(main_guard_calls)))
    if cli_frameworks:
        evidence.append("uses CLI framework: " + ", ".join(sorted(cli_frameworks)))
    if cli_arguments:
        evidence.append("CLI arguments: " + ", ".join(sorted(cli_arguments)[:12]))
    matched_functions = sorted(
        name for name in function_names
        if name in _FUNCTION_TYPES or name == "main"
    )
    if matched_functions:
        evidence.append("entry-like functions: " + ", ".join(matched_functions))
    if has_long_training_hint:
        evidence.append("contains a possible long training loop or large epoch count")
    evidence.extend(f"README invocation: `{command}`" for command in invocations)

    score = (
        int(has_main_guard)
        + int(bool(cli_frameworks))
        + int(bool(matched_functions))
        + int(bool(invocations))
        + int(bool(main_guard_calls & set(_FUNCTION_TYPES)))
    )
    confidence = "high" if score >= 3 else "medium" if score >= 1 else "low"
    return {
        "path": relative,
        "types": _sort_types(types),
        "invocations": invocations,
        "confidence": confidence,
        "evidence": evidence,
    }


def _readme_commands(root: Path) -> list[str]:
    readme = next(
        (
            path for path in root.iterdir()
            if path.is_file() and path.name.lower() == "readme.md"
        ),
        None,
    )
    if readme is None:
        return []
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    commands = []
    for match in _README_COMMAND_RE.finditer(text):
        command = match.group(1).strip().rstrip(".,;")
        if command and command not in commands:
            commands.append(command)
    return commands[:50]


def _commands_for_path(relative: str, commands: list[str]) -> list[str]:
    normalized = relative.replace("\\", "/")
    basename = Path(relative).name
    module = normalized[:-3].replace("/", ".") if normalized.endswith(".py") else ""
    matches = []
    for command in commands:
        command_normalized = command.replace("\\", "/")
        if (
            normalized in command_normalized
            or basename in command_normalized
            or (module and re.search(rf"\b-m\s+{re.escape(module)}\b", command))
        ):
            matches.append(command)
    return matches


def _declared_script_entries(root: Path, readme_commands: list[str]) -> list[dict]:
    entries: list[tuple[str, str, str]] = []
    pyproject = root / "pyproject.toml"
    if tomllib is not None and pyproject.is_file():
        try:
            with pyproject.open("rb") as file:
                scripts = tomllib.load(file).get("project", {}).get("scripts", {})
            entries.extend(("pyproject.toml", name, target) for name, target in scripts.items())
        except (OSError, ValueError):
            pass

    setup_cfg = root / "setup.cfg"
    if setup_cfg.is_file():
        parser = configparser.ConfigParser()
        try:
            parser.read(setup_cfg)
            raw = parser.get("options.entry_points", "console_scripts", fallback="")
            for line in raw.splitlines():
                if "=" in line:
                    name, target = line.split("=", 1)
                    entries.append(("setup.cfg", name.strip(), target.strip()))
        except configparser.Error:
            pass

    setup_py = root / "setup.py"
    if setup_py.is_file():
        try:
            text = setup_py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for match in re.finditer(r"[\"']([\w.-]+)\s*=\s*([\w.]+(?::[\w.]+)?)[\"']", text):
            entries.append(("setup.py", match.group(1), match.group(2)))

    results = []
    for source, name, target in entries:
        invocation = name
        matching = [command for command in readme_commands if command.startswith(name)]
        results.append({
            "path": f"{source}:[{name}]",
            "types": ["utility"],
            "invocations": matching or [invocation],
            "confidence": "high",
            "evidence": [f"declared console script `{name} = {target}`"],
        })
    return results


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


def _called_names(node: ast.If) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                names.add(child.func.id.lower())
            elif isinstance(child.func, ast.Attribute):
                names.add(child.func.attr.lower())
    return names


def _import_names(node: ast.Import | ast.ImportFrom) -> set[str]:
    if isinstance(node, ast.Import):
        return {alias.name.split(".")[0] for alias in node.names}
    return {(node.module or "").split(".")[0]}


def _argparse_argument(node: ast.Call) -> str:
    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in {"add_argument", "option"}
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    return ""


def _long_training_hint(node: ast.AST) -> bool:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if (
            any(isinstance(target, ast.Name) and target.id.lower() in {"epochs", "num_epochs", "max_epochs"}
                for target in targets)
            and isinstance(value, ast.Constant)
            and isinstance(value.value, int)
            and value.value >= 100
        ):
            return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "range":
        return any(
            isinstance(arg, ast.Constant) and isinstance(arg.value, int) and arg.value >= 100
            for arg in node.args
        )
    return False


def _types_from_filename(filename: str) -> list[str]:
    types = []
    if filename == "__main__.py":
        types.append("utility")
    if "train" in filename:
        types.append("training")
    if filename in {"infer.py", "inference.py", "predict.py"}:
        types.append("inference")
    if filename in {"eval.py", "evaluate.py", "test.py"}:
        types.append("evaluation")
    if filename in {"demo.py", "app.py"}:
        types.append("demo")
    return types or ["unknown"]


def _sort_types(types: set[str] | list[str]) -> list[str]:
    order = ["training", "evaluation", "inference", "demo", "utility", "unknown"]
    return [entry_type for entry_type in order if entry_type in types]
