#!/usr/bin/env python3
"""compose_batch.py — T5 batch GHQB runner (SGXEM-owned).

Generates a distribution-correct seed list (cluster 40/15/15/15/15, hop 40/35/25,
over-weighted temporal_sensitivity=recency), then concurrently composes each via
GLM-5.2 (reusing compose_one). Resume-safe: appends raw records to a JSONL keyed by
seed_id; reject-on-insufficient records are logged, not dropped (so the HTML can show
them). Per-hop MiniCheck (verify_hops_nli.py) and emit/HTML are separate stages.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose_one import retrieve, call_glm, assemble  # noqa: E402
from generate_seeds import TEMPLATES, CLUSTER_WEIGHT, HOP_WEIGHT, alloc  # noqa: E402

# recency retrieval angles per cluster — target post-cutoff facts the dated CRS/wiki carry
RECENCY = {
    "venezuela": [
        ("event_to_actor", "Venezuela 2026 Organic Hydrocarbons Law amendment OFAC general license latest sanctions"),
        ("person_to_role", "Venezuela current government official 2026 acting president minister latest"),
        ("org_to_country", "Venezuela 2025 2026 oil exports vessel seizures latest enforcement"),
    ],
    "iran": [
        ("org_to_location", "Iran 2025 uranium enrichment level IAEA latest report current stockpile"),
        ("entity_to_designation", "Iran 2025 2026 latest sanctions designation petrochemical drone"),
    ],
    "taiwan": [
        ("event_to_actor", "Taiwan 2025 2026 latest US arms sale package current administration"),
        ("person_to_role", "Taiwan current president 2026 cross-strait latest"),
    ],
    "cuba": [
        ("event_to_actor", "Cuba 2025 2026 latest US policy change sanctions current designation"),
    ],
    "brazil": [
        ("event_to_actor", "Brazil 2025 2026 latest Amazon deforestation enforcement current policy"),
        ("org_to_country", "Brazil 2025 2026 latest defense cooperation agreement current"),
    ],
}


def build_seeds(target: int, recency_frac: float) -> list[dict]:
    """Distribution-correct seed list of ~target items."""
    counts = alloc(target, [CLUSTER_WEIGHT[c] for c in CLUSTER_WEIGHT])
    seeds, sid = [], 0
    for cluster, cn in zip(CLUSTER_WEIGHT, counts):
        n_rec = int(round(cn * recency_frac))
        subs = list(TEMPLATES[cluster].keys())
        # timeless seeds
        ti_count = cn - n_rec
        sub_alloc = alloc(ti_count, [1 / len(subs)] * len(subs))
        for sub, sc in zip(subs, sub_alloc):
            hops = alloc(sc, [w for _, w in HOP_WEIGHT])
            tmpls = TEMPLATES[cluster][sub]
            ti = 0
            for (hop, _), hc in zip(HOP_WEIGHT, hops):
                for _ in range(hc):
                    bt, q = tmpls[ti % len(tmpls)]; ti += 1
                    seeds.append({"seed_id": f"S{sid:05d}", "cluster": cluster, "sub_topic": sub,
                                  "bridge_type": bt, "hop_count": hop, "retrieval_query": q,
                                  "source_reliability": "high", "temporal_sensitivity": "timeless",
                                  "seq": sid}); sid += 1
        # recency seeds
        rec_tmpls = RECENCY[cluster]
        hops_r = alloc(n_rec, [w for _, w in HOP_WEIGHT])
        ri = 0
        for (hop, _), hc in zip(HOP_WEIGHT, hops_r):
            for _ in range(hc):
                bt, q = rec_tmpls[ri % len(rec_tmpls)]; ri += 1
                seeds.append({"seed_id": f"S{sid:05d}", "cluster": cluster, "sub_topic": "recency",
                              "bridge_type": bt, "hop_count": hop, "retrieval_query": q,
                              "source_reliability": "medium", "temporal_sensitivity": "recency",
                              "seq": sid}); sid += 1
    return seeds


def compose_seed(seed: dict, topk: int, as_of: str) -> dict:
    try:
        passages = retrieve(seed["retrieval_query"], topk)
        comp = call_glm(seed, passages)
        if comp.get("rejection"):
            return {"seed_id": seed["seed_id"], "rejection": True, "reason": comp.get("reason", ""),
                    "cluster": seed["cluster"], "hop_count": seed["hop_count"],
                    "temporal_sensitivity": seed["temporal_sensitivity"]}
        rec = assemble(seed, comp, passages, as_of)
        rec["seed_id"] = seed["seed_id"]
        return rec
    except Exception as exc:  # noqa: BLE001
        return {"seed_id": seed["seed_id"], "rejection": True, "reason": f"error: {exc}",
                "cluster": seed["cluster"], "hop_count": seed["hop_count"],
                "temporal_sensitivity": seed["temporal_sensitivity"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", type=int, default=2000)
    ap.add_argument("--recency-frac", type=float, default=0.30)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--as-of", default="2026-06-29")
    ap.add_argument("--out", type=Path, default=Path("data/t5_raw/compositions.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="pilot: only first N seeds")
    a = ap.parse_args()

    # load Fireworks key
    if "FIREWORKS_API_KEY" not in os.environ:
        for envf in ("/research/afwerk/.env", "/research/kms/.env"):
            for line in Path(envf).read_text().splitlines() if Path(envf).exists() else []:
                if line.startswith("FIREWORKS_API_KEY"):
                    os.environ["FIREWORKS_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
    assert os.environ.get("FIREWORKS_API_KEY"), "FIREWORKS_API_KEY not found"

    seeds = build_seeds(a.target, a.recency_frac)
    if a.limit:
        seeds = seeds[:a.limit]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if a.out.exists():
        for line in a.out.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line).get("seed_id"))
    todo = [s for s in seeds if s["seed_id"] not in done]
    print(f"seeds={len(seeds)} done={len(done)} todo={len(todo)} workers={a.workers}", flush=True)

    n_ok = n_rej = 0
    with a.out.open("a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(compose_seed, s, a.topk, a.as_of): s for s in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            if rec.get("rejection"):
                n_rej += 1
            else:
                n_ok += 1
            if i % 10 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)}  ok={n_ok} rej={n_rej}", flush=True)
    print(f"DONE: composed={n_ok} rejected={n_rej} -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
