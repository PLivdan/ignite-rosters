/* Ignite Stage 2 power ranking.
   Teams get ordinal placements, not tiers: 1..N within EU, 1..N within NA, and
   1..N globally, kept as three independent orders. No framework and no backend
   so it runs off GitHub Pages and survives a stream with no network. */
(() => {
"use strict";

const MODES = ["EU", "NA", "GLOBAL"];
const ROLES = [["DPS", "Duelist"], ["Tank", "Vanguard"], ["Support", "Strategist"]];
const RANKS = ["S", "A", "B", "C", "D", "F"];
const RANK_VAL = { S: 6, A: 5, B: 4, C: 3, D: 2, F: 1 };
const KEY = "ignite-s2-board-v2";

let DATA = null, S = null, sel = null, mode = "GLOBAL";

/* ---------- state ---------- */
function freshState() {
  const rosters = {};
  for (const t of DATA.teams) {
    const slots = [];
    for (const [role] of ROLES) {
      const inRole = t.roster.filter(p => p.status === "main" && p.role === role);
      for (let i = 0; i < 2; i++) {
        const p = inRole[i];
        slots.push({ role, name: p ? p.name : "",
                     status: p ? "confirmed" : "open", rank: null });
      }
    }
    const extra = t.roster.filter(p => p.status === "main" &&
      !slots.some(s => s.name === p.name));
    const map = p => ({ role: p.role, name: p.name, status: "confirmed", rank: null });
    rosters[t.id] = {
      slots, extra: extra.map(map),
      subs: t.roster.filter(p => p.status === "sub").map(map),
      staff: t.roster.filter(p => p.status === "staff").map(map),
    };
  }
  return { order: { EU: [], NA: [], GLOBAL: [] }, rosters, log: [] };
}

const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} };

function load() {
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || "null");
    if (!s || !s.rosters || !s.order) return null;
    const fresh = freshState();
    for (const t of DATA.teams) if (!s.rosters[t.id]) s.rosters[t.id] = fresh.rosters[t.id];
    // Teams dropped from data.json must leave every order, or render() throws.
    const known = new Set(DATA.teams.map(t => t.id));
    for (const k of Object.keys(s.rosters)) if (!known.has(k)) delete s.rosters[k];
    for (const m of MODES) s.order[m] = (s.order[m] || []).filter(id => known.has(id));
    return s;
  } catch (e) { return null; }
}

const team = id => DATA.teams.find(t => t.id === id);
const inScope = id => mode === "GLOBAL" || team(id).region === mode;
const scopeIds = () => DATA.teams.filter(t => inScope(t.id)).map(t => t.id);
const order = () => S.order[mode];
const poolIds = () => scopeIds().filter(id => !order().includes(id));

function teamAvg(id) {
  const rated = S.rosters[id].slots.filter(p => p.name && p.rank);
  if (!rated.length) return null;
  const mean = rated.reduce((a, p) => a + RANK_VAL[p.rank], 0) / rated.length;
  return { letter: RANKS[Math.round(6 - mean)] ?? "F", mean, n: rated.length };
}

const nextRank = r => RANKS[RANKS.indexOf(r) + 1] ?? (r == null ? "S" : null);
const esc = s => String(s == null ? "" : s).replace(/&/g, "&amp;")
  .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function logChange(teamId, from, to) {
  S.log.unshift({ t: new Date().toTimeString().slice(0, 5),
                  team: team(teamId).short || team(teamId).name,
                  from: from || "(open)", to: to || "(cleared)" });
  S.log = S.log.slice(0, 60);
}

/* ---------- board ---------- */
function pips(id) {
  return S.rosters[id].slots.map(s =>
    `<i class="pip ${!s.name ? "empty" : s.status === "leaked" ? "leak" : ""}"></i>`).join("");
}

function rowCard(id, place) {
  const t = team(id), a = teamAvg(id);
  return `<li class="rank-row${sel === id ? " sel" : ""}" draggable="true" data-id="${id}">
    <span class="place">${place}</span>
    <img src="${t.logo}" alt="">
    <span class="rname">${esc(t.name)}</span>
    ${mode === "GLOBAL" ? `<span class="reg">${t.region === "EU" ? "EMEA" : "AM"}</span>` : ""}
    <span class="pips">${pips(id)}</span>
    ${a ? `<span class="avg" data-t="${a.letter}" title="Players average ${a.mean.toFixed(1)}">${a.letter}</span>`
        : `<span class="avg none">–</span>`}
    <span class="grip" title="Drag to reorder">⠿</span>
  </li>`;
}

function poolCard(id) {
  const t = team(id), a = teamAvg(id);
  return `<div class="team${sel === id ? " sel" : ""}" draggable="true" data-id="${id}"
               title="${esc(t.name)}">
    ${a ? `<span class="avg" data-t="${a.letter}">${a.letter}</span>` : ""}
    <img src="${t.logo}" alt="">
    <div class="nm">${esc(t.short || t.name)}</div>
    <div class="pips">${pips(id)}</div>
  </div>`;
}

function renderBoard() {
  const list = order(), pool = poolIds();
  const label = mode === "GLOBAL" ? "Global" : mode === "EU" ? "EMEA" : "Americas";
  document.getElementById("board").innerHTML = `
    <div class="board-head">
      <h2>${label} power ranking</h2>
      <div class="board-tools">
        ${mode === "GLOBAL" ? `<button class="tool sm" id="seed">Seed from EU + NA</button>` : ""}
        <button class="tool sm" id="sortrated">Order by player rating</button>
        <button class="tool sm" id="clearorder">Clear</button>
      </div>
    </div>
    <ol class="ranking" id="ranking">
      ${list.map((id, i) => rowCard(id, i + 1)).join("")}
      ${list.length ? "" : `<li class="drop-hint">Drag teams up from below to start ranking.</li>`}
    </ol>
    <div class="pool-wrap">
      <p class="pool-title">Unranked — ${pool.length} team${pool.length === 1 ? "" : "s"}</p>
      <div class="pool" id="pool">${pool.map(poolCard).join("")}</div>
    </div>`;
  wireDnd();
}

/* ---------- roster panel ---------- */
function rowHtml(teamId, kind, i, s) {
  const open = !s.name;
  const cls = s.status === "leaked" ? "leak" : open ? "empty" : "";
  const label = open ? "open" : s.status;
  const rk = s.rank || "";
  return `<div class="row ${cls}">
    <button class="rank${rk ? "" : " unrated"}" data-t="${rk}" data-team="${teamId}"
            data-kind="${kind}" data-i="${i}" ${open ? "disabled" : ""}
            title="Rate this player. Click to cycle S to F, again to clear.">${rk || "–"}</button>
    <input value="${esc(s.name)}" placeholder="open slot"
           data-team="${teamId}" data-kind="${kind}" data-i="${i}" spellcheck="false">
    <button class="chip" data-s="${label}" data-team="${teamId}"
            data-kind="${kind}" data-i="${i}"
            title="Click to cycle confirmed / leaked / open">${label}</button>
  </div>`;
}

function renderPanel() {
  const el = document.getElementById("panel");
  if (!sel) { el.className = "hint"; return; }
  const t = team(sel), r = S.rosters[sel];
  const filled = r.slots.filter(s => s.name).length;
  const leaks = r.slots.filter(s => s.status === "leaked" && s.name).length;
  const avg = teamAvg(sel);
  const place = order().indexOf(sel);

  const groups = ROLES.map(([role, lab], gi) => {
    const idx = [gi * 2, gi * 2 + 1];
    return `<div class="grp" data-r="${role}">
      <div class="grp-h"><img src="roles/${lab}.png" alt=""><span>${lab}</span></div>
      ${idx.map(i => rowHtml(sel, "slots", i, r.slots[i])).join("")}
    </div>`;
  }).join("");

  const block = (title, kind, arr, addable) =>
    `<div class="sub-h">${title}</div>` +
    (arr.length ? arr.map((s, i) => rowHtml(sel, kind, i, s)).join("")
                : `<p class="empty-note">None listed.</p>`) +
    (addable ? `<button class="addbtn" data-add="${kind}">+ add ${addable}</button>` : "");

  el.className = "rp";
  el.innerHTML = `
    <div class="rp-head"><img src="${t.logo}" alt="">
      <div><div class="rp-name">${esc(t.name)}</div>
      <div class="rp-place">${place > -1
        ? `${mode === "GLOBAL" ? "Global" : mode === "EU" ? "EMEA" : "Americas"} #${place + 1}`
        : "Unranked"}</div></div></div>
    <div class="rp-meta">${t.region === "EU" ? "EMEA" : "Americas"}
      &nbsp;&nbsp; ${filled}/6 starters${leaks ? ` &nbsp;&nbsp; ${leaks} leaked` : ""}</div>
    ${avg ? `<div class="rp-avg">Players average <b data-t="${avg.letter}">${avg.letter}</b>
       <span>${avg.mean.toFixed(1)} over ${avg.n} rated</span></div>` : ""}
    ${t.contested.length ? `<div class="rp-warn">Source lists ${esc(t.contested.join(", "))}
       — one of these is likely wrong. Clear the name that does not belong.</div>` : ""}
    ${groups}
    ${r.extra.length ? block("Unresolved extra starters", "extra", r.extra, null) : ""}
    ${block("Subs", "subs", r.subs, "sub")}
    ${block("Staff", "staff", r.staff, "staff")}`;
}

function renderLog() {
  const ol = document.getElementById("log");
  ol.innerHTML = S.log.length
    ? S.log.map(e => `<li><span class="t">${esc(e.t)}</span>
        <span class="team-tag">${esc(e.team)}</span>
        <span class="from">${esc(e.from)}</span><span class="arw">→</span>
        <span class="to">${esc(e.to)}</span></li>`).join("")
    : `<li class="empty-note">Nothing changed yet.</li>`;
}

const render = () => { renderBoard(); renderPanel(); renderLog(); save(); };

/* ---------- drag to reorder ---------- */
let dragId = null;

function clearMarks() {
  document.querySelectorAll(".rank-row").forEach(r =>
    r.classList.remove("ins-before", "ins-after"));
  document.getElementById("pool")?.classList.remove("over");
}

function wireDnd() {
  document.querySelectorAll("[data-id]").forEach(el => {
    el.addEventListener("dragstart", e => {
      dragId = el.dataset.id;
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", dragId);
      setTimeout(() => el.classList.add("drag"), 0);
    });
    el.addEventListener("dragend", () => { el.classList.remove("drag"); dragId = null; clearMarks(); });
    el.addEventListener("click", () => { sel = el.dataset.id; render(); });
  });

  const list = document.getElementById("ranking");
  list.addEventListener("dragover", e => {
    e.preventDefault();
    clearMarks();
    const row = e.target.closest(".rank-row");
    if (row) {
      const r = row.getBoundingClientRect();
      row.classList.add(e.clientY < r.top + r.height / 2 ? "ins-before" : "ins-after");
    } else if (!order().length) {
      list.classList.add("over");
    }
  });
  list.addEventListener("dragleave", clearMarks);
  list.addEventListener("drop", e => {
    e.preventDefault();
    const id = dragId || e.dataTransfer.getData("text/plain");
    if (!id) return;
    const row = e.target.closest(".rank-row");
    let idx = order().length;
    if (row) {
      const r = row.getBoundingClientRect();
      idx = order().indexOf(row.dataset.id) + (e.clientY < r.top + r.height / 2 ? 0 : 1);
    }
    const cur = order().indexOf(id);
    if (cur > -1 && cur < idx) idx--;      // removing it first shifts everything below up
    if (cur > -1) order().splice(cur, 1);
    order().splice(Math.max(0, Math.min(idx, order().length)), 0, id);
    clearMarks();
    render();
  });

  const pool = document.getElementById("pool");
  pool.addEventListener("dragover", e => { e.preventDefault(); pool.classList.add("over"); });
  pool.addEventListener("dragleave", () => pool.classList.remove("over"));
  pool.addEventListener("drop", e => {
    e.preventDefault();
    const id = dragId || e.dataTransfer.getData("text/plain");
    const i = order().indexOf(id);
    if (i > -1) order().splice(i, 1);
    clearMarks();
    render();
  });
}

/* ---------- editing ---------- */
const bucket = (teamId, kind) => S.rosters[teamId][kind];

document.addEventListener("input", e => {
  const el = e.target;
  if (el.tagName !== "INPUT" || !el.dataset.team) return;
  const rec = bucket(el.dataset.team, el.dataset.kind)[+el.dataset.i];
  if (rec) rec.name = el.value;
  save();
});
document.addEventListener("focusin", e => {
  if (e.target.tagName === "INPUT" && e.target.dataset.team)
    e.target.dataset.before = e.target.value;
});
function commit(el) {
  const before = el.dataset.before ?? "", after = el.value.trim();
  if (before.trim() === after) return;
  const rec = bucket(el.dataset.team, el.dataset.kind)[+el.dataset.i];
  if (!rec) return;
  rec.name = after;
  if (after && before.trim() === "") rec.status = "leaked";   // typed live = unconfirmed
  if (!after) { rec.status = "open"; rec.rank = null; }
  logChange(el.dataset.team, before.trim(), after);
  el.dataset.before = after;
  render();
}
document.addEventListener("focusout", e => {
  if (e.target.tagName === "INPUT" && e.target.dataset.team) commit(e.target);
});
document.addEventListener("keydown", e => {
  if (e.target.tagName !== "INPUT" || !e.target.dataset.team) return;
  if (e.key === "Enter") {
    e.preventDefault(); commit(e.target);
    const all = [...document.querySelectorAll(".rp input")];
    const i = all.indexOf(e.target);
    if (all[i + 1]) all[i + 1].focus();
  }
  if (e.key === "Escape") { e.target.value = e.target.dataset.before ?? ""; e.target.blur(); }
});

document.addEventListener("click", e => {
  const rk = e.target.closest(".rank");
  if (rk && !rk.disabled) {
    const rec = bucket(rk.dataset.team, rk.dataset.kind)[+rk.dataset.i];
    if (rec) { rec.rank = nextRank(rec.rank); render(); }
    return;
  }
  const c = e.target.closest(".chip");
  if (c) {
    const rec = bucket(c.dataset.team, c.dataset.kind)[+c.dataset.i];
    if (!rec) return;
    rec.status = !rec.name ? "open"
      : rec.status === "confirmed" ? "leaked"
      : rec.status === "leaked" ? "open" : "confirmed";
    render();
    return;
  }
  const add = e.target.closest(".addbtn");
  if (add && sel) {
    bucket(sel, add.dataset.add).push({ role: "", name: "", status: "open", rank: null });
    renderPanel();
    const ins = document.querySelectorAll(`.rp input[data-kind="${add.dataset.add}"]`);
    if (ins.length) ins[ins.length - 1].focus();
    return;
  }
  if (e.target.id === "sortrated") {
    const score = id => { const a = teamAvg(id); return a ? a.mean : -1; };
    const merged = [...order(), ...poolIds()].filter(id => score(id) >= 0);
    const rest = order().filter(id => score(id) < 0);
    merged.sort((x, y) => score(y) - score(x));
    S.order[mode] = [...merged, ...rest];
    render();
  }
  if (e.target.id === "clearorder") { S.order[mode] = []; render(); }
  if (e.target.id === "seed") {
    // interleave the two regional orders so global starts somewhere sensible
    const eu = [...S.order.EU], na = [...S.order.NA], out = [];
    while (eu.length || na.length) { if (eu.length) out.push(eu.shift()); if (na.length) out.push(na.shift()); }
    for (const id of scopeIds()) if (!out.includes(id) && S.order.GLOBAL.includes(id)) out.push(id);
    S.order.GLOBAL = out;
    render();
  }
});

/* ---------- toolbar ---------- */
// A browser holding a cached index.html from an older deploy will run this
// (fresh) script against markup that no longer matches, and every lookup below
// returns null. Detect it and reload once past the cache rather than dying with
// a blank board.
if (!document.getElementById("modes")) {
  if (!sessionStorage.getItem("wev-stale-html")) {
    sessionStorage.setItem("wev-stale-html", "1");
    location.replace(location.pathname + "?r=" + Date.now());
  } else {
    document.body.innerHTML =
      '<p style="color:#AEB6C2;font:16px system-ui;padding:40px;line-height:1.6">' +
      'This page is running a cached older version. Hard-refresh to update: ' +
      '<b>Cmd+Shift+R</b> on Mac, <b>Ctrl+F5</b> on Windows.</p>';
  }
  return;
}
sessionStorage.removeItem("wev-stale-html");

// Missing nodes must never take the whole board down.
const on = (id, ev, fn) => {
  const el = document.getElementById(id);
  if (el) el.addEventListener(ev, fn);
};

document.getElementById("modes").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  mode = b.dataset.m;
  [...e.currentTarget.children].forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  render();
});
on("export", "click", () => {
  const blob = new Blob([JSON.stringify({ v: 2, saved: new Date().toISOString(), state: S }, null, 2)],
                        { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ignite-s2-ranking.json";
  a.click(); URL.revokeObjectURL(a.href);
});
on("import", "click", () => document.getElementById("file")?.click());
on("file", "change", e => {
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = () => {
    try {
      const p = JSON.parse(r.result);
      if (p?.state?.rosters && p.state.order) { S = p.state; render(); }
    } catch (err) { /* a bad file must never blank the board mid-stream */ }
  };
  r.readAsText(f); e.target.value = "";
});
on("reset", "click", () => {
  const b = document.getElementById("reset");
  if (b.dataset.armed) { S = freshState(); sel = null; render();
                         delete b.dataset.armed; b.textContent = "Reset"; return; }
  b.dataset.armed = "1"; b.textContent = "Sure?";
  setTimeout(() => { delete b.dataset.armed; b.textContent = "Reset"; }, 3000);
});

fetch("data.json", { cache: "no-store" }).then(r => r.json()).then(d => {
  DATA = d; S = load() || freshState(); render();
}).catch(() => {
  document.getElementById("board").innerHTML =
    `<p class="hint">Could not load <b>data.json</b>. If you opened this file directly,
     serve the folder instead: <b>python3 -m http.server</b></p>`;
});
})();
