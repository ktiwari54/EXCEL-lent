from __future__ import annotations

from typing import Any

import pandas as pd


def detect_relationships(datasets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    datasets: [{id, name, columns: [str], sample_frames optional via dfs dict}]
    Pass list of {dataset_id, name, df}
    """
    rels: list[dict[str, Any]] = []
    if len(datasets) < 2:
        return rels

    for i, left in enumerate(datasets):
        for right in datasets[i + 1 :]:
            ldf: pd.DataFrame = left["df"]
            rdf: pd.DataFrame = right["df"]
            for lc in ldf.columns:
                for rc in rdf.columns:
                    conf = _column_match_confidence(ldf[lc], rdf[rc], str(lc), str(rc))
                    if conf >= 0.7:
                        rels.append(
                            {
                                "left_dataset_id": left["id"],
                                "left_dataset_name": left["name"],
                                "left_column": str(lc),
                                "right_dataset_id": right["id"],
                                "right_dataset_name": right["name"],
                                "right_column": str(rc),
                                "confidence": round(conf * 100),
                                "status": "suggested",  # suggested | accepted | ignored
                                "label": f"{left['name']}.{lc} → {right['name']}.{rc}",
                            }
                        )
    # best first
    rels.sort(key=lambda r: r["confidence"], reverse=True)
    return rels[:20]


def _column_match_confidence(a: pd.Series, b: pd.Series, an: str, bn: str) -> float:
    name_score = 0.0
    al, bl = an.lower().replace(" ", ""), bn.lower().replace(" ", "")
    if al == bl:
        name_score = 0.55
    elif al in bl or bl in al:
        name_score = 0.35
    elif al.endswith("id") and bl.endswith("id") and (al.replace("id", "") in bl or bl.replace("id", "") in al):
        name_score = 0.4

    sa = set(a.dropna().astype(str).head(500).tolist())
    sb = set(b.dropna().astype(str).head(500).tolist())
    if not sa or not sb:
        return name_score * 0.5

    overlap = len(sa & sb) / max(min(len(sa), len(sb)), 1)
    # prefer ID-like columns for relationships
    id_boost = 0.1 if ("id" in al or "id" in bl or "code" in al or "code" in bl or "sku" in al) else 0.0
    score = min(1.0, name_score + 0.55 * overlap + id_boost)
    if overlap < 0.05 and name_score < 0.5:
        return 0.0
    return score
