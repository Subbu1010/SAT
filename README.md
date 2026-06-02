# PSAT/SAT Adaptive Learning Platform (Streamlit + Supabase)

A production-oriented, multi-user PSAT/SAT preparation platform with adaptive practice, mock exams, analytics, admin controls, and AI tutoring with RAG.

## Highlights

- Multi-role access: Admin, Teacher, Student
- Supabase-backed auth + data storage
- Adaptive difficulty practice engine
- Timed mock exam flow
- AI tutor using Gemini through OpenAI-compatible client
- pgvector semantic retrieval for RAG
- Premium Streamlit UI with custom CSS + Plotly
- Centralized services for future LangChain/LlamaIndex/agent integrations

## Project Structure

```text
app/
├── app.py
├── pages/
├── components/
├── services/
├── database/
├── styles/
├── utils/
├── assets/
├── prompts/
├── models/
├── authentication/
├── analytics/
├── rag/
├── vector/
└── tests/
```

## Quick Start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure secrets:

- Streamlit secrets (`.streamlit/secrets.toml`) OR
- Environment variables (`.env`)

Required (Supabase **Project Settings → API**):

- `SUPABASE_URL` — Project URL
- `SUPABASE_PUBLISHABLE_KEY` — Publishable key (client-safe)
- `SUPABASE_SECRET_KEY` — Secret key (server-side only; used for seeding/admin)

Aliases also supported: `SUPABASE_KEY` (publishable), `SUPABASE_SERVICE_ROLE_KEY` (secret).

- `GEMINI_API_KEY`
- `GEMINI_MODEL` (recommended: `gemini-2.5-pro`)

**One-time database setup:** paste `app/database/schema.sql` into Supabase **SQL Editor** and run it.  
You do **not** need a Postgres `SUPABASE_DB_URL` if you only have API keys.

Optional:

- `SUPABASE_DB_URL` — only for automatic `schema.sql` execution via direct Postgres
- `GEMINI_BASE_URL` (defaults to Google OpenAI-compatible Gemini endpoint)

### Auto-seed on startup

When the server starts, it automatically:

1. Verifies API connection (publishable + secret keys)
2. Seeds test users (secret key)
3. Seeds 12 sample SAT/PSAT questions (idempotent)

Test login password: `TestPassword123!`

| Email | Role |
|-------|------|
| admin@test.local | admin |
| teacher@test.local | teacher |
| student@test.local | student |
| student2@test.local | student |

Manual seed (optional):

```powershell
.\.venv\Scripts\python scripts/seed_test_users.py
```

3. Run DB schema in Supabase SQL editor:

- `app/database/schema.sql`

4. Run app:

```bash
.\.venv\Scripts\python -m streamlit run streamlit_app.py
```

Or from PowerShell:

```powershell
.\run.ps1
```

## Notes on Question Banks and Licensing

The system supports importing CSV/Excel question banks. Only import content you have legal rights to store and redistribute. The app includes source tracking in the questions table for governance.

## Core Modules

- `app/authentication/auth_service.py` – auth, sessions, role checks
- `app/services/question_service.py` – question retrieval and attempt writes
- `app/services/adaptive_engine.py` – adaptive difficulty progression
- `app/services/gemini_service.py` – tutoring/explanations (retry, cache, rate-limit)
- `app/services/rag_service.py` – retrieval pipeline
- `app/database/schema.sql` – full schema + pgvector RPC + RLS policies

## Deployment

See `DEPLOYMENT.md`.
