import os
import sqlite3
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

@dataclass(frozen=True)
class SnowflakeCfg:
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str

def cfg_from_env() -> SnowflakeCfg:
    missing = [var for var in [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
    ] if not os.getenv(var)]
    if missing:
        raise RuntimeError(f"Missing env vars: {missing}")

    return SnowflakeCfg(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )

def fetch_tickets(sf: SnowflakeCfg) -> pd.DataFrame:
    conn = snowflake.connector.connect(
        account=sf.account,
        user=sf.user,
        password=sf.password,
        warehouse=sf.warehouse,
        database=sf.database,
        schema=sf.schema,
    )
    try:
        sql = """
        SELECT ticket_id, created_at, source, customer, priority, text
        FROM TICKETS.PUBLIC.TICKETS
        ORDER BY created_at;
        """
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()

def write_sqlite(df: pd.DataFrame, sqlite_path: str) -> None:
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    with sqlite3.connect(sqlite_path) as cx:
        df.to_sql("tickets", cx, if_exists="replace", index=False)

def main() -> None:
    sf = cfg_from_env()
    df = fetch_tickets(sf)
    print(f"Fetched {len(df)} tickets from Snowflake.")
    out_path = "data/tickets.db"
    write_sqlite(df, out_path)
    print(f"Wrote SQLite snapshot to {out_path}")

if __name__ == "__main__":
    main()