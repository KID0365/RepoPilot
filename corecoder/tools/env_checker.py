"""Static environment and reproduction-risk checks for AI/ML repositories."""

import re
from pathlib import Path

from .base import Tool


_ENV_FILES = (
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "setup.py",
    "setup.cfg",
    "Dockerfile",
    ".env.example",
    "README.md",
)

_DEPENDENCIES = (
    "torch",
    "torchvision",
    "transformers",
    "diffusers",
    "opencv",
    "numpy",
    "pandas",
    "scipy",
    "timm",
    "accelerate",
    "datasets",
    "gradio",
    "streamlit",
)

_DATA_TERMS = ("dataset", "data", "checkpoint", "ckpt", "pretrained", "weight", "model zoo")
_CUDA_TERMS = ("cuda", "cudnn", "gpu", "nvidia", "nvcc")
_ARTIFACT_TERMS = ("dataset", "checkpoint", "ckpt", "pretrained", "weight", "model zoo")


class EnvCheckerTool(Tool):
    name = "env_checker"
    description = (
        "Statically inspect environment files and flag dependency, Python, "
        "PyTorch, CUDA, dataset, and checkpoint reproduction risks."
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
        combined = "\n".join(contents.values())
        lower = combined.lower()

        dependencies = {
            dep: _dependency_versions(dep, combined)
            for dep in _DEPENDENCIES
            if _dependency_present(dep, lower)
        }
        python_mentions = _matching_lines(contents, ("python",), limit=8)
        cuda_mentions = _matching_lines(contents, _CUDA_TERMS, limit=10)
        data_mentions = _matching_lines(contents, _DATA_TERMS, limit=12)

        risks: list[str] = []
        dependency_files = {
            "requirements.txt", "pyproject.toml", "environment.yml",
            "setup.py", "setup.cfg", "Dockerfile",
        }
        if not dependency_files.intersection(found):
            risks.append("No dependency or container specification was found.")
        if not python_mentions:
            risks.append("Python version is not explicitly declared in inspected files.")
        if "torch" in dependencies and not dependencies["torch"]:
            risks.append("PyTorch is referenced without a detected version constraint.")
        if any(term in lower for term in _CUDA_TERMS):
            if not re.search(r"(cuda|cu)\s*[-:=]?\s*\d+(?:\.\d+)?", lower):
                risks.append("GPU/CUDA is referenced but no clear CUDA version was detected.")
        artifact_risk = any(term in lower for term in _ARTIFACT_TERMS)
        data_setup_risk = bool(
            re.search(r"\b(data|dataset)\b.{0,80}\b(download|prepare|path|directory|root)\b", lower)
            or re.search(r"\b(download|prepare)\b.{0,80}\b(data|dataset)\b", lower)
        )
        if artifact_risk or data_setup_risk:
            risks.append("Dataset or pretrained artifact preparation requires manual verification.")
        if ".env.example" not in found and any(term in lower for term in ("api key", "token", "secret")):
            risks.append("Credentials may be required, but no `.env.example` was found.")

        risk_level = _risk_level(
            risks,
            found,
            dependencies,
            artifact_risk or data_setup_risk,
        )
        completeness = _completeness(found)

        lines = [
            "# Environment Check",
            "",
            f"- Root: `{root}`",
            f"- Environment file completeness: **{completeness}**",
            f"- Reproduction risk level: **{risk_level}**",
            "",
            "## Files",
        ]
        for name in _ENV_FILES:
            path = found.get(name)
            lines.append(f"- {name}: " + (f"`{path.relative_to(root)}`" if path else "not found"))

        lines.extend(["", "## Key Dependencies"])
        if dependencies:
            for dep, versions in dependencies.items():
                detail = ", ".join(versions) if versions else "version not detected"
                lines.append(f"- `{dep}`: {detail}")
        else:
            lines.append("- No listed key AI/ML dependencies were detected.")

        lines.extend(["", "## Python / CUDA / PyTorch"])
        lines.append("- Python declarations:")
        lines.extend(f"  - {item}" for item in python_mentions or ["not detected"])
        lines.append("- CUDA/GPU declarations:")
        lines.extend(f"  - {item}" for item in cuda_mentions or ["not detected"])
        torch_detail = dependencies.get("torch")
        lines.append(
            "- PyTorch declaration: "
            + (", ".join(torch_detail) if torch_detail else "not detected or unpinned")
        )

        lines.extend(["", "## Dataset / Weight Preparation"])
        lines.extend(f"- {item}" for item in data_mentions or ["No explicit preparation keywords detected."])

        lines.extend(["", "## Reproduction Risks"])
        lines.extend(f"- {risk}" for risk in risks or ["No major static risks detected; runtime compatibility remains unverified."])
        return "\n".join(lines)


def _find_env_files(root: Path) -> dict[str, Path]:
    children = {
        path.name.lower(): path
        for path in root.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    return {
        name: children[name.lower()]
        for name in _ENV_FILES
        if name.lower() in children
    }


def _read_limited(path: Path, max_chars: int = 100_000) -> str:
    try:
        return path.read_text(errors="replace")[:max_chars]
    except OSError:
        return ""


def _dependency_versions(name: str, text: str) -> list[str]:
    package = r"opencv(?:-python)?" if name == "opencv" else re.escape(name)
    pattern = re.compile(
        rf"(?im)^\s*[\"']?{package}(?:\[[^\]]+\])?\s*"
        rf"((?:==|>=|<=|~=|>|<)\s*[^\s,;]+)?"
    )
    versions = []
    for match in pattern.finditer(text):
        value = (match.group(1) or "").replace(" ", "")
        if value and value not in versions:
            versions.append(value)
    return versions[:5]


def _dependency_present(name: str, text: str) -> bool:
    package = r"opencv(?:-python)?" if name == "opencv" else re.escape(name)
    return bool(re.search(rf"(?<![\w-]){package}(?![\w-])", text))


def _matching_lines(
    contents: dict[str, str],
    terms: tuple[str, ...],
    limit: int,
) -> list[str]:
    matches: list[str] = []
    pattern = re.compile(
        "|".join(rf"\b{re.escape(term)}\b" for term in terms),
        re.IGNORECASE,
    )
    for filename, text in contents.items():
        for line_number, line in enumerate(text.splitlines(), 1):
            clean = line.strip()
            if clean and pattern.search(clean):
                matches.append(f"`{filename}:{line_number}` {clean[:180]}")
                if len(matches) >= limit:
                    return matches
    return matches


def _completeness(found: dict[str, Path]) -> str:
    dependency_files = {
        "requirements.txt", "pyproject.toml", "environment.yml",
        "setup.py", "setup.cfg", "Dockerfile",
    }
    count = len(dependency_files.intersection(found))
    has_readme = "README.md" in found
    if count >= 2 and has_readme:
        return "good"
    if count >= 1:
        return "partial"
    return "poor"


def _risk_level(
    risks: list[str],
    found: dict[str, Path],
    dependencies: dict[str, list[str]],
    artifact_risk: bool,
) -> str:
    score = len(risks)
    if not found:
        score += 2
    if "torch" in dependencies and not dependencies["torch"]:
        score += 1
    if artifact_risk:
        score += 1
    if score >= 5:
        return "high"
    if score >= 2:
        return "medium"
    return "low"
