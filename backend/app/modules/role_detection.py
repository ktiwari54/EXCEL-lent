from __future__ import annotations

import re
from typing import Any

ID_RE = re.compile(r"(^id$|_id$|uuid|sku|code|order.?id|customer.?id|employee.?id|invoice|ref)", re.I)
DATE_RE = re.compile(r"(date|time|period|dob|timestamp)", re.I)
MEASURE_RE = re.compile(
    r"(amount|revenue|sales|price|cost|profit|margin|total|qty|quantity|units|fee|discount|salary|budget|value)",
    re.I,
)
DIM_RE = re.compile(
    r"(region|country|city|category|product|customer|client|salesperson|employee|segment|channel|brand|store|location|market)",
    re.I,
)
STATUS_RE = re.compile(r"(status|state|stage|phase|flag)", re.I)
CONTACT_RE = re.compile(r"(email|phone|mobile|address|contact)", re.I)


def detect_role(name: str, data_type: str, unique_count: int, row_count: int) -> dict[str, Any]:
    """Likely analytical role of a column."""
    name_s = str(name)

    if data_type in ("email", "phone", "url") or CONTACT_RE.search(name_s):
        return {"role": "contact", "confidence": 0.9, "suggested_uses": ["Clean Data", "Lookup / Match"]}

    if data_type in ("date", "datetime") or DATE_RE.search(name_s):
        return {
            "role": "date_dimension",
            "confidence": 0.92,
            "suggested_uses": ["Compare", "Summarize", "Charts", "Dashboard"],
        }

    if data_type == "identifier" or ID_RE.search(name_s):
        return {
            "role": "identifier",
            "confidence": 0.9,
            "suggested_uses": ["Lookup / Match", "Find Duplicates"],
        }

    if STATUS_RE.search(name_s) or (data_type == "category" and unique_count <= 15 and STATUS_RE.search(name_s)):
        return {
            "role": "status",
            "confidence": 0.8,
            "suggested_uses": ["Summarize", "Compare", "Charts"],
        }

    if data_type in ("currency", "number", "integer", "decimal", "percentage") or MEASURE_RE.search(name_s):
        # high cardinality numeric still measure; low unique integers might be dimension
        if data_type in ("integer",) and unique_count <= 20 and not MEASURE_RE.search(name_s):
            return {
                "role": "dimension",
                "confidence": 0.6,
                "suggested_uses": ["Summarize", "Compare", "Charts"],
            }
        return {
            "role": "measure",
            "confidence": 0.88 if MEASURE_RE.search(name_s) else 0.75,
            "suggested_uses": ["Calculate", "Compare", "Summarize", "Charts", "Dashboard"],
        }

    if data_type == "category" or DIM_RE.search(name_s):
        return {
            "role": "dimension",
            "confidence": 0.85 if DIM_RE.search(name_s) else 0.7,
            "suggested_uses": ["Summarize", "Compare", "Charts", "Pivot Table"],
        }

    if data_type == "boolean":
        return {"role": "status", "confidence": 0.7, "suggested_uses": ["Summarize", "Filter"]}

    # text with low unique → dimension
    if row_count and unique_count / max(row_count, 1) < 0.2:
        return {
            "role": "dimension",
            "confidence": 0.65,
            "suggested_uses": ["Summarize", "Charts"],
        }

    return {
        "role": "dimension" if unique_count < max(50, row_count * 0.3) else "text_attribute",
        "confidence": 0.5,
        "suggested_uses": ["Clean Data", "Lookup / Match"],
    }
