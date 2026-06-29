#!/usr/bin/env python3
"""Pre-create the 3-vector `afwerk_defense_corpus` Qdrant collection (SGXEM-owned).

SGXEM owns the collection schema + the NV-Embed pass (locked decision #3). The
afwerk ingest runs UNMODIFIED and WITHOUT --recreate against this pre-created
collection; `create_collection_if_needed` is create-if-not-exists, so the
3-vector schema survives ingest (which only writes mxbai+qwen3vl).

Named vectors:
  mxbai   1024  COSINE   (afwerk ingest)
  qwen3vl 1024  COSINE   (afwerk ingest)
  nvembed 4096  COSINE   (SGXEM NV-Embed-v2 pass; headline retrieval vector)

Qdrant host comes from $QDRANT_HOST (default localhost) — the canonical Qdrant is
the dev box localhost:6333; 100.115.144.22 (the afwerk default) is decommissioned.
"""

from __future__ import annotations

import argparse
import os

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

VECTORS = {
    "mxbai": VectorParams(size=1024, distance=Distance.COSINE),
    "qwen3vl": VectorParams(size=1024, distance=Distance.COSINE),
    "nvembed": VectorParams(size=4096, distance=Distance.COSINE),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--collection", default="afwerk_defense_corpus")
    ap.add_argument("--host", default=os.getenv("QDRANT_HOST", "localhost"))
    ap.add_argument("--port", type=int, default=int(os.getenv("QDRANT_PORT", "6333")))
    ap.add_argument("--recreate", action="store_true",
                    help="DANGER: delete + recreate. Not used in normal flow.")
    args = ap.parse_args()

    client = QdrantClient(host=args.host, port=args.port, timeout=60)
    existing = {c.name for c in client.get_collections().collections}

    if args.collection in existing:
        if args.recreate:
            client.delete_collection(args.collection)
            existing.discard(args.collection)
        else:
            info = client.get_collection(args.collection)
            cfg = info.config.params.vectors
            names = sorted(cfg.keys()) if isinstance(cfg, dict) else [str(cfg)]
            print(f"EXISTS: {args.collection} already present (vectors={names}); "
                  f"points={info.points_count}. No-op.")
            return 0

    client.create_collection(
        collection_name=args.collection,
        vectors_config=VECTORS,
        on_disk_payload=True,
    )
    info = client.get_collection(args.collection)
    cfg = info.config.params.vectors
    cfg = cfg if isinstance(cfg, dict) else {}
    report = {name: f"{vp.size}d/{vp.distance}" for name, vp in cfg.items()}
    print(f"CREATED: {args.collection} on {args.host}:{args.port} "
          f"on_disk_payload=True vectors={report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
