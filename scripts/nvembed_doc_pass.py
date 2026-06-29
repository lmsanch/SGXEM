#!/usr/bin/env python3
"""nvembed_doc_pass.py — fill the `nvembed` (NV-Embed-v2, 4096-D) named vector
for every point in a Qdrant collection (SGXEM-owned; the only net-new GPU compute).

Doc-side pass: encodes each point's passage text with instruction="" (asymmetric;
the query side uses the "Instruct: ... \nQuery: " prefix at retrieval time), then
writes the vector back onto the SAME point IDs via the Qdrant REST API
(`PUT /collections/<c>/points/vectors`). REST avoids needing qdrant_client in the
Spark embedding venv.

Reuses the validated recipe from afwerk/scripts/nvembed_encode_retrieve.py
(DynamicCache shim + bfloat16 + OOM-retry model load).

Run ON SPARK (model cached, GPU there; Qdrant is the dev box over tailscale):
  cd /home/luis/afwerk && HF_HOME=/home/luis/afwerk/.hfcache \
    PYTHONPATH=/home/luis/afwerk/.tf442 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /home/luis/faster-qwen3-tts/.venv/bin/python nvembed_doc_pass.py \
    --collection afwerk_defense_corpus --qdrant-url http://100.126.109.117:6333
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
DOC_INSTRUCTION = ""  # doc side is un-instructed (locked decision #2)


def rest(url: str, payload: dict | None = None, method: str = "POST") -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def scroll_all(base: str, collection: str, text_field: str) -> list[tuple]:
    """Return [(point_id, text), ...] for the whole collection."""
    out, offset = [], None
    while True:
        body = {"limit": 256, "with_payload": [text_field], "with_vector": False}
        if offset is not None:
            body["offset"] = offset
        res = rest(f"{base}/collections/{collection}/points/scroll", body)["result"]
        for p in res["points"]:
            out.append((p["id"], p["payload"].get(text_field, "")))
        offset = res.get("next_page_offset")
        if offset is None:
            break
    return out


def load_model(retries=8, wait=60):
    from transformers import AutoModel
    for i in range(retries):
        try:
            m = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True,
                                          torch_dtype=torch.bfloat16).cuda()
            m.eval()
            return m
        except torch.AcceleratorError as e:  # transient GPU contention
            if "out of memory" not in str(e).lower() or i == retries - 1:
                raise
            torch.cuda.empty_cache()
            print(f"[oom] model load attempt {i+1} failed; wait {wait}s", flush=True)
            time.sleep(wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collection", required=True)
    ap.add_argument("--qdrant-url", default="http://100.126.109.117:6333")
    ap.add_argument("--vector-name", default="nvembed")
    ap.add_argument("--text-field", default="text")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--upsert-batch", type=int, default=64)
    ap.add_argument("--normalize", action="store_true", default=True)
    a = ap.parse_args()
    base = a.qdrant_url.rstrip("/")

    rows = scroll_all(base, a.collection, a.text_field)
    ids = [r[0] for r in rows]
    texts = [r[1] or " " for r in rows]
    print(f"points={len(rows)} collection={a.collection}", flush=True)
    if not rows:
        print("nothing to embed")
        return

    model = load_model()
    t0 = time.time()
    vecs = []
    for i in range(0, len(texts), a.batch_size):
        with torch.no_grad():
            e = model.encode(texts[i:i + a.batch_size], instruction=DOC_INSTRUCTION,
                             max_length=a.max_length)
        if isinstance(e, torch.Tensor):
            e = e.float().cpu().numpy()
        vecs.append(e)
        if (i // a.batch_size) % 10 == 0:
            print(f"  encoded {min(i + a.batch_size, len(texts))}/{len(texts)}", flush=True)
    arr = np.vstack(vecs).astype(np.float32)
    if a.normalize:
        n = np.linalg.norm(arr, axis=1, keepdims=True); n[n == 0] = 1e-10
        arr = arr / n
    dim = arr.shape[1]
    print(f"encoded {arr.shape[0]} x {dim} in {time.time()-t0:.1f}s", flush=True)
    assert dim == 4096, f"expected 4096-D NV-Embed-v2, got {dim}"

    written = 0
    for i in range(0, len(ids), a.upsert_batch):
        pts = [{"id": pid, "vector": {a.vector_name: arr[j].tolist()}}
               for j, pid in enumerate(ids[i:i + a.upsert_batch], start=i)]
        rest(f"{base}/collections/{a.collection}/points/vectors?wait=true",
             {"points": pts}, method="PUT")
        written += len(pts)
        print(f"  wrote nvembed {written}/{len(ids)}", flush=True)
    print(f"DONE: nvembed written to {written} points in {a.collection}", flush=True)


if __name__ == "__main__":
    main()
