#!/usr/bin/env python3
"""verify_hops_nli.py — per-hop MiniCheck gate (SGXEM-owned). Runs ON SPARK.

For each composed record, verify every decomposition hop's sub-answer is entailed by its
cited passage (paragraphs[paragraph_support_idx]). Sets gate.nli_all_hops_entailed and a
per-hop `_nli` list. Pure file in/out (no Qdrant) so it's safe to run on Spark.

  HF_HOME=/home/luis/afwerk/.hfcache PYTHONPATH=/home/luis/kms \
    /home/luis/ir-training-venv/bin/python verify_hops_nli.py --in recs.jsonl --out recs.nli.jsonl
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="flan-t5-large")
    a = ap.parse_args()

    recs = [json.loads(l) for l in a.inp.read_text().splitlines() if l.strip()]
    claims, sources, owner = [], [], []   # owner[i] = (rec_index, hop_index)
    for ri, r in enumerate(recs):
        if r.get("rejection"):
            continue
        paras = r.get("paragraphs", [])
        for hi, h in enumerate(r.get("question_decomposition", [])):
            idx = h.get("paragraph_support_idx", -1)
            if not (isinstance(idx, int) and 0 <= idx < len(paras)):
                owner.append((ri, hi)); claims.append("x"); sources.append("")  # will fail -> not entailed
                continue
            q = str(h.get("question", "")).rstrip("?").strip()
            ans = str(h.get("answer", "")).strip()
            claims.append(f"{q}: {ans}")
            sources.append(paras[idx].get("paragraph_text", ""))
            owner.append((ri, hi))

    print(f"[load] {len(recs)} records, {len(claims)} hop-claims", flush=True)
    from services.triple_extraction.nli_verifier import NLIVerifier
    v = NLIVerifier(model=a.model, batch_size=32)
    results = v.verify(claims=claims, sources=sources) if claims else []

    per_rec: dict[int, dict[int, bool]] = {}
    for (ri, hi), res in zip(owner, results):
        ok = bool(getattr(res, "supported", getattr(res, "entailed", False)))
        per_rec.setdefault(ri, {})[hi] = ok

    n_pass = 0
    for ri, r in enumerate(recs):
        if r.get("rejection"):
            continue
        flags = per_rec.get(ri, {})
        nhop = len(r.get("question_decomposition", []))
        all_ok = nhop > 0 and all(flags.get(hi, False) for hi in range(nhop))
        r.setdefault("gate", {})["nli_all_hops_entailed"] = all_ok
        r["_nli"] = [flags.get(hi, False) for hi in range(nhop)]
        n_pass += 1 if all_ok else 0

    a.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
    composed = sum(1 for r in recs if not r.get("rejection"))
    print(f"[nli] all-hops-entailed: {n_pass}/{composed} composed records -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
