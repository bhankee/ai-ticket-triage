from __future__ import annotations
import json
import re
import sqlite3
import traceback
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent  # app/
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = (DATA_DIR / "tickets.db").resolve()

def db_conn() -> sqlite3.Connection:
    cx = sqlite3.connect(str(DB_PATH))
    cx.row_factory = sqlite3.Row
    return cx

app = FastAPI(title="AI Ticket Triage API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}

@app.get("/stats")
def stats():
    with db_conn() as cx:
        total = cx.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()["n"]

   
        review = cx.execute(
            """
            SELECT COUNT(*) AS n
            FROM (
              SELECT ticket_id, MAX(rowid) AS rid
              FROM ticket_analysis
              GROUP BY ticket_id
            ) latest
            JOIN ticket_analysis ta ON ta.rowid = latest.rid
            WHERE ta.needs_human_review = 1
            """
        ).fetchone()["n"]

        cats = cx.execute(
            """
            SELECT ta.category, COUNT(*) AS n
            FROM (
              SELECT ticket_id, MAX(rowid) AS rid
              FROM ticket_analysis
              GROUP BY ticket_id
            ) latest
            JOIN ticket_analysis ta ON ta.rowid = latest.rid
            GROUP BY ta.category
            ORDER BY n DESC, ta.category
            """
        ).fetchall()

    return {
        "total": total,
        "needs_review": review,
        "categories": [lower_keys(r) for r in cats],
    }


@app.get("/tickets")
def list_tickets(needs_review: Optional[int] = None):
    where = ""
    params = []
    if needs_review in (0, 1):
        # apply filter to analysis side
        where = "WHERE ta.needs_human_review = ?"
        params.append(needs_review)

   
    sql = f"""
    SELECT
      t.ticket_id, t.created_at, t.source, t.customer, t.priority,
      t.text AS raw_text,
      ta.category, ta.severity, ta.needs_human_review,
      ta.summary, ta.suggested_next_steps, ta.confidence, ta.redacted_text
    FROM tickets t
    LEFT JOIN ticket_analysis ta ON ta.ticket_id = t.ticket_id
    {where}
    ORDER BY
      COALESCE(ta.needs_human_review, 0) DESC,
      t.priority DESC,
      t.created_at DESC
    """

    with db_conn() as cx:
        rows = cx.execute(sql, params).fetchall()

    items = [lower_keys(r) for r in rows]

    # Fill redacted_text if missing using raw_text
    for it in items:
        raw_text = it.get("raw_text") or ""
        if not it.get("redacted_text"):
            it["redacted_text"] = redact_text(raw_text)

        # remove raw text from API response (avoid leaking secrets to UI)
        it.pop("raw_text", None)

    return {"items": items}


@app.get("/debug/db")
def debug_db():
    try:
        resolved = Path(DB_PATH).expanduser().resolve()
        exists = resolved.exists()

        out: Dict[str, Any] = {
            "db_path_resolved": str(resolved),
            "exists": exists,
        }

        if not exists:
            return out

        with sqlite3.connect(str(resolved)) as cx:
            out["database_list"] = cx.execute("PRAGMA database_list;").fetchall()
            tables = cx.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
            ).fetchall()
            out["tables"] = [t[0] for t in tables]

            if "tickets" in out["tables"]:
                out["tickets_count"] = cx.execute("SELECT COUNT(*) FROM tickets;").fetchone()[0]
            if "ticket_analysis" in out["tables"]:
                out["ticket_analysis_count"] = cx.execute("SELECT COUNT(*) FROM ticket_analysis;").fetchone()[0]

        return out
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}


@app.get("/debug/tickets_sample")
def debug_tickets_sample():
    with db_conn() as cx:
        rows = cx.execute(
            """
            SELECT
              t.ticket_id,
              t.text AS raw_text,
              ta.summary,
              ta.suggested_next_steps,
              ta.redacted_text
            FROM tickets t
            LEFT JOIN ticket_analysis ta ON ta.ticket_id = t.ticket_id
            ORDER BY t.ticket_id ASC
            LIMIT 5;
            """
        ).fetchall()

    items = [lower_keys(r) for r in rows]
    for it in items:
        if not it.get("redacted_text"):
            it["redacted_text"] = redact_text(it.get("raw_text") or "")
        it.pop("raw_text", None)

    return {"items": items}


# ----------------------------
# Redaction (v1)
# ----------------------------
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}\b")
API_KEY_RE = re.compile(r"\b(sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z\-_]{20,})\b")
JWT_RE = re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b")
CC_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


def redact_text(text: str) -> str:
    """
    Simple regex redaction. Good enough for v1.
    """
    t = text or ""
    t = EMAIL_RE.sub("[EMAIL]", t)
    t = PHONE_RE.sub("[PHONE]", t)
    t = API_KEY_RE.sub("[SECRET]", t)
    t = JWT_RE.sub("[TOKEN]", t)
    # very rough CC detector; can false-positive on long IDs
    t = CC_RE.sub("[POSSIBLE_CARD]", t)
    return t


def lower_keys(row: sqlite3.Row) -> Dict[str, Any]:
    """
    sqlite Row -> dict with lowercase keys, parse JSON fields, normalize types.
    """
    d: Dict[str, Any] = {k.lower(): row[k] for k in row.keys()}

    # Parse suggested_next_steps if stored as JSON string
    raw_steps = d.get("suggested_next_steps")
    if raw_steps:
        if isinstance(raw_steps, str):
            try:
                parsed = json.loads(raw_steps)
                d["suggested_next_steps"] = parsed if isinstance(parsed, list) else []
            except Exception:
                d["suggested_next_steps"] = []
        elif isinstance(raw_steps, list):
            d["suggested_next_steps"] = raw_steps
        else:
            d["suggested_next_steps"] = []
    else:
        d["suggested_next_steps"] = []

    # Normalize needs_human_review
    if d.get("needs_human_review") is not None:
        try:
            d["needs_human_review"] = int(d["needs_human_review"])
        except Exception:
            pass

    # Normalize confidence
    if d.get("confidence") is not None:
        try:
            d["confidence"] = float(d["confidence"])
        except Exception:
            pass

    return d


