#!/usr/bin/env python3
"""SGXEM build validator — checks QA pairs against schema and defensibility rules."""

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "id", "question", "answer", "bridge_entity", "modality",
    "text_source", "artifact_path", "ablation_result",
    "red_team_verdict", "difficulty",
]
VALID_MODALITIES = {"thermal", "audio", "depth"}
VALID_VERDICTS = {"KEEP", "ADD_DISTRACTORS", "REWRITE", "DISCARD", "PLACEHOLDER"}
VALID_DIFFICULTIES = {"2-hop", "3-hop", "mixed-chain"}
VALID_ABLATION = {"INSUFFICIENT EVIDENCE", "INSUFFICIENT_INFORMATION", "PLACEHOLDER"}


def validate_pair(pair: dict) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in pair:
            errors.append(f"missing field: {field}")

    if pair.get("modality") not in VALID_MODALITIES:
        errors.append(f"invalid modality: {pair.get('modality')}")
    if pair.get("red_team_verdict") not in VALID_VERDICTS:
        errors.append(f"invalid red_team_verdict: {pair.get('red_team_verdict')}")
    if pair.get("difficulty") not in VALID_DIFFICULTIES:
        errors.append(f"invalid difficulty: {pair.get('difficulty')}")
    if pair.get("ablation_result") not in VALID_ABLATION:
        errors.append(f"invalid ablation_result (must be INSUFFICIENT EVIDENCE): {pair.get('ablation_result')}")

    if pair.get("bridge_entity", "").lower() in pair.get("question", "").lower():
        errors.append(f"bridge entity '{pair['bridge_entity']}' leaked into question text")

    return errors


def main():
    qa_path = Path(__file__).parent / "qa_pairs.jsonl"
    if not qa_path.exists():
        print("ERROR: qa_pairs.jsonl not found")
        sys.exit(1)

    pairs = []
    with open(qa_path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                pairs.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Line {i}: JSON parse error: {e}")
                sys.exit(1)

    total = len(pairs)
    errors_all = {}
    for pair in pairs:
        errs = validate_pair(pair)
        if errs:
            errors_all[pair.get("id", f"line-{pair}")] = errs

    modalities = {}
    verdicts = {}
    for pair in pairs:
        m = pair.get("modality", "unknown")
        modalities[m] = modalities.get(m, 0) + 1
        v = pair.get("red_team_verdict", "unknown")
        verdicts[v] = verdicts.get(v, 0) + 1

    print(f"SGXEM Validation Report")
    print(f"=======================")
    print(f"Total QA pairs: {total}")
    print(f"Modalities: {dict(modalities)}")
    print(f"Verdicts: {dict(verdicts)}")

    shipped = sum(1 for p in pairs if p.get("red_team_verdict") == "KEEP")
    placeholder = sum(1 for p in pairs if p.get("red_team_verdict") == "PLACEHOLDER")
    discarded = sum(1 for p in pairs if p.get("red_team_verdict") == "DISCARD")

    print(f"\nShipped (KEEP): {shipped}")
    print(f"Placeholders: {placeholder}")
    print(f"Discarded: {discarded}")

    if errors_all:
        print(f"\n❌ {len(errors_all)} pair(s) with errors:")
        for qid, errs in errors_all.items():
            print(f"  {qid}: {'; '.join(errs)}")
        sys.exit(1)
    else:
        print(f"\n✅ All {total} pairs pass validation.")

    bridge_entities = [p.get("bridge_entity", "") for p in pairs]
    unique_bridges = set(bridge_entities)
    if len(unique_bridges) < len(bridge_entities):
        from collections import Counter
        dupes = {k: v for k, v in Counter(bridge_entities).items() if v > 1}
        print(f"\n⚠️  Duplicate bridge entities: {dupes}")

    for p in pairs:
        ts = p.get("text_source", "")
        ts_path = Path(__file__).parent / "text_sources" / ts
        if not ts_path.exists():
            print(f"⚠️  Missing text source: {ts} (referenced by {p['id']})")


if __name__ == "__main__":
    main()
