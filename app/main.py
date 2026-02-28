import os
from app.pipeline.analyze_tickets import run

def main() -> None:
    sqlite_path = os.getenv("SQLITE_PATH", "data/tickets.db")
    run(sqlite_path)

if __name__ == "__main__":
    main()