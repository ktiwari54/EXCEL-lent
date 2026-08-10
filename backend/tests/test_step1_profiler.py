from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.modules.dataset_manager import DatasetManager
from app.modules.profiler import profile_dataframe
from app.modules.workbook_parser import parse_upload, suggest_dataset_name

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sales_sample.csv"


def test_parse_csv():
    content = SAMPLE.read_bytes()
    parsed = parse_upload(content, "sales_sample.csv")
    assert parsed["kind"] == "csv"
    assert len(parsed["sheets"]) == 1
    assert parsed["sheets"][0]["rows"] == 30


def test_profile_sales():
    df = pd.read_csv(SAMPLE)
    p = profile_dataframe(df)
    assert p["rows"] == 30
    assert p["health"]["score"] >= 0
    names = {c["name"]: c for c in p["column_profiles"]}
    assert "Revenue" in names
    assert names["Revenue"]["role"] in ("measure",)
    assert names["OrderDate"]["data_type"] in ("date", "datetime") or "date" in names["OrderDate"]["data_type"]


def test_dataset_manager_roundtrip(tmp_path, monkeypatch):
    # use isolated manager root
    mgr = DatasetManager()
    content = SAMPLE.read_bytes()
    result = mgr.create_from_upload(content, "sales_sample.csv")
    assert len(result["datasets"]) == 1
    ds = result["datasets"][0]
    assert ds["rows"] == 30
    assert ds["health"]["score"] is not None
    listed = mgr.list_datasets()
    assert any(x["id"] == ds["id"] for x in listed)
    renamed = mgr.rename(ds["id"], "Sales – Test")
    assert renamed["name"] == "Sales – Test"
    prev = mgr.preview_page(ds["id"], page=1, page_size=10)
    assert len(prev["rows"]) == 10
    mgr.delete(ds["id"])
    assert not any(x["id"] == ds["id"] for x in mgr.list_datasets())


def test_suggest_name():
    assert "Sales" in suggest_dataset_name("Sales_Aug.xlsx", "Data") or "Sales_Aug" in suggest_dataset_name(
        "Sales_Aug.xlsx"
    )
