# API and Question Source Reference

This document lists every API, endpoint, and data source used to load questions in the SAT Adaptive Learning Platform.

---

## Active sources (used by the app)

### 1. OpenSAT community JSON — primary bulk download

| Field | Value |
|--------|--------|
| **Endpoint** | `GET https://api.jsonsilo.com/public/942c3c3b-3a0c-4be3-81c2-12029def19f5` |
| **Method** | HTTP GET (`urllib`) |
| **Timeout** | 120 seconds |
| **User-Agent** | `SAT-Adaptive-Learning-Platform/1.0 (+educational; opensat attribution)` |
| **Response** | JSON with `math` and `english` arrays |
| **DB source label** | `opensat_community` |
| **Code** | `app/database/official_loaders/opensat_loader.py` |
| **Triggered by** | Admin **Download latest question bank**, `python scripts/reload_exam_questions.py` |

Upstream project: [github.com/Anas099X/OpenSAT](https://github.com/Anas099X/OpenSAT)

---

### 2. College Board Bluebook practice — bundled local files (not a live API)

| Field | Value |
|--------|--------|
| **Source** | Local JS files in the repository |
| **Files** | `bluebook_raw_10_module1.js`, `bluebook_raw_10_module2.js`, `bluebook_raw_11_module1.js`, `bluebook_raw_11_module2.js` |
| **Location** | `app/database/official_loaders/` |
| **DB source label** | `bluebook_official_practice` |
| **Code** | `app/database/official_loaders/bluebook_loader.py` |
| **Triggered by** | Same bulk download flow as OpenSAT |

No HTTP endpoint — questions are parsed from files shipped with the project.

---

### 3. Supabase `questions` table — storage and runtime reads

| Field | Value |
|--------|--------|
| **Base URL** | `SUPABASE_URL` from `.env` (project-specific) |
| **REST pattern** | `{SUPABASE_URL}/rest/v1/questions` |
| **Auth** | `SUPABASE_PUBLISHABLE_KEY` (reads), `SUPABASE_SECRET_KEY` (admin writes/deletes) |
| **Operations** | `SELECT`, `INSERT`, `DELETE` via Supabase Python client |
| **Code** | `app/database/supabase_client.py`, `app/services/question_service.py`, `app/services/question_import_service.py` |
| **Used for** | Practice, mock exams, admin import approval, bulk seed writes |

Typical queries:

- **Read:** filter by `exam_type`, `subject`, `difficulty`, `topic`, `source`
- **Write:** bulk insert (batches of 25), admin CSV import after approval
- **Delete:** wipe all questions before reload (optional Admin checkbox)

Environment variables (see `.env.example`):

```
SUPABASE_URL=
SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
```

---

### 4. Admin CSV/Excel upload — manual import (not an external question API)

| Field | Value |
|--------|--------|
| **Source** | File uploaded in Admin UI |
| **Template** | `app/database/seed_questions.csv` |
| **DB source label** | Unique per batch, e.g. `import:licensed_question_bank:20260606T153045Z:a1b2c3` |
| **Code** | `app/services/question_import_service.py`, `app/pages/admin.py` |
| **Flow** | Upload → Review (optional Gemini normalization) → Approve → Supabase insert |

Practice and mock exams prefer the latest `import:...` batch when one exists.

---

### 5. Local seed template (dev/bootstrap only)

| Field | Value |
|--------|--------|
| **File** | `app/database/seed_questions.csv` (sample questions) |
| **Code** | `app/database/seed.py`, `app/database/seed_data.py` |
| **Purpose** | Local dev seeding and import templates — not a production question API |

---

## Referenced but not used as live question APIs

These appear in docs/code for policy and research. The app does **not** call them to download questions.

| Source | URL | Status in project |
|--------|-----|-------------------|
| **College Board Educator Question Bank** | https://satsuiteeducatorquestionbank.collegeboard.org/ | **No public API** — PDF export only; use Admin CSV import |
| **Reddit r/SAT** | https://www.reddit.com/r/SAT/ | **Rejected** — memory reconstructions, no official keys |
| **Tutor recap blogs** | https://thetestadvantage.com/blog/ | **Rejected** — transcribed forum content |
| **Discord / Telegram “leaks”** | N/A | **Rejected** — unverifiable / policy issues |

Forum verification (`app/database/official_loaders/forum_verification.py`) evaluates hardcoded sample candidates through validation gates. It does not scrape Reddit or blogs at runtime. Current result: **0 forum questions imported**.

See also: `docs/QUESTION_SOURCES.md`

---

## Related API (not a question bank)

### Gemini — CSV normalization only

| Field | Value |
|--------|--------|
| **Base URL** | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| **Model** | `GEMINI_MODEL` (default: `gemini-2.5-pro`) |
| **Purpose** | Map and repair uploaded spreadsheet columns during **Review upload** |
| **Code** | `app/services/gemini_service.py`, `app/services/question_import_llm_service.py` |
| **Note** | Does **not** download SAT questions into the database |

Environment variables:

```
GEMINI_API_KEY=
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
GEMINI_MODEL=gemini-2.5-pro
```

---

## End-to-end flow

```
OpenSAT JSON API  ──┐
Bluebook local JS   ├──► Supabase questions table ──► Practice / Mock Exam
Admin CSV/Excel     ──┘      (optional Gemini on upload)
```

| How questions enter the DB | API / endpoint |
|----------------------------|----------------|
| **Download latest question bank** | OpenSAT GET + local Bluebook files → Supabase insert |
| **Review upload → Approve** | Uploaded file (+ Gemini if needed) → Supabase insert |
| **Practice / mock exam** | Supabase `questions` SELECT (prefers latest `import:...` batch if present) |

---

## Quick reference — external question HTTP endpoint

Only one live HTTP endpoint fetches external question content:

```
GET https://api.jsonsilo.com/public/942c3c3b-3a0c-4be3-81c2-12029def19f5
```

All other question data comes from Supabase (your project URL), local bundled files, or manual admin upload.

---

## Reload command (CLI)

```bash
python scripts/reload_exam_questions.py
```

Deletes all existing questions and reloads from OpenSAT (+ Bluebook + forum verification pipeline).
