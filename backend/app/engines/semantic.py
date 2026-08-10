from __future__ import annotations

from typing import Any

import pandas as pd


class SemanticDataLayer:
    """
    Business-friendly view of a dataset:
    measures, dimensions, dates, identifiers, quality signals.
    Built from Step 1 column_profiles + live dataframe.
    """

    def build(self, dataset: dict[str, Any], df: pd.DataFrame | None = None) -> dict[str, Any]:
        profiles = dataset.get("column_profiles") or []
        measures, dimensions, dates, identifiers, contacts = [], [], [], [], []

        for p in profiles:
            entry = {
                "name": p.get("name"),
                "data_type": p.get("data_type"),
                "role": p.get("role"),
                "null_pct": p.get("null_pct"),
            }
            role = p.get("role")
            dtype = p.get("data_type")
            if role == "measure" or dtype in ("currency", "number", "integer", "decimal", "percentage"):
                measures.append(entry)
            if role in ("dimension", "status") or dtype == "category":
                dimensions.append(entry)
            if role == "date_dimension" or dtype in ("date", "datetime"):
                dates.append(entry)
            if role == "identifier" or dtype == "identifier":
                identifiers.append(entry)
            if role == "contact" or dtype in ("email", "phone"):
                contacts.append(entry)

        quality = dataset.get("quality") or {}
        return {
            "dataset_id": dataset.get("id"),
            "dataset_name": dataset.get("name"),
            "rows": dataset.get("rows") or (len(df) if df is not None else 0),
            "columns": dataset.get("columns") or (len(df.columns) if df is not None else 0),
            "measures": measures,
            "dimensions": dimensions,
            "dates": dates,
            "identifiers": identifiers,
            "contacts": contacts,
            "health": (dataset.get("health") or {}).get("score"),
            "quality_issue_count": quality.get("issue_count", 0),
            "column_names": list(df.columns) if df is not None else [p.get("name") for p in profiles],
            "layer": "semantic_data",
        }

    def resolve_column(self, semantic: dict[str, Any], preferred: str | None, catalog: str = "measures") -> str | None:
        if preferred and preferred in (semantic.get("column_names") or []):
            return preferred
        items = semantic.get(catalog) or []
        return items[0]["name"] if items else None
