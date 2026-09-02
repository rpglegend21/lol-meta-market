# The LoL Meta Market

**2025 pro League of Legends, priced like a stock market.** Every champion scored on two axes — how badly teams *wanted* it (demand) and whether it actually *won* (value) — so the interesting ones fall out on their own: hype that isn't earned, and quiet picks that are.

> 🔗 **Live:** _link goes here once published_
> 📊 Built on **2,198 real games** from the 2025 season (LCK · LPL · LEC · LTA N/S · Worlds).

---

## What it is

Four layers, each answering a question a draft analyst actually asks:

| Layer | Question |
|---|---|
| **The Market Map** | Where does each champion land on demand × win rate? (four quadrants: Blue Chip, Sleeper, Overvalued, Speculative) |
| **Analyst Calls** | Six champions I think are mispriced — buy, sell, hold, and *why*. |
| **The Player Factor** | Is a champion's win rate the *champion*, or the *pilot*? Split by who's holding it and it often falls apart. |
| **Draft Synergies** | Which pairs win far above the sum of their parts — and which collapse together. |

**A few findings:**
- **Varus** is the blue chip — contested in ~64% of games, wins 56%.
- **Corki** wins 42% and is *still* one of the most-fought-over picks. The reputation is doing the work, not the champion.
- **Gnar's** win rate swings 55 points depending on the pilot (369: 100% over 14 games; everyone else: 44.7%). The "meta" is partly just a few rosters — Gen.G especially — being better than everyone else.
- **Annie + Rakan** win 88.5% together vs ~55% apart (+33.5 lift). **Orianna + Xin Zhao** *lose* together (30%, −21.9).

---

## My role

I didn't hand-write the SQL — I **directed** the build, made the product calls, and **verified every number**. That's the point of the piece: the judgment, not the typing.

What that looked like in practice:

- **Defined "done" up front** — four pillars, a real question and a decision attached to each. No scope creep.
- **Made the framing calls** — e.g. the specialist chart shows each champion's *best* pilot vs the field, not its *most frequent* pilot. Most-frequent hides the story; best-vs-field *is* the story.
- **Caught the wrong-but-plausible results** — the ones a plausible-looking query slips past you:
  - Empty ban slots were being counted as a champion → `WHERE champion IS NOT NULL`.
  - Nearly filtered out `datacompleteness = 'partial'` games — until I checked and confirmed their **draft + result are 100% intact** (only deep in-game stats are missing, which this doesn't use). Dropping them would have shrunk the sample for no gain.
  - Set the pick floor at 15 games knowing it's a *listing* threshold, not a significance test — so every headline call leans on champions with hundreds of games, not fifteen.
- **Owned the voice** — the analyst theses are mine, in plain League terms, not marketing polish.

The honest caveats are built into the product, not hidden: contest ≠ causation, concentration is evidence not proof, a season-average isn't a snapshot of today's patch.

---

## How it's built

```
data/lol_2025.csv                     Oracle's Elixir raw match data (gitignored — see below)
        │  pipeline/load_lol.py
        ▼
lol.duckdb  (table: games)            ~120k rows, one DuckDB file (gitignored)
        │  pipeline/build_*.py
        ▼
data/*.json                           three small datasets the page embeds
        │  (injected into meta_market.html)
        ▼
meta_market.html                      the shipped, self-contained artifact
```

**The pipeline (`pipeline/`):**
| Script | Does |
|---|---|
| `load_lol.py` | Loads the CSV into `lol.duckdb` and prints the table's shape (grain, leagues, key columns). |
| `build_meta_market.py` | Per-champion contest rate (picks + bans ÷ games) vs win rate → `data/meta_market.json`. |
| `build_player_factor.py` | Splits each champion's win rate into top-pilot vs the field → `data/player_factor.json`. |
| `build_synergies.py` | Same-team champion pairs, win rate together vs the average apart (lift) → `data/synergies.json`. |

### Run it yourself
```bash
pip install duckdb
# 1. drop Oracle's Elixir's 2025 CSV at data/lol_2025.csv (see Data below)
python pipeline/load_lol.py
python pipeline/build_meta_market.py
python pipeline/build_player_factor.py
python pipeline/build_synergies.py
# the three data/*.json are regenerated; open meta_market.html to view the result
```

---

## Data

Match data from **[Oracle's Elixir](https://oracleselixir.com/tools/downloads)** — free public pro-play data, credit to Tim Sevenhuysen. The raw CSV (~79 MB) and the built `lol.duckdb` are **not** committed (see `.gitignore`); grab the 2025 file from the link above and drop it at `data/lol_2025.csv`.

**Universe:** 2025 season — LCK, LPL, LEC, LTA N, LTA S, and Worlds. Academy tiers and minor regional leagues excluded.

---

## Tech
DuckDB (SQL over the raw CSV, no warehouse) · Python (stdlib + `duckdb`) · a single self-contained HTML/CSS/SVG file, no build step and no dependencies.

The code here is MIT-licensed. The match data belongs to Oracle's Elixir under its own terms.
