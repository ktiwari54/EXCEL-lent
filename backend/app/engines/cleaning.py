from __future__ import annotations

from typing import Any

import pandas as pd

from app.models.schemas import CleanAction


def detect_issues(df: pd.DataFrame) -> list[str]:
    issues: list[str] = []
    n = len(df)
    if n == 0:
        return ["Dataset is empty."]

    dups = int(df.duplicated().sum())
    if dups:
        issues.append(f"{dups} duplicate row(s) detected ({100 * dups / n:.1f}%).")

    for col in df.columns:
        nulls = int(df[col].isna().sum())
        if nulls:
            issues.append(f"Column '{col}': {nulls} missing value(s) ({100 * nulls / n:.1f}%).")

        if df[col].dtype == object:
            s = df[col].dropna().astype(str)
            if len(s) and (s != s.str.strip()).any():
                issues.append(f"Column '{col}': extra leading/trailing spaces found.")
            # numbers stored as text
            coerced = pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce")
            if coerced.notna().mean() > 0.8 and not pd.api.types.is_numeric_dtype(df[col]):
                issues.append(f"Column '{col}': numbers may be stored as text.")

    return issues


def clean_dataframe(
    df: pd.DataFrame,
    actions: list[CleanAction],
    fill_value: str | None = None,
    case_mode: str = "title",
) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    log: list[str] = []
    do_all = CleanAction.all in actions

    def want(a: CleanAction) -> bool:
        return do_all or a in actions

    if want(CleanAction.trim_spaces):
        for col in out.select_dtypes(include=["object", "string"]).columns:
            out[col] = out[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        log.append("Trimmed extra spaces in text columns.")

    if want(CleanAction.normalize_case):
        for col in out.select_dtypes(include=["object", "string"]).columns:
            if case_mode == "lower":
                out[col] = out[col].map(lambda x: x.lower() if isinstance(x, str) else x)
            elif case_mode == "upper":
                out[col] = out[col].map(lambda x: x.upper() if isinstance(x, str) else x)
            else:
                out[col] = out[col].map(lambda x: x.title() if isinstance(x, str) else x)
        log.append(f"Normalized text case ({case_mode}).")

    if want(CleanAction.numbers_as_text):
        for col in out.columns:
            if out[col].dtype == object:
                coerced = pd.to_numeric(
                    out[col].astype(str).str.replace(",", "", regex=False).str.strip(),
                    errors="coerce",
                )
                if coerced.notna().mean() > 0.8:
                    out[col] = coerced
                    log.append(f"Converted '{col}' from text to numbers.")

    if want(CleanAction.fix_dates):
        for col in out.columns:
            if "date" in str(col).lower() or out[col].dtype == object:
                parsed = pd.to_datetime(out[col], errors="coerce")
                if parsed.notna().mean() > 0.6 and not pd.api.types.is_datetime64_any_dtype(out[col]):
                    out[col] = parsed
                    log.append(f"Parsed dates in '{col}'.")

    if want(CleanAction.fill_blanks):
        fill = fill_value if fill_value is not None else ""
        before = int(out.isna().sum().sum())
        for col in out.columns:
            if pd.api.types.is_numeric_dtype(out[col]):
                out[col] = out[col].fillna(0 if fill_value is None else pd.to_numeric(fill_value, errors="coerce"))
            else:
                out[col] = out[col].fillna(fill if fill != "" else "Unknown")
        after = int(out.isna().sum().sum())
        log.append(f"Filled blanks (missing cells {before} → {after}).")

    if want(CleanAction.drop_blanks):
        before = len(out)
        out = out.dropna(how="any")
        log.append(f"Dropped rows with any blank ({before - len(out)} rows).")

    if want(CleanAction.drop_duplicates):
        before = len(out)
        out = out.drop_duplicates()
        log.append(f"Removed {before - len(out)} duplicate row(s).")

    out = out.reset_index(drop=True)
    return out, log
