from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


SUPPORTED_EXT = {".xlsx", ".xls", ".xlsm", ".csv", ".txt"}


class ParseError(Exception):
    def __init__(self, user_message: str, detail: str | None = None):
        self.user_message = user_message
        self.detail = detail
        super().__init__(user_message)


def validate_filename(filename: str) -> str:
    name = (filename or "").strip()
    if not name:
        raise ParseError("We couldn't read this file.", "Missing filename.")
    lower = name.lower()
    if not any(lower.endswith(ext) for ext in SUPPORTED_EXT):
        raise ParseError(
            "This file type isn't supported.",
            "Please upload an Excel (.xlsx, .xls) or CSV (.csv) file.",
        )
    return name


def parse_upload(content: bytes, filename: str) -> dict[str, Any]:
    """
    Returns workbook structure:
    {
      filename, kind: csv|excel,
      sheets: [{name, rows, columns, headers, empty, df}],
      errors: []
    }
    Does not mutate content. Each df is a copy of raw data.
    """
    filename = validate_filename(filename)
    if not content or len(content) == 0:
        raise ParseError(
            "This file appears to be empty.",
            "Please check the file and try again.",
        )

    lower = filename.lower()
    try:
        if lower.endswith((".csv", ".txt")):
            return _parse_csv(content, filename)
        return _parse_excel(content, filename)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(
            "We couldn't read this file.",
            "The workbook appears to be corrupted or uses an unsupported format. "
            "Please try opening it in Excel and saving it again as .xlsx.",
        ) from e


def _parse_csv(content: bytes, filename: str) -> dict[str, Any]:
    try:
        df = pd.read_csv(BytesIO(content))
    except UnicodeDecodeError:
        df = pd.read_csv(BytesIO(content), encoding="latin-1")
    except Exception as e:
        raise ParseError(
            "We couldn't read this CSV file.",
            "Please check the file encoding and that it uses a standard comma separator.",
        ) from e

    df = _normalize_df(df, filename)
    return {
        "filename": filename,
        "kind": "csv",
        "sheets": [_sheet_meta("Data", df)],
    }


def _parse_excel(content: bytes, filename: str) -> dict[str, Any]:
    lower = filename.lower()
    # Legacy .xls needs xlrd; prefer clear guidance
    if lower.endswith(".xls") and not lower.endswith(".xlsx") and not lower.endswith(".xlsm"):
        try:
            xl = pd.ExcelFile(BytesIO(content), engine="xlrd")
        except Exception as e:
            raise ParseError(
                "We couldn't open this older .xls file.",
                "Please open it in Excel and save it as .xlsx, then upload again.",
            ) from e
    else:
        try:
            xl = pd.ExcelFile(BytesIO(content), engine="openpyxl")
        except Exception as e:
            # fallback without engine pin
            try:
                xl = pd.ExcelFile(BytesIO(content))
            except Exception as e2:
                raise ParseError(
                    "We couldn't open this Excel workbook.",
                    "The file may be corrupted, password-protected, or not a real .xlsx file. "
                    "Open it in Excel and use File → Save As → Excel Workbook (.xlsx).",
                ) from e2

    sheets = []
    for name in xl.sheet_names:
        try:
            df = pd.read_excel(xl, sheet_name=name)
            df = _normalize_df(df, name)
            sheets.append(_sheet_meta(str(name), df))
        except Exception:
            sheets.append(
                {
                    "name": str(name),
                    "rows": 0,
                    "columns": 0,
                    "headers": [],
                    "empty": True,
                    "error": "Could not read this sheet.",
                    "df": pd.DataFrame(),
                }
            )

    if not sheets:
        raise ParseError("This workbook has no readable sheets.")

    return {"filename": filename, "kind": "excel", "sheets": sheets}


def _normalize_df(df: pd.DataFrame, context: str) -> pd.DataFrame:
    if df is None or df.empty:
        # allow empty detection later
        return pd.DataFrame() if df is None else df.copy()

    out = df.copy()
    # stringify headers, fix duplicates
    headers = []
    seen: dict[str, int] = {}
    for i, h in enumerate(out.columns):
        base = str(h).strip() if str(h).strip() and not str(h).startswith("Unnamed") else f"Column_{i+1}"
        if base in seen:
            seen[base] += 1
            base = f"{base}_{seen[base]}"
        else:
            seen[base] = 1
        headers.append(base)
    out.columns = headers
    return out


def _sheet_meta(name: str, df: pd.DataFrame) -> dict[str, Any]:
    empty = df is None or len(df) == 0 or len(df.columns) == 0
    return {
        "name": name,
        "rows": int(len(df)) if df is not None else 0,
        "columns": int(len(df.columns)) if df is not None else 0,
        "headers": list(df.columns) if df is not None else [],
        "empty": empty,
        "df": df if df is not None else pd.DataFrame(),
    }


def suggest_dataset_name(filename: str, sheet_name: str | None = None) -> str:
    base = filename.rsplit(".", 1)[0]
    base = base.replace("_", " ").replace("-", " ").strip()
    if sheet_name and sheet_name not in ("Data", base):
        return f"{base} – {sheet_name}"
    return base
