"""Draft Synergies: champion pairs that win more together than apart.

For every 2-champion combo drafted on the same team, compare the pair's win rate to
what you'd expect from each champion alone (the average of their solo win rates).
LIFT = pair_wr - expected. High lift = "better together" than the sum of the parts.

CAVEAT (framed in the artifact too): lift is a heuristic, not proof of causation.
Strong teams draft these pairs; two good champions co-occur; samples are small.
"""
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "lol.duckdb"
OUT = ROOT / "data" / "synergies.json"
MAJORS = ("LCK", "LPL", "LEC", "LTA N", "LTA S", "WLDs")

PAIR_FLOOR = 20    # min games a pair was drafted together
SOLO_FLOOR = 40    # each champ needs a stable solo win rate

con = duckdb.connect(str(DB), read_only=True)
league_list = ", ".join(f"'{m}'" for m in MAJORS)
U = f"position <> 'team' AND league IN ({league_list})"

# roles for labels
roles = {r[0]: r[1] for r in con.execute(f"""
    SELECT champion, MODE(position) FROM games WHERE {U} GROUP BY champion
""").fetchall()}

# solo win rates
solo = {r[0]: {"picks": r[1], "wr": r[2]} for r in con.execute(f"""
    SELECT champion, COUNT(*), AVG(result)*100 FROM games WHERE {U} GROUP BY champion
""").fetchall()}

# same-team pairs (same game + side), champion a < b to dedupe
pairs = con.execute(f"""
    WITH p AS (SELECT gameid, side, champion, result FROM games WHERE {U})
    SELECT a.champion AS c1, b.champion AS c2, COUNT(*) g, AVG(a.result)*100 AS pair_wr
    FROM p a JOIN p b ON a.gameid=b.gameid AND a.side=b.side AND a.champion < b.champion
    GROUP BY 1,2
    HAVING COUNT(*) >= {PAIR_FLOOR}
""").fetchall()

rows = []
for c1, c2, g, pair_wr in pairs:
    if solo[c1]["picks"] < SOLO_FLOOR or solo[c2]["picks"] < SOLO_FLOOR:
        continue
    exp = (solo[c1]["wr"] + solo[c2]["wr"]) / 2
    rows.append({
        "c1": c1, "c2": c2, "r1": roles.get(c1, "?"), "r2": roles.get(c2, "?"),
        "g": g, "pair_wr": round(pair_wr, 1),
        "solo1": round(solo[c1]["wr"], 1), "solo2": round(solo[c2]["wr"], 1),
        "lift": round(pair_wr - exp, 1),
    })

rows.sort(key=lambda r: r["lift"], reverse=True)

payload = {"meta": {"pair_floor": PAIR_FLOOR, "solo_floor": SOLO_FLOOR, "n_pairs": len(rows)},
           "top": rows[:12], "worst": rows[-4:][::-1]}
OUT.write_text(json.dumps(payload, indent=2))

print(f"qualifying pairs: {len(rows)}  (>= {PAIR_FLOOR} games together)")
print(f"\n{'pair':30s} {'g':>3s} {'pair%':>6s} {'solo':>13s} {'lift':>6s}")
for r in rows[:12]:
    print(f"  {r['c1']+' + '+r['c2']:30s} {r['g']:3d} {r['pair_wr']:6.1f} "
          f"{str(r['solo1'])+'/'+str(r['solo2']):>13s} {r['lift']:+6.1f}")
print("\nlowest lift (anti-synergy):")
for r in rows[-4:][::-1]:
    print(f"  {r['c1']+' + '+r['c2']:30s} {r['g']:3d} {r['pair_wr']:6.1f} "
          f"{str(r['solo1'])+'/'+str(r['solo2']):>13s} {r['lift']:+6.1f}")
print(f"\nwrote {OUT}")
con.close()
