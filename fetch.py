#!/usr/bin/env python3
"""Fetch PUBLIC ESPN soccer JSON (league eng.1) for the Chelsea matchday preview. Read-only, no auth, ~16 requests.
Writes data/raw/*.json and data/raw/manifest.json (URL + fetched-at for every file)."""
import json, os, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "data", "raw")
ET = ZoneInfo("America/New_York")
EVENT = os.environ.get("EVENT", "401878775")  # Chelsea vs AFC Bournemouth, Sat Oct 10 2026, 10:00 AM ET
BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1"
U = {"summary": BASE + "/summary?event={}", "standings": "https://site.api.espn.com/apis/v2/sports/soccer/eng.1/standings",
     "schedule": BASE + "/teams/{}/schedule",
     "core": "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/seasons/{}/types/1/teams/{}/statistics",
     "injuries": "https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/teams/{}/injuries",
     "team": BASE + "/teams/{}?enable=roster,injuries"}


def get(url, name):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (TokenMax chelsea-matchday; local)", "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    json.loads(body)
    p = os.path.join(RAW, name); open(p + ".tmp", "wb").write(body); os.replace(p + ".tmp", p)
    time.sleep(0.25)  # be gentle
    return {"url": url, "fetchedAt": datetime.now(ET).isoformat(timespec="seconds")}


def main():
    os.makedirs(RAW, exist_ok=True)
    man = {"event": EVENT, "files": {}}
    F = man["files"]
    F["pregame.json"] = get(U["summary"].format(EVENT), "pregame.json")
    pre = json.load(open(os.path.join(RAW, "pregame.json")))
    comp = pre["header"]["competitions"][0]
    teams = {c["team"]["abbreviation"]: c["team"]["id"] for c in comp["competitors"]}
    year = pre["header"].get("season", {}).get("year", 2026)
    man["teams"] = teams
    F["standings.json"] = get(U["standings"], "standings.json")
    for ab, tid in teams.items():
        F[f"schedule_{ab}.json"] = get(U["schedule"].format(tid), f"schedule_{ab}.json")
        F[f"teamstats_{ab}.json"] = get(U["core"].format(year, tid), f"teamstats_{ab}.json")
        F[f"injuries_{ab}.json"] = get(U["injuries"].format(tid), f"injuries_{ab}.json")
        F[f"team_{ab}.json"] = get(U["team"].format(tid), f"team_{ab}.json")
        sched = json.load(open(os.path.join(RAW, f"schedule_{ab}.json")))
        for e in sched.get("events", []):
            if e["competitions"][0]["status"]["type"].get("completed") and f"match_{e['id']}.json" not in F:
                F[f"match_{e['id']}.json"] = get(U["summary"].format(e["id"]), f"match_{e['id']}.json")
                print("fetched match", e["id"], file=sys.stderr)
    json.dump(man, open(os.path.join(RAW, "manifest.json"), "w"), indent=1)
    print(f"fetched {len(F)} files")


if __name__ == "__main__":
    main()
