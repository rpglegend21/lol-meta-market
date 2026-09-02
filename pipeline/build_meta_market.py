"""Build the Meta Market dataset: per-champion adoption (contest rate) vs performance (win rate).

Universe (v1): 2025 four majors + complete data.
Outputs data/meta_market.json for the artifact to embed.
"""
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "lol.duckdb"
OUT = ROOT / "data" / "meta_market.json"

# --- universe: 2025 top domestic leagues + Worlds ---
# NOTE: no datacompleteness filter. 'partial' games are missing deep in-game stats
# (gold/vision/etc.) we don't use; their draft + result are 100% intact, so excluding
# them would just shrink the sample for no gain. Verified: partial games have full
# champion/result/ban coverage.
MAJORS = ("LCK", "LPL", "LEC", "LTA N", "LTA S", "WLDs")
PICK_FLOOR = 15  # min games picked for a trustworthy win rate (accuracy != significance)

con = duckdb.connect(str(DB), read_only=True)

league_list = ", ".join(f"'{m}'" for m in MAJORS)
universe = f"league IN ({league_list})"

total_games = con.execute(
    f"SELECT COUNT(DISTINCT gameid) FROM games WHERE {universe}"
).fetchone()[0]

# per-champion picks + win rate (player rows), primary role = most-played position
picks = con.execute(f"""
    SELECT champion,
           COUNT(*)                       AS picks,
           ROUND(AVG(result) * 100, 1)    AS winrate_pct,
           MODE(position)                 AS primary_role
    FROM games
    WHERE position <> 'team' AND {universe}
    GROUP BY champion
""").fetchall()

# per-champion bans (team rows, 5 ban slots unpivoted, nulls dropped)
bans = dict(con.execute(f"""
    SELECT champion, COUNT(*) AS bans
    FROM (
        SELECT ban1 AS champion FROM games WHERE position = 'team' AND {universe}
        UNION ALL SELECT ban2 FROM games WHERE position = 'team' AND {universe}
        UNION ALL SELECT ban3 FROM games WHERE position = 'team' AND {universe}
        UNION ALL SELECT ban4 FROM games WHERE position = 'team' AND {universe}
        UNION ALL SELECT ban5 FROM games WHERE position = 'team' AND {universe}
    )
    WHERE champion IS NOT NULL
    GROUP BY champion
""").fetchall())

rows = []
for champ, n_picks, winrate, role in picks:
    n_bans = bans.get(champ, 0)
    contest = n_picks + n_bans
    rows.append({
        "champion": champ,
        "role": role,
        "picks": n_picks,
        "bans": n_bans,
        "contest": contest,
        "contest_rate": round(contest * 100.0 / total_games, 1),
        "winrate": winrate,
    })

# keep champions with a trustworthy win rate for the plot
plotted = [r for r in rows if r["picks"] >= PICK_FLOOR]
plotted.sort(key=lambda r: r["contest_rate"], reverse=True)

# quadrant split lines: win rate at 50%, contest at the median of plotted champs
contests = sorted(r["contest_rate"] for r in plotted)
mid = len(contests) // 2
contest_line = (contests[mid] if len(contests) % 2
                else round((contests[mid - 1] + contests[mid]) / 2, 1))

payload = {
    "meta": {
        "season": "2025",
        "leagues": list(MAJORS),
        "total_games": total_games,
        "pick_floor": PICK_FLOOR,
        "contest_line": contest_line,
        "winrate_line": 50.0,
        "n_champions": len(plotted),
    },
    "champions": plotted,
}
OUT.write_text(json.dumps(payload, indent=2))

print(f"universe: 2025 {MAJORS}  ->  {total_games} games")
print(f"champions plotted (>= {PICK_FLOOR} picks): {len(plotted)}")
print(f"quadrant lines: winrate = 50.0%, contest = {contest_line}%")
print("\ntop 12 by contest rate:")
print(f"  {'champ':14s} {'role':5s} {'pick':>5s} {'ban':>5s} {'contest%':>8s} {'win%':>6s}")
for r in plotted[:12]:
    print(f"  {r['champion']:14s} {r['role']:5s} {r['picks']:5d} {r['bans']:5d} "
          f"{r['contest_rate']:8.1f} {r['winrate']:6.1f}")
print(f"\nwrote {OUT}")
con.close()
