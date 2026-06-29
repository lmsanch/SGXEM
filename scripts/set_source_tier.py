#!/usr/bin/env python3
"""set_source_tier.py — stamp `source_tier` onto every point from `source_type` (SGXEM-owned).

The MuSiQue output gate enforces paragraphs[].source_tier ∈
{wikipedia,crs,ofac,institutional,sgx_owned}. The afwerk records carry `source_type`
but not `source_tier`; this SGXEM-owned payload patch derives the tier and writes it
back via Qdrant set_payload. Idempotent.
"""
from __future__ import annotations

import argparse
import os

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

# source_type (afwerk record) -> source_tier (MuSiQue citable tier)
TIER = {
    "wikipedia": "wikipedia",
    "wikidata": "wikipedia",
    "crs": "crs",
    "ofac": "ofac",
    "institutional": "institutional",
    "world_bank": "institutional",
    "imf": "institutional",
    "sgx_owned": "sgx_owned",
    "venezuelan_assets": "sgx_owned",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--collection", default="afwerk_defense_corpus")
    ap.add_argument("--host", default=os.getenv("QDRANT_HOST", "localhost"))
    ap.add_argument("--port", type=int, default=6333)
    a = ap.parse_args()
    c = QdrantClient(host=a.host, port=a.port, timeout=120)

    # discover the source_types present
    seen: dict[str, int] = {}
    offset = None
    while True:
        pts, offset = c.scroll(a.collection, limit=1000, with_payload=["source_type"],
                               with_vectors=False, offset=offset)
        for p in pts:
            st = (p.payload or {}).get("source_type", "")
            seen[st] = seen.get(st, 0) + 1
        if offset is None:
            break
    print("source_type counts:", seen)

    total = 0
    for st, n in seen.items():
        tier = TIER.get(st)
        if not tier:
            print(f"  ! no tier mapping for source_type={st!r} ({n} pts) — skipped")
            continue
        c.set_payload(
            collection_name=a.collection,
            payload={"source_tier": tier},
            points=Filter(must=[FieldCondition(key="source_type", match=MatchValue(value=st))]),
        )
        print(f"  set source_tier={tier} on {n} pts (source_type={st})")
        total += n
    print(f"DONE: source_tier set on {total} points")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
