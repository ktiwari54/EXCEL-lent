from __future__ import annotations

from typing import Any


def merge_explanations(pieces: list[dict[str, Any]], task_request: dict[str, Any]) -> dict[str, Any]:
    """Build business + technical transparency block for results."""
    explanations = [p["explanation"] for p in pieces if p.get("explanation")]
    primary = explanations[0] if explanations else {}
    filters = (task_request.get("normalized") or {}).get("filters") or []
    return {
        "business": primary.get("what")
        or task_request.get("task_name")
        or "Analysis complete",
        "logic": primary.get("logic") or "Computed from configured fields and filters.",
        "fields_used": primary.get("fields")
        or list(
            filter(
                None,
                [
                    (task_request.get("normalized") or {}).get("measure"),
                    (task_request.get("normalized") or {}).get("date_field"),
                ],
            )
        ),
        "filters_applied": filters,
        "excel_equivalent": primary.get("excel_equivalent"),
        "assumptions": [
            "Blank numeric values are ignored in aggregations.",
            "Filters use AND logic unless specified.",
            "Correlation does not imply causation." if any(p.get("engine") == "statistics" for p in pieces) else None,
        ],
        "mode": {
            "business": primary.get("what") or "Result ready for decision-making.",
            "technical": primary.get("excel_equivalent") or primary.get("logic"),
        },
    }
