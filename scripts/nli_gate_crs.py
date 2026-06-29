#!/usr/bin/env python3
"""nli_gate_crs.py — T2 gate: MiniCheck NLI verifies CRS-passage claims (SGXEM-owned).

Samples CRS points from afwerk_defense_corpus (each carrying RELiK `triples` + text),
verbalizes one triple per passage into a claim, and runs KMS's NLIVerifier
(MiniCheck-Flan-T5-Large) to check entailment against the source passage. Reports the
supported-rate over the sample.

Run ON SPARK (model cached, kms importable):
  HF_HOME=/home/luis/afwerk/.hfcache PYTHONPATH=/home/luis/kms \
    /home/luis/faster-qwen3-tts/.venv/bin/python nli_gate_crs.py \
    --qdrant-url http://100.126.109.117:6333 --sample 15
"""
from __future__ import annotations

import argparse
import json
import urllib.request


def rest(url: str, payload: dict, method: str = "POST") -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def verbalize(t: dict) -> str | None:
    s = t.get("subject") or t.get("s") or t.get("head")
    p = t.get("predicate") or t.get("p") or t.get("relation")
    o = t.get("object") or t.get("o") or t.get("tail")
    if not (s and p and o):
        return None
    return f"{s} {str(p).replace('_', ' ')} {o}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--collection", default="afwerk_defense_corpus")
    ap.add_argument("--qdrant-url", default="http://100.126.109.117:6333")
    ap.add_argument("--source-type", default="crs")
    ap.add_argument("--sample", type=int, default=15)
    ap.add_argument("--model", default="flan-t5-large")
    a = ap.parse_args()
    base = a.qdrant_url.rstrip("/")

    # scroll CRS points with triples + text, collect first verbalizable triple per passage
    claims, sources, meta = [], [], []
    offset = None
    while len(claims) < a.sample:
        body = {"limit": 256, "with_payload": ["text", "triples", "title", "source_type"],
                "with_vector": False,
                "filter": {"must": [{"key": "source_type", "match": {"value": a.source_type}}]}}
        if offset is not None:
            body["offset"] = offset
        res = rest(f"{base}/collections/{a.collection}/points/scroll", body)["result"]
        for p in res["points"]:
            pl = p["payload"]
            text = (pl.get("text") or "").strip()
            for t in (pl.get("triples") or []):
                claim = verbalize(t) if isinstance(t, dict) else None
                if claim and len(text) > 100:
                    claims.append(claim)
                    sources.append(f"{pl.get('title','')}. {text}".strip())
                    meta.append({"id": p["id"], "title": pl.get("title", "")})
                    break
            if len(claims) >= a.sample:
                break
        offset = res.get("next_page_offset")
        if offset is None:
            break

    print(f"[load] {len(claims)} CRS claims to verify")
    if not claims:
        print("[warn] no verifiable CRS triples found")
        return 1

    from services.triple_extraction.nli_verifier import NLIVerifier
    print(f"[model] loading NLIVerifier({a.model}) ...", flush=True)
    v = NLIVerifier(model=a.model, batch_size=16)
    results = v.verify(claims=claims, sources=sources)

    sup = 0
    for i, r in enumerate(results):
        ok = getattr(r, "supported", getattr(r, "entailed", None))
        sup += 1 if ok else 0
        print(f"  [{'OK ' if ok else 'NO '}] {claims[i][:80]!r}  ({meta[i]['title'][:40]})")
    rate = 100.0 * sup / len(results)
    print(f"\nT2 NLI gate: supported {sup}/{len(results)} = {rate:.0f}%  (model={a.model})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
