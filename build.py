#!/usr/bin/env python3
"""SGXEM build validator — schema + defensibility rules.

Two schemas:
  • MuSiQue defense records (the output contract) -> data/afwerk_defense_benchmark.jsonl
  • legacy multimodal QA pairs                    -> qa_pairs.jsonl
main() validates the MuSiQue file if present, else falls back to the legacy file.
"""

import json
import re
import sys
from pathlib import Path

# ───────────────────────── MuSiQue defense schema (T5/T6) ─────────────────────────
MUSIQUE_REQUIRED = [
    "id", "question", "answer", "answer_aliases", "paragraphs",
    "question_decomposition", "cluster", "sub_topic", "hop_count",
    "modality", "source_reliability", "gate", "as_of", "temporal_sensitivity",
]
VALID_CLUSTERS = {"venezuela", "iran", "taiwan", "cuba", "brazil", "supply_chain"}
VALID_MODALITY = {"text", "audio", "depth", "thermal"}
VALID_RELIABILITY = {"high", "medium", "low"}
VALID_TEMPORAL = {"timeless", "recency"}          # the as-of temporal split
CITABLE_TIERS = {"wikipedia", "crs", "ofac", "institutional", "sgx_owned"}
GATE_KEYS = {"red_team_breakable", "nli_all_hops_entailed", "single_passage_sufficient"}
AS_OF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_musique(rec: dict) -> list[str]:
    e: list[str] = []
    for f in MUSIQUE_REQUIRED:
        if f not in rec:
            e.append(f"missing field: {f}")
    if e:
        return e  # bail early; downstream checks assume fields exist

    if rec["cluster"] not in VALID_CLUSTERS:
        e.append(f"invalid cluster: {rec['cluster']}")
    if rec["modality"] not in VALID_MODALITY:
        e.append(f"invalid modality: {rec['modality']}")
    if rec["source_reliability"] not in VALID_RELIABILITY:
        e.append(f"invalid source_reliability: {rec['source_reliability']}")
    if rec["temporal_sensitivity"] not in VALID_TEMPORAL:
        e.append(f"invalid temporal_sensitivity: {rec['temporal_sensitivity']}")
    if not (isinstance(rec["hop_count"], int) and rec["hop_count"] in (2, 3, 4)):
        e.append(f"invalid hop_count (int 2/3/4): {rec['hop_count']}")
    if not (isinstance(rec["as_of"], str) and AS_OF_RE.match(rec["as_of"])):
        e.append(f"invalid as_of (YYYY-MM-DD): {rec.get('as_of')}")
    if not isinstance(rec["answer_aliases"], list):
        e.append("answer_aliases must be a list")

    # gate object
    gate = rec.get("gate", {})
    if not isinstance(gate, dict) or set(gate) != GATE_KEYS:
        e.append(f"gate must have exactly keys {sorted(GATE_KEYS)}")

    # paragraphs: citable tiers, supporting set, indices
    paras = rec["paragraphs"]
    if not isinstance(paras, list) or not paras:
        e.append("paragraphs must be a non-empty list")
    else:
        for p in paras:
            tier = p.get("source_tier")
            if tier not in CITABLE_TIERS:
                e.append(f"paragraph idx={p.get('idx')} source_tier not citable: {tier}")
            for k in ("idx", "title", "paragraph_text", "is_supporting"):
                if k not in p:
                    e.append(f"paragraph idx={p.get('idx')} missing {k}")
        if not any(p.get("is_supporting") for p in paras):
            e.append("no supporting paragraph (is_supporting=true) present")

    # decomposition: length == hop_count, indices valid, bridge_qid present
    decomp = rec["question_decomposition"]
    n_para = len(paras) if isinstance(paras, list) else 0
    if not isinstance(decomp, list) or len(decomp) != rec["hop_count"]:
        e.append(f"question_decomposition length {len(decomp)} != hop_count {rec['hop_count']}")
    else:
        for h in decomp:
            for k in ("question", "answer", "paragraph_support_idx", "bridge_qid"):
                if k not in h:
                    e.append(f"decomposition step missing {k}")
            idx = h.get("paragraph_support_idx")
            if isinstance(idx, int) and not (0 <= idx < n_para):
                e.append(f"paragraph_support_idx {idx} out of range [0,{n_para})")

    # bridge must not leak: no decomposition step's answer (a bridge entity) may
    # appear verbatim in the question — except the final answer.
    q_low = rec["question"].lower()
    for h in decomp[:-1] if isinstance(decomp, list) else []:
        ans = str(h.get("answer", "")).strip().lower()
        if ans and len(ans) > 2 and ans in q_low:
            e.append(f"bridge entity '{h.get('answer')}' leaked into question text")

    # single-passage-sufficiency must be false (else not multi-hop)
    if gate.get("single_passage_sufficient") is True:
        e.append("single_passage_sufficient=true -> not multi-hop, reject")
    return e


# ───────────────────────── legacy multimodal schema ─────────────────────────
LEGACY_REQUIRED = [
    "id", "question", "answer", "bridge_entity", "modality",
    "text_source", "artifact_path", "ablation_result", "red_team_verdict", "difficulty",
]
VALID_MODALITIES = {"thermal", "audio", "depth"}
VALID_VERDICTS = {"KEEP", "ADD_DISTRACTORS", "REWRITE", "DISCARD", "PLACEHOLDER"}
VALID_DIFFICULTIES = {"2-hop", "3-hop", "mixed-chain"}
VALID_ABLATION = {"INSUFFICIENT EVIDENCE", "INSUFFICIENT_INFORMATION", "PLACEHOLDER"}


def validate_pair(pair: dict) -> list[str]:
    errors = []
    for field in LEGACY_REQUIRED:
        if field not in pair:
            errors.append(f"missing field: {field}")
    if pair.get("modality") not in VALID_MODALITIES:
        errors.append(f"invalid modality: {pair.get('modality')}")
    if pair.get("red_team_verdict") not in VALID_VERDICTS:
        errors.append(f"invalid red_team_verdict: {pair.get('red_team_verdict')}")
    if pair.get("difficulty") not in VALID_DIFFICULTIES:
        errors.append(f"invalid difficulty: {pair.get('difficulty')}")
    if pair.get("ablation_result") not in VALID_ABLATION:
        errors.append(f"invalid ablation_result: {pair.get('ablation_result')}")
    if pair.get("bridge_entity", "").lower() in pair.get("question", "").lower():
        errors.append(f"bridge entity '{pair['bridge_entity']}' leaked into question text")
    return errors


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as ex:
            print(f"Line {i}: JSON parse error: {ex}")
            sys.exit(1)
    return rows


def main():
    root = Path(__file__).parent
    musique = root / "data" / "afwerk_defense_benchmark.jsonl"
    legacy = root / "qa_pairs.jsonl"

    if musique.exists():
        recs = _load_jsonl(musique)
        errors = {r.get("id", f"line-{i}"): validate_musique(r) for i, r in enumerate(recs)}
        errors = {k: v for k, v in errors.items() if v}
        print("SGXEM MuSiQue Validation Report")
        print("===============================")
        print(f"File: {musique.relative_to(root)}  records: {len(recs)}")
        from collections import Counter
        print("by cluster:", dict(Counter(r.get('cluster') for r in recs)))
        print("by hop_count:", dict(Counter(r.get('hop_count') for r in recs)))
        print("by temporal_sensitivity:", dict(Counter(r.get('temporal_sensitivity') for r in recs)))
        if errors:
            print(f"\n❌ {len(errors)} record(s) with errors:")
            for rid, errs in errors.items():
                print(f"  {rid}: {'; '.join(errs)}")
            sys.exit(1)
        print(f"\n✅ All {len(recs)} records pass MuSiQue validation.")
        return

    if not legacy.exists():
        print("ERROR: neither data/afwerk_defense_benchmark.jsonl nor qa_pairs.jsonl found")
        sys.exit(1)
    pairs = _load_jsonl(legacy)
    errors_all = {p.get("id", f"line-{i}"): validate_pair(p) for i, p in enumerate(pairs)}
    errors_all = {k: v for k, v in errors_all.items() if v}
    print(f"SGXEM Validation Report (legacy)\nTotal QA pairs: {len(pairs)}")
    if errors_all:
        print(f"\n❌ {len(errors_all)} pair(s) with errors:")
        for qid, errs in errors_all.items():
            print(f"  {qid}: {'; '.join(errs)}")
        sys.exit(1)
    print(f"\n✅ All {len(pairs)} pairs pass validation.")


if __name__ == "__main__":
    main()
