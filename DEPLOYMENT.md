# Deployment Guide

## Option A: Streamlit Community Cloud

1. Push project to GitHub.
2. In Streamlit Cloud, create a new app from repository.
3. Set app entry point to `app/app.py`.
4. Add secrets:
   - `SUPABASE_URL`
   - `SUPABASE_PUBLISHABLE_KEY`
   - `SUPABASE_SECRET_KEY`
   - `GEMINI_API_KEY`
   - `OPENAI_BASE_URL` (optional)
   - `OPENAI_MODEL` (optional)
5. Deploy.

## Option B: Container Deployment

1. Build image with Python 3.12.
2. Install dependencies from `requirements.txt`.
3. Inject env vars via secret manager.
4. Run:

```bash
streamlit run app/app.py --server.port 8501 --server.address 0.0.0.0
```

## Production Hardening Checklist

- Enable HTTPS/TLS at ingress or reverse proxy.
- Restrict service-role key usage to backend-only operations.
- Validate RLS policies in Supabase for all student-facing tables.
- Add audit logs for admin actions (enable/disable/reset role changes).
- Add CI pipeline for linting, tests, and security scans.
- Add API request quotas and monitoring for Gemini usage.
- Add data retention policy and backup schedule.
