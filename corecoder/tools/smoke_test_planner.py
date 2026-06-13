"""Generate a safe smoke-test plan without executing repository code."""

import ast
import os
from pathlib import Path

from ..diagnosis import format_risks_markdown, make_evidence, make_risk
from .base import Tool
from .entry_detector import (
    _candidate_files,
    _declared_script_entries,
    _inspect_candidate,
    _long_training_hint,
    _readme_commands,
)
from .repo_map import _SKIP_DIRS


class SmokeTestPlannerTool(Tool):
    name = "smoke_test_planner"
    description = (
        "Generate a low-cost, evidence-based smoke test plan. "
        "Only suggests commands; never executes them or downloads artifacts."
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

        commands = _readme_commands(root)
        candidates = [
            _inspect_candidate(root, path, commands)
            for path in _candidate_files(root)
            if path.suffix.lower() == ".py"
        ]
        candidates.extend(_declared_script_entries(root, commands))
        python_files = _python_files(root)
        signals = _scan_signals(root, python_files)
        imports = _import_checks(root, python_files)
        cli_checks = _cli_checks(candidates)
        risks = _planning_risks(root, signals)

        lines = [
            "# Smoke Test Plan",
            "",
            "> Suggested only, not executed. This tool does not run commands, "
            "download data, train models, modify files, or use the network.",
            "",
            "## 1. Preflight Checks",
            "- `python --version`",
        ]
        if signals["torch"]:
            lines.extend([
                '- `python -c "import torch; print(torch.__version__)"`',
                '- `python -c "import torch; print(torch.cuda.is_available())"`',
            ])
        else:
            lines.append("- Confirm the documented Python environment before installing dependencies.")

        lines.extend(["", "## 2. Import Checks"])
        lines.extend(f"- `{command}`" for command in imports)
        if not imports:
            lines.append("- No safe importable top-level modules were identified.")

        lines.extend(["", "## 3. CLI Checks"])
        lines.extend(f"- `{command}`" for command in cli_checks)
        if not cli_checks:
            lines.append("- No high-confidence `--help` command was identified.")

        lines.extend([
            "",
            "## 4. Safe Runtime Checks",
            "- Prefer CPU-only checks before enabling CUDA or multiple GPUs.",
        ])
        if signals["download"]:
            lines.append(
                "- Dataset preparation may require download, but RepoPilot does "
                "not execute or suggest download commands as smoke tests."
            )
        if signals["long_training"]:
            lines.extend([
                "- Do not run the default training entry as a smoke test: a long epoch/step count was detected.",
                (
                    "- A lightweight runtime check would require explicit bounded "
                    "options such as `--epochs 1` and `--cpu`; do not assume those "
                    "options exist unless the repository defines them."
                ),
            ])
        if signals["checkpoint"]:
            lines.append("- Confirm checkpoint paths before inference or resume checks.")
        if signals["data_parallel"]:
            lines.append("- Start with a single device; DataParallel or distributed behavior is not part of this plan.")
        if not any((
            signals["download"], signals["long_training"],
            signals["checkpoint"], signals["data_parallel"],
        )):
            lines.append("- Only run bounded help/import checks unless the user explicitly approves more.")

        lines.extend([
            "",
            "## 5. Expected Failures",
            format_risks_markdown(risks),
            "",
            "## 6. Verification Status",
            "- Static evidence: **available**",
            "- Smoke-test verified: **not executed**",
            "- Full reproduction: **unverified**",
        ])
        return "\n".join(lines)


def _python_files(root: Path, limit: int = 300) -> list[Path]:
    files = []
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        dirnames[:] = [
            name for name in dirnames
            if name not in _SKIP_DIRS
            and name != "tests"
            and not (current_path / name).is_symlink()
        ]
        for filename in filenames:
            path = current_path / filename
            if filename.endswith(".py") and not path.is_symlink():
                files.append(path)
                if len(files) >= limit:
                    return files
    return files


def _scan_signals(root: Path, files: list[Path]) -> dict[str, bool]:
    signals = {
        "torch": False,
        "cuda": False,
        "cudnn": False,
        "data_parallel": False,
        "download": False,
        "checkpoint": False,
        "long_training": False,
    }
    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name.split(".")[0] == "torch" for alias in node.names):
                    signals["torch"] = True
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] == "torch":
                    signals["torch"] = True
            elif isinstance(node, ast.Call):
                call_name = _call_name(node.func)
                lower_name = call_name.lower()
                if lower_name.endswith((".cuda", ".to")):
                    signals["cuda"] = True
                if lower_name.endswith(("dataparallel", "distributeddataparallel")):
                    signals["data_parallel"] = True
                if lower_name.endswith(("torch.load", "load_state_dict", "from_pretrained")):
                    signals["checkpoint"] = True
                for keyword in node.keywords:
                    if (
                        keyword.arg == "download"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ):
                        signals["download"] = True
            elif isinstance(node, ast.Attribute):
                if node.attr.lower() == "cudnn":
                    signals["cudnn"] = True
                if node.attr.lower() == "cuda":
                    signals["cuda"] = True
            if _long_training_hint(node):
                signals["long_training"] = True
    return signals


def _import_checks(root: Path, files: list[Path]) -> list[str]:
    modules = []
    for path in files:
        relative = path.relative_to(root)
        if len(relative.parts) == 1 and path.name not in {"setup.py", "__main__.py"}:
            modules.append(path.stem)
        elif (
            path.name == "__init__.py"
            and len(relative.parts) == 2
            and relative.parts[0] != "tests"
        ):
            modules.append(relative.parts[0])
    commands = []
    for module in sorted(set(modules))[:8]:
        if module.isidentifier():
            commands.append(
                f"python -c \"import {module}; print('{module} OK')\""
            )
    return commands


def _cli_checks(candidates: list[dict]) -> list[str]:
    checks = []
    for candidate in candidates:
        evidence = " ".join(candidate["evidence"]).lower()
        if "declared console script" in evidence and candidate["invocations"]:
            command = f"{candidate['invocations'][0]} --help"
        elif "cli framework" in evidence or "cli arguments" in evidence:
            command = f"python {candidate['path']} --help"
        else:
            continue
        if command not in checks:
            checks.append(command)
    return checks[:10]


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _planning_risks(root: Path, signals: dict[str, bool]) -> list[dict]:
    risks = []
    dependency_files = [
        root / "requirements.txt",
        root / "pyproject.toml",
        root / "environment.yml",
        root / "environment.yaml",
        root / "setup.py",
        root / "setup.cfg",
    ]
    if not any(path.exists() for path in dependency_files):
        risks.append(make_risk(
            "dependency_file_missing", "dependency", "high", 1.0,
            make_evidence(text="No standard dependency file was found."),
            "Import checks may fail before the application is reached.",
            "Create an isolated environment from documented, pinned dependencies first.",
        ))
    if signals["download"]:
        risks.append(make_risk(
            "network_download_required", "dataset", "high", 0.95,
            make_evidence(text="Source code contains `download=True`."),
            "Running an entry point may start an unapproved network download.",
            "Prepare data separately and disable automatic download before any runtime check.",
        ))
    if signals["checkpoint"]:
        risks.append(make_risk(
            "checkpoint_required", "checkpoint", "medium", 0.8,
            make_evidence(text="Checkpoint or pretrained loading code was detected."),
            "Inference, evaluation, or resume commands may fail without an artifact.",
            "Confirm the expected checkpoint path before executing a runtime command.",
        ))
    if signals["long_training"]:
        risks.append(make_risk(
            "long_training_default", "entry_point", "high", 0.9,
            make_evidence(text="A large default epoch or step count was detected."),
            "Running the default entry may start a costly training job.",
            "Use only `--help` until a bounded epoch or max-step override is confirmed.",
        ))
    if signals["cuda"] and not (root / "Dockerfile").exists():
        risks.append(make_risk(
            "cuda_environment_unverified", "cuda", "medium", 0.75,
            make_evidence(text="CUDA usage was detected without a container definition."),
            "GPU checks may fail because of driver or PyTorch binary mismatch.",
            "Verify Python, PyTorch, CUDA, and driver versions before enabling GPU execution.",
        ))
    return risks
