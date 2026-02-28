# AI Ticket Triage (Internal Tool Demo)

A small internal-tool style project that triages support tickets using a **deterministic, auditable pipeline** and exposes results through a **FastAPI backend + Next.js dashboard**.

This project is designed to demonstrate:

- Strong Python engineering (outside web-framework-centric apps)
- Deterministic analysis pipelines
- Clear separation between logic and presentation
- Human-review workflows
- Pragmatic AI integration (LLM assist layer ready to be added)

---

# Architecture Overview

## Data Flow

Snowflake (optional dev source)
↓
Export Script
↓
SQLite Snapshot (`data/tickets.db`)
↓
Deterministic Pipeline
↓
FastAPI API
↓
Next.js Dashboard (read-only)

---

# Tech Stack

Backend:

- Python 3
- SQLite
- FastAPI
- Uvicorn
- Pydantic

Frontend:

- Next.js (App Router)
- TypeScript
- Tailwind CSS

Optional:

- Snowflake (development data source)

---

# Project Structure

```
ai-ticket-triage/
│
├── app/
│   ├── api.py                  # FastAPI server
│   ├── main.py                 # Runs deterministic pipeline
│   └── pipeline/
│       └── analyze_tickets.py  # Core triage logic
│
├── scripts/
│   └── export_snowflake_to_sqlite.py
│
├── web/                        # Next.js UI
│
├── data/                       # SQLite snapshot (not committed)
│
├── requirements.txt
└── README.md
```

---

# Prerequisites

- Python 3.11+
- Node.js 18+
- (Optional) Snowflake trial account

---

# Setup Instructions

## 1️⃣ Clone Repo

```bash
git clone <your-repo-url>
cd ai-ticket-triage
```

---

## 2️⃣ Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If requirements.txt does not exist yet:

```bash
pip install snowflake-connector-python pydantic python-dotenv pandas fastapi uvicorn
pip freeze > requirements.txt
```

---

## 3️⃣ Configure Environment Variables

Create a `.env` file:

```bash
cp .env.example .env
```

Add your Snowflake credentials (optional if exporting data).

`.env` is ignored by git.

---

# Data Setup

## Option A: Export from Snowflake (Dev Mode)

```bash
python scripts/export_snowflake_to_sqlite.py
```

This creates:

```
data/tickets.db
```

---

## Option B: Use Existing SQLite Snapshot

If `data/tickets.db` already exists, you can skip Snowflake entirely.

---

# Run the Deterministic Pipeline

This processes tickets and writes to `ticket_analysis`.

```bash
python -m app.main
```

Sanity check:

```bash
python - <<'PY'
import sqlite3
cx = sqlite3.connect("data/tickets.db")
print("tickets:", cx.execute("select count(*) from tickets").fetchone()[0])
print("analysis:", cx.execute("select count(*) from ticket_analysis").fetchone()[0])
PY
```

---

# Run the API (FastAPI)

From project root:

```bash
source .venv/bin/activate
python -m uvicorn app.api:app --reload --port 8000
```

API endpoints:

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/stats
- http://127.0.0.1:8000/tickets
- http://127.0.0.1:8000/docs (Swagger)

---

# Run the Web UI (Next.js)

In a new terminal:

```bash
cd web
npm install
npm run dev
```

Open:

```
http://localhost:3000
```

---

## Web Environment Variable

Create:

```
web/.env.local
```

Add:

```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

Restart `npm run dev` if needed.

---

# Typical Development Workflow

Terminal 1 (Pipeline):

```bash
source .venv/bin/activate
python -m app.main
```

Terminal 2 (API):

```bash
source .venv/bin/activate
python -m uvicorn app.api:app --reload --port 8000
```

Terminal 3 (Web UI):

```bash
cd web
npm run dev
```

---

# Design Philosophy

This project intentionally:

- Uses deterministic logic for core categorization
- Flags uncertain tickets for human review
- Separates analysis from presentation
- Stores results in a portable SQLite snapshot
- Avoids autonomous AI decision-making

The architecture is designed so an LLM can be added as an **assistive interpretation layer** without becoming the source of truth.

---

# Next Improvements (Planned)

- Add idempotent UPSERT behavior
- Add `ticket_decisions` audit table
- Add structured LLM assist layer (JSON + schema validation)
- Replace SQLite with Postgres for production
- Add authentication & RBAC

---

# Security Notes

- `.env` is not committed
- `data/*.db` is ignored
- Demo data is synthetic

---

# License

Add a license if publishing publicly.
