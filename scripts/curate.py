#!/usr/bin/env python3
"""curate.py — quality + diversity curation (SGXEM-owned).

Keeps only ALL-GREEN records (nli_all_hops_entailed AND not red_team_breakable AND not
single_passage_sufficient AND not forced_link AND build.py-clean), then enforces diversity:
  - at most 2 questions per distinct (normalized) answer
  - drops near-duplicate questions (token-Jaccard >= threshold)
Writes the curated set and a used-answers tally (so the next generation round can AVOID
already-used answers). Rejections and non-green records are dropped entirely.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build import validate_musique  # noqa: E402

PUB = ["id", "question", "answer", "answer_aliases", "paragraphs", "question_decomposition",
       "cluster", "sub_topic", "hop_count", "modality", "source_reliability", "as_of",
       "temporal_sensitivity", "gate"]


def norm_ans(a: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", str(a).lower())).strip()


def toks(q: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", q.lower()))


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--per-answer", type=int, default=2)
    ap.add_argument("--qsim", type=float, default=0.85, help="drop a question if Jaccard>=this vs a kept one")
    a = ap.parse_args()

    recs = [json.loads(l) for l in a.inp.read_text().splitlines() if l.strip()]
    # green only
    green = [r for r in recs if not r.get("rejection") and r.get("_audit", {}).get("green") is True]
    # build.py clean (defensive)
    green = [r for r in green if not validate_musique({k: r[k] for k in PUB if k in r})]
    # prefer keeping 2-hop... no: prefer diversity — keep in given order but cap per answer + dedup q
    ans_count: Counter = Counter()
    kept, kept_sigs = [], []
    n_ans_cap = n_qdup = 0
    for r in green:
        ak = norm_ans(r["answer"])
        if ans_count[ak] >= a.per_answer:
            n_ans_cap += 1
            continue
        sig = toks(r["question"])
        if any(jaccard(sig, s) >= a.qsim for s in kept_sigs):
            n_qdup += 1
            continue
        ans_count[ak] += 1
        kept_sigs.append(sig)
        kept.append({k: r[k] for k in PUB if k in r})

    a.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
    used = sorted({norm_ans(r["answer"]) for r in kept})
    (a.out.with_suffix(".used_answers.json")).write_text(json.dumps(used, ensure_ascii=False, indent=0))

    cl = Counter(r["cluster"] for r in kept)
    hp = Counter(r["hop_count"] for r in kept)
    tp = Counter(r["temporal_sensitivity"] for r in kept)
    print(f"in={len(recs)} green={len(green)} -> kept {len(kept)} "
          f"(dropped: answer-cap {n_ans_cap}, q-dup {n_qdup})")
    print(f"  distinct answers={len(set(norm_ans(r['answer']) for r in kept))}  "
          f"cluster {dict(cl)}  hop {dict(hp)}  temporal {dict(tp)}")
    print(f"  -> {a.out}  (+ used_answers list)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
