#!/usr/bin/env python3
"""compose_recency.py — focused recency-question pass (SGXEM-owned, T5 recency block).

The recency axis (paper knockout: frozen-cutoff frontier LLMs fail, our retrieval-grounded
stack wins) needs questions whose FINAL answer hinges on a concrete 2025-2026 dated fact the
corpus holds. Generic 'latest' seeds rejected ~99%; this uses curated recent-fact anchors +
a recency-aware prompt (timeless bridges, recency-sensitive final hop) and composes (with
temperature jitter for diversity) until --target survivors. Runs parallel to the bulk run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose_one import retrieve, assemble, http_json, _extract_json, FW_URL, FW_MODEL  # noqa: E402

RECENCY_SYSTEM = """You compose RECENCY questions for an open defense/geopolitical multi-hop QA benchmark,
as of {as_of}. You get a SEED (cluster, hop_count) and RETRIEVED PASSAGES (source_id, title,
source_tier, wikidata_id, text).

This is a RECENCY question: the FINAL answer must be a fact that became true in 2025 or 2026
(after typical LLM training cutoffs) and is stated, with its date, in a cited passage. Earlier
hops may be timeless; ONLY the last hop hinges on the recent dated fact.

HARD RULES:
- Use ONLY facts in the passages. If no passage states a 2025/2026 dated fact that completes a
  genuine {hop_count}-hop chain, output {"rejection": true, "reason": "no recent dated fact"}.
- The BRIDGE ENTITY (linking hop i's answer to hop i+1's passage) MUST NOT appear in the final
  `question`. Phrase the question "As of {as_of}, ..." so the recent value is what's asked.
- Cite the EXACT source_id supporting each hop. The final answer must be verbatim (or a minimal
  span) from the dated passage, and the chain must require {hop_count} passages.

Output JSON ONLY:
{"question": "...", "answer": "...", "answer_aliases": ["..."], "hidden_bridge": "...",
 "recent_date": "the 2025/2026 date the answer depends on",
 "hops": [{"question": "...", "answer": "...", "source_id": <int>, "bridge_qid": "Qxxxx"}]}
hops length == hop_count."""

# curated recent-fact anchors (retrieval queries that pull dated 2025-2026 passages)
ANCHORS = {
    "venezuela": [
        "Venezuela Organic Hydrocarbons Law amendment January 2026 private participation arbitration royalties",
        "Venezuela OFAC general license 2026 oil natural gas sector US jurisdiction provision",
        "United States seized vessels transporting Venezuelan oil 2025 2026 December",
        "OFAC sanctions E.O. 13850 individuals entities vessels Venezuela count 2026",
        "Venezuela Central Bank Minerven gold company sanctioned E.O. 13850",
        "Venezuela oil exports barrels per day 2026 seven-year high destination",
        "OFAC sanctioned entity owner purchasing drones Iran December 2025 Venezuela E.O. 13949",
        "Venezuela natural gas reserves billion cubic meters 2026 hydrocarbons framework",
        "E.O. 13884 Maduro government designations January 2026 individuals entities vessels",
        "Venezuela SLB oilfield services contract 2026 production recovery PDVSA",
    ],
    "iran": [
        "Iran uranium enrichment stockpile 2025 IAEA latest enriched level percent",
        "Iran sanctions 2025 petrochemical banking designation latest OFAC",
    ],
    "taiwan": [
        "Taiwan United States arms sale 2025 latest package notification value",
        "China Taiwan 2025 military exercise cross-strait latest",
    ],
    "cuba": [
        "Cuba United States policy 2025 sanctions designation latest restriction",
    ],
    "brazil": [
        "Brazil Amazon deforestation 2025 enforcement operation latest agency",
        "Brazil defense cooperation agreement 2025 United States latest",
    ],
}
# cluster weight for which anchors to over-use (Venezuela depth)
CLUSTER_REPEATS = {"venezuela": 4, "iran": 2, "taiwan": 2, "cuba": 2, "brazil": 2}


def build_recency_seeds() -> list[dict]:
    # merge mined corpus anchors (distinct dated facts) with curated ones
    anchors = {k: list(v) for k, v in ANCHORS.items()}
    mined_path = Path("data/t5_raw/recency_anchors.json")
    if mined_path.exists():
        mined = json.loads(mined_path.read_text())
        for c, qs in mined.items():
            anchors.setdefault(c, [])
            for q in qs:
                if q not in anchors[c]:
                    anchors[c].append(q)
    seeds, sid = [], 0
    for cluster, qs in anchors.items():
        reps = CLUSTER_REPEATS[cluster]
        for q in qs:
            for hop in (2, 3):
                for rep in range(reps):
                    seeds.append({"seed_id": f"R{sid:05d}", "cluster": cluster, "sub_topic": "recency",
                                  "bridge_type": "event_to_fact", "hop_count": hop, "retrieval_query": q,
                                  "source_reliability": "medium", "temporal_sensitivity": "recency",
                                  "seq": 10000 + sid, "_temp": 0.3 + 0.15 * rep})
                    sid += 1
    return seeds


def recency_call(seed: dict, passages: list[dict], as_of: str) -> dict:
    sysp = RECENCY_SYSTEM.replace("{hop_count}", str(seed["hop_count"])).replace("{as_of}", as_of)
    lines = [f"SEED: cluster={seed['cluster']} hop_count={seed['hop_count']} (RECENCY, as of {as_of})",
             "", "RETRIEVED PASSAGES:"]
    for p in passages:
        lines.append(f"[source_id={p['source_id']}] title={p['title']!r} tier={p['source_tier']} "
                     f"wikidata_id={p['wikidata_id']}\n{p['text'][:700]}")
    resp = http_json(FW_URL, {
        "model": FW_MODEL, "temperature": seed.get("_temp", 0.4), "max_tokens": 12000,
        "messages": [{"role": "system", "content": sysp}, {"role": "user", "content": "\n\n".join(lines)}],
    }, headers={"Authorization": f"Bearer {os.environ['FIREWORKS_API_KEY']}"}, timeout=240)
    content = resp["choices"][0]["message"].get("content", "") or ""
    obj = _extract_json(content)
    return obj if obj is not None else {"rejection": True, "reason": "unparseable"}


def compose(seed: dict, topk: int, as_of: str) -> dict:
    try:
        passages = retrieve(seed["retrieval_query"], topk)
        comp = recency_call(seed, passages, as_of)
        if comp.get("rejection"):
            return {"seed_id": seed["seed_id"], "rejection": True, "reason": comp.get("reason", ""),
                    "cluster": seed["cluster"], "hop_count": seed["hop_count"], "temporal_sensitivity": "recency"}
        rec = assemble(seed, comp, passages, as_of)
        rec["seed_id"] = seed["seed_id"]
        rec["_audit"]["recent_date"] = comp.get("recent_date", "")
        return rec
    except Exception as exc:  # noqa: BLE001
        return {"seed_id": seed["seed_id"], "rejection": True, "reason": f"error: {exc}",
                "cluster": seed["cluster"], "hop_count": seed["hop_count"], "temporal_sensitivity": "recency"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", type=int, default=150, help="stop after this many composed survivors")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--as-of", default="2026-06-29")
    ap.add_argument("--out", type=Path, default=Path("data/t5_raw/recency.jsonl"))
    a = ap.parse_args()
    if "FIREWORKS_API_KEY" not in os.environ:
        for line in Path("/research/afwerk/.env").read_text().splitlines():
            if line.startswith("FIREWORKS_API_KEY"):
                os.environ["FIREWORKS_API_KEY"] = line.split("=", 1)[1].strip().strip('"')

    seeds = build_recency_seeds()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    done, n_ok = set(), 0
    if a.out.exists():
        for line in a.out.read_text().splitlines():
            if line.strip():
                r = json.loads(line); done.add(r.get("seed_id"))
                if not r.get("rejection"):
                    n_ok += 1
    todo = [s for s in seeds if s["seed_id"] not in done]
    print(f"recency seeds={len(seeds)} done={len(done)} todo={len(todo)} have_ok={n_ok} target={a.target}", flush=True)

    n_rej = 0
    with a.out.open("a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(compose, s, a.topk, a.as_of): s for s in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            if rec.get("rejection"):
                n_rej += 1
            else:
                n_ok += 1
            if i % 10 == 0:
                print(f"  attempted {i}/{len(todo)}  ok={n_ok} rej={n_rej}", flush=True)
            if n_ok >= a.target:
                print(f"  reached target {a.target}", flush=True)
                break
    print(f"DONE recency: composed={n_ok} rejected={n_rej} -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
