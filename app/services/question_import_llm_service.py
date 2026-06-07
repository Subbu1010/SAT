from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

from app.services.gemini_service import GeminiService
from app.services.import_progress import ImportProgressReporter, NoOpImportProgress
from app.services.question_import_service import (
    REQUIRED_COLUMNS,
    _combine_split_option_columns,
    _missing_columns,
    _normalize_columns,
    _parse_options,
)

CANONICAL_FIELDS = sorted(REQUIRED_COLUMNS | {"passage", "strategy_tip", "estimated_time", "skill_category"})
_MAX_SAMPLE_ROWS = 5
_MAX_REPAIR_ROWS = 12

_COLUMN_MAPPING_SYSTEM = (
    "You map spreadsheet columns to a fixed SAT question import schema. "
    "Return only valid JSON with no markdown."
)

_COLUMN_MAPPING_USER = """Map the uploaded spreadsheet to these canonical fields:
{fields}

Uploaded column headers:
{headers}

Sample data rows (JSON list of objects keyed by uploaded headers):
{samples}

Return JSON exactly in this shape:
{{
  "header_row_index": 0,
  "column_mapping": {{
    "exam_type": "<uploaded column name or null>",
    "subject": "<uploaded column name or null>",
    "topic": "<uploaded column name or null>",
    "difficulty": "<uploaded column name or null>",
    "question_text": "<uploaded column name or null>",
    "options": "<uploaded column name or null>",
    "answer": "<uploaded column name or null>",
    "explanation": "<uploaded column name or null>",
    "passage": "<uploaded column name or null>",
    "strategy_tip": "<uploaded column name or null>",
    "estimated_time": "<uploaded column name or null>",
    "skill_category": "<uploaded column name or null>"
  }},
  "option_columns": ["option_a", "option_b"],
  "notes": "short explanation of mapping decisions"
}}

Rules:
- Use exact uploaded header strings in column_mapping values.
- exam_type must be SAT, PSAT, or PSAT 8/9 when inferable.
- subject must be Math, Reading, or Writing when inferable.
- difficulty must be Easy, Medium, or Hard when inferable.
- If choices are split across columns, list those uploaded headers in option_columns and set options to null.
- If a canonical field cannot be mapped, use null.
"""

_ROW_REPAIR_SYSTEM = (
    "You complete missing SAT question import fields using context from each row. "
    "Return only valid JSON with no markdown."
)

_ROW_REPAIR_USER = """Fill missing required fields for these question rows.
Canonical fields: {fields}

Rows needing repair (JSON list):
{rows}

Return JSON:
{{
  "rows": [
    {{
      "row_index": 1,
      "exam_type": "SAT",
      "subject": "Math",
      "topic": "Algebra",
      "difficulty": "Medium",
      "question_text": "...",
      "options": "A||B||C||D",
      "answer": "B",
      "explanation": "...",
      "passage": "",
      "strategy_tip": "",
      "estimated_time": 60,
      "skill_category": ""
    }}
  ],
  "notes": "short summary"
}}

Rules:
- Keep existing non-empty values unchanged.
- Infer reasonable values only when missing.
- options may be a list or a string separated by ||.
- Never invent unrelated content; use row context.
"""


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response was not a JSON object.")
    return parsed


def _json_preview(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _sample_rows(df: pd.DataFrame, limit: int = _MAX_SAMPLE_ROWS) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    for row in df.fillna("").to_dict(orient="records"):
        if any(_json_preview(value) for value in row.values()):
            samples.append({str(key): _json_preview(value) for key, value in row.items()})
        if len(samples) >= limit:
            break
    return samples


def _row_is_complete(row: dict[str, Any]) -> bool:
    for field in REQUIRED_COLUMNS:
        if field == "options":
            if not _parse_options(row.get("options")):
                return False
            continue
        if not _json_preview(row.get(field)):
            return False
    return True


def _apply_column_mapping(df: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for source_row in df.fillna("").to_dict(orient="records"):
        canonical: dict[str, Any] = {}
        for field in CANONICAL_FIELDS:
            source_column = mapping.get(field)
            if source_column and source_column in source_row:
                canonical[field] = source_row[source_column]
            else:
                canonical[field] = ""
        rows.append(canonical)
    return pd.DataFrame(rows)


def _apply_option_columns(df: pd.DataFrame, option_columns: list[str]) -> pd.DataFrame:
    if "options" in df.columns and df["options"].astype(str).str.strip().any():
        return df
    usable = [column for column in option_columns if column in df.columns]
    if len(usable) < 2:
        return df
    updated = df.copy()
    updated["options"] = updated.apply(
        lambda row: "||".join(_json_preview(row[column]) for column in usable if _json_preview(row[column])),
        axis=1,
    )
    return updated


def _infer_column_mapping(
    df: pd.DataFrame,
    gemini: GeminiService,
    progress: ImportProgressReporter,
) -> dict[str, Any]:
    progress.detail(
        f"Sending {len(df.columns)} column header(s) and up to {_MAX_SAMPLE_ROWS} sample row(s) to Gemini."
    )
    prompt = _COLUMN_MAPPING_USER.format(
        fields=", ".join(CANONICAL_FIELDS),
        headers=json.dumps([str(column) for column in df.columns], ensure_ascii=True),
        samples=json.dumps(_sample_rows(df), ensure_ascii=True),
    )
    progress.detail("Waiting for Gemini column-mapping response...")
    response = gemini.tutor_reply(prompt, context=_COLUMN_MAPPING_SYSTEM)
    progress.detail("Received column mapping from Gemini.")
    payload = _extract_json_object(response)
    mapping = payload.get("column_mapping") or {}
    if not isinstance(mapping, dict):
        raise ValueError("LLM column mapping response was invalid.")
    normalized_mapping = {
        str(key): (None if value in (None, "", "null") else str(value))
        for key, value in mapping.items()
    }
    option_columns = payload.get("option_columns") or []
    if not isinstance(option_columns, list):
        option_columns = []
    return {
        "header_row_index": int(payload.get("header_row_index") or 0),
        "column_mapping": normalized_mapping,
        "option_columns": [str(column) for column in option_columns],
        "notes": str(payload.get("notes") or "").strip(),
    }


def _repair_rows(
    df: pd.DataFrame,
    row_indices: list[int],
    gemini: GeminiService,
    progress: ImportProgressReporter,
) -> tuple[pd.DataFrame, str]:
    if not row_indices:
        return df, ""

    repaired_df = df.copy()
    notes: list[str] = []
    total_chunks = (len(row_indices) + _MAX_REPAIR_ROWS - 1) // _MAX_REPAIR_ROWS
    for chunk_number, start in enumerate(range(0, len(row_indices), _MAX_REPAIR_ROWS), start=1):
        chunk = row_indices[start : start + _MAX_REPAIR_ROWS]
        row_numbers = ", ".join(str(index + 1) for index in chunk[:5])
        if len(chunk) > 5:
            row_numbers += ", ..."
        progress.detail(
            f"LLM repair batch {chunk_number}/{total_chunks} for row(s): {row_numbers}"
        )
        payload_rows = []
        for row_index in chunk:
            row_number = row_index + 1
            source_row = repaired_df.iloc[row_index].fillna("").to_dict()
            payload_rows.append({"row_index": row_number, **source_row})
        prompt = _ROW_REPAIR_USER.format(
            fields=", ".join(CANONICAL_FIELDS),
            rows=json.dumps(payload_rows, ensure_ascii=True),
        )
        progress.detail("Waiting for Gemini row-repair response...")
        response = gemini.tutor_reply(prompt, context=_ROW_REPAIR_SYSTEM)
        progress.detail(f"Applied repairs from batch {chunk_number}/{total_chunks}.")
        payload = _extract_json_object(response)
        for item in payload.get("rows") or []:
            if not isinstance(item, dict):
                continue
            target_index = int(item.get("row_index", 0)) - 1
            if target_index < 0 or target_index >= len(repaired_df):
                continue
            for field in CANONICAL_FIELDS:
                if field not in item:
                    continue
                current = _json_preview(repaired_df.iloc[target_index].get(field))
                incoming = item.get(field)
                if not current and _json_preview(incoming):
                    repaired_df.at[target_index, field] = incoming
        chunk_notes = str(payload.get("notes") or "").strip()
        if chunk_notes:
            notes.append(chunk_notes)
    return repaired_df, " ".join(notes).strip()


def normalize_upload_with_llm(
    df: pd.DataFrame,
    gemini: GeminiService | None = None,
    *,
    progress: ImportProgressReporter | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Use Gemini to map mismatched headers and fill missing values when rule-based parsing fails."""
    reporter = progress or NoOpImportProgress()
    if gemini is None:
        reporter.step("Connecting to Gemini")
        gemini = GeminiService()
        reporter.detail(f"Using model: {gemini.model}")
    else:
        reporter.step("Using Gemini for column mapping")

    meta: dict[str, Any] = {"llm_assisted": True, "notes": [], "column_mapping": {}}
    working = df.copy()

    mapping_result = _infer_column_mapping(working, gemini, reporter)
    meta["column_mapping"] = mapping_result["column_mapping"]
    if mapping_result["notes"]:
        meta["notes"].append(mapping_result["notes"])
    mapped_fields = [field for field, column in mapping_result["column_mapping"].items() if column]
    reporter.detail(
        "Mapped fields: " + (", ".join(mapped_fields) if mapped_fields else "none")
    )

    reporter.step("Applying column mapping to uploaded rows")
    working = _apply_column_mapping(working, mapping_result["column_mapping"])
    reporter.detail(f"Transformed {len(working)} row(s) into the import schema.")

    reporter.step("Formatting answer options")
    working = _apply_option_columns(working, mapping_result["option_columns"])
    working = _normalize_columns(working)
    working = _combine_split_option_columns(working)
    reporter.detail("Normalized headers and combined split option columns.")

    reporter.step("Checking rows for missing required values")
    incomplete_indices = [
        index
        for index, row in enumerate(working.fillna("").to_dict(orient="records"))
        if not _row_is_complete(row)
    ]
    if incomplete_indices:
        reporter.detail(
            f"Found {len(incomplete_indices)} row(s) needing Gemini value repair."
        )
        reporter.step("Repairing incomplete rows with Gemini")
        working, repair_notes = _repair_rows(working, incomplete_indices, gemini, reporter)
        if repair_notes:
            meta["notes"].append(repair_notes)
        working = _combine_split_option_columns(_normalize_columns(working))
        reporter.detail("Re-validated rows after repair.")
    else:
        reporter.detail("All rows already contain the required fields.")

    if _missing_columns(working):
        missing = sorted(_missing_columns(working))
        raise ValueError(
            "LLM could not map required columns: "
            f"{missing}. Found columns: {sorted(str(column) for column in working.columns)}."
        )

    incomplete_after = [
        index + 1
        for index, row in enumerate(working.fillna("").to_dict(orient="records"))
        if not _row_is_complete(row)
    ]
    if incomplete_after:
        preview = ", ".join(str(row_number) for row_number in incomplete_after[:10])
        raise ValueError(
            "LLM-assisted import still has incomplete rows after repair: "
            f"{preview}. Fill missing values and upload again."
        )

    reporter.step("Validating LLM-normalized import data")
    reporter.detail("All required columns and row values are present.")

    meta["notes"] = [note for note in meta["notes"] if note]
    return working, meta
