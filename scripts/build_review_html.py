#!/usr/bin/env python3
"""build_review_html.py — scannable HTML review doc for composed records (SGXEM-owned).

Renders each composed record as a card: question, answer+aliases, hidden bridge (audit),
the decomposition hops, the cited evidence passages (supporting highlighted, distractors
dimmed), gate verdicts, and cluster/hop/temporal badges. Each card has Yes/No/Maybe +
a comment box; choices persist in the browser (localStorage) and export to a decisions
JSON you can hand back. Rejections are shown too (so good ones the gate killed can be rescued).
"""
from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def badge(label: str, val, cls: str = "") -> str:
    return f'<span class="badge {cls}">{esc(label)}: {esc(val)}</span>'


def gate_badge(g: dict) -> str:
    out = []
    for k in ("nli_all_hops_entailed", "red_team_breakable", "single_passage_sufficient"):
        v = g.get(k)
        cls = "g-na" if v is None else ("g-good" if (v is False if "breakable" in k or "single" in k else v) else "g-bad")
        out.append(f'<span class="badge {cls}">{esc(k)}={esc(v)}</span>')
    return " ".join(out)


def card(rec: dict) -> str:
    rid = rec.get("id") or rec.get("seed_id", "?")
    if rec.get("rejection"):
        return (f'<div class="card rej" data-id="{esc(rid)}" data-cluster="{esc(rec.get("cluster"))}" '
                f'data-hop="{esc(rec.get("hop_count"))}" data-temporal="{esc(rec.get("temporal_sensitivity"))}" '
                f'data-status="rejected">'
                f'<div class="hdr"><b>{esc(rid)}</b> {badge("cluster", rec.get("cluster"))} '
                f'{badge("hop", rec.get("hop_count"))} {badge("temporal", rec.get("temporal_sensitivity"))} '
                f'<span class="badge g-bad">REJECTED</span></div>'
                f'<div class="reason">reason: {esc(rec.get("reason"))}</div>'
                f'{review_controls(rid)}</div>')

    paras = rec.get("paragraphs", [])
    decomp = rec.get("question_decomposition", [])
    audit = rec.get("_audit", {})
    hops_html = ""
    for i, h in enumerate(decomp, 1):
        hops_html += (f'<div class="hop"><span class="hn">{i}</span> '
                      f'<span class="hq">{esc(h.get("question"))}</span> '
                      f'<span class="ha">→ {esc(h.get("answer"))}</span> '
                      f'<span class="hb">[bridge_qid={esc(h.get("bridge_qid"))}, para#{esc(h.get("paragraph_support_idx"))}]</span></div>')
    ev_html = ""
    for p in paras:
        cls = "sup" if p.get("is_supporting") else "dis"
        tag = "SUPPORT" if p.get("is_supporting") else "distractor"
        ev_html += (f'<div class="ev {cls}"><div class="evh">[{esc(p.get("idx"))}] '
                    f'<b>{esc(p.get("title"))}</b> <span class="tier">{esc(p.get("source_tier"))}</span> '
                    f'<span class="evtag">{tag}</span></div>'
                    f'<div class="evt">{esc((p.get("paragraph_text") or "")[:900])}</div></div>')
    aliases = ", ".join(esc(a) for a in rec.get("answer_aliases", []))
    return (f'<div class="card" data-id="{esc(rid)}" data-cluster="{esc(rec.get("cluster"))}" '
            f'data-hop="{esc(rec.get("hop_count"))}" data-temporal="{esc(rec.get("temporal_sensitivity"))}" '
            f'data-status="composed">'
            f'<div class="hdr"><b>{esc(rid)}</b> {badge("cluster", rec.get("cluster"))} '
            f'{badge("sub", rec.get("sub_topic"))} {badge("hop", rec.get("hop_count"))} '
            f'{badge("temporal", rec.get("temporal_sensitivity"), "t-"+str(rec.get("temporal_sensitivity")))} '
            f'{badge("reliab", rec.get("source_reliability"))}</div>'
            f'<div class="q">Q: {esc(rec.get("question"))}</div>'
            f'<div class="a">A: <b>{esc(rec.get("answer"))}</b> <span class="al">aliases: {aliases}</span></div>'
            f'<div class="bridge">hidden bridge (audit): {esc(audit.get("hidden_bridge"))}</div>'
            f'<div class="gate">{gate_badge(rec.get("gate", {}))}</div>'
            f'<details><summary>decomposition ({len(decomp)} hops)</summary>{hops_html}</details>'
            f'<details><summary>evidence ({len(paras)} passages)</summary>{ev_html}</details>'
            f'{review_controls(rid)}</div>')


def review_controls(rid: str) -> str:
    return (f'<div class="rev" data-rid="{esc(rid)}">'
            f'<label><input type="radio" name="v_{esc(rid)}" value="yes">✅ keep</label> '
            f'<label><input type="radio" name="v_{esc(rid)}" value="no">❌ drop</label> '
            f'<label><input type="radio" name="v_{esc(rid)}" value="rewrite">✏️ rewrite</label> '
            f'<input class="cmt" type="text" placeholder="comment…" data-rid="{esc(rid)}"></div>')


CSS = """
body{font:14px/1.5 -apple-system,system-ui,sans-serif;margin:0;background:#0f1115;color:#e7e9ee}
.top{position:sticky;top:0;background:#171a21;padding:10px 16px;border-bottom:1px solid #2a2f3a;z-index:10}
.top h1{font-size:16px;margin:0 0 6px}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
select,button{background:#222732;color:#e7e9ee;border:1px solid #38404f;border-radius:6px;padding:5px 8px}
button{cursor:pointer}
.wrap{padding:14px;max-width:1100px;margin:0 auto}
.card{background:#161922;border:1px solid #283041;border-radius:10px;padding:12px 14px;margin:10px 0}
.card.rej{opacity:.7;border-color:#5a2330}
.hdr{margin-bottom:6px}
.badge{display:inline-block;background:#222a38;border:1px solid #313a4d;border-radius:12px;padding:1px 8px;margin:1px 3px 1px 0;font-size:12px}
.t-recency{background:#3a2a12;border-color:#7a5a22;color:#ffd591}
.g-good{background:#16331f;border-color:#2f7a44;color:#9be3ad}.g-bad{background:#3a1620;border-color:#7a2f44;color:#ff9bb0}.g-na{opacity:.6}
.q{font-size:15px;font-weight:600;margin:6px 0}
.a{margin:4px 0}.al{color:#8b93a7;font-size:12px}
.bridge{color:#c8923a;font-size:12px;margin:2px 0}
.gate{margin:4px 0}
details{margin:6px 0;background:#11141c;border:1px solid #232a38;border-radius:8px;padding:4px 8px}
summary{cursor:pointer;color:#9fb0d0}
.hop{margin:4px 0;padding-left:6px}.hn{display:inline-block;width:18px;height:18px;background:#2a3550;border-radius:50%;text-align:center;font-size:11px}
.hq{color:#cdd6e8}.ha{color:#9be3ad}.hb{color:#6b7488;font-size:11px}
.ev{margin:5px 0;border-left:3px solid #333;padding:3px 8px}
.ev.sup{border-color:#2f7a44;background:#10241680}.ev.dis{border-color:#444;opacity:.65}
.evh{font-size:12px}.tier{background:#222a38;border-radius:8px;padding:0 6px;font-size:11px}
.evtag{float:right;font-size:11px;color:#8b93a7}.evt{font-size:12px;color:#aeb6c6;margin-top:2px}
.rev{margin-top:8px;padding-top:8px;border-top:1px dashed #2a3344}
.rev label{margin-right:10px}.cmt{width:50%;background:#11141c;border:1px solid #313a4d;border-radius:6px;padding:3px 6px;color:#e7e9ee}
.counts{color:#8b93a7;font-size:12px}
"""

JS = """
const K='sgxem_review_v1';
let st=JSON.parse(localStorage.getItem(K)||'{}');
function save(){localStorage.setItem(K,JSON.stringify(st))}
document.addEventListener('change',e=>{
  if(e.target.name&&e.target.name.startsWith('v_')){const id=e.target.name.slice(2);st[id]=st[id]||{};st[id].v=e.target.value;save();filt()}
});
document.addEventListener('input',e=>{
  if(e.target.classList.contains('cmt')){const id=e.target.dataset.rid;st[id]=st[id]||{};st[id].c=e.target.value;save()}
});
function restore(){for(const id in st){const v=st[id].v;if(v){const r=document.querySelector(`input[name="v_${id}"][value="${v}"]`);if(r)r.checked=true}
  const c=document.querySelector(`.cmt[data-rid="${id}"]`);if(c&&st[id].c)c.value=st[id].c}}
function exp(){const b=new Blob([JSON.stringify(st,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='review_decisions.json';a.click()}
function filt(){const fc=val('fc'),fh=val('fh'),ft=val('ft'),fs=val('fs'),fv=val('fv');let n=0,dec=0;
  document.querySelectorAll('.card').forEach(c=>{const id=c.dataset.id;const v=(st[id]&&st[id].v)||'';
    if(v)dec++;
    const vok = !fv ? true : (fv==='undecided' ? !v : v===fv);
    const ok=(!fc||c.dataset.cluster===fc)&&(!fh||c.dataset.hop===fh)&&(!ft||c.dataset.temporal===ft)&&(!fs||c.dataset.status===fs)&&vok;
    c.style.display=ok?'':'none';if(ok)n++});
  document.getElementById('shown').textContent=n;
  const d=document.getElementById('decided');if(d)d.textContent=dec}
function val(id){return document.getElementById(id).value}
window.onload=()=>{restore();filt()}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--title", default="SGXEM Defense Benchmark — Review")
    a = ap.parse_args()
    recs = [json.loads(l) for l in a.inp.read_text().splitlines() if l.strip()]
    ok = [r for r in recs if not r.get("rejection")]
    cl = Counter(r.get("cluster") for r in ok)
    hp = Counter(r.get("hop_count") for r in ok)
    tp = Counter(r.get("temporal_sensitivity") for r in ok)
    summary = (f"{len(recs)} records · composed {len(ok)} · rejected {len(recs)-len(ok)} · "
               f"cluster {dict(cl)} · hop {dict(hp)} · temporal {dict(tp)}")
    opts = lambda vals: "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in vals)
    cards = "\n".join(card(r) for r in recs)
    htmldoc = f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(a.title)}</title>
<style>{CSS}</style></head><body>
<div class="top"><h1>{esc(a.title)}</h1>
<div class="counts">{esc(summary)}</div>
<div class="controls">
 cluster <select id="fc" onchange="filt()"><option value="">all</option>{opts(sorted(c for c in cl))}</select>
 hop <select id="fh" onchange="filt()"><option value="">all</option>{opts([2,3,4])}</select>
 temporal <select id="ft" onchange="filt()"><option value="">all</option>{opts(["timeless","recency"])}</select>
 status <select id="fs" onchange="filt()"><option value="">all</option>{opts(["composed","rejected"])}</select>
 <b>my review</b> <select id="fv" onchange="filt()"><option value="undecided">⬜ to review</option><option value="">all</option><option value="keep">✅ keep</option><option value="drop">❌ drop</option><option value="rewrite">✏️ rewrite</option></select>
 <button onclick="exp()">⬇ export decisions</button>
 <span class="counts">showing <b id="shown">0</b> · decided <b id="decided">0</b></span>
</div></div>
<div class="wrap">{cards}</div>
<script>{JS}</script></body></html>"""
    a.out.write_text(htmldoc, encoding="utf-8")
    print(f"wrote {a.out}  ({len(recs)} cards: {len(ok)} composed, {len(recs)-len(ok)} rejected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
