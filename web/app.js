/* Chelsea Matchday wall: renders data/match.json (+ optional research notes).
   ESPN public soccer JSON + on-disk ij_* notes only. Nothing estimated; missing sections say so. */
(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const et = (iso, o) => new Date(iso).toLocaleString("en-US", Object.assign({ timeZone: "America/New_York" }, o || { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })) + " ET";
  const day = (iso, yr) => new Date(iso).toLocaleDateString("en-US", Object.assign({ timeZone: "America/New_York", day: "numeric", month: "short" }, yr ? { year: "numeric" } : {}));
  const f1 = (v) => (typeof v === "number" && Number.isInteger(v) ? v.toFixed(1) : v);
  const ord = (n) => n + (n % 100 >= 11 && n % 100 <= 13 ? "th" : { 1: "st", 2: "nd", 3: "rd" }[n % 10] || "th");
  const sgn = (n) => (n > 0 ? "+" + n : n < 0 ? "−" + Math.abs(n) : "0");
  const am = (n) => (n == null ? "" : n > 0 ? "+" + n : String(n));
  let D, H, A, C, R;

  function render(data, research) {
    D = data; R = research || null; H = D.match.home; A = D.match.away;
    C = { [H]: D.teams[H].color || "#1a5db8", [A]: D.teams[A].color || "#c62828" };
    document.documentElement.style.setProperty("--che", C[H]); document.documentElement.style.setProperty("--bou", C[A]);
    mast(); formstrip(); hero(); vibe(); lineup(); news(); keys(); table(); ctx(); line(); stats(); form(); h2h(); results(); leaders(); audit(); sources();
    document.body.dataset.ready = "1";
  }
  const nm = (ab) => D.teams[ab].short || D.teams[ab].name;

  function mast() {
    const m = D.match;
    const club = (ab, r) => `<div class="club ${r ? "r" : ""}">${r ? "" : crest(ab)}<div><div class="nm">${esc(D.teams[ab].name)}</div><div class="sub">${esc(ord(D.context[ab].rank))} · ${esc(D.teams[ab].record || "")} W-D-L · ${D.context[ab].pts} pts</div></div>${r ? crest(ab) : ""}</div>`;
    const kickEt = et(m.date, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    $("#mast").innerHTML = `<div class="kick"><span>Stamford Bridge · Night Wall</span><span>${esc(m.season || "Premier League")}</span><span>Data as of ${et(D.generatedAt)}</span></div>
      <div class="vs">${club(H, false)}<div class="mid"><div class="v">v</div><div class="when">${kickEt}</div>
      <div class="where">${esc(m.venue || "")}${m.city ? ", " + esc(m.city) : ""}</div>${(m.broadcasts || []).map((b) => `<span class="tv">${esc(b)}</span>`).join(" ")}</div>${club(A, true)}</div>`;
  }
  function crest(ab) { return `<div class="crest" style="background:${C[ab]}">${esc(ab)}</div>`; }

  function formstrip() {
    const strip = (ab) => {
      const L = D.last5[ab] || []; // oldest → newest so most recent is RIGHT
      if (!L.length) return `<div class="fs"><span class="lab" style="color:${C[ab]}">${esc(nm(ab))}</span><span class="info">No form in ESPN data</span></div>`;
      return `<div class="fs"><span class="lab" style="color:${C[ab]}">${esc(nm(ab))}</span>
        <div class="chips">${L.map((r) => `<div class="chip ${r.result}" title="${esc(r.oppName || r.opp)} · ${esc(r.score || "")}">${r.result}</div>`).join("")}</div>
        <span class="meta">last 5 · most recent right${D.teams[ab].form ? ` · ESPN ${esc(D.teams[ab].form)}` : ""}</span></div>`;
    };
    $("#formstrip").innerHTML = strip(H) + strip(A);
  }

  function hero() {
    const m = D.match, o = (D.odds || [])[0];
    const kick = et(m.date, { weekday: "long", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
    $("#hero").innerHTML = `<h2>Next fixture<span class="aside">Kick-off in America/New_York</span></h2>
      <div class="kick-big">${esc(kick)}</div>
      <div class="kick-sub">${esc(m.venue || "Venue n/a")} · ${esc((m.broadcasts || []).join(" · ") || "Broadcast not in ESPN data")} · ESPN event ${esc(m.id)}</div>
      <div class="row">
        <div class="pill"><em>Chelsea</em><b>${ord(D.context[H].rank)} · ${D.context[H].pts} pts</b></div>
        <div class="pill"><em>Bournemouth</em><b>${ord(D.context[A].rank)} · ${D.context[A].pts} pts</b></div>
        <div class="pill"><em>H2H (last ${D.h2h ? D.h2h.events.length : "—"})</em><b>${D.h2h ? `${D.h2h.w}W ${D.h2h.d}D ${D.h2h.l}L` : "n/a"}</b></div>
        ${o ? `<div class="pill"><em>Line · ${esc(o.provider)}</em><b>${esc(o.kind === "american" ? o.details : o.home)}</b></div>` : `<div class="pill"><em>The line</em><b>not in ESPN</b></div>`}
      </div>`;
  }

  function vibe() {
    const s = D.season[H], x = D.xg[H], c = D.context[H];
    const items = [
      { lab: "League pts", val: c.pts, max: 15, note: `${ord(c.rank)} of 20` },
      { lab: "Goals / match", val: s.gfpm, max: 3, note: `${s.gf} scored in ${s.gp}` },
      { lab: "Conceded / match", val: s.gapm, max: 3, note: `${s.ga} against`, invert: true },
      { lab: "Shot conversion", val: s.conv, max: 25, note: `${s.gf}/${s.shots}` },
    ];
    if (x) items.push({ lab: "xG / match", val: x.xg, max: 2.5, note: `xGA ${x.xga}` });
    const vibeTag = c.rank <= 4 ? "European pace" : c.rank <= 10 ? "Mid-table climb" : c.rank <= 17 ? "Looking over the shoulder" : "Relegation scrap";
    $("#vibe").innerHTML = `<h2>Season vibe<span class="aside">${esc(nm(H))} · ${s.gp} PL matches</span></h2>
      <div class="meter">${items.map((it) => {
        const pct = Math.max(4, Math.min(100, (Number(it.val) / it.max) * 100));
        return `<div class="m"><span>${esc(it.lab)}</span><div class="bar"><i style="width:${pct}%"></i></div><b>${esc(String(it.val))}</b></div>`;
      }).join("")}</div>
      <span class="tag">${esc(vibeTag)} · GD ${sgn(c.gd)} · ${c.ucl && c.ucl.gapBehind != null ? `${c.ucl.gapBehind} pts off top 4 (${c.ucl.abbr})` : "top-4 gap n/a"}</span>
      <div class="small" style="margin-top:8px">Tag is a label from table position only — not a prediction.</div>`;
  }

  function lineup() {
    const leaders = D.leaders[H] || [];
    const espnEmpty = !(D.injuries && D.injuries.available);
    let html = `<h2>Lineup board<span class="aside">Names from ESPN season leaders · XI not published</span></h2>`;
    html += `<div class="missing"><b>Starting XI missing</b>ESPN's public pre-match data has no confirmed starting lineup or bench for this fixture (empty rosters${espnEmpty ? "; injuries endpoint also empty" : ""}). Nothing invented below.</div>`;
    if (leaders.length) {
      html += `<div class="xi-grid" style="margin-top:12px">${leaders.map((l) => `<div class="namecard"><div class="cat">${esc(l.cat)}</div><div class="nm">${esc(l.name)}</div><div class="val">${esc(String(l.value).replace(/^Matches: \d+, /, ""))}</div></div>`).join("")}</div>`;
      html += `<div class="small" style="margin-top:8px">Board shows ESPN season leaders only — not today's XI.</div>`;
    } else {
      html += `<div class="info" style="margin-top:10px">ESPN lists no season leaders for ${esc(nm(H))}.</div>`;
    }
    $("#lineup").innerHTML = html;
  }

  function news() {
    const I = D.injuries;
    let html = `<h2>Team news<span class="aside">ESPN + ij_* research</span></h2>`;
    if (!I.available) {
      html += `<div class="missing"><b>ESPN injuries: none listed</b>Public ESPN data has no injury/suspension list for either club (0 items). That is not a clean bill of health.</div>`;
    } else {
      html += Object.entries(I.detail).map(([ab, v]) => `<div class="nw"><h4 style="color:${C[ab]}">${esc(D.teams[ab].name)}</h4>${(v.items || []).map((i) => `<div class="ldr">${esc(JSON.stringify(i))}</div>`).join("")}</div>`).join("");
    }
    if (R && R.sections && R.sections.length) {
      html += `<div class="small" style="margin:12px 0 6px;color:var(--gold)">${esc(R.label || "Research notes")}</div>`;
      R.sections.forEach((sec) => {
        html += `<div class="sec"><div class="srcf">${esc(sec.file)} · ${esc(sec.heading)}</div><ul>${(sec.bullets || []).map((b) => `<li>${esc(b.replace(/\*\*/g, ""))}</li>`).join("")}</ul>`;
        if (sec.urls && sec.urls.length) html += `<div class="src">${sec.urls.slice(0, 2).map((u) => `<a href="${esc(u)}" rel="noopener">${esc(u.replace(/^https?:\/\//, "").slice(0, 48))}…</a>`).join(" · ")}</div>`;
        html += `</div>`;
      });
    } else {
      html += `<div class="info" style="margin-top:10px">No on-disk ij_* research notes attached.</div>`;
    }
    $("#news").innerHTML = html;
  }

  function keys() {
    const f = (l, v, k) => (typeof v === "number" ? (/xG/.test(l) && !/total/.test(l) ? String(v) : k.perMatch ? f1(v) : v) : esc(v));
    $("#keys").innerHTML = `<h2>Keys to the match<span class="aside">Fixed rules · 6 biggest ESPN gaps · no predictions</span></h2>
      <div class="keys">${D.keys.map((k, i) => `<div class="key"><div class="n">${i + 1}</div><div><div class="t">${esc(k.title)}</div>
      <div class="nums">${k.nums.map(([l, v]) => `<span><em>${esc(l)}</em><b>${f(l, v, k)}</b></span>`).join("")}</div><div class="x">${esc(k.text)}</div></div></div>`).join("")}</div>`;
  }

  function table() {
    const rows = D.table.rows;
    const z = (r) => (r.note === "Champions League" ? "z-ucl" : r.note === "Europa League" ? "z-uel" : r.note === "Relegation" ? "z-rel" : "");
    $("#table").innerHTML = `<h2>Premier League table<span class="aside">${esc(D.table.season || "")} · ESPN · ${et(D.sources["standings.json"].fetchedAt)}</span></h2>
      <table class="lt"><tr><th>#</th><th class="tm">Club</th><th>P</th><th>W</th><th>D</th><th>L</th><th>GF</th><th>GA</th><th>GD</th><th>Pts</th></tr>
      ${rows.map((r, i) => { const hi = r.abbr === H || r.abbr === A; const cut = rows[i + 1] && rows[i + 1].note !== r.note && (r.note === "Relegation" || rows[i + 1].note === "Relegation" || (r.note && !rows[i + 1].note));
        return `<tr class="${z(r)} ${hi ? "hi" : ""} ${cut ? "cut" : ""}" style="--c:${hi ? C[r.abbr] : "transparent"}"><td class="rk">${r.rank}</td><td class="tm">${esc(r.team)}</td><td>${r.gp}</td><td>${r.w}</td><td>${r.d}</td><td>${r.l}</td><td>${r.gf}</td><td>${r.ga}</td><td>${sgn(r.gd)}</td><td class="pts">${r.pts}</td></tr>`; }).join("")}</table>
      <div class="legend"><span><i style="background:#2b6cb0"></i>Champions League</span><span><i style="background:#dd8a1e"></i>Europa League</span><span><i style="background:var(--loss)"></i>Relegation</span><span>(zones as ESPN marks them)</span></div>`;
  }

  function ctx() {
    const col = (ab) => { const c = D.context[ab]; const r = [];
      r.push(["Position", ord(c.rank)], ["Points (P" + c.gp + ")", c.pts], ["Points per match", c.ppg], ["Goal difference", sgn(c.gd)]);
      if (c.above) r.push([`Gap to ${ord(c.above.rank)} (${c.above.abbr})`, c.above.gap ? `−${c.above.gap} pts` : "level"]);
      if (c.below) r.push([`Lead over ${ord(c.below.rank)} (${c.below.abbr})`, c.below.gap ? `+${c.below.gap} pts` : "level"]);
      if (c.ucl && !c.ucl.inZone) r.push([`Gap to top 4 (${c.ucl.abbr})`, `−${c.ucl.gapBehind} pts`]);
      if (c.relegation && !c.relegation.inZone) r.push([`Above the drop (${ord(c.relegation.rank)} ${c.relegation.abbr})`, c.relegation.gapAbove ? `+${c.relegation.gapAbove} pts` : "level on pts"]);
      r.push([`Gap to leaders (${c.leader.abbr})`, `−${c.leader.gap} pts`]);
      return `<div><h4 style="color:${C[ab]}">${esc(D.teams[ab].name)}</h4>${r.map(([l, v]) => `<div class="r"><span>${esc(l)}</span><b>${esc(v)}</b></div>`).join("")}</div>`; };
    $("#ctx").innerHTML = `<h2>Table context</h2><div class="ctx">${col(H)}${col(A)}</div>`;
  }

  function line() {
    const O = D.odds || [];
    if (!O.length) { $("#line").innerHTML = `<h2>The line</h2><div class="info">ESPN's public data has no betting line for this match, so none is shown.</div>`; return; }
    $("#line").innerHTML = `<h2>The line<span class="aside">ESPN pre-match snapshot</span></h2>` + O.map((o) => o.kind === "american" ? `<div class="odds"><div class="p">${esc(o.provider)} · moneyline</div>
      <div class="row"><div><em>${esc(H)}</em><b>${am(o.homeML)}</b></div><div><em>Draw</em><b>${am(o.drawML)}</b></div><div><em>${esc(A)}</em><b>${am(o.awayML)}</b></div></div>
      <div class="ex">Total ${o.overUnder} goals: over ${am(o.overOdds)} / under ${am(o.underOdds)}${o.spread != null ? ` · Handicap ${esc(H)} ${o.spread} (${am(o.homeSpreadOdds)}), ${esc(A)} +${Math.abs(o.spread)} (${am(o.awaySpreadOdds)})` : ""}</div>
      <div class="src">Source: ${esc(o.source)}, fetched ${et(o.fetchedAt)}.</div></div>` : `<div class="odds"><div class="p">${esc(o.provider)} · full-time result (fractional)</div>
      <div class="row"><div><em>${esc(H)}</em><b>${esc(o.home)}</b></div><div><em>Draw</em><b>${esc(o.draw || "")}</b></div><div><em>${esc(A)}</em><b>${esc(o.away)}</b></div></div>
      ${o.goalLine ? `<div class="ex">Goal line ${esc(o.goalLine)}: over ${esc(o.goalLineOver || "")} / under ${esc(o.goalLineUnder || "")}</div>` : ""}
      <div class="src">Source: ${esc(o.source)}, fetched ${et(o.fetchedAt)}.</div></div>`).join("") + `<div class="src">Lines move; this is a snapshot. For information only. Sportsbook links left out.</div>`;
  }

  function stats() {
    const a = D.season[H], b = D.season[A], x = D.xg;
    const Rrows = [["Attack", null], ["Goals per match", "gfpm", 1, (s) => `${s.gf} in ${s.gp}`], ["Shots per match", "shotspm", 1, (s) => `${s.shots} total`], ["On target per match", "sotpm", 1, (s) => `${s.sot} total`],
      ["Shot conversion %", "conv", 1, (s) => `${s.gf} goals / ${s.shots} shots`], ["Possession % (avg)", "poss", 0, () => "mean of match figures"], ["Pass accuracy %", "passPct", 0, (s) => `${s.passAcc}/${s.pass}`],
      ["Corners per match", "cornerspm", 0, (s) => `${s.corners} total`], ["Defence", null], ["Conceded per match", "gapm", -1, (s) => `${s.ga} in ${s.gp}`], ["Shots faced per match", "shotsApm", -1, (s) => `${s.shotsA} total`],
      ["On target faced per match", "sotApm", -1, (s) => `${s.sotA} total`], ["Clean sheets", "cs", 1, (s) => `of ${s.gp}`], ["Discipline", null], ["Fouls per match", "foulspm", -1, (s) => `${s.fouls} total`], ["Yellow cards", "yc", -1, (s) => `${s.rc} red`]];
    let html = Rrows.map(([lab, k, dir, sub]) => { if (!k) return `<div class="st grp"><div>${lab}</div></div>`; const va = a[k], vb = b[k]; if (va == null || vb == null) return "";
      const tot = (va + vb) || 1, best = dir === 0 || va === vb ? 0 : (va > vb ? 1 : -1) * dir;
      const pm = /pm$/.test(k), fa = pm ? f1(va) : va, fb = pm ? f1(vb) : vb;
      return `<div class="st"><div class="v ${best > 0 ? "best" : ""}">${fa}<small>${esc(sub(a))}</small></div><div class="bar l"><i style="width:${(100 * va) / tot}%;background:${C[H]}"></i></div><div class="lab">${lab}</div><div class="bar r"><i style="width:${(100 * vb) / tot}%;background:${C[A]}"></i></div><div class="v r ${best < 0 ? "best" : ""}">${fb}<small>${esc(sub(b))}</small></div></div>`; }).join("");
    if (x[H] && x[A]) {
      html += `<div class="st grp"><div>Expected goals (ESPN season stats, per match)</div></div>` + [["xG per match", "xg", 1], ["xG against per match", "xga", -1], ["xG difference per match", "xgd", 1]].map(([lab, k, dir]) => {
        const va = x[H][k], vb = x[A][k], best = va === vb ? 0 : (va > vb ? 1 : -1) * dir, tot = Math.abs(va) + Math.abs(vb) || 1;
        return `<div class="st"><div class="v ${best > 0 ? "best" : ""}">${va}</div><div class="bar l"><i style="width:${(100 * Math.abs(va)) / tot}%;background:${C[H]}"></i></div><div class="lab">${lab}</div><div class="bar r"><i style="width:${(100 * Math.abs(vb)) / tot}%;background:${C[A]}"></i></div><div class="v r ${best < 0 ? "best" : ""}">${vb}</div></div>`; }).join("");
    } else html += `<div class="info" style="margin-top:8px">ESPN's public data has no xG for these clubs, so it's left out.</div>`;
    $("#stats").innerHTML = `<h2>Season stats, side by side<span class="aside"><b style="color:${C[H]}">${esc(D.teams[H].name)}</b> v <b style="color:${C[A]}">${esc(D.teams[A].name)}</b> · ${a.gp} league matches · ESPN box scores</span></h2>${html}
      <div class="small" style="margin-top:8px">xG from ESPN season team statistics. Underline = better of the two.</div>`;
  }

  function form() {
    const col = (ab) => { const L = D.last5[ab] || []; if (!L.length) return `<div class="fm"><h4>${esc(D.teams[ab].name)}</h4><div class="info">ESPN lists no recent matches.</div></div>`;
      const recent = [...L].reverse();
      return `<div class="fm"><h4 style="color:${C[ab]}">${esc(D.teams[ab].name)}</h4><div class="chips">${recent.map((r) => `<div class="chip ${r.result}" title="${esc(r.comp)}">${r.result}</div>`).join("")}<span class="info" style="align-self:center;font-size:11px;margin-left:6px">most recent first</span></div>
        ${recent.map((r) => `<div class="fr"><span>${day(r.date)}</span><span>${r.home ? "H" : "A"}</span><span><span class="o">${esc(r.oppName || r.opp)}</span> <span class="c">${esc(r.comp || "")}</span></span><span class="s">${r.us}–${r.them}</span><span class="${r.result} rs">${r.result}</span></div>`).join("")}</div>`; };
    $("#form").innerHTML = `<h2>Form guide: last 5<span class="aside">All competitions · ESPN pre-match</span></h2>${col(H)}<div style="height:12px"></div>${col(A)}`;
  }

  function h2h() {
    const h = D.h2h;
    if (!h || !h.events.length) { $("#h2h").innerHTML = `<h2>Head-to-head</h2><div class="info">ESPN's public data has no head-to-head history for this fixture, so none is shown.</div>`; return; }
    $("#h2h").innerHTML = `<h2>Head-to-head<span class="aside">${esc(h.label || "")} · ESPN · ${esc(nm(h.focus))}'s side</span></h2>
      <div class="h2hsum"><div><b style="color:${C[H]}">${h.w}</b><em>${esc(nm(H))} wins</em></div><div><b>${h.d}</b><em>Draws</em></div><div><b style="color:${C[A]}">${h.l}</b><em>${esc(nm(A))} wins</em></div><div><b>${h.gf}–${h.ga}</b><em>Goals</em></div></div>
      ${h.events.map((e) => `<div class="hr"><span class="info">${day(e.date, true)}${e.comp ? `<br><small>${esc(e.comp)}</small>` : ""}</span><span class="a"><b style="color:${C[e.home] || "inherit"}">${esc(e.home)}</b></span><span class="s">${e.hs}–${e.as}</span><span><b style="color:${C[e.away] || "inherit"}">${esc(e.away)}</b></span></div>`).join("")}
      <div class="src">ESPN summary: "${esc(h.espnSummary || "")}" (W-L-D).</div>`;
  }

  function results() {
    const col = (ab) => `<div class="res"><h4 style="color:${C[ab]}">${esc(D.teams[ab].name)}</h4><table><tr><th>Date</th><th>Opponent</th><th>Score</th><th>Shots</th><th>Opp shots</th><th>Poss %</th></tr>
      ${[...D.matches[ab]].reverse().map((m) => `<tr><td>${day(m.date)}</td><td>${m.home ? "v" : "@"} ${esc(m.oppName)}</td><td class="${m.result} rs">${m.result} ${m.us}–${m.them}</td><td>${m.shots} (${m.sot})</td><td>${m.oppShots}</td><td>${m.poss}</td></tr>`).join("")}</table></div>`;
    $("#results").innerHTML = `<h2>League results<span class="aside">ESPN box scores · shots (on target)</span></h2>${col(H)}<div style="height:12px"></div>${col(A)}`;
  }

  function leaders() {
    const col = (ab) => `<div class="ld"><h4 style="color:${C[ab]}">${esc(nm(ab))}</h4>${(D.leaders[ab] || []).map((l) => `<div class="ldr"><span class="c">${esc(l.cat)}</span><span class="n">${esc(l.name)}</span><span class="v">${esc(String(l.value).replace(/^Matches: \d+, /, ""))}</span></div>`).join("") || '<div class="info">None in ESPN data</div>'}</div>`;
    $("#leaders").innerHTML = `<h2>Top performers<span class="aside">ESPN season leaders</span></h2><div class="ld2">${col(H)}${col(A)}</div>`;
  }

  function audit() {
    const hard = D.checks.filter((c) => c.hard), ok = hard.filter((c) => c.ok).length;
    const tbl = (ab) => `<table><tr><th style="color:${C[ab]}">${esc(ab)}</th><th>Our sum</th><th>ESPN</th><th></th></tr>${D.checks.filter((c) => c.team === ab).map((c) => `<tr><td>${esc(c.label)} <span class="info">· ${esc(c.source)}</span></td><td>${c.ours}</td><td>${c.espn ?? "n/a"}</td><td>${c.hard ? (c.ok ? '<span class="ok">✓ match</span>' : '<span class="bad">✕ mismatch</span>') : '<span class="info">info</span>'}</td></tr>`).join("")}</table>`;
    $("#audit").innerHTML = `<h2>Programme audit<span class="aside">${ok}/${hard.length} hard checks match</span></h2><div class="au">${tbl(H)}${tbl(A)}</div>
      <div class="small" style="margin-top:6px">Box-score sums vs ESPN standings / season stats / pre-match. Possession is info-only.</div>`;
  }

  function sources() {
    const S = D.sources, list = Object.entries(S).filter(([k]) => !/^match_/.test(k));
    const nM = Object.keys(S).filter((k) => /^match_/.test(k)).length;
    $("#sources").innerHTML = `<b>Sources (ESPN public JSON, eng.1):</b> ${list.map(([k, v]) => `${esc(k.replace(".json", ""))} <code>${esc(v.url)}</code> (${et(v.fetchedAt)})`).join("; ")}; plus ${nM} match summaries in data/raw/manifest.json.
      ${R ? `Research notes: ${esc(R.generatedNote || "")} from ${(R.sections || []).map((s) => esc(s.file)).join(", ")}.` : ""}
      ESPN match page: <a href="${esc(D.match.espnPage)}">${esc(D.match.espnPage)}</a>. Nothing estimated; missing fields labelled. Built ${et(D.generatedAt)}. Not affiliated with the Premier League, ESPN, any bookmaker or either club.`;
  }

  function fail(m) { document.getElementById("page").insertAdjacentHTML("afterbegin", `<div class="panel" style="border-color:var(--loss)"><b>Match data unavailable.</b> ${esc(m)}</div>`); document.body.dataset.ready = "error"; }

  function boot(match, research) {
    try { render(match, research); } catch (e) { fail(e.message); console.error(e); }
  }

  if (window.__MATCH__) {
    boot(window.__MATCH__, window.__RESEARCH__ || null);
  } else {
    Promise.all([
      fetch("/api/match").then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))),
      fetch("/api/research").then((r) => (r.ok ? r.json() : null)).catch(() => null),
    ]).then(([m, res]) => boot(m, res)).catch((e) => fail(e.message));
  }
})();
