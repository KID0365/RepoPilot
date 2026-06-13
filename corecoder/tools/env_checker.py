"""Evidence-based environment and reproduction-risk checks."""

import ast
import configparser
import re
from pathlib import Path

from ..diagnosis import format_risks_markdown, make_evidence, make_risk
from .base import Tool

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None


_ROOT_ENV_FILES = (
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "environment.yaml",
    "setup.py",
    "setup.cfg",
    "Dockerfile",
    ".env.example",
    "README.md",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
)

_DEPENDENCY_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "environment.yaml",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
}

_KEY_DEPENDENCIES = {
    "torch", "torchvision", "transformers", "diffusers", "opencv-python",
    "numpy", "pandas", "scipy", "timm", "accelerate", "datasets",
    "gradio", "streamlit",
}

_CUDA_TERMS = ("cuda", "cudnn", "gpu", "nvidia", "nvcc", "cudatoolkit")
_CHECKPOINT_PATTERN = re.compile(
    r"\b(checkpoint|ckpt|pretrained|model\s+zoo|weights?\.(?:pt|pth|ckpt|bin|safetensors))\b",
    re.IGNORECASE,
)


class EnvCheckerTool(Tool):
    name = "env_checker"
    description = (
        "Statically parse environment files and report evidence-based dependency, "
        "Python, PyTorch, CUDA, dataset, checkpoint, and platform risks."
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

        found = _find_env_files(root)
        contents = {
            name: _read_limited(path)
            for name, path in found.items()
        }
        parsed = _parse_environment_files(found, contents)
        risks = _build_risks(found, contents, parsed)
        risk_level = _overall_risk_level(risks)

        lines = [
            "# Environment Check",
            "",
            f"- Root: `{root}`",
            f"- Environment file completeness: **{_completeness(found)}**",
            f"- Reproduction risk level: **{risk_level}**",
            "",
            "## Environment Files",
        ]
        for name in _ROOT_ENV_FILES:
            path = found.get(name)
            lines.append(f"- {name}: " + (f"`{path.relative_to(root)}`" if path else "not found"))
        requirement_files = sorted(
            name for name in found
            if name.startswith("requirements/") and name.endswith(".txt")
        )
        for name in requirement_files:
            lines.append(f"- {name}: `{found[name].relative_to(root)}`")

        lines.extend(["", "## Parsed Dependencies"])
        dependencies = parsed["dependencies"]
        if dependencies:
            for name in sorted(dependencies):
                values = dependencies[name]
                detail = ", ".join(values) if values else "version not detected"
                lines.append(f"- `{name}`: {detail}")
        else:
            lines.append("- No key AI/ML dependencies were parsed.")
        lines.append(
            "- Python requirement: "
            + (f"`{parsed['python']}`" if parsed["python"] else "not detected")
        )

        lines.extend([
            "",
            "## Structured Risks",
            format_risks_markdown(risks),
            "",
            "## Evidence",
        ])
        evidence_lines = _collect_evidence(contents)
        lines.extend(f"- {item}" for item in evidence_lines or ["No environment evidence lines detected."])

        lines.extend([
            "",
            "## Reproduction Environment Summary",
            f"- Dependency specification: **{'available' if _has_dependency_spec(found) else 'missing'}**",
            f"- Python version: **{parsed['python'] or 'unresolved'}**",
            (
                "- PyTorch: **"
                + (_dependency_summary(dependencies, "torch") or "not detected")
                + "**"
            ),
            f"- CUDA/GPU requirement: **{'referenced' if parsed['cuda_referenced'] else 'not detected'}**",
            "- Runtime installation and hardware compatibility remain unverified.",
        ])
        return "\n".join(lines)


def _find_env_files(root: Path) -> dict[str, Path]:
    children = {
        path.name.lower(): path
        for path in root.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    found = {
        name: children[name.lower()]
        for name in _ROOT_ENV_FILES
        if name.lower() in children
    }
    requirements_dir = root / "requirements"
    if requirements_dir.is_dir() and not requirements_dir.is_symlink():
        for path in sorted(requirements_dir.glob("*.txt")):
            if path.is_file() and not path.is_symlink():
                found[path.relative_to(root).as_posix()] = path
    return found


def _read_limited(path: Path, max_chars: int = 100_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return ""


def _parse_environment_files(
    found: dict[str, Path],
    contents: dict[str, str],
) -> dict:
    dependencies: dict[str, list[str]] = {}
    python_requirement = ""

    for name, text in contents.items():
        if name == "pyproject.toml":
            py_deps, py_python = _parse_pyproject(found[name])
            _merge_dependencies(dependencies, py_deps)
            python_requirement = python_requirement or py_python
        elif name == "setup.cfg":
            cfg_deps, cfg_python = _parse_setup_cfg(text)
            _merge_dependencies(dependencies, cfg_deps)
            python_requirement = python_requirement or cfg_python
        elif name == "setup.py":
            setup_deps, setup_python = _parse_setup_py(text)
            _merge_dependencies(dependencies, setup_deps)
            python_requirement = python_requirement or setup_python
        elif name == "requirements.txt" or name.startswith("requirements/"):
            _merge_dependencies(dependencies, _parse_requirement_lines(text))
        elif name in {"environment.yml", "environment.yaml"}:
            _merge_dependencies(dependencies, _parse_environment_text(text))
            python_requirement = python_requirement or _extract_python_requirement(text)

    combined = "\n".join(contents.values())
    cuda_evidence = _first_operational_evidence(
        contents,
        tuple(rf"\b{term}\b" for term in _CUDA_TERMS),
    )
    if not python_requirement:
        python_requirement = _extract_python_requirement(combined)
    return {
        "dependencies": dependencies,
        "python": python_requirement,
        "cuda_referenced": bool(cuda_evidence.get("text")),
        "cuda_version": _extract_cuda_version(combined),
    }


def _parse_pyproject(path: Path) -> tuple[dict[str, list[str]], str]:
    if tomllib is None:
        return {}, ""
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except (OSError, ValueError):
        return {}, ""

    project = data.get("project", {})
    requirements = list(project.get("dependencies", []))
    for values in project.get("optional-dependencies", {}).values():
        requirements.extend(values)
    poetry = data.get("tool", {}).get("poetry", {})
    for name, value in poetry.get("dependencies", {}).items():
        if name.lower() == "python":
            continue
        requirements.append(f"{name}{value}" if isinstance(value, str) else name)
    python_requirement = project.get("requires-python", "")
    if not python_requirement:
        value = poetry.get("dependencies", {}).get("python", "")
        python_requirement = value if isinstance(value, str) else ""
    return _parse_requirement_items(requirements), python_requirement


def _parse_setup_cfg(text: str) -> tuple[dict[str, list[str]], str]:
    parser = configparser.ConfigParser()
    try:
        parser.read_string(text)
    except configparser.Error:
        return {}, ""
    dependencies: dict[str, list[str]] = {}
    python_requirement = ""
    if parser.has_section("options"):
        _merge_dependencies(
            dependencies,
            _parse_requirement_lines(parser.get("options", "install_requires", fallback="")),
        )
        python_requirement = parser.get("options", "python_requires", fallback="")
    return dependencies, python_requirement


def _parse_setup_py(text: str) -> tuple[dict[str, list[str]], str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _parse_requirement_lines(text), _extract_python_requirement(text)
    requirements: list[str] = []
    python_requirement = ""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg == "install_requires" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                for item in keyword.value.elts:
                    if isinstance(item, ast.Constant) and isinstance(item.value, str):
                        requirements.append(item.value)
            elif (
                keyword.arg == "python_requires"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                python_requirement = keyword.value.value
    return _parse_requirement_items(requirements), python_requirement


def _parse_requirement_lines(text: str) -> dict[str, list[str]]:
    items = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-", "git+", "http://", "https://")):
            continue
        items.append(line.split(";", 1)[0].strip())
    return _parse_requirement_items(items)


def _parse_environment_text(text: str) -> dict[str, list[str]]:
    items = []
    for line in text.splitlines():
        clean = line.strip().lstrip("-").strip()
        if clean and any(name in clean.lower() for name in _KEY_DEPENDENCIES):
            items.append(clean)
    return _parse_requirement_items(items)


def _parse_requirement_items(items: list[str]) -> dict[str, list[str]]:
    dependencies: dict[str, list[str]] = {}
    pattern = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$")
    for item in items:
        match = pattern.match(str(item))
        if not match:
            continue
        raw_name, constraint = match.groups()
        normalized = raw_name.lower().replace("_", "-")
        key = "opencv-python" if normalized.startswith("opencv") else normalized
        if key not in _KEY_DEPENDENCIES:
            continue
        value = constraint.strip().rstrip(",")
        dependencies.setdefault(key, [])
        if value and value not in dependencies[key]:
            dependencies[key].append(value)
    return dependencies


def _merge_dependencies(target: dict[str, list[str]], source: dict[str, list[str]]) -> None:
    for name, values in source.items():
        target.setdefault(name, [])
        for value in values:
            if value not in target[name]:
                target[name].append(value)


def _build_risks(
    found: dict[str, Path],
    contents: dict[str, str],
    parsed: dict,
) -> list[dict]:
    risks: list[dict] = []
    combined = "\n".join(contents.values())
    dependencies = parsed["dependencies"]

    if not _has_dependency_spec(found):
        risks.append(make_risk(
            "dependency_file_missing", "dependency", "high", 1.0,
            make_evidence(text="No supported dependency specification was found."),
            "The Python environment cannot be reconstructed reliably.",
            "Add requirements.txt, pyproject.toml, or environment.yml with version constraints.",
        ))
    if not parsed["python"]:
        risks.append(make_risk(
            "python_version_missing", "environment", "medium", 0.9,
            make_evidence(text="No explicit Python version requirement was parsed."),
            "Different Python versions may produce installation or syntax failures.",
            "Declare requires-python or document an exact supported Python range.",
        ))
    if "torch" in dependencies and not dependencies["torch"]:
        risks.append(make_risk(
            "pytorch_version_unpinned", "dependency", "high", 0.95,
            _first_evidence(contents, (r"\btorch\b",)),
            "PyTorch API and binary compatibility may vary across installations.",
            "Pin or bound the supported PyTorch version.",
        ))
    if parsed["cuda_referenced"] and not parsed["cuda_version"]:
        risks.append(make_risk(
            "cuda_version_missing", "cuda", "high", 0.9,
            _first_operational_evidence(
                contents,
                tuple(rf"\b{term}\b" for term in _CUDA_TERMS),
            ),
            "The PyTorch build, driver, and CUDA runtime may be incompatible.",
            "Document a tested PyTorch, CUDA, and driver combination.",
        ))

    dataset_evidence = _first_operational_evidence(
        contents,
        (r"\bdataset\b", r"\bdata(?:set)?\s+(?:root|path|directory)\b"),
    )
    dataset_text = dataset_evidence.get("text", "")
    if dataset_text and not re.search(
        r"(download|prepare|path|directory|root|place|extract|data/|datasets?/)",
        dataset_text,
        re.IGNORECASE,
    ):
        risks.append(make_risk(
            "dataset_preparation_unclear", "dataset", "medium", 0.7,
            dataset_evidence,
            "The required dataset location or preparation steps may be ambiguous.",
            "Document dataset source, expected directory layout, and preparation command.",
        ))

    checkpoint_evidence = _first_operational_evidence(
        contents,
        (_CHECKPOINT_PATTERN.pattern,),
    )
    checkpoint_text = checkpoint_evidence.get("text", "")
    if checkpoint_text and not re.search(
        r"(https?://|download|path|directory|load|from_pretrained|\.pt\b|\.pth\b|\.ckpt\b)",
        checkpoint_text,
        re.IGNORECASE,
    ):
        risks.append(make_risk(
            "checkpoint_preparation_unclear", "checkpoint", "medium", 0.75,
            checkpoint_evidence,
            "Evaluation or inference may depend on an unavailable model artifact.",
            "Document the checkpoint source, filename, checksum, and expected location.",
        ))

    if parsed["cuda_referenced"] and "Dockerfile" not in found:
        risks.append(make_risk(
            "docker_missing", "environment", "low", 0.65,
            make_evidence(text="CUDA/GPU is referenced but no Dockerfile was found."),
            "System-level dependencies may be harder to reproduce consistently.",
            "Optionally provide a tested container definition or exact system requirements.",
        ))

    credential_evidence = _first_evidence(
        contents, (r"\bapi[_ -]?key\b", r"\baccess[_ -]?token\b", r"\bsecret\b")
    )
    if credential_evidence.get("text") and ".env.example" not in found:
        risks.append(make_risk(
            "env_example_missing", "config", "medium", 0.85,
            credential_evidence,
            "Required credentials or configuration names may be unclear.",
            "Add a redacted .env.example listing required variables.",
        ))

    download_evidence = _first_evidence(
        contents,
        (r"\b(?:wget|curl)\b", r"\bdownload\s*=\s*True\b", r"\bdownload\b.*https?://"),
    )
    if download_evidence.get("text"):
        risks.append(make_risk(
            "network_download_required", "dataset", "medium", 0.9,
            download_evidence,
            "A first run may require network access or download large artifacts.",
            "Document download size and provide an offline preparation path.",
        ))

    platform_evidence = _first_evidence(
        contents,
        (r"\bstty\b", r"\bchmod\b", r"\bapt(?:-get)?\b", r"\bexport\s+\w+=", r"\bsource\s+\S+"),
    )
    has_cross_platform_activation = bool(
        re.search(r"\bsource\s+\S+", combined, re.IGNORECASE)
        and re.search(r"Activate\.ps1", combined, re.IGNORECASE)
    )
    if platform_evidence.get("text") and not has_cross_platform_activation:
        risks.append(make_risk(
            "platform_specific_command", "platform", "medium", 0.8,
            platform_evidence,
            "The documented command may fail on another operating system.",
            "Provide equivalent Windows and POSIX instructions or a portable alternative.",
        ))
    return risks


def _first_evidence(
    contents: dict[str, str],
    patterns: tuple[str, ...],
) -> dict:
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for filename, text in contents.items():
        for line_number, line in _evidence_lines(filename, text):
            clean = line.strip()
            if clean and any(regex.search(clean) for regex in regexes):
                return make_evidence(filename, line_number, clean[:240])
    return make_evidence()


def _first_operational_evidence(
    contents: dict[str, str],
    patterns: tuple[str, ...],
) -> dict:
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    operational = re.compile(
        r"(require|install|pip |conda |version|>=|==|cuda\d|cu\d{2,3}|"
        r"torch\.|download|load|resume|path|directory|root|run |python |"
        r"需要|要求|安装|版本|下载|加载|路径|运行)",
        re.IGNORECASE,
    )
    descriptive = re.compile(
        r"(diagnos|detect|inspect|check|risk|report|tool|unverified|not verified|"
        r"诊断|检测|检查|识别|风险|报告|工具|是否明确|如何准备|不验证|未验证|兼容性)",
        re.IGNORECASE,
    )
    for filename, text in contents.items():
        for line_number, line in _evidence_lines(filename, text):
            clean = line.strip()
            if not clean or descriptive.search(clean):
                continue
            if any(regex.search(clean) for regex in regexes) and (
                filename != "README.md" or operational.search(clean)
            ):
                return make_evidence(filename, line_number, clean[:240])
    return make_evidence()


def _collect_evidence(contents: dict[str, str], limit: int = 16) -> list[str]:
    patterns = (
        r"\bpython\b", r"\btorch(?:vision)?\b", r"\bcuda\b", r"\bcudnn\b",
        r"\bdataset\b", _CHECKPOINT_PATTERN.pattern, r"\bdownload\b", r"\bstty\b",
    )
    matches: list[str] = []
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for filename, text in contents.items():
        for line_number, line in _evidence_lines(filename, text):
            clean = line.strip()
            if clean and any(regex.search(clean) for regex in regexes):
                matches.append(f"`{filename}:{line_number}` {clean[:200]}")
                if len(matches) >= limit:
                    return matches
    return matches


def _evidence_lines(filename: str, text: str):
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if filename == "README.md" and line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield line_number, line


def _extract_python_requirement(text: str) -> str:
    patterns = (
        r"requires-python\s*=\s*[\"']([^\"']+)",
        r"python_requires\s*=\s*[\"']([^\"']+)",
        r"\bpython\s*(?:version)?\s*[:=]?\s*(>=|<=|==|~=|>|<)?\s*(\d+\.\d+(?:\.\d+)?)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = [group for group in match.groups() if group]
            return "".join(groups)
    return ""


def _extract_cuda_version(text: str) -> str:
    match = re.search(
        r"\b(?:cuda|cudatoolkit)\s*[-:=]?\s*(\d+(?:\.\d+)?)\b|\bcu(\d{2,3})\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""
    return next(group for group in match.groups() if group)


def _has_dependency_spec(found: dict[str, Path]) -> bool:
    return any(
        name in _DEPENDENCY_FILES or name.startswith("requirements/")
        for name in found
    )


def _completeness(found: dict[str, Path]) -> str:
    count = sum(
        1 for name in found
        if name in _DEPENDENCY_FILES or name.startswith("requirements/")
    )
    has_readme = "README.md" in found
    if count >= 2 and has_readme:
        return "good"
    if count >= 1:
        return "partial"
    return "poor"


def _overall_risk_level(risks: list[dict]) -> str:
    severities = {risk["severity"] for risk in risks}
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def _dependency_summary(dependencies: dict[str, list[str]], name: str) -> str:
    if name not in dependencies:
        return ""
    return ", ".join(dependencies[name]) if dependencies[name] else "version not detected"
