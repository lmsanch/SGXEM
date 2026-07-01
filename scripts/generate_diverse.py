#!/usr/bin/env python3
"""generate_diverse.py — round-based composer with LIVE answer-dedup (SGXEM-owned).

Discards repeated answers WHILE generating (not just post-hoc): each round counts accepted
answers, and any answer already at the cap is (a) skipped if a new composition repeats it and
(b) fed into the next round's compose prompt as a "do NOT use these answers" avoid-list — so
the model is pushed toward NEW facts in real time. Diverse mined anchors at the source keep
retrieval varied. Output = accepted raw compositions (gate + curate run downstream).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compose_one import retrieve, call_glm, assemble  # noqa: E402

HOPW = [(2, 0.40), (3, 0.35), (4, 0.25)]


def norm(a: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", str(a).lower())).strip()


def seed_pool(cluster: str, anchors: list[str], recency_frac: float = 0.4) -> list[dict]:
    seeds, sid = [], 0
    rthr = round(recency_frac * 10)
    hops = [h for h, w in HOPW for _ in range(int(w * 20))]  # 8x2,7x3,5x4 pattern
    for ai, q in enumerate(anchors):
        for k in range(2):
            hop = hops[(ai * 2 + k) % len(hops)]
            rec = ((ai * 2 + k) % 10) < rthr  # recency fraction (the knockout axis)
            seeds.append({"seed_id": f"{cluster[:2].upper()}{sid:05d}", "cluster": cluster,
                          "sub_topic": "recency" if rec else "general", "bridge_type": "entity_bridge",
                          "hop_count": hop, "retrieval_query": (q + (" 2025 2026 latest" if rec else "")),
                          "source_reliability": "medium" if rec else "high",
                          "temporal_sensitivity": "recency" if rec else "timeless", "seq": sid})
            sid += 1
    return seeds


def compose_seed(seed: dict, avoid: list[str], topk: int, as_of: str) -> dict:
    try:
        seed = {**seed, "avoid_answers": avoid}
        passages = retrieve(seed["retrieval_query"], topk)
        comp = call_glm(seed, passages)
        if comp.get("rejection"):
            return {"seed_id": seed["seed_id"], "rejection": True, "reason": comp.get("reason", "")}
        rec = assemble(seed, comp, passages, as_of)
        rec["seed_id"] = seed["seed_id"]
        return rec
    except Exception as exc:  # noqa: BLE001
        return {"seed_id": seed["seed_id"], "rejection": True, "reason": f"error: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clusters", default="venezuela,iran,taiwan,cuba,brazil")
    ap.add_argument("--anchors", type=Path, default=Path("data/t5_raw/all_anchors.json"))
    ap.add_argument("--accept-per-cluster", type=int, default=120, help="raw accepts/cluster (oversample for gating)")
    ap.add_argument("--per-answer", type=int, default=2)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--round-size", type=int, default=24)
    ap.add_argument("--topk", type=int, default=10)
    ap.add_argument("--as-of", default="2026-06-29")
    ap.add_argument("--recency-frac", type=float, default=0.4)
    ap.add_argument("--seed-avoid", type=Path, default=None,
                    help="JSON list of answers to pre-avoid (e.g. an existing batch's answers)")
    ap.add_argument("--out", type=Path, default=Path("data/t5_raw/breadth.jsonl"))
    a = ap.parse_args()
    if "FIREWORKS_API_KEY" not in os.environ:
        for line in Path("/research/afwerk/.env").read_text().splitlines():
            if line.startswith("FIREWORKS_API_KEY"):
                os.environ["FIREWORKS_API_KEY"] = line.split("=", 1)[1].strip().strip('"')
    anchors = json.loads(a.anchors.read_text())
    avoid_seed = [norm(x) for x in json.loads(a.seed_avoid.read_text())] if a.seed_avoid else []

    a.out.parent.mkdir(parents=True, exist_ok=True)
    # resume: load prior accepted answers per cluster
    ans_count: dict[str, Counter] = {}
    done_seed: set[str] = set()
    if a.out.exists():
        for line in a.out.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line); done_seed.add(r.get("seed_id"))
            if not r.get("rejection"):
                ans_count.setdefault(r["cluster"], Counter())[norm(r["answer"])] += 1

    fout = a.out.open("a", encoding="utf-8")
    for cluster in a.clusters.split(","):
        cnt = ans_count.setdefault(cluster, Counter())
        accepted = sum(cnt.values())                # real accepts from resume (0 for a fresh file)
        for av in avoid_seed:                       # pre-seed existing-batch answers at cap -> avoided (not counted)
            cnt[av] = max(cnt[av], a.per_answer)
        pool = [s for s in seed_pool(cluster, anchors.get(cluster, []), a.recency_frac) if s["seed_id"] not in done_seed]
        print(f"[{cluster}] pool={len(pool)} already_accepted={accepted} target={a.accept_per_cluster}", flush=True)
        pi = 0
        while accepted < a.accept_per_cluster and pi < len(pool):
            batch = pool[pi:pi + a.round_size]; pi += a.round_size
            avoid = [an for an, c in cnt.items() if c >= a.per_answer]
            with ThreadPoolExecutor(max_workers=a.workers) as ex:
                futs = [ex.submit(compose_seed, s, avoid, a.topk, a.as_of) for s in batch]
                for fut in as_completed(futs):
                    rec = fut.result()
                    if rec.get("rejection"):
                        fout.write(json.dumps(rec, ensure_ascii=False) + "\n"); continue
                    ak = norm(rec["answer"])
                    if cnt[ak] >= a.per_answer:           # live dedup: discard repeat
                        rec["rejection"] = True; rec["reason"] = f"answer-cap repeat: {ak[:40]}"
                        fout.write(json.dumps(rec, ensure_ascii=False) + "\n"); continue
                    cnt[ak] += 1; accepted += 1
                    fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fout.flush()
            print(f"  [{cluster}] accepted={accepted}/{a.accept_per_cluster} distinct_answers={len(cnt)} "
                  f"pool@{pi}/{len(pool)} avoid={len(avoid)}", flush=True)
        print(f"[{cluster}] DONE accepted={accepted} distinct_answers={len(cnt)}", flush=True)
    fout.close()
    print(f"DONE breadth -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
