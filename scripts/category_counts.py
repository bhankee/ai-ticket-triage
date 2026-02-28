import sqlite3

DB = "data/tickets.db"

with sqlite3.connect(DB) as cx:
    rows = cx.execute(
        """
        SELECT category, COUNT(*) AS n
        FROM ticket_analysis
        GROUP BY category
        ORDER BY n DESC, category;
        """
    ).fetchall()

for category, n in rows:
    print(f"{category:15} {n}")