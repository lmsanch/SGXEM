#!/usr/bin/env python3
"""emit_benchmark.py — freeze the 2-file deliverable (SGXEM-owned, per AFWERK contract).

From composed+gated records, emit exactly what AFWERK consumes:
  1. afwerk_defense_benchmark.jsonl   (canonical, one record/line — the hashed artifact)
  2. afwerk_defense_benchmark.json    (same records, JSON array — what eval_kms_reader_f1 loads)
  3. afwerk_defense_corpus.json       ([{title,text}], de-duped union of every record's
                                       paragraphs; supporting paragraph_text appears verbatim
                                       — the gold-match join key)
Drops internal fields (_audit, seed_id). Optionally gates on nli_all_hops_entailed.
Prints the SHA-256 of the .jsonl for pre-registration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

PUBLISH_FIELDS = ["id", "question", "answer", "answer_aliases", "paragraphs",
                  "question_decomposition", "cluster", "sub_topic", "hop_count",
                  "modality", "source_reliability", "as_of", "temporal_sensitivity", "gate"]


def expand_aliases(answer: str, aliases: list[str]) -> list[str]:
    """Add common surface variants (abbreviations) so SQuAD-norm + aliases match."""
    s = set(a.strip() for a in aliases if a and a.strip())
    s.add(answer.strip())
    m = re.search(r"\b(?:E\.?O\.?|Executive Order)\s*(\d{4,5})\b", answer, re.I)
    if m:
        n = m.group(1)
        s.update({f"E.O. {n}", f"EO {n}", f"Executive Order {n}", n})
    return [x for x in dict.fromkeys([answer.strip(), *sorted(s)]) if x]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True, help="composed records jsonl")
    ap.add_argument("--outdir", type=Path, default=Path("data"))
    ap.add_argument("--require-nli", action="store_true", help="keep only gate.nli_all_hops_entailed==true")
    ap.add_argument("--name", default="afwerk_defense_benchmark")
    a = ap.parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from build import validate_musique  # noqa: E402

    recs = [json.loads(l) for l in a.inp.read_text().splitlines() if l.strip()]
    kept, n_build_fail = [], 0
    for r in recs:
        if r.get("rejection"):
            continue
        if a.require_nli and r.get("gate", {}).get("nli_all_hops_entailed") is not True:
            continue
        r["answer_aliases"] = expand_aliases(r.get("answer", ""), r.get("answer_aliases", []))
        pub = {k: r[k] for k in PUBLISH_FIELDS if k in r}
        if validate_musique(pub):       # build.py schema/defensibility gate
            n_build_fail += 1
            continue
        kept.append(pub)

    # global corpus: de-duped union of all paragraphs (text is the join key)
    corpus, seen = [], {}
    for r in kept:
        for p in r["paragraphs"]:
            t = p["paragraph_text"]
            if t not in seen:
                seen[t] = len(corpus)
                corpus.append({"title": p.get("title", ""), "text": t})

    # verify every supporting paragraph_text is in the corpus verbatim
    missing = 0
    for r in kept:
        for p in r["paragraphs"]:
            if p.get("is_supporting") and p["paragraph_text"] not in seen:
                missing += 1

    a.outdir.mkdir(parents=True, exist_ok=True)
    jsonl_path = a.outdir / f"{a.name}.jsonl"
    json_path = a.outdir / f"{a.name}.json"
    corpus_path = a.outdir / "afwerk_defense_corpus.json"
    jsonl_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept), encoding="utf-8")
    json_path.write_text(json.dumps(kept, ensure_ascii=False, indent=0), encoding="utf-8")
    corpus_path.write_text(json.dumps(corpus, ensure_ascii=False, indent=0), encoding="utf-8")

    sha = hashlib.sha256(jsonl_path.read_bytes()).hexdigest()
    cl = Counter(r["cluster"] for r in kept)
    hp = Counter(r["hop_count"] for r in kept)
    tp = Counter(r["temporal_sensitivity"] for r in kept)
    print(f"kept {len(kept)}/{len(recs)} records  | corpus {len(corpus)} passages  | "
          f"verbatim-join missing={missing}  | build.py-dropped={n_build_fail}")
    print(f"  cluster {dict(cl)}  hop {dict(hp)}  temporal {dict(tp)}")
    print(f"  {jsonl_path}\n  {json_path}\n  {corpus_path}")
    print(f"SHA-256 ({jsonl_path.name}): {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
