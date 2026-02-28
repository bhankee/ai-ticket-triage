import sqlite3

DB = "data/tickets.db"

with sqlite3.connect(DB) as cx:
    rows = cx.execute(
        """
        SELECT ticket_id, category, needs_human_review, summary
        FROM ticket_analysis
        WHERE needs_human_review = 1
        ORDER BY ticket_id;
        """
    ).fetchall()

print(f"Needs human review: {len(rows)}")
for ticket_id, category, _, summary in rows[:20]:
    print(f"- #{ticket_id} [{category}] {summary}")