# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "duckdb",
#     "python-dotenv",
#     "numpy",
#     "pandas",
# ]
# ///

import json
import os
from datetime import datetime
from pathlib import Path

import duckdb
from dotenv import load_dotenv

load_dotenv()

FILES_DB = os.getenv("DB", "database/PodcastSrv.duckdb")

# Output JSON file for exported orphan records
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
EXPORT_JSON_FILE = f"database/orphaned_playlists_{TIMESTAMP}.json"


def clean_missing_playlists():
    if not os.path.exists(FILES_DB):
        print(f"Database not found at: {FILES_DB}")
        return

    con = duckdb.connect(FILES_DB)

    # Query distinct playlists along with their directory paths
    db_playlists = con.execute("""
        SELECT DISTINCT playlist, dir 
        FROM FilesCast 
        WHERE playlist IS NOT NULL
    """).fetchall()

    if not db_playlists:
        print("No playlist entries found in database.")
        con.close()
        return

    orphaned_playlists = []
    
    # Check if the associated directory physically exists on disk
    for playlist, dir_path in db_playlists:
        if not dir_path or not Path(dir_path).is_dir():
            orphaned_playlists.append(playlist)

    if not orphaned_playlists:
        print("All playlist directories exist on disk. No clean-up needed.")
        con.close()
        return

    print(f"Found {len(orphaned_playlists)} playlist(s) with missing directories:")
    for p in set(orphaned_playlists):
        print(f" - {p}")

    # 1. Fetch records for orphaned playlists as a DataFrame
    query = f"""
        SELECT * FROM FilesCast 
        WHERE playlist IN ({", ".join(["?"] * len(orphaned_playlists))})
    """
    df_orphans = con.execute(query, orphaned_playlists).df()
    orphan_records = df_orphans.to_dict(orient="records")

    # 2. Export to JSON file
    with open(EXPORT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(orphan_records, f, indent=4, default=str)
    print(
        f"\nSuccessfully exported {len(orphan_records)} record(s) to"
        f" '{EXPORT_JSON_FILE}'"
    )

    # 3. Remove orphaned playlist records from DuckDB
    con.execute(
        f"""
        DELETE FROM FilesCast 
        WHERE playlist IN ({", ".join(["?"] * len(orphaned_playlists))})
    """,
        orphaned_playlists,
    )

    print(f"Successfully removed orphaned records from '{FILES_DB}'.")
    con.close()


if __name__ == "__main__":
    clean_missing_playlists()
