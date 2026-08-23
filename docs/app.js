/* Ignite Stage 2 power-ranking board.
   No framework and no backend: this has to run off GitHub Pages and survive a
   stream with no network. State lives in localStorage and exports to JSON. */
(() => {
"use strict";

const TIERS = ["S", "A", "B", "C", "D", "F"];
const ROLES = [["DPS", "Duelist"], ["Tank", "Vanguard"], ["Support", "Strategist"]];
const KEY = "ignite-s2-board-v1";

let DATA = null;      // immutable baseline from data.json
let S = null;         // mutable session state
let sel = null;       // selected team id
let region = "ALL";

/* ---------- state ---------- */
function freshState() {
  const rosters = {};
  for (const t of DATA.teams) {
    const slots = [];
    for (const [role] of ROLES) {
      const inRole = t.roster.filter(p => p.status === "main" && p.role === role);
      for (let i = 0; i < 2; i++) {
        const p = inRole[i];
        slots.push({
          role,
          name: p ? p.name : "",
          status: p ? "confirmed" : "open",
        });
      }
    }
    // starters the source lists beyond 2-2-2 (contested rows) stay visible
    const extra = t.roster.filter(p => p.status === "main" &&
      !slots.some(s => s.name === p.name));
    rosters[t.id] = {
      slots,
      extra: extra.map(p => ({ role: p.role, name: p.name, status: "confirmed" })),
      subs: t.roster.filter(p => p.status === "sub")
              .map(p => ({ role: p.role, name: p.name, status: "confirmed" })),
      staff: t.roster.filter(p => p.status === "staff")
              .map(p => ({ role: p.role, name: p.name, status: "confirmed" })),
    };
  }
  return { tiers: Object.fromEntries(TIERS.map(t => [t, []])), rosters, log: [] };
}

function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} }

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const s = JSON.parse(raw);
    if (!s || !s.rosters || !s.tiers) return null;
    // tolerate a data.json refresh that adds teams
    for (const t of DATA.teams) if (!s.rosters[t.id]) s.rosters[t.id] = freshState().rosters[t.id];
    return s;
  } catch (e) { return null; }
}

const team = id => DATA.teams.find(t => t.id === id);
const ranked = () => new Set(TIERS.flatMap(t => S.tiers[t]));
const visible = id => region === "ALL" || team(id).region === region;

function logChange(teamId, from, to) {
  const now = new Date();
  S.log.unshift({
    t: now.toTimeString().slice(0, 5),
    team: team(teamId).short || team(teamId).name,
    from: from || "(open)", to: to || "(cleared)",
  });
  S.log = S.log.slice(0, 60);
}

/* ---------- rendering ---------- */
function pips(id) {
  const r = S.rosters[id];
  return r.slots.map(s =>
    `<i class="pip ${s.status === "open" || !s.name ? "empty" :
                     s.status === "leaked" ? "leak" : ""}"></i>`).join("");
}

function chip(id) {
  const t = team(id);
  return `<div class="team${sel === id ? " sel" : ""}" draggable="true" data-id="${id}"
               title="${esc(t.name)}">
    <img src="${t.logo}" alt="">
    <div class="nm">${esc(t.short || t.name)}</div>
    <div class="pips">${pips(id)}</div>
  </div>`;
}

function renderBoard() {
  const board = document.getElementById("board");
  const inTier = ranked();
  const pool = DATA.teams.map(t => t.id).filter(id => !inTier.has(id) && visible(id));
  board.innerHTML =
    TIERS.map(t => `<div class="tier" data-t="${t}">
        <div class="tier-label">${t}</div>
        <div class="slot" data-tier="${t}">
          ${S.tiers[t].filter(visible).map(chip).join("")}
        </div>
      </div>`).join("") +
    `<div class="pool-wrap">
       <p class="pool-title">Unranked — ${pool.length} teams</p>
       <div class="pool slot" data-tier="">${pool.map(chip).join("")}</div>
     </div>`;
  wireDnd();
}

function rowHtml(teamId, kind, i, s) {
  const open = !s.name;
  const cls = s.status === "leaked" ? "leak" : open ? "empty" : "";
  const label = open ? "open" : s.status;
  return `<div class="row ${cls}" data-kind="${kind}" data-i="${i}">
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

  const groups = ROLES.map(([role, label], gi) => {
    const idx = [gi * 2, gi * 2 + 1];
    return `<div class="grp" data-r="${role}">
      <div class="grp-h"><img src="roles/${label}.png" alt=""><span>${label}</span></div>
      ${idx.map(i => rowHtml(sel, "slots", i, r.slots[i])).join("")}
    </div>`;
  }).join("");

  const extras = r.extra.length ? `<div class="sub-h">Unresolved extra starters</div>` +
    r.extra.map((s, i) => rowHtml(sel, "extra", i, s)).join("") : "";
  const subs = `<div class="sub-h">Subs</div>` +
    (r.subs.length ? r.subs.map((s, i) => rowHtml(sel, "subs", i, s)).join("")
                   : `<p class="empty-note">None listed.</p>`);
  const staff = `<div class="sub-h">Staff</div>` +
    (r.staff.length ? r.staff.map((s, i) => rowHtml(sel, "staff", i, s)).join("")
                    : `<p class="empty-note">None listed.</p>`);

  el.className = "rp";
  el.innerHTML = `
    <div class="rp-head"><img src="${t.logo}" alt="">
      <div class="rp-name">${esc(t.name)}</div></div>
    <div class="rp-meta">${t.region === "EU" ? "EMEA" : "Americas"}
      &nbsp;&nbsp; ${filled}/6 starters${leaks ? ` &nbsp;&nbsp; ${leaks} leaked` : ""}</div>
    ${t.contested.length ? `<div class="rp-warn">Source lists ${esc(t.contested.join(", "))}
       — one of these is likely wrong. Clear the name that does not belong.</div>` : ""}
    ${groups}${extras}
    ${subs}<button class="addbtn" data-add="subs">+ add sub</button>
    ${staff}<button class="addbtn" data-add="staff">+ add staff</button>`;
}

function renderLog() {
  const ol = document.getElementById("log");
  if (!S.log.length) { ol.innerHTML = `<li class="empty-note">Nothing changed yet.</li>`; return; }
  ol.innerHTML = S.log.map(e => `<li>
      <span class="t">${esc(e.t)}</span>
      <span class="team-tag">${esc(e.team)}</span>
      <span class="from">${esc(e.from)}</span>
      <span class="arw">→</span>
      <span class="to">${esc(e.to)}</span>
    </li>`).join("");
}

const render = () => { renderBoard(); renderPanel(); renderLog(); save(); };
const esc = s => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/* ---------- drag & drop ---------- */
let dragId = null;
function wireDnd() {
  document.querySelectorAll(".team").forEach(el => {
    el.addEventListener("dragstart", e => {
      dragId = el.dataset.id; el.classList.add("drag");
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", dragId);
    });
    el.addEventListener("dragend", () => { el.classList.remove("drag"); dragId = null; });
    el.addEventListener("click", () => { sel = el.dataset.id; render(); });
  });
  document.querySelectorAll(".slot").forEach(slot => {
    slot.addEventListener("dragover", e => { e.preventDefault(); slot.classList.add("over"); });
    slot.addEventListener("dragleave", () => slot.classList.remove("over"));
    slot.addEventListener("drop", e => {
      e.preventDefault(); slot.classList.remove("over");
      const id = dragId || e.dataTransfer.getData("text/plain");
      if (!id) return;
      for (const t of TIERS) S.tiers[t] = S.tiers[t].filter(x => x !== id);
      const dest = slot.dataset.tier;
      if (dest) S.tiers[dest].push(id);
      render();
    });
  });
}

/* ---------- editing ---------- */
function bucket(teamId, kind) { return S.rosters[teamId][kind]; }

document.addEventListener("input", e => {
  const el = e.target;
  if (el.tagName !== "INPUT" || !el.dataset.team) return;
  const arr = bucket(el.dataset.team, el.dataset.kind);
  const rec = arr[+el.dataset.i];
  if (rec) rec.name = el.value;   // keep typing snappy; commit happens on blur/Enter
  save();
});

document.addEventListener("focusin", e => {
  if (e.target.tagName === "INPUT" && e.target.dataset.team)
    e.target.dataset.before = e.target.value;
});

function commit(el) {
  const before = el.dataset.before ?? "";
  const after = el.value.trim();
  if (before.trim() === after) return;
  const arr = bucket(el.dataset.team, el.dataset.kind);
  const rec = arr[+el.dataset.i];
  if (!rec) return;
  rec.name = after;
  // A name typed into an empty slot during a stream is a leak until confirmed.
  if (after && before.trim() === "") rec.status = "leaked";
  if (!after) rec.status = "open";
  logChange(el.dataset.team, before.trim(), after);
  el.dataset.before = after;
  render();
}

document.addEventListener("focusout", e => {
  if (e.target.tagName === "INPUT" && e.target.dataset.team) commit(e.target);
});

document.addEventListener("keydown", e => {
  if (e.target.tagName !== "INPUT" || !e.target.dataset.team) return;
  if (e.key === "Enter") { e.preventDefault(); commit(e.target); focusNext(e.target); }
  if (e.key === "Escape") { e.target.value = e.target.dataset.before ?? ""; e.target.blur(); }
});

function focusNext(el) {
  const all = [...document.querySelectorAll(".rp input")];
  const i = all.indexOf(el);
  if (i > -1 && all[i + 1]) all[i + 1].focus();
}

document.addEventListener("click", e => {
  const c = e.target.closest(".chip");
  if (c) {
    const arr = bucket(c.dataset.team, c.dataset.kind);
    const rec = arr[+c.dataset.i];
    if (!rec) return;
    if (!rec.name) { rec.status = "open"; }
    else { rec.status = rec.status === "confirmed" ? "leaked"
                      : rec.status === "leaked" ? "open" : "confirmed"; }
    render();
    return;
  }
  const add = e.target.closest(".addbtn");
  if (add && sel) {
    bucket(sel, add.dataset.add).push({ role: "", name: "", status: "open" });
    renderPanel();
    const ins = document.querySelectorAll(`.rp input[data-kind="${add.dataset.add}"]`);
    if (ins.length) ins[ins.length - 1].focus();
  }
});

/* ---------- toolbar ---------- */
document.getElementById("regions").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  region = b.dataset.r;
  [...e.currentTarget.children].forEach(x =>
    x.setAttribute("aria-pressed", String(x === b)));
  render();
});

document.getElementById("export").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify({ v: 1, saved: new Date().toISOString(), state: S }, null, 2)],
                        { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ignite-s2-ranking.json";
  a.click();
  URL.revokeObjectURL(a.href);
});

document.getElementById("import").addEventListener("click", () =>
  document.getElementById("file").click());

document.getElementById("file").addEventListener("change", e => {
  const f = e.target.files[0]; if (!f) return;
  const r = new FileReader();
  r.onload = () => {
    try {
      const p = JSON.parse(r.result);
      if (p && p.state && p.state.rosters && p.state.tiers) { S = p.state; render(); }
    } catch (err) { /* a bad file should never blank the board mid-stream */ }
  };
  r.readAsText(f);
  e.target.value = "";
});

document.getElementById("reset").addEventListener("click", () => {
  // Deliberately not a confirm() dialog: a modal mid-stream is worse than a
  // second click, and the export button is right there.
  const b = document.getElementById("reset");
  if (b.dataset.armed) { S = freshState(); sel = null; render(); delete b.dataset.armed;
                         b.textContent = "Reset"; return; }
  b.dataset.armed = "1"; b.textContent = "Sure?";
  setTimeout(() => { delete b.dataset.armed; b.textContent = "Reset"; }, 3000);
});

/* ---------- boot ---------- */
fetch("data.json").then(r => r.json()).then(d => {
  DATA = d;
  S = load() || freshState();
  render();
}).catch(() => {
  document.getElementById("board").innerHTML =
    `<p class="hint">Could not load <b>data.json</b>. If you opened this file
     directly, serve the folder instead: <b>python3 -m http.server</b></p>`;
});
})();
