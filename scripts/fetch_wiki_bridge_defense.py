#!/usr/bin/env python3
"""Drive afwerk's wiki_bridge fetcher over a defense entity-spec list (SGXEM-owned).

REUSE, don't rebuild: this imports `build_bridge_entry` from
afwerk/sgxem/wiki_bridge.py (the sanctioned Wikipedia/Wikidata fetcher + registry
writer) and feeds it our defense entity-spec list. wiki_bridge.py hardcodes its
own `BRIDGE_ENTITIES` (multimodal seeds) with no CLI to inject a list, so this
thin driver supplies the list and writes the same `bridge_corpus_report.json`
that `build_sgxem_hotspot_kms_records.py::build_wiki_bridge_records()` consumes.

Run from anywhere with afwerk importable:
  PYTHONPATH=/research/afwerk python scripts/fetch_wiki_bridge_defense.py \
      --entities data/defense_corpus/cluster1_venezuela_entities.jsonl \
      --corpus-dir data/defense_corpus
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sgxem.wiki_bridge import build_bridge_entry  # afwerk module (PYTHONPATH)


def load_specs(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--entities", type=Path, required=True,
                    help="entity-spec JSONL (entity, wikidata_id, type, domain, related_label)")
    ap.add_argument("--corpus-dir", type=Path, required=True,
                    help="defense corpus root; WIKI-*.txt go in <root>/corpus/wiki_bridge/")
    ap.add_argument("--registry", type=Path, default=None,
                    help="source registry JSONL (default <corpus-dir>/sgxem_source_registry.jsonl)")
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    wiki_dir = args.corpus_dir / "corpus" / "wiki_bridge"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    registry_path = args.registry or (args.corpus_dir / "sgxem_source_registry.jsonl")

    specs = load_specs(args.entities)
    print(f"Fetching {len(specs)} entities -> {wiki_dir}")

    results = []
    for i, spec in enumerate(specs, 1):
        if args.dry_run:
            print(f"[dry-run] {spec['entity']} (Q={spec.get('wikidata_id')})")
            continue
        entry = build_bridge_entry(spec, wiki_dir, registry_path, delay=args.delay)
        # Preserve our taxonomy fields for downstream tracking.
        entry.setdefault("cluster", spec.get("cluster", ""))
        entry.setdefault("sub_topic", spec.get("sub_topic", ""))
        results.append(entry)
        status = f"wiki={entry['wikipedia_status']}, wikidata={entry['wikidata_status']}"
        print(f"  [{i}/{len(specs)}] {spec['entity']}: {status}"
              + (f"  ERROR: {entry['error']}" if entry.get("error") else ""))

    if args.dry_run:
        return 0

    report_path = wiki_dir / "bridge_corpus_report.json"
    fetched = sum(1 for r in results
                  if r.get("wikipedia_status") in ("fetched", "already_staged"))
    failed = sum(1 for r in results if r.get("error"))
    report = {"total_entities": len(results), "fetched": fetched,
              "failed": failed, "results": results}
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(f"\nBridge corpus: {fetched}/{len(results)} fetched, {failed} failed")
    print(f"Report:   {report_path}")
    print(f"Registry: {registry_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
