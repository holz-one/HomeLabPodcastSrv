# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "duckdb",
#     "pandas",
#     "sqlalchemy",
#     "python-dotenv",
# ]
# ///
import duckdb
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost:5332")
POSTGRES_DB = os.getenv("POSTGRES_DB", "podcast_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASS = os.getenv("POSTGRES_PASS", "postgres")
FILES_DB = os.getenv("DB", "database/PodcastSrv.duckdb")

# Read from DuckDB
con = duckdb.connect(FILES_DB)
df = con.execute("SELECT * FROM FilesCast").df()
con.close()

# Write straight to PostgreSQL
engine = create_engine(f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}/{POSTGRES_DB}")
df.to_sql("FilesCast", engine, if_exists="append", index=False)