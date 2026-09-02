"""The Player Factor: is a champion's win rate the champion, or the pilot?

Two views, both over the 2025 universe (majors + Worlds):
  1. specialists  - champ win rate split into its top pilot vs the rest of the field
  2. signature    - the standout player-champion combos (who owns what)
Outputs data/player_factor.json for the artifact.

CAVEAT baked into the framing: concentration is evidence, not proof. Good players
earn comfort picks; good teams draft to their stars; samples are small. This flags
where an average is hiding a pilot - it does not prove causation.
"""
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "lol.duckdb"
OUT = ROOT / "data" / "player_factor.json"
MAJORS = ("LCK", "LPL", "LEC", "LTA N", "LTA S", "WLDs")

CHAMP_FLOOR = 40   # champion needs a real sample to have a "field"
PILOT_FLOOR = 12   # a specialist needs enough games to mean something
SIG_FLOOR   = 14   # signature combo threshold

con = duckdb.connect(str(DB), read_only=True)
league_list = ", ".join(f"'{m}'" for m in MAJORS)
U = f"position <> 'team' AND league IN ({league_list})"

# champion totals
champ = {r[0]: {"picks": r[1], "wins": r[2]} for r in con.execute(f"""
    SELECT champion, COUNT(*), SUM(result) FROM games WHERE {U} GROUP BY champion
""").fetchall()}

# champion x player
cp = con.execute(f"""
    SELECT champion, playername, COUNT(*) g, SUM(result) w, MODE(teamname) team
    FROM games WHERE {U} GROUP BY champion, playername
""").fetchall()

# --- specialists: the BEST pilot (min games) vs the field ---
# "specialist" = the pilot with the highest win rate among those with >= PILOT_FLOOR
# games on the champ, NOT the most frequent pilot. That's the whole point of the chart.
top_by_champ = {}
for champ_name, player, g, w, team in cp:
    if g < PILOT_FLOOR:
        continue
    wr = w / g
    cur = top_by_champ.get(champ_name)
    if cur is None or wr > cur[4] or (wr == cur[4] and g > cur[2]):
        top_by_champ[champ_name] = (player, team, g, w, wr)

specialists = []
for name, agg in champ.items():
    if agg["picks"] < CHAMP_FLOOR or name not in top_by_champ:
        continue
    player, team, tg, tw, _ = top_by_champ[name]
    field_g = agg["picks"] - tg
    field_w = agg["wins"] - tw
    if field_g < 15:
        continue
    top_wr = tw / tg * 100
    field_wr = field_w / field_g * 100
    specialists.append({
        "champion": name, "picks": agg["picks"],
        "overall_wr": round(agg["wins"] / agg["picks"] * 100, 1),
        "pilot": player, "team": team, "pilot_g": tg, "pilot_wr": round(top_wr, 1),
        "field_g": field_g, "field_wr": round(field_wr, 1),
        "gap": round(top_wr - field_wr, 1),
    })
specialists.sort(key=lambda r: r["gap"], reverse=True)

# --- signature combos: who owns what ---
signature = []
for champ_name, player, g, w, team in cp:
    if g >= SIG_FLOOR:
        signature.append({
            "pilot": player, "champion": champ_name, "team": team,
            "g": g, "wr": round(w / g * 100, 1),
        })
signature.sort(key=lambda r: (r["wr"], r["g"]), reverse=True)

payload = {
    "meta": {"champ_floor": CHAMP_FLOOR, "pilot_floor": PILOT_FLOOR, "sig_floor": SIG_FLOOR},
    "specialists": specialists[:16],
    "signature": signature[:14],
}
OUT.write_text(json.dumps(payload, indent=2))

print("SPECIALISTS  (biggest pilot-vs-field gap):")
print(f"  {'champ':13s} {'ovr':>5s} | {'pilot':12s} {'pg':>3s} {'pwr':>5s} | {'field_wr':>8s} {'gap':>6s}")
for s in specialists[:12]:
    print(f"  {s['champion']:13s} {s['overall_wr']:5.1f} | {s['pilot']:12s} {s['pilot_g']:3d} "
          f"{s['pilot_wr']:5.1f} | {s['field_wr']:8.1f} {s['gap']:+6.1f}")
print("\nSIGNATURE combos:")
for s in signature[:14]:
    print(f"  {s['pilot']:12s} {s['champion']:12s} {s['team']:20s} {s['g']:3d}g {s['wr']:5.1f}%")
print(f"\nwrote {OUT}")
con.close()
