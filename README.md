# Ledgerly

Invoice ingestion assistant for French accounting-firm bookkeepers. Drop supplier PDFs, auto-extract and classify, download Sage-ready Excel.

## Quick start

```bash
cp .env.example .env
# Fill in your keys
pip install .
uvicorn app.main:app --reload
```

## Stack

FastAPI + HTMX + Tailwind CSS, Supabase (Postgres + Storage), Groq LLM, Render hosting. Zero paid services.
