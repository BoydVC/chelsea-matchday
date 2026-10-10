# Chelsea Matchday

A **Stamford Bridge night wall** for **Chelsea v AFC Bournemouth**, Premier League. Kick-off **Sat Oct 10, 2026, 10:00 AM ET**, Stamford Bridge, on **Peacock**. Built only from ESPN public soccer JSON (league `eng.1`) already on disk, plus labelled team-news notes from `/workspace/ij_*` research. Nothing is invented: every section without data says so.

## What's new — Sat Oct 10 afternoon remaster
- **Night wall aesthetic:** deep Bridge floodlight look (navy void, Chelsea blue glow, gold trim) instead of the paper programme sheet.
- **Multi-panel layout:** hero next-fixture (ET), form strip, season vibe meters, lineup board, research team news, keys, table, H2H, stats.
- **Lineup board honesty:** ESPN public data has **no starting XI** — panel says so; season leaders shown only as named board cards, not as a guessed XI.
- **Research notes:** `data/research_notes.json` from on-disk `ij_2026-10-05/06/07_research.md` (Palmer / João Pedro / Caicedo / Bournemouth absences), clearly labelled *not ESPN*.
- **Ship pattern (ship-it-stats style):** `export_static.py` → `dist/chelsea-matchday-snapshot.html`; `screenshot.sh` → `screenshots/00-best-home.png`; `run.sh` + stdlib server on **127.0.0.1:4276**.

## Open it
- Live: http://127.0.0.1:4276 (`./run.sh start`, 127.0.0.1 only)
- Offline: `dist/chelsea-matchday-snapshot.html` (match + research + CSS/JS/fonts inlined, file:// safe)
- Best screenshot: `screenshots/00-best-home.png` (also `overview.png`, `full.png`, `mobile.png`, `live.png`)

## Headline numbers (ESPN, fetched Oct 7, 2026; 5 league matches each)
| | Chelsea | Bournemouth |
|---|---|---|
| Table | 10th, 7 pts (W2 D1 L2), GD −2 | 17th, 3 pts (W0 D3 L2), GD −2 |
| Goals for–against | 10–12 (2.0–2.4 per match) | 6–8 (1.2–1.6 per match) |
| Last 5, all competitions (oldest → newest) | W L W D L | D W D W L |
| H2H last 5 | CHE 2 W, 3 D, 0 L · goals 7–5 | |

Team news in ESPN public data: **empty**. Research notes (ij_*) are shown separately and may conflict across days — the wall labels the file each bullet came from.

## Commands
```
./run.sh start|stop|restart|status
./run.sh ship      # export_static + restart + screenshots + smoke
./run.sh build     # build.py + export_static + screenshot.sh
./run.sh test      # python3 tests/smoke_test.py
./run.sh fetch     # re-pull ESPN then build (optional; remaster used on-disk data)
```

## Privacy and scope
Public ESPN JSON + local research files only. No accounts, no keys, nothing sent. Server binds 127.0.0.1. Betting lines are informational only. Not affiliated with the Premier League, ESPN, any bookmaker, Chelsea FC or AFC Bournemouth.


---
## Repo notes
- **Built:** Oct 10, 2026, by TokenMax (Boyd's Grok Bot) on the Grok Bot box.
- **Run:** `./run.sh` (then open the localhost URL it prints).
- Imported from `/workspace/tokenmax/chelsea-matchday` on Oct 23, 2026. node_modules, virtualenvs, logs and files over 20 MB were left out.
- Personal details (emails, phone numbers, home street address) were replaced with `[redacted-…]` placeholders.
