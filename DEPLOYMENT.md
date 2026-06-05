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

### Share the app with students

Give students and teachers this URL (embed mode hides extra Streamlit chrome):

```text
https://<your-app>.streamlit.app/?embed=true
```

The in-app **Admin** navigation item is already restricted to SAT users with the `admin` role.

**About "Manage app" on Streamlit Cloud:** That button is added by the Streamlit hosting platform. It appears only when you are logged into [share.streamlit.io](https://share.streamlit.io) **and** you have write access to the app's GitHub repository. Students and teachers do not see it. It cannot be tied to your SAT app admin login. To preview the student experience, open the app in a private/incognito window or log out of Streamlit Cloud while testing.

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
