from __future__ import annotations

import io

import pandas as pd

from app.database.supabase_client import get_supabase_client


class QuestionImportService:
    def __init__(self):
        self.client = get_supabase_client()

    def import_dataframe(self, df: pd.DataFrame, source: str):
        required = {
            "exam_type",
            "subject",
            "topic",
            "difficulty",
            "question_text",
            "options",
            "answer",
            "explanation",
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")

        rows = df.fillna("").to_dict(orient="records")
        for row in rows:
            if isinstance(row.get("options"), str):
                row["options"] = [x.strip() for x in row["options"].split("||")]
            row["source"] = source
        return self.client.table("questions").insert(rows).execute()

    def import_csv_bytes(self, file_bytes: bytes, source: str):
        df = pd.read_csv(io.BytesIO(file_bytes))
        return self.import_dataframe(df, source)

    def import_excel_bytes(self, file_bytes: bytes, source: str):
        df = pd.read_excel(io.BytesIO(file_bytes))
        return self.import_dataframe(df, source)
