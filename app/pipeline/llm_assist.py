import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# We keep categories limited (guardrail)
ALLOWED_CATEGORIES = [
    "incident",
    "auth_access",
    "billing",
    "performance",
    "integrations",
    "general_support",
]

PROMPT_VERSION = "llm-assist-v1"


@dataclass(frozen=True)
class TicketForLLM:
    ticket_id: int
    priority: str
    redacted_text: str


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def db_conn(db_path: str) -> sqlite3.Connection:
    cx = sqlite3.connect(db_path)
    cx.row_factory = sqlite3.Row
    return cx


def fetch_review_tickets(db_path: str, limit: int = 50) -> List[TicketForLLM]:
    with db_conn(db_path) as cx:
        rows = cx.execute(
            """
            SELECT
              ta.ticket_id,
              t.priority,
              ta.redacted_text
            FROM ticket_analysis ta
            JOIN tickets t ON t.ticket_id = ta.ticket_id
            WHERE ta.needs_human_review = 1
            ORDER BY t.priority DESC, t.created_at DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()

    out: List[TicketForLLM] = []
    for r in rows:
        d = {k.lower(): r[k] for k in r.keys()}
        out.append(
            TicketForLLM(
                ticket_id=int(d["ticket_id"]),
                priority=str(d["priority"]),
                redacted_text=str(d["redacted_text"]),
            )
        )
    return out

def upsert_suggestion(
    db_path: str,
    *,
    ticket_id: int,
    prompt_version: str,
    model_version: str,
    input_hash: str,
    category: str,
    severity: str,
    summary: str,
    suggested_next_steps_json: str,  
    needs_human_review: int,         # 0/1
    confidence: float,
    redacted_text: str | None = None,
) -> None:
    """
    Upserts a single analysis row per ticket into `ticket_analysis`.

    Assumes `ticket_analysis.ticket_id` is UNIQUE / PRIMARY KEY (one row per ticket).
    If you want history (multiple rows per ticket), remove the UNIQUE constraint and
    insert rows instead of upserting.
    """
    cx = sqlite3.connect(db_path)
    try:
        cx.execute("PRAGMA foreign_keys = ON;")

    
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_analysis (
              ticket_id INTEGER PRIMARY KEY,
              prompt_version TEXT,
              model_version TEXT,
              input_hash TEXT,
              summary TEXT,
              category TEXT,
              severity TEXT,
              suggested_next_steps TEXT,      -- JSON string
              needs_human_review INTEGER,
              confidence REAL,
              redacted_text TEXT,
              created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )

        cx.execute(
            """
            INSERT INTO ticket_analysis (
              ticket_id,
              prompt_version,
              model_version,
              input_hash,
              summary,
              category,
              severity,
              suggested_next_steps,
              needs_human_review,
              confidence,
              redacted_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
              prompt_version        = excluded.prompt_version,
              model_version         = excluded.model_version,
              input_hash            = excluded.input_hash,
              summary               = excluded.summary,
              category              = excluded.category,
              severity              = excluded.severity,
              suggested_next_steps  = excluded.suggested_next_steps,
              needs_human_review    = excluded.needs_human_review,
              confidence            = excluded.confidence,
              redacted_text         = excluded.redacted_text,
              created_at            = datetime('now');
            """,
            (
                ticket_id,
                prompt_version,
                model_version,
                input_hash,
                summary,
                category,
                severity,
                suggested_next_steps_json,
                int(needs_human_review),
                float(confidence),
                redacted_text,
            ),
        )

        cx.commit()
    finally:
        cx.close()




def call_llm(client: OpenAI, model: str, ticket: TicketForLLM) -> Dict[str, Any]:  

    instructions = (
        "You are assisting a support engineer. "
        "Return ONLY the JSON that matches the schema. "
        "Do not include PII; text is already redacted."
    )

    prompt = (
        f"Ticket priority: {ticket.priority}\n"
        f"Ticket text (redacted):\n{ticket.redacted_text}\n\n"
        "Task:\n"
        "- Provide a 1-2 sentence summary\n"
        "- Choose the best category from the allowed enum\n"
        "- Provide 1-5 short bullet rationales\n"
        "- Provide confidence 0..1 (lower if ambiguous)\n"
    )

    # Using Responses API with Structured Outputs. 
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": prompt},
        ],
         text={
        "format": {
            "type": "json_schema",
            "name": "ticket_triage",  
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "category": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "incident"]},
                    "summary": {"type": "string"},
                    "suggested_next_steps": {"type": "array", "items": {"type": "string"}},
                    "needs_human_review": {"type": "boolean"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": [
                    "category",
                    "severity",
                    "summary",
                    "suggested_next_steps",
                    "needs_human_review",
                    "confidence",
                ],
            },
        }
    }
    )


    text_out = resp.output_text
    return json.loads(text_out)


ALLOWED_SEVERITIES = {"low", "medium", "high", "incident"}

def validate_output(data: dict):
    category = str(data["category"]).strip()
    severity = str(data["severity"]).strip()
    summary = str(data["summary"]).strip()
    steps = data["suggested_next_steps"]
    needs_human_review = bool(data["needs_human_review"])
    confidence = float(data["confidence"])

    if not category:
        raise ValueError("empty category")
    if severity not in ALLOWED_SEVERITIES:
        raise ValueError(f"invalid severity: {severity}")
    if not summary:
        raise ValueError("empty summary")
    if not isinstance(steps, list) or len(steps) < 1:
        raise ValueError("suggested_next_steps must be a non-empty list")
    steps = [str(s).strip() for s in steps if str(s).strip()]
    if not steps:
        raise ValueError("suggested_next_steps are empty")

    if not (0.0 <= confidence <= 1.0):
        raise ValueError("confidence out of range")

    return category, severity, summary, steps, needs_human_review, confidence

def run_llm_assist(db_path: str = "data/tickets.db", limit: int = 50) -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in environment")

    client = OpenAI(api_key=api_key)

    tickets = fetch_review_tickets(db_path, limit=limit)
    if not tickets:
        print("No tickets flagged for human review. Nothing to do.")
        return

    wrote = 0
    for t in tickets:
        input_hash = sha256_text(t.redacted_text)

        try:
            out = call_llm(client, model, t)
            print("LLM OUT:", out)
            category, severity, summary, steps, needs_human_review, confidence = validate_output(out)

            upsert_suggestion(
                db_path,
                ticket_id=t.ticket_id,
                prompt_version=PROMPT_VERSION,
                model_version=model,
                input_hash=input_hash,
                category=category,
                severity=severity,
                summary=summary,
                suggested_next_steps_json=json.dumps(steps),
                needs_human_review=1 if needs_human_review else 0,
                confidence=confidence,
                redacted_text=t.redacted_text,
            )
            wrote += 1
        except Exception as e:
          
            print(f"[warn] ticket {t.ticket_id}: LLM assist failed: {e}")

    print(f"Wrote/updated {wrote} LLM suggestions (of {len(tickets)} review tickets).")


if __name__ == "__main__":
    run_llm_assist()