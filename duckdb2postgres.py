# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "duckdb",
#     "python-dotenv",
# ]
# ///

# =========================
# Currently untested
# =========================

import os
import sys
import duckdb
from dotenv import load_dotenv

load_dotenv()

# Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5332") # Default split host/port safely
POSTGRES_DB = os.getenv("POSTGRES_DB", "podcast_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASS = os.getenv("POSTGRES_PASS", "postgres")
FILES_DB = os.getenv("DB", "database/PodcastSrv.duckdb")

# Format host/port if specified together in host var (e.g. "localhost:5332")
if ":" in POSTGRES_HOST:
    POSTGRES_HOST, POSTGRES_PORT = POSTGRES_HOST.split(":")

# 1. Connect to local DuckDB file
conn = duckdb.connect(FILES_DB)

try:
    # 2. Install and load Postgres extension
    conn.execute("INSTALL postgres; LOAD postgres;")

    # 3. Attach PostgreSQL target DB
    pg_conn_str = f"dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASS} host={POSTGRES_HOST} port={POSTGRES_PORT}"
    conn.execute(f"ATTACH '{pg_conn_str}' AS pgsql (TYPE POSTGRES);")

    print("Connected to DuckDB and PostgreSQL. Starting migration...")

    # 4. Stream tables directly in foreign key dependency order
    tables = ["users", "FilesCast", "media_views", "media_progress", "media_notes"]

    for table in tables:
        print(f"Migrating table: {table}...")
        conn.execute(f"INSERT INTO pgsql.public.{table} SELECT * FROM main.{table};")

    print("Migration completed successfully!")

except Exception as e:
    print(f"Migration error: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    conn.close()