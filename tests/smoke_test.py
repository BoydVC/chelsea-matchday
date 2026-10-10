#!/usr/bin/env python3
"""Chelsea Matchday smoke test (stdlib only): python3 tests/smoke_test.py
Re-derives every number on the page from the raw ESPN JSON in data/raw (it doesn't import build.py) and cross-checks:
match box-score sums vs ESPN standings vs ESPN season team statistics vs ESPN's pre-match summary; table context;
last-5 form; head-to-head; betting lines; injuries; keys to the match; plus the live server, snapshot and screenshots."""
import json, os, re, subprocess, sys, urllib.request
from decimal import Decimal, ROUND_HALF_UP
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(HERE, *a)
R = lambda n: json.load(open(P("data", "raw", n), encoding="utf-8"))
fails, passes = [], 0


def check(name, cond, detail=""):
    global passes
    if cond: passes += 1; print(f"  ok   {name}")
    else: fails.append(name); print(f"  FAIL {name} {detail}")


q = lambda n, d=1, pl="0.1": float((Decimal(str(n)) / Decimal(str(d))).quantize(Decimal(pl), rounding=ROUND_HALF_UP))
near = lambda a, b, t=0.051: a is not None and b is not None and abs(float(a) - float(b)) < t
D = json.load(open(P("data", "match.json"), encoding="utf-8"))
man = R("manifest.json"); pre = R("pregame.json")
comp = pre["header"]["competitions"][0]
H = next(c["team"]["abbreviation"] for c in comp["competitors"] if c["homeAway"] == "home")
A = next(c["team"]["abbreviation"] for c in comp["competitors"] if c["homeAway"] == "away")

print("fixture")
check("fixture is Chelsea (home) v AFC Bournemouth (away)", (H, A) == ("CHE", "BOU") and D["match"]["home"] == H and D["match"]["away"] == A)
check("kick-off 2026-10-10 14:00Z = Sat Oct 10, 10:00 AM ET", D["match"]["date"] == comp["date"] == "2026-10-10T14:00Z")
check("broadcast lists Peacock (ESPN)", "Peacock" in D["match"]["broadcasts"])
check("league eng.1 source URLs", all("/soccer/eng.1/" in v["url"] or "/leagues/eng.1/" in v["url"] for v in man["files"].values()))
check("every raw file has a fetched-at time", all(v.get("fetchedAt") for v in man["files"].values()))

print("season stats: independent re-sum of ESPN match box scores")
std = {}
for en in R("standings.json")["children"][0]["standings"]["entries"]:
    st = {x["name"]: x.get("value") for x in en["stats"]}; std[en["team"]["abbreviation"]] = st
for ab in (H, A):
    t = dict(gp=0, w=0, d=0, l=0, gf=0, ga=0, shots=0, sot=0, shotsA=0, sotA=0, corners=0, fouls=0, yc=0, rc=0, saves=0, pas=0, acc=0, cs=0); poss = []
    rows = []
    for e in R(f"schedule_{ab}.json")["events"]:
        if not e["competitions"][0]["status"]["type"].get("completed"): continue
        m = R(f"match_{e['id']}.json")
        sc = {c["team"]["abbreviation"]: int(c["score"]) for c in m["header"]["competitions"][0]["competitors"]}
        op = [k for k in sc if k != ab][0]
        bx = {x["team"]["abbreviation"]: {s["name"]: s["displayValue"] for s in x["statistics"]} for x in m["boxscore"]["teams"]}
        me, oo = bx[ab], bx[op]
        t["gp"] += 1; t["gf"] += sc[ab]; t["ga"] += sc[op]; t["w" if sc[ab] > sc[op] else "d" if sc[ab] == sc[op] else "l"] += 1; t["cs"] += sc[op] == 0
        for k, n in [("shots", "totalShots"), ("sot", "shotsOnTarget"), ("corners", "wonCorners"), ("fouls", "foulsCommitted"), ("yc", "yellowCards"), ("rc", "redCards"),
                     ("saves", "saves"), ("pas", "totalPasses"), ("acc", "accuratePasses")]:
            t[k] += int(me[n])
        t["shotsA"] += int(oo["totalShots"]); t["sotA"] += int(oo["shotsOnTarget"]); poss.append(Decimal(me["possessionPct"]))
        rows.append((e["id"], sc[ab], sc[op]))
    S = D["season"][ab]; g = t["gp"]
    for k_s, k_t in [("gp", "gp"), ("w", "w"), ("d", "d"), ("l", "l"), ("gf", "gf"), ("ga", "ga"), ("shots", "shots"), ("sot", "sot"), ("shotsA", "shotsA"), ("sotA", "sotA"),
                     ("corners", "corners"), ("fouls", "fouls"), ("yc", "yc"), ("rc", "rc"), ("saves", "saves"), ("pass", "pas"), ("passAcc", "acc"), ("cs", "cs")]:
        check(f"[{ab}] {k_s} = {t[k_t]} (independent sum)", S[k_s] == t[k_t], f"page has {S[k_s]}")
    # vs ESPN league table
    st = std[ab]
    for lab, ours, k in [("played", g, "gamesPlayed"), ("wins", t["w"], "wins"), ("draws", t["d"], "ties"), ("losses", t["l"], "losses"), ("GF", t["gf"], "pointsFor"),
                         ("GA", t["ga"], "pointsAgainst"), ("GD", t["gf"] - t["ga"], "pointDifferential"), ("points", 3 * t["w"] + t["d"], "points")]:
        check(f"[{ab}] {lab} {ours} == ESPN table {st.get(k)}", near(ours, st.get(k)))
    # vs ESPN season team statistics
    core = {}
    for cat in R(f"teamstats_{ab}.json")["splits"]["categories"]:
        for s_ in cat["stats"]: core.setdefault(s_["name"], s_.get("value"))
    for lab, ours, k in [("goals", t["gf"], "totalGoals"), ("conceded", t["ga"], "goalsConceded"), ("shots", t["shots"], "totalShots"), ("on target", t["sot"], "shotsOnTarget"),
                         ("shots faced", t["shotsA"], "shotsFaced"), ("corners", t["corners"], "wonCorners"), ("fouls", t["fouls"], "foulsCommitted"), ("yellows", t["yc"], "yellowCards"),
                         ("reds", t["rc"], "redCards"), ("saves", t["saves"], "saves"), ("passes", t["pas"], "totalPasses"), ("accurate passes", t["acc"], "accuratePasses"), ("clean sheets", t["cs"], "cleanSheet")]:
        check(f"[{ab}] {lab} {ours} == ESPN season stats {core.get(k)}", near(ours, core.get(k)))
    # vs pre-match summary
    pb = next({s_["name"]: s_["displayValue"] for s_ in x["statistics"]} for x in pre["boxscore"]["teams"] if x["team"]["abbreviation"] == ab)
    check(f"[{ab}] GF/GA/GD == pre-match summary ({pb.get('totalGoals')}/{pb.get('goalsConceded')}/{pb.get('goalDifference')})",
          near(t["gf"], pb.get("totalGoals")) and near(t["ga"], pb.get("goalsConceded")) and near(t["gf"] - t["ga"], pb.get("goalDifference")))
    rec = {r["type"]: r["displayValue"] for r in next(c for c in comp["competitors"] if c["team"]["abbreviation"] == ab)["record"]}
    check(f"[{ab}] pre-match record {rec.get('total')} (W-D-L) and points {rec.get('points')} agree", rec.get("total") == f"{t['w']}-{t['d']}-{t['l']}" and int(rec.get("points")) == 3 * t["w"] + t["d"])
    # displayed derived numbers
    for k, v in [("gfpm", q(t["gf"], g, "0.01")), ("gapm", q(t["ga"], g, "0.01")), ("shotspm", q(t["shots"], g)), ("sotpm", q(t["sot"], g)), ("shotsApm", q(t["shotsA"], g)),
                 ("sotApm", q(t["sotA"], g)), ("passPct", q(100 * t["acc"], t["pas"])), ("cornerspm", q(t["corners"], g)), ("foulspm", q(t["fouls"], g)),
                 ("conv", q(100 * t["gf"], t["shots"])), ("poss", float((sum(poss) / len(poss)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))), ("pts", 3 * t["w"] + t["d"])]:
        check(f"[{ab}] displayed {k} = {v}", S[k] == v, f"page has {S[k]}")
    # xG straight from ESPN season stats, internally consistent
    x = D["xg"].get(ab)
    if core.get("avgExpectedGoals") is not None:
        check(f"[{ab}] xG {x and x['xg']} / xGA {x and x['xga']} == ESPN season stats", x and near(x["xg"], core["avgExpectedGoals"], 0.0006) and near(x["xga"], core["avgExpectedGoalsConceded"], 0.0006))
        check(f"[{ab}] ESPN xG − xGA == ESPN xG difference", near(core["avgExpectedGoals"] - core["avgExpectedGoalsConceded"], core["avgExpectedGoalDifferential"], 0.0011))
    else:
        check(f"[{ab}] no ESPN xG -> none shown", x is None)
    pm = {r["id"]: r for r in D["matches"][ab]}
    check(f"[{ab}] league results list == completed schedule ({len(rows)})", set(pm) == {r[0] for r in rows} and all(pm[i]["us"] == u and pm[i]["them"] == th for i, u, th in rows))
check("every on-page hard audit row matches", all(c["ok"] for c in D["checks"] if c["hard"]) and sum(c["hard"] for c in D["checks"]) >= 50)

print("league table + context")
raw_rows = sorted(R("standings.json")["children"][0]["standings"]["entries"], key=lambda e: [x["value"] for x in e["stats"] if x["name"] == "rank"][0])
check("table has all 20 clubs in ESPN order", [r["abbr"] for r in D["table"]["rows"]] == [e["team"]["abbreviation"] for e in raw_rows] and len(raw_rows) == 20)
check("every table cell == ESPN standings", all(r["pts"] == int(std[r["abbr"]]["points"]) and r["gd"] == int(std[r["abbr"]]["pointDifferential"]) and r["gp"] == int(std[r["abbr"]]["gamesPlayed"])
                                                and r["w"] == int(std[r["abbr"]]["wins"]) and r["d"] == int(std[r["abbr"]]["ties"]) and r["l"] == int(std[r["abbr"]]["losses"]) for r in D["table"]["rows"]))
rows = D["table"]["rows"]; byab = {r["abbr"]: r for r in rows}
for ab in (H, A):
    c = D["context"][ab]; me = byab[ab]; i = rows.index(me)
    ok = c["rank"] == me["rank"] and c["pts"] == me["pts"] and c["leader"]["gap"] == rows[0]["pts"] - me["pts"]
    ok &= c.get("above", {}).get("gap") == (rows[i - 1]["pts"] - me["pts"] if i else None) and c.get("below", {}).get("gap") == (me["pts"] - rows[i + 1]["pts"] if i < 19 else None)
    rel = min(r["rank"] for r in rows if r["note"] == "Relegation"); ucl = max(r["rank"] for r in rows if r["note"] == "Champions League")
    ok &= c["relegation"].get("gapAbove") == me["pts"] - rows[rel - 1]["pts"] and c["ucl"].get("gapBehind") == rows[ucl - 1]["pts"] - me["pts"]
    check(f"[{ab}] table context gaps recomputed ({c['rank']}th, {c['pts']} pts; +{c['relegation'].get('gapAbove')} over the drop)", ok)

print("form, head-to-head, line, team news, leaders")
for ab in (H, A):
    raw5 = next(x for x in pre["lastFiveGames"] if x["team"]["abbreviation"] == ab)["events"]
    ours = D["last5"][ab]
    check(f"[{ab}] last-5 == ESPN lastFiveGames ({len(raw5)} matches)", sorted(e["id"] for e in raw5) == sorted(r["id"] for r in ours))
    okr = all((r["result"] == ("W" if r["us"] > r["them"] else "D" if r["us"] == r["them"] else "L")) for r in ours)
    check(f"[{ab}] every last-5 W/D/L agrees with its score from {ab}'s side", okr)
    form = next(c for c in comp["competitors"] if c["team"]["abbreviation"] == ab).get("form")
    check(f"[{ab}] ESPN form string {form} == last-5 results, most recent first", form == "".join(r["result"] for r in sorted(ours, key=lambda r: r["date"], reverse=True)))
    pl = {r["id"]: r for r in D["matches"][ab]}
    check(f"[{ab}] league matches in the last 5 agree with their box scores", all(pl[r["id"]]["us"] == r["us"] and pl[r["id"]]["them"] == r["them"] for r in ours if r["id"] in pl))
ss = (pre.get("seasonseries") or [None])[0]
if ss:
    w = d = l = gf = ga = 0
    for e in ss["events"]:
        c = {x["team"]["abbreviation"]: int(x["score"]) for x in e["competitors"]}
        us, them = c["CHE"], c[[k for k in c if k != "CHE"][0]]; gf += us; ga += them
        w += us > them; d += us == them; l += us < them
    h = D["h2h"]
    check(f"H2H {w}W {d}D {l}L, goals {gf}-{ga} recomputed from ESPN's {len(ss['events'])} meetings", (h["w"], h["d"], h["l"], h["gf"], h["ga"]) == (w, d, l, gf, ga))
    m_ = re.search(r"leads series (\d+)-(\d+)-(\d+)", ss.get("summary", ""))
    check(f"ESPN summary '{ss.get('summary')}' (W-L-D) and seriesScore '{ss.get('seriesScore')}' (W-D-L) agree", m_ and tuple(map(int, m_.groups())) == (w, l, d) and ss.get("seriesScore") == f"{w}-{d}-{l}")
else:
    check("no H2H in ESPN data -> none shown", D["h2h"] is None)
pc = pre.get("pickcenter") or []
o = {x["provider"]: x for x in D["odds"]}
if pc:
    p0 = pc[0]; dk = o.get(p0["provider"]["name"], {})
    check(f"{p0['provider']['name']} line == ESPN pickcenter ({p0['details']}, draw {p0['drawOdds']['moneyLine']}, away {p0['awayTeamOdds']['moneyLine']}, O/U {p0['overUnder']})",
          dk.get("details") == p0["details"] and dk.get("homeML") == p0["homeTeamOdds"]["moneyLine"] and dk.get("awayML") == p0["awayTeamOdds"]["moneyLine"]
          and dk.get("drawML") == p0["drawOdds"]["moneyLine"] and dk.get("overUnder") == p0["overUnder"])
for p in pre.get("odds") or []:
    nm = p["provider"]["name"]
    if nm in o and o[nm]["kind"] == "fractional":
        check(f"{nm} fractional prices == ESPN odds ({p['homeTeamOdds']['odds']['summary']} / {p['drawOdds']['summary']} / {p['awayTeamOdds']['odds']['summary']})",
              (o[nm]["home"], o[nm]["draw"], o[nm]["away"]) == (p["homeTeamOdds"]["odds"]["summary"], p["drawOdds"]["summary"], p["awayTeamOdds"]["odds"]["summary"]))
check("every line labelled with source + fetched-at of the pre-match summary", D["odds"] and all(x.get("source") and x["url"] == man["files"]["pregame.json"]["url"] and x["fetchedAt"] == man["files"]["pregame.json"]["fetchedAt"] for x in D["odds"]))
check("no sportsbook links carried into the page data", "draftkings.com" not in json.dumps(D["odds"]) and "bet365.com" not in json.dumps(D["odds"]))
raw_inj = sum(len(R(f"injuries_{ab}.json").get("items", [])) for ab in (H, A)) + sum(1 for ab in (H, A) for a in R(f"team_{ab}.json")["team"].get("athletes", []) if a.get("injuries")) + len(pre.get("injuries") or [])
check(f"team news shown only if ESPN has it (ESPN entries: {raw_inj})", D["injuries"]["available"] == (raw_inj > 0))
for ab in (H, A):
    rl = next(x for x in pre["leaders"] if x["team"]["abbreviation"] == ab)["leaders"]
    check(f"[{ab}] top performers == ESPN leaders", [(l_["cat"], l_["name"], l_["value"]) for l_ in D["leaders"][ab]] == [(c_["displayName"], c_["leaders"][0]["athlete"]["displayName"], c_["leaders"][0]["displayValue"]) for c_ in rl if c_.get("leaders")])

print("keys to the match")
vals = set()
for ab in (H, A):
    for v in list(D["season"][ab].values()) + list((D["xg"].get(ab) or {}).values()) + [D["context"][ab]["rank"], D["context"][ab]["pts"], D["context"][ab]["gp"]]:
        if isinstance(v, (int, float)): vals.add(round(abs(float(v)), 3))
h = D["h2h"]
if h: vals |= {h["w"], h["d"], h["l"], h["gf"], h["ga"], len(h["events"])} | {int(e["date"][:4]) for e in h["events"]}
for ab in (H, A):
    if D["xg"].get(ab):
        exp = q(D["xg"][ab]["xg"] * D["season"][ab]["gp"], 1, "0.01"); vals |= {exp, round(abs(D["season"][ab]["gf"] - exp), 3)}
ok1 = ok2 = ok3 = True
for k in D["keys"]:
    ns = [v for _, v in k["nums"]]
    ok1 &= all(round(abs(float(v)), 3) in vals for v in ns)
    if k.get("perMatch"): ok2 &= near(k["gap"], abs(ns[0] - ns[1]), 0.006)
    allowed = vals | {round(float(k["gap"]), 3)}
    toks = [round(float(t_), 3) for t_ in re.findall(r"\d+(?:\.\d+)?", re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", k["text"]))]
    ok3 &= all(t_ in allowed for t_ in toks)
    if not all(t_ in allowed for t_ in toks): print("    untraced number in:", k["text"], [t_ for t_ in toks if t_ not in allowed])
check(f"{len(D['keys'])} keys, each citing 2 numbers", 3 <= len(D["keys"]) <= 6 and all(len(k["nums"]) == 2 for k in D["keys"]))
check("keys: every cited number is a computed or ESPN stat", ok1)
check("keys: per-match gaps = |a − b|", ok2)
check("keys: every number in the text traces to the stats", ok3)

print("live server (4276)")
try:
    with urllib.request.urlopen("http://127.0.0.1:4276/api/match", timeout=3) as r: check("/api/match serves match.json", json.load(r)["match"]["id"] == D["match"]["id"])
    for path in ("/", "/app.js", "/style.css", "/healthz"):
        with urllib.request.urlopen("http://127.0.0.1:4276" + path, timeout=3) as r: check(f"{path} served", r.status == 200)
except Exception as e:
    check("server reachable on 127.0.0.1:4276", False, str(e))

print("deliverables")
snap = P("dist", "chelsea-matchday-snapshot.html")
check("snapshot exists", os.path.exists(snap))
if os.path.exists(snap):
    h_ = open(snap, encoding="utf-8").read()
    check("snapshot inlines data + fonts", "window.__MATCH__=" in h_ and "data:font/ttf;base64," in h_)
    check("snapshot inlines research", "window.__RESEARCH__=" in h_)
    check("snapshot has no external script/css/font refs", not re.search(r'<script[^>]+src=|<link[^>]+stylesheet|url\("fonts/', h_))
    try:
        dom = subprocess.run(["nice", "-n", "10", "google-chrome", "--headless=new", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=3000", "--dump-dom", "file://" + snap],
                             capture_output=True, text=True, timeout=90).stdout
        dom = re.sub(r"<script\b.*?</script>", "", dom, flags=re.S)
        check("snapshot renders (data-ready=1)", 'data-ready="1"' in dom)
        check("rendered table has 20 rows", len(re.findall(r'<td class="rk">', dom)) == 20)
        check("rendered keys + audit (no mismatches)", dom.count('class="key"') == len(D["keys"]) and "✕ mismatch" not in dom and dom.count("✓ match") == sum(c["hard"] for c in D["checks"]))
    except Exception as e:
        check("headless render", False, str(e))
for s_ in ("00-best-home", "overview", "full", "mobile"):
    p_ = P("screenshots", s_ + ".png"); check(f"screenshot {s_}.png", os.path.exists(p_) and os.path.getsize(p_) > 20_000)
for f in ("README.md", "run.sh", "fetch.py", "build.py", "server.py", "export_static.py", "export_snapshot.py", "screenshot.sh", "render.sh"):
    check(f"{f} present", os.path.exists(P(f)))
rp = P("data", "research_notes.json")
check("research_notes.json present", os.path.exists(rp))
if os.path.exists(rp):
    rn = json.load(open(rp, encoding="utf-8"))
    check("research notes have sections from ij_*", bool(rn.get("sections")))


print(f"\n{passes} passed, {len(fails)} failed")
sys.exit(1 if fails else 0)
