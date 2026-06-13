"""Lightweight structured evidence and risk helpers."""

from typing import Any


def make_evidence(
    file: str = "",
    line: int | None = None,
    text: str = "",
) -> dict[str, Any]:
    """Create a normalized evidence record."""
    return {
        "file": file,
        "line": line,
        "text": text.strip(),
    }


def make_risk(
    risk_type: str,
    category: str,
    severity: str,
    confidence: float,
    evidence: dict[str, Any] | None,
    impact: str,
    remediation: str,
) -> dict[str, Any]:
    """Create a normalized structured risk record."""
    if severity not in {"low", "medium", "high"}:
        raise ValueError(f"Unsupported severity: {severity}")
    return {
        "type": risk_type,
        "category": category,
        "severity": severity,
        "confidence": max(0.0, min(float(confidence), 1.0)),
        "evidence": evidence or make_evidence(),
        "impact": impact,
        "remediation": remediation,
    }


def format_risks_markdown(risks: list[dict[str, Any]]) -> str:
    """Render structured risks as concise Markdown."""
    if not risks:
        return "- No major static risks detected; runtime compatibility remains unverified."

    lines: list[str] = []
    for risk in risks:
        evidence = risk.get("evidence", {})
        location = evidence.get("file") or "repository"
        if evidence.get("line") is not None:
            location += f":{evidence['line']}"
        text = evidence.get("text") or "No direct line evidence."
        lines.extend([
            f"### `{risk['type']}`",
            (
                f"- Category: **{risk['category']}** | Severity: "
                f"**{risk['severity']}** | Confidence: **{risk['confidence']:.2f}**"
            ),
            f"- Evidence: `{location}` {text}",
            f"- Impact: {risk['impact']}",
            f"- Remediation: {risk['remediation']}",
            "",
        ])
    return "\n".join(lines).rstrip()
