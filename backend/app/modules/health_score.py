from __future__ import annotations

from typing import Any


def compute_health_score(
    *,
    rows: int,
    columns: int,
    missing_cells: int,
    duplicate_rows: int,
    issues: list[dict[str, Any]],
    type_confidences: list[float],
) -> dict[str, Any]:
    """Transparent data health score 0-100 with component breakdown."""
    cells = max(rows * max(columns, 1), 1)

    # Completeness: non-missing cells
    missing_ratio = missing_cells / cells
    completeness = max(0.0, 100.0 * (1.0 - missing_ratio))

    # Uniqueness: penalize duplicate rows
    dup_ratio = duplicate_rows / max(rows, 1)
    uniqueness = max(0.0, 100.0 * (1.0 - min(dup_ratio * 2, 1.0)))

    # Validity: penalize high/warning validity issues
    validity_hits = sum(
        1
        for i in issues
        if i.get("category") in ("validity",) or i.get("severity") == "high"
    )
    validity = max(0.0, 100.0 - validity_hits * 8)

    # Consistency: capitalization / formatting issues
    consistency_hits = sum(1 for i in issues if i.get("category") in ("consistency", "formatting"))
    consistency = max(0.0, 100.0 - consistency_hits * 5)

    # Type confidence
    if type_confidences:
        type_confidence = 100.0 * (sum(type_confidences) / len(type_confidences))
    else:
        type_confidence = 50.0

    overall = round(
        0.30 * completeness
        + 0.20 * validity
        + 0.20 * uniqueness
        + 0.15 * consistency
        + 0.15 * type_confidence
    )
    overall = int(max(0, min(100, overall)))

    reasons: list[str] = []
    if missing_ratio > 0.02:
        reasons.append(f"Completeness reduced by {missing_pct(missing_ratio)}% missing cells.")
    if duplicate_rows:
        reasons.append(f"{duplicate_rows} duplicate row(s) reduce uniqueness.")
    if validity_hits:
        reasons.append(f"{validity_hits} validity concern(s) found.")
    if consistency_hits:
        reasons.append(f"{consistency_hits} formatting/consistency issue(s) found.")
    if type_confidence < 70:
        reasons.append("Some columns have low type-detection confidence.")
    if not reasons:
        reasons.append("No major quality issues detected; score is based on completeness and type confidence.")

    return {
        "score": overall,
        "completeness": round(completeness, 1),
        "validity": round(validity, 1),
        "uniqueness": round(uniqueness, 1),
        "consistency": round(consistency, 1),
        "type_confidence": round(type_confidence, 1),
        "explanation": reasons,
        "weights": {
            "completeness": 0.30,
            "validity": 0.20,
            "uniqueness": 0.20,
            "consistency": 0.15,
            "type_confidence": 0.15,
        },
    }


def missing_pct(ratio: float) -> str:
    return f"{100 * ratio:.1f}"
