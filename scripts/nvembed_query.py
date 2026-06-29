#!/usr/bin/env python3
"""nvembed_query.py — query the `nvembed` vector of a Qdrant collection (SGXEM-owned).

The T1 retrieval gate: encode a question with the asymmetric query instruction
("Instruct: Given a question, retrieve passages that answer the question\\nQuery: ")
and search the collection with using="nvembed". Loads NV-Embed-v2 once and runs
all queries from --in (amortizes the costly model load under GPU contention).

Run ON SPARK:
  cd /home/luis/afwerk && HF_HOME=/home/luis/afwerk/.hfcache \
    PYTHONPATH=/home/luis/afwerk/.tf442 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /home/luis/faster-qwen3-tts/.venv/bin/python nvembed_query.py \
    --in /tmp/gate_queries.jsonl --collection afwerk_defense_corpus \
    --qdrant-url http://100.126.109.117:6333 --topk 5 --out /tmp/gate_hits.json
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request

import numpy as np
import torch

from transformers import DynamicCache
if not hasattr(DynamicCache, "get_usable_length"):
    DynamicCache.get_usable_length = lambda self, *a, **kw: self.get_seq_length()

MODEL_NAME = "nvidia/NV-Embed-v2"
QUERY_INSTRUCTION = "Instruct: Given a question, retrieve passages that answer the question\nQuery: "


def rest(url: str, payload: dict, method: str = "POST") -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def load_model(retries=8, wait=60):
    from transformers import AutoModel
    for i in range(retries):
        try:
            m = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True,
                                          torch_dtype=torch.bfloat16).cuda()
            m.eval()
            return m
        except torch.AcceleratorError as e:
            if "out of memory" not in str(e).lower() or i == retries - 1:
                raise
            torch.cuda.empty_cache()
            print(f"[oom] model load attempt {i+1} failed; wait {wait}s", flush=True)
            time.sleep(wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="jsonl {id,text} per line")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--qdrant-url", default="http://100.126.109.117:6333")
    ap.add_argument("--vector-name", default="nvembed")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--max-length", type=int, default=128)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    base = a.qdrant_url.rstrip("/")

    rows = [json.loads(l) for l in open(a.inp) if l.strip()]
    model = load_model()

    results = {}
    for r in rows:
        with torch.no_grad():
            e = model.encode([r["text"]], instruction=QUERY_INSTRUCTION, max_length=a.max_length)
        if isinstance(e, torch.Tensor):
            e = e.float().cpu().numpy()
        v = e[0].astype(np.float32)
        v = v / (np.linalg.norm(v) or 1e-10)
        body = {"vector": {"name": a.vector_name, "vector": v.tolist()},
                "limit": a.topk, "with_payload": ["title", "wikidata_id", "related_label"]}
        hits = rest(f"{base}/collections/{a.collection}/points/search", body)["result"]
        results[r["id"]] = [
            {"title": h["payload"].get("title"), "score": round(h["score"], 4),
             "wikidata_id": h["payload"].get("wikidata_id"),
             "sub_topic": h["payload"].get("related_label")}
            for h in hits
        ]
        top = results[r["id"]][0] if results[r["id"]] else {}
        print(f"[{r['id']}] {r['text'][:60]!r} -> {top.get('title')} ({top.get('score')})", flush=True)

    json.dump(results, open(a.out, "w"), ensure_ascii=False, indent=2)
    print(f"saved {len(results)} -> {a.out}", flush=True)


if __name__ == "__main__":
    main()
