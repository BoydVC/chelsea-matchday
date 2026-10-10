#!/usr/bin/env python3
"""Compile data/match.json for the Chelsea matchday programme from data/raw (no network).
Season stats are summed from ESPN's per-match box scores and cross-checked against ESPN's season team statistics,
the league table and the pre-match summary. Optional sections (xG, head-to-head, injuries, betting lines) appear
only if ESPN's public data has them. Keys to the match come from fixed rules over the stat gaps. Nothing invented."""
import json, os
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "data", "raw")
ET = ZoneInfo("America/New_York")
J = lambda n: json.load(open(os.path.join(RAW, n), encoding="utf-8"))
FOCUS = "CHE"


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def g1(x):  # per-match figure: always at least one decimal (2.0, 2.4, 1.351)
    return f"{x:.1f}" if float(x) * 10 == int(float(x) * 10) else f"{x:g}"


def q(num, den=1, places="0.1"):
    return float((Decimal(str(num)) / Decimal(str(den))).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def sv(stats, name):
    return {s["name"]: s for s in stats}.get(name)


def standings():
    s = J("standings.json")
    ch = s["children"][0]
    rows = []
    for en in ch["standings"]["entries"]:
        st = {x["name"]: x.get("value") for x in en["stats"]}
        t = en["team"]
        rows.append({"rank": int(st["rank"]), "team": t.get("displayName"), "short": t.get("shortDisplayName"), "abbr": t.get("abbreviation"), "id": t.get("id"),
                     "gp": int(st["gamesPlayed"]), "w": int(st["wins"]), "d": int(st["ties"]), "l": int(st["losses"]), "gf": int(st["pointsFor"]),
                     "ga": int(st["pointsAgainst"]), "gd": int(st["pointDifferential"]), "pts": int(st["points"]), "note": (en.get("note") or {}).get("description"),
                     "noteColor": (en.get("note") or {}).get("color")})
    rows.sort(key=lambda r: r["rank"])
    return {"season": ch.get("name"), "rows": rows}


def table_context(ab, rows):
    me = next(r for r in rows if r["abbr"] == ab)
    i = rows.index(me)
    zones = {}
    for r in rows:
        if r["note"]: zones.setdefault(r["note"], []).append(r["rank"])
    ctx = {"rank": me["rank"], "pts": me["pts"], "gp": me["gp"], "gd": me["gd"], "ppg": q(me["pts"], me["gp"], "0.01") if me["gp"] else None}
    if i > 0: ctx["above"] = {"abbr": rows[i - 1]["abbr"], "rank": rows[i - 1]["rank"], "gap": rows[i - 1]["pts"] - me["pts"]}
    if i < len(rows) - 1: ctx["below"] = {"abbr": rows[i + 1]["abbr"], "rank": rows[i + 1]["rank"], "gap": me["pts"] - rows[i + 1]["pts"]}
    ctx["leader"] = {"abbr": rows[0]["abbr"], "gap": rows[0]["pts"] - me["pts"]}
    rel = zones.get("Relegation")
    if rel:
        top_rel = min(rel); r18 = rows[top_rel - 1]
        ctx["relegation"] = {"rank": top_rel, "abbr": r18["abbr"], "gapAbove": me["pts"] - r18["pts"]} if me["rank"] < top_rel else {"inZone": True}
    ucl = zones.get("Champions League")
    if ucl:
        last = max(ucl); rr = rows[last - 1]
        ctx["ucl"] = {"rank": last, "abbr": rr["abbr"], "gapBehind": rr["pts"] - me["pts"]} if me["rank"] > last else {"inZone": True}
    return ctx


def season_from_matches(ab):
    """Sum ESPN per-match box scores for every completed league match in the club's eng.1 schedule."""
    T = {k: 0 for k in ["gp", "w", "d", "l", "gf", "ga", "shots", "sot", "shotsA", "sotA", "corners", "fouls", "yc", "rc", "saves", "pass", "passAcc", "cs"]}
    poss, matches = [], []
    for e in J(f"schedule_{ab}.json")["events"]:
        c = e["competitions"][0]
        if not c["status"]["type"].get("completed"):
            continue
        m = J(f"match_{e['id']}.json")
        comp = m["header"]["competitions"][0]
        cs = {x["team"]["abbreviation"]: x for x in comp["competitors"]}
        op = [k for k in cs if k != ab][0]
        us, them = int(cs[ab]["score"]), int(cs[op]["score"])
        S = {t["team"]["abbreviation"]: {x["name"]: x.get("displayValue") for x in t["statistics"]} for t in m["boxscore"]["teams"]}
        me, oo = S[ab], S[op]
        T["gp"] += 1; T["gf"] += us; T["ga"] += them
        T["w" if us > them else "d" if us == them else "l"] += 1
        T["cs"] += 1 if them == 0 else 0
        T["shots"] += int(me["totalShots"]); T["sot"] += int(me["shotsOnTarget"]); T["shotsA"] += int(oo["totalShots"]); T["sotA"] += int(oo["shotsOnTarget"])
        T["corners"] += int(me["wonCorners"]); T["fouls"] += int(me["foulsCommitted"]); T["yc"] += int(me["yellowCards"]); T["rc"] += int(me["redCards"])
        T["saves"] += int(me["saves"]); T["pass"] += int(me["totalPasses"]); T["passAcc"] += int(me["accuratePasses"])
        poss.append(Decimal(me["possessionPct"]))
        matches.append({"id": e["id"], "date": comp["date"], "opp": op, "oppName": cs[op]["team"].get("displayName"), "home": cs[ab]["homeAway"] == "home",
                        "us": us, "them": them, "result": "W" if us > them else "D" if us == them else "L",
                        "shots": int(me["totalShots"]), "sot": int(me["shotsOnTarget"]), "poss": float(me["possessionPct"]), "oppShots": int(oo["totalShots"])})
    g = T["gp"] or 1
    T["poss"] = float((sum(poss) / len(poss)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)) if poss else None
    T.update({"pts": 3 * T["w"] + T["d"], "gd": T["gf"] - T["ga"], "gfpm": q(T["gf"], g, "0.01"), "gapm": q(T["ga"], g, "0.01"),
              "shotspm": q(T["shots"], g), "sotpm": q(T["sot"], g), "shotsApm": q(T["shotsA"], g), "sotApm": q(T["sotA"], g),
              "passPct": q(100 * T["passAcc"], T["pass"]) if T["pass"] else None, "cornerspm": q(T["corners"], g), "foulspm": q(T["fouls"], g),
              "ycpm": q(T["yc"], g, "0.01"), "conv": q(100 * T["gf"], T["shots"]) if T["shots"] else None})
    matches.sort(key=lambda r: r["date"])
    return T, matches


def core_stats(ab):
    out = {}
    for cat in J(f"teamstats_{ab}.json")["splits"]["categories"]:
        for s in cat["stats"]:
            out.setdefault(s["name"], s.get("value"))
    return out


def checks_for(ab, T, core, row, pre_box, rec):
    C = []
    def add(label, ours, espn, src, hard=True):
        ok = espn is not None and abs(float(ours) - float(espn)) < 0.051
        C.append({"team": ab, "label": label, "ours": ours, "espn": espn, "source": src, "hard": hard, "ok": ok if hard else None})
    # vs league table
    for lab, k, rk in [("Matches played", "gp", "gp"), ("Wins", "w", "w"), ("Draws", "d", "d"), ("Losses", "l", "l"), ("Goals for", "gf", "gf"),
                       ("Goals against", "ga", "ga"), ("Goal difference", "gd", "gd"), ("Points", "pts", "pts")]:
        add(lab, T[k], row[rk], "league table")
    # vs ESPN season team statistics
    for lab, k, ck in [("Goals for", "gf", "totalGoals"), ("Goals against", "ga", "goalsConceded"), ("Shots", "shots", "totalShots"), ("Shots on target", "sot", "shotsOnTarget"),
                       ("Shots faced", "shotsA", "shotsFaced"), ("Corners won", "corners", "wonCorners"), ("Fouls committed", "fouls", "foulsCommitted"),
                       ("Yellow cards", "yc", "yellowCards"), ("Red cards", "rc", "redCards"), ("Saves", "saves", "saves"), ("Passes", "pass", "totalPasses"),
                       ("Accurate passes", "passAcc", "accuratePasses"), ("Clean sheets", "cs", "cleanSheet"), ("Wins", "w", "wins"), ("Matches", "gp", "appearances")]:
        add(lab, T[k], core.get(ck), "season stats")
    # vs the pre-match summary
    add("Goals for", T["gf"], (pre_box.get("totalGoals") or {}).get("displayValue"), "pre-match summary")
    add("Goals against", T["ga"], (pre_box.get("goalsConceded") or {}).get("displayValue"), "pre-match summary")
    add("Goal difference", T["gd"], (pre_box.get("goalDifference") or {}).get("displayValue"), "pre-match summary")
    if rec: add("Points", T["pts"], rec.get("points"), "pre-match summary")
    # xG internal consistency (xG itself cannot be re-derived from match box scores)
    if core.get("avgExpectedGoals") is not None and core.get("avgExpectedGoalsConceded") is not None:
        add("xG diff/match = xG − xGA", round(core["avgExpectedGoals"] - core["avgExpectedGoalsConceded"], 3), round(core.get("avgExpectedGoalDifferential"), 3), "season stats")
    # information only (not equal by construction)
    if T["poss"] is not None:
        add("Possession % (mean of match figures)", T["poss"], round(core.get("possessionPct"), 1) if core.get("possessionPct") is not None else None, "season stats", hard=False)
    return C


def last_five(pre, ab):
    for t in pre.get("lastFiveGames", []):
        if t["team"]["abbreviation"] != ab:
            continue
        out = []
        for e in t["events"]:
            hs, as_ = e.get("homeTeamScore"), e.get("awayTeamScore")
            home = e.get("atVs") == "vs"
            us, them = (hs, as_) if home else (as_, hs)
            out.append({"id": e.get("id"), "date": e.get("gameDate"), "comp": e.get("leagueName"), "compAbbr": e.get("leagueAbbreviation"), "home": home,
                        "opp": (e.get("opponent") or {}).get("abbreviation"), "oppName": (e.get("opponent") or {}).get("displayName"),
                        "us": int(us) if us not in (None, "") else None, "them": int(them) if them not in (None, "") else None, "result": e.get("gameResult"),
                        "score": e.get("score")})
        out.sort(key=lambda r: r["date"] or "")
        return out
    return []


def h2h(pre):
    ss = (pre.get("seasonseries") or [])
    if not ss:
        return None
    s = ss[0]; ev = []
    for e in s.get("events", []):
        cs = {c["homeAway"]: c for c in e.get("competitors", [])}
        if not cs: continue
        ev.append({"id": e.get("id"), "date": e.get("date"), "comp": e.get("competitionName"), "home": cs["home"]["team"]["abbreviation"],
                   "away": cs["away"]["team"]["abbreviation"], "hs": int(cs["home"]["score"]), "as": int(cs["away"]["score"]),
                   "status": (e.get("statusType") or {}).get("detail")})
    w = d = l = gf = ga = 0
    for e in ev:
        us, them = (e["hs"], e["as"]) if e["home"] == FOCUS else (e["as"], e["hs"])
        gf += us; ga += them
        if us > them: w += 1
        elif us == them: d += 1
        else: l += 1
    return {"title": s.get("title"), "espnSummary": s.get("summary"), "label": s.get("shortSummary"), "events": ev,
            "focus": FOCUS, "w": w, "d": d, "l": l, "gf": gf, "ga": ga}


def odds(pre, src):
    out = []
    for p in pre.get("pickcenter") or []:
        o = {"provider": (p.get("provider") or {}).get("name"), "kind": "american", "details": p.get("details"),
             "homeML": (p.get("homeTeamOdds") or {}).get("moneyLine"), "awayML": (p.get("awayTeamOdds") or {}).get("moneyLine"),
             "drawML": (p.get("drawOdds") or {}).get("moneyLine"), "overUnder": p.get("overUnder"), "overOdds": p.get("overOdds"), "underOdds": p.get("underOdds"),
             "spread": p.get("spread"), "homeSpreadOdds": (p.get("homeTeamOdds") or {}).get("spreadOdds"), "awaySpreadOdds": (p.get("awayTeamOdds") or {}).get("spreadOdds"),
             "source": "ESPN pre-match summary (pickcenter)"}
        out.append({k: v for k, v in o.items() if v is not None})
    seen = {o["provider"] for o in out}
    for p in pre.get("odds") or []:
        name = (p.get("provider") or {}).get("name")
        if name in seen: continue
        to = ((p.get("bettingOdds") or {}).get("teamOdds") or {})
        o = {"provider": name, "kind": "fractional",
             "home": ((p.get("homeTeamOdds") or {}).get("odds") or {}).get("summary"), "away": ((p.get("awayTeamOdds") or {}).get("odds") or {}).get("summary"),
             "draw": (p.get("drawOdds") or {}).get("summary"), "goalLine": (to.get("preMatchOverUnderHandicap") or {}).get("value"),
             "goalLineOver": (to.get("preMatchGoalLineOver") or {}).get("value"), "goalLineUnder": (to.get("preMatchGoalLineUnder") or {}).get("value"),
             "source": "ESPN pre-match summary (odds)"}
        o = {k: v for k, v in o.items() if v is not None}
        if o.get("home") or o.get("away"): out.append(o)
    for o in out: o.update({"url": src["url"], "fetchedAt": src["fetchedAt"]})
    return out


def leaders(pre):
    out = {}
    for L in pre.get("leaders", []):
        ab = L["team"]["abbreviation"]; out[ab] = []
        for c in L.get("leaders", []):
            if c.get("leaders"):
                x = c["leaders"][0]
                out[ab].append({"cat": c.get("displayName"), "name": x["athlete"].get("displayName"), "value": x.get("displayValue")})
    return out


def keys(H, A, S, X, ctx, h, last5):
    a, b = S[H], S[A]; K = []
    def unit(title, x, xl, y, yl, unit_, off, de, scale=None):
        gap = round(abs(x - y), 2); rel = gap / max(abs(x), abs(y), 0.01)
        if y != x:
            verdict = f"{de} {'concede' if 'goal' in unit_ else 'allow'}s {g1(gap)} {'fewer' if y < x else 'more'} {unit_} per match than {off} {'score' if 'goal' in unit_ else 'produce'}s."
        else:
            verdict = f"Even: {de} allows exactly what {off} produces."
        K.append({"title": title, "rel": round(rel, 3), "gap": gap, "nums": [[xl, x], [yl, y]], "perMatch": True, "text": f"{xl}: {g1(x)}/match. {yl}: {g1(y)}/match. {verdict}"})
    unit(f"{H} attack vs. {A} defence", a["gfpm"], f"{H} goals scored", b["gapm"], f"{A} goals conceded", "goals", H, A)
    unit(f"{A} attack vs. {H} defence", b["gfpm"], f"{A} goals scored", a["gapm"], f"{H} goals conceded", "goals", A, H)
    unit(f"{H} shots vs. {A} shots allowed", a["shotspm"], f"{H} shots", b["shotsApm"], f"{A} shots faced", "shots", H, A)
    unit(f"{A} shots vs. {H} shots allowed", b["shotspm"], f"{A} shots", a["shotsApm"], f"{H} shots faced", "shots", A, H)
    unit(f"{H} on target vs. {A}", a["sotpm"], f"{H} shots on target", b["sotApm"], f"{A} on-target shots faced", "shots on target", H, A)
    unit(f"{A} on target vs. {H}", b["sotpm"], f"{A} shots on target", a["sotApm"], f"{H} on-target shots faced", "shots on target", A, H)
    if X.get(H) and X.get(A):
        unit(f"{H} xG vs. {A} xG against", X[H]["xg"], f"{H} xG", X[A]["xga"], f"{A} xG against", "xG", H, A)
        unit(f"{A} xG vs. {H} xG against", X[A]["xg"], f"{A} xG", X[H]["xga"], f"{H} xG against", "xG", A, H)
        for ab in (H, A):
            exp = q(X[ab]["xg"] * S[ab]["gp"], 1, "0.01"); diff = round(S[ab]["gf"] - exp, 2)
            K.append({"title": f"{ab} finishing vs. xG", "rel": round(min(1, abs(diff) / max(exp, 0.01)), 3), "gap": abs(diff),
                      "nums": [[f"{ab} goals", S[ab]["gf"]], [f"{ab} xG total (xG/match × {S[ab]['gp']})", exp]],
                      "text": f"{ab} have scored {S[ab]['gf']} from {exp:g} xG ({X[ab]['xg']:g}/match × {S[ab]['gp']} matches): {abs(diff):g} goals {'above' if diff > 0 else 'below'} xG."})
    pa, pb = ctx[H]["pts"], ctx[A]["pts"]
    K.append({"title": "League table", "rel": round(abs(pa - pb) / max(pa, pb, 1), 3), "gap": abs(pa - pb), "nums": [[f"{H} points", pa], [f"{A} points", pb]],
              "text": f"{H}: {ordinal(ctx[H]['rank'])}, {pa} pts from {ctx[H]['gp']}. {A}: {ordinal(ctx[A]['rank'])}, {pb} pts from {ctx[A]['gp']}. Gap: {abs(pa - pb)} pts, {H if pa > pb else A} ahead."})
    ya, yb = a["yc"], b["yc"]
    K.append({"title": "Discipline", "rel": round(abs(ya - yb) / max(ya, yb, 1), 3), "gap": abs(ya - yb), "nums": [[f"{H} yellow cards", ya], [f"{A} yellow cards", yb]],
              "text": f"{H}: {ya} yellows, {a['fouls']} fouls. {A}: {yb} yellows, {b['fouls']} fouls (league matches). {A if yb > ya else H} have {abs(ya - yb)} more yellows."})
    if h and (h["w"] + h["d"] + h["l"]):
        n = h["w"] + h["d"] + h["l"]
        K.append({"title": "Head-to-head", "rel": round(abs(h["w"] - h["l"]) / n, 3), "gap": abs(h["w"] - h["l"]), "nums": [[f"{H} wins", h["w"]], [f"{A} wins", h["l"]]],
                  "text": f"Last {n} meetings ({h['events'][-1]['date'][:4]}–{h['events'][0]['date'][:4]}, per ESPN): {H} {h['w']} W, {h['d']} D, {h['l']} L; goals {h['gf']}–{h['ga']}."})
    K.sort(key=lambda k: -k["rel"])
    return K[:6], K


def main():
    man = json.load(open(os.path.join(RAW, "manifest.json")))
    pre = J("pregame.json"); src = man["files"]["pregame.json"]
    comp = pre["header"]["competitions"][0]
    cs = {c["homeAway"]: c for c in comp["competitors"]}
    H, A = cs["home"]["team"]["abbreviation"], cs["away"]["team"]["abbreviation"]
    tab = standings()
    pre_box = {t["team"]["abbreviation"]: {s["name"]: s for s in t.get("statistics", [])} for t in pre.get("boxscore", {}).get("teams", [])}
    teams, S, M, X, ctx, checks = {}, {}, {}, {}, {}, []
    for ha, c in cs.items():
        t = c["team"]; ab = t["abbreviation"]
        recs = {r.get("type"): r.get("displayValue") for r in c.get("record", [])}
        teams[ab] = {"abbr": ab, "name": t.get("displayName"), "short": t.get("shortDisplayName"), "color": "#" + t.get("color", "777777"),
                     "alt": "#" + t.get("alternateColor", "ffffff"), "homeAway": ha, "record": recs.get("total"), "points": recs.get("points"), "form": c.get("form")}
        S[ab], M[ab] = season_from_matches(ab)
        core = core_stats(ab)
        if core.get("avgExpectedGoals") is not None:
            X[ab] = {"xg": round(core["avgExpectedGoals"], 3), "xga": round(core["avgExpectedGoalsConceded"], 3), "xgd": round(core["avgExpectedGoalDifferential"], 3)}
        row = next(r for r in tab["rows"] if r["abbr"] == ab)
        ctx[ab] = table_context(ab, tab["rows"])
        checks += checks_for(ab, S[ab], core, row, pre_box.get(ab, {}), {"points": recs.get("points")})
    L5 = {ab: last_five(pre, ab) for ab in (H, A)}
    hh = h2h(pre)
    inj = {}
    for ab in (H, A):
        items = J(f"injuries_{ab}.json").get("items", [])
        roster_inj = [a.get("displayName") for a in J(f"team_{ab}.json")["team"].get("athletes", []) if a.get("injuries")]
        statuses = sorted({(a.get("status") or {}).get("name") for a in J(f"team_{ab}.json")["team"].get("athletes", []) if a.get("status")})
        inj[ab] = {"items": items, "rosterFlags": roster_inj, "rosterStatuses": statuses}
    inj_avail = any(v["items"] or v["rosterFlags"] for v in inj.values()) or bool(pre.get("injuries"))
    K, allK = keys(H, A, S, X, ctx, hh, L5)
    gi = pre.get("gameInfo", {})
    out = {"generatedAt": datetime.now(ET).isoformat(timespec="seconds"), "focus": FOCUS,
           "match": {"id": man["event"], "date": comp.get("date"), "home": H, "away": A, "status": comp["status"]["type"].get("detail"),
                     "venue": (gi.get("venue") or {}).get("fullName"), "city": ", ".join(x for x in [((gi.get("venue") or {}).get("address") or {}).get("city"), ((gi.get("venue") or {}).get("address") or {}).get("country")] if x),
                     "broadcasts": [b.get("media", {}).get("shortName") for b in pre.get("broadcasts", []) if b.get("media")],
                     "season": pre["header"].get("season", {}).get("name"), "espnPage": f"https://www.espn.com/soccer/match/_/gameId/{man['event']}"},
           "teams": teams, "table": tab, "context": ctx, "season": S, "matches": M, "xg": X, "checks": checks, "last5": L5, "h2h": hh,
           "injuries": {"available": inj_avail, "detail": inj}, "odds": odds(pre, src), "leaders": leaders(pre), "keys": K, "allKeys": allK,
           "sources": man["files"]}
    p = os.path.join(HERE, "data", "match.json")
    json.dump(out, open(p + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":")); os.replace(p + ".tmp", p)
    bad = [c for c in checks if c["hard"] and not c["ok"]]
    print(f"match.json: {A} @ {H}; {sum(1 for c in checks if c['hard'])} hard checks, {len(bad)} mismatches; xG {'yes' if X else 'no'}; "
          f"h2h {len(hh['events']) if hh else 0}; odds {len(out['odds'])}; injuries {'yes' if inj_avail else 'none in ESPN data'}; {os.path.getsize(p)//1024} KB")
    for c in bad: print("  MISMATCH", c)


if __name__ == "__main__":
    main()
