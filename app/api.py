from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from typing import Optional

DB = "data/tickets.db"

app = FastAPI(title="AI Ticket Triage API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db_conn() -> sqlite3.Connection:
    cx = sqlite3.connect(DB)
    cx.row_factory = sqlite3.Row
    return cx

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/stats")
def stats():
    with db_conn() as cx:
        total = cx.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"]
        review = cx.execute(
            "SELECT COUNT(*) AS n FROM ticket_analysis WHERE needs_human_review = 1"
        ).fetchone()["n"]
        cats = cx.execute(
            """
            SELECT category, COUNT(*) AS n
            FROM ticket_analysis
            GROUP BY category
            ORDER BY n DESC, category
            """
        ).fetchall()
    return {"total": total, "needs_review": review, "categories": [lower_keys(r) for r in cats]}

@app.get("/tickets")
def list_tickets(needs_review: Optional[int] = None):
    where = ""
    params = []
    if needs_review in (0, 1):
        where = "WHERE ta.needs_human_review = ?"
        params.append(needs_review)

    sql = f"""
    SELECT
      t.ticket_id, t.created_at, t.source, t.customer, t.priority,
      ta.category, ta.needs_human_review, ta.summary, ta.redacted_text
    FROM tickets t
    JOIN ticket_analysis ta ON ta.ticket_id = t.ticket_id
    {where}
    ORDER BY ta.needs_human_review DESC, t.priority DESC, t.created_at DESC
    """

    with db_conn() as cx:
        rows = cx.execute(sql, params).fetchall()
    return {"items": [lower_keys(r) for r in rows]}

def lower_keys(row: sqlite3.Row) -> dict:
    return {k.lower(): row[k] for k in row.keys()}