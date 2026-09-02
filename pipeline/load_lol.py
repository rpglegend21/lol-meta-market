"""Load the Oracle's Elixir pro-match CSV into lol.duckdb and inspect its shape."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
CSV = (ROOT / "data" / "lol_2025.csv").as_posix()
DB = ROOT / "lol.duckdb"

if DB.exists():
    DB.unlink()
con = duckdb.connect(str(DB))
con.execute(f"""
    CREATE TABLE games AS
    SELECT * FROM read_csv_auto('{CSV}', header=true, sample_size=-1, all_varchar=false);
""")

n = con.execute("SELECT COUNT(*) FROM games").fetchone()[0]
ncols = len(con.execute("PRAGMA table_info('games')").fetchall())
print(f"Rows: {n:,}   Columns: {ncols}")

# datacompleteness + position tell us team-rows vs player-rows
print("\n-- position values (team summary rows vs the 10 players) --")
for r in con.execute("SELECT position, COUNT(*) c FROM games GROUP BY 1 ORDER BY 2 DESC").fetchall():
    print(f"  {str(r[0]):10s} {r[1]:,}")

print("\n-- leagues (top 12 by rows) --")
for r in con.execute("SELECT league, COUNT(*) c FROM games GROUP BY 1 ORDER BY 2 DESC LIMIT 12").fetchall():
    print(f"  {str(r[0]):10s} {r[1]:,}")

print("\n-- a few columns that matter for adoption vs performance --")
cols = [c[1] for c in con.execute("PRAGMA table_info('games')").fetchall()]
for key in ["gameid","datacompleteness","league","split","patch","side","position",
            "playername","teamname","champion","result","ban1","ban2","ban3","ban4","ban5"]:
    print(f"  {key:18s} {'present' if key in cols else 'MISSING'}")

print("\n-- sample: 3 player rows --")
for r in con.execute("""
    SELECT league, patch, position, champion, result
    FROM games WHERE position <> 'team' LIMIT 3
""").fetchall():
    print("  ", r)

print(f"\nDB written: {DB}  (table: games)")
con.close()
