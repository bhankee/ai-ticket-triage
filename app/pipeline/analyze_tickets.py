import re
import sqlite3
from dataclasses import dataclass
from typing import Iterable


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")


@dataclass(frozen=True)
class Ticket:
    ticket_id: int
    created_at: str
    source: str
    customer: str
    priority: str
    text: str


@dataclass(frozen=True)
class AnalysisResult:
    ticket_id: int
    prompt_version: str
    model_version: str
    summary: str
    category: str
    needs_human_review: int
    redacted_text: str


def redact_pii(text: str) -> str:
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text


def classify_deterministic(priority: str, text: str) -> tuple[str, int]:
    """Returns category, score... score: higher = more urgent"""
    
    formatted_text = text.lower()

    score = 0
   
    if priority.lower() == "high":
        score += 3
    elif priority.lower() == "medium":
        score += 1

    
    outage_terms = ["500", "outage", "down", "crash", "blank screen", "failed to fetch", "token exchange failed"]
    perf_terms = ["slow", "lcp", "core web vitals", "cpu", "perf", "latency"]
    billing_terms = ["invoice", "charged", "refund", "tax", "chargeback", "billing"]
    auth_terms = ["login", "mfa", "sso", "okta", "401", "access denied", "scim"]
    webhook_terms = ["webhook", "events", "payload", "429", "rate limit"]

    def has_any(terms: list[str]) -> bool:
        return any(term in formatted_text for term in terms)

    if has_any(outage_terms):
        return ("incident", score + 3)
    if has_any(auth_terms):
        return ("auth_access", score + 2)
    if has_any(billing_terms):
        return ("billing", score + 2)
    if has_any(perf_terms):
        return ("performance", score + 1)
    if has_any(webhook_terms):
        return ("integrations", score + 1)

    return ("general_support", score)


def summarize_deterministic(text: str) -> str:
    # simple, reliable “summary”: first sentence-ish / truncated
    stripped_text = text.strip().replace("\n", " ")
    return (stripped_text[:180] + "...") if len(stripped_text) > 180 else stripped_text


def needs_review(score: int, redacted_text: str) -> int:
    # Always require review if high score or redaction occurred
    redacted = ("[REDACTED_EMAIL]" in redacted_text) or ("[REDACTED_PHONE]" in redacted_text)
    return 1 if score >= 4 or redacted else 0


def fetch_tickets(db_path: str) -> Iterable[Ticket]:
    with sqlite3.connect(db_path) as cx:
        cx.row_factory = sqlite3.Row
        rows = cx.execute(
            "SELECT ticket_id, created_at, source, customer, priority, text FROM tickets ORDER BY created_at"
        ).fetchall()
    for r in rows:
       row = {k.lower(): r[k] for k in r.keys()}
       yield Ticket(**row)


def write_results(sqlite_path: str, results: list[AnalysisResult]) -> None:
    with sqlite3.connect(sqlite_path) as cx:
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_analysis (
              ticket_id INTEGER,
              prompt_version TEXT,
              model_version TEXT,
              summary TEXT,
              category TEXT,
              needs_human_review INTEGER,
              redacted_text TEXT,
              created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        cx.executemany(
            """
            INSERT INTO ticket_analysis
              (ticket_id, prompt_version, model_version, summary, category, needs_human_review, redacted_text)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            [
                (
                    r.ticket_id,
                    r.prompt_version,
                    r.model_version,
                    r.summary,
                    r.category,
                    r.needs_human_review,
                    r.redacted_text,
                )
                for r in results
            ],
        )
        cx.commit()


def run(sqlite_path: str) -> None:
    out: list[AnalysisResult] = []

    for ticket in fetch_tickets(sqlite_path):
        redacted = redact_pii(ticket.text)
        category, score = classify_deterministic(ticket.priority, redacted)
        summary = summarize_deterministic(redacted)
        review = needs_review(score, redacted)

        out.append(
            AnalysisResult(
                ticket_id=ticket.ticket_id,
                prompt_version="deterministic-v1",
                model_version="none",
                summary=summary,
                category=category,
                needs_human_review=review,
                redacted_text=redacted,
            )
        )

    write_results(sqlite_path, out)
    print(f"Wrote {len(out)} analysis rows to ticket_analysis")


if __name__ == "__main__":
    run("data/tickets.db")