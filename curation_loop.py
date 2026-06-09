#!/usr/bin/env python3
"""Run the SGXEM 3-prompt curation pipeline from artifacts/labels.csv."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = Path(__file__).parent
PROMPTS = BASE / "prompts"
TEXT_SOURCES = BASE / "text_sources"


def read_labels(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def load_text_sources() -> str:
    parts = []
    for path in sorted(TEXT_SOURCES.glob("*.md")):
        parts.append(f"# {path.name}\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(parts)


def prompt(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def call_llm(endpoint: str, model: str, api_key: str | None, content: str) -> str:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    response = requests.post(
        endpoint,
        headers=headers,
        json={"model": model, "messages": [{"role": "user", "content": content}], "temperature": 0},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_json_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def build_generation_prompt(label: dict) -> str:
    return (
        prompt("01_generation.md")
        + "\n\n"
        + "NON_TEXT_MODALITY: {modality}\n"
        + "NON_TEXT_ITEM_ID: {artifact_id}\n"
        + "HOP1_BRIDGE_ENTITY: {ground_truth_label}\n"
        + "TEXT_SOURCE_FACT: {text_fact}\n"
    ).format(**label)


def qa_pair_from_candidate(label: dict, candidate: dict, red_team: dict, ablation: str) -> dict:
    return {
        "id": label["artifact_id"],
        "question": candidate["question"],
        "answer": candidate.get("answer") or label["answer"],
        "bridge_entity": label["ground_truth_label"],
        "modality": label["modality"],
        "text_source": label["text_source"],
        "artifact_path": label["artifact_path"],
        "ablation_result": "INSUFFICIENT EVIDENCE" if "INSUFFICIENT EVIDENCE" in ablation.upper() else ablation,
        "red_team_verdict": red_team.get("verdict", "DISCARD"),
        "difficulty": "2-hop",
    }


def run_label(label: dict, args: argparse.Namespace, text_corpus: str) -> tuple[dict, dict | None]:
    now = datetime.now(timezone.utc).isoformat()
    base = {
        "timestamp": now,
        "artifact_id": label["artifact_id"],
        "bridge_entity": label["ground_truth_label"],
        "modality": label["modality"],
        "verification_status": label.get("verification_status", ""),
    }
    generation = build_generation_prompt(label)
    if args.dry_run:
        return {**base, "status": "DRY_RUN", "generation_prompt": generation}, None

    generated_text = call_llm(args.llm_endpoint, args.model, args.api_key, generation)
    candidate = parse_json_response(generated_text)

    red_team_prompt = (
        prompt("02_red_team.md")
        + "\n\nQUESTION: {question}\nANSWER: {answer}\nTEXT_SOURCES_AVAILABLE:\n{corpus}\nNON_TEXT_ARTIFACT: withheld\n"
    ).format(question=candidate["question"], answer=candidate.get("answer") or label["answer"], corpus=text_corpus)
    red_team_text = call_llm(args.llm_endpoint, args.model, args.api_key, red_team_prompt)
    red_team = parse_json_response(red_team_text)
    verdict = red_team.get("verdict", "DISCARD")
    if verdict != "KEEP":
        return {
            **base,
            "status": "DISCARD",
            "failure_reason": verdict,
            "candidate": candidate,
            "red_team": red_team,
        }, None

    ablation_prompt = (
        prompt("03_text_only_ablation.md")
        + "\n\nQUESTION: {question}\n\nTEXT CORPUS:\n{corpus}\n"
    ).format(question=candidate["question"], corpus=text_corpus)
    ablation = call_llm(args.llm_endpoint, args.model, args.api_key, ablation_prompt)
    if (candidate.get("answer") or label["answer"]).casefold() in ablation.casefold():
        return {
            **base,
            "status": "DISCARD",
            "failure_reason": "TEXT_ONLY_ABLATION_ANSWERED",
            "candidate": candidate,
            "red_team": red_team,
            "ablation_output": ablation,
        }, None

    pair = qa_pair_from_candidate(label, candidate, red_team, ablation)
    return {**base, "status": "SHIP", "candidate": candidate, "red_team": red_team, "ablation_output": ablation}, pair


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--labels", type=Path, default=BASE / "artifacts" / "labels.csv")
    p.add_argument("--curation-log", type=Path, default=BASE / "curation_log.jsonl")
    p.add_argument("--qa-pairs", type=Path, default=BASE / "qa_pairs.jsonl")
    p.add_argument("--artifact-id")
    p.add_argument("--batch", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--llm-endpoint", default=os.getenv("OPENAI_COMPAT_URL"))
    p.add_argument("--model", default=os.getenv("SGXEM_LLM_MODEL", "gpt-4o"))
    p.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not args.batch and not args.artifact_id:
        raise SystemExit("set --batch or --artifact-id")
    if not args.dry_run and not args.llm_endpoint:
        raise SystemExit("set --llm-endpoint/OPENAI_COMPAT_URL or use --dry-run")

    labels = read_labels(args.labels)
    if args.artifact_id:
        labels = [row for row in labels if row["artifact_id"] == args.artifact_id]

    processed = {row.get("artifact_id") for row in read_jsonl(args.curation_log) if row.get("status") in {"SHIP", "DISCARD", "DRY_RUN"}}
    text_corpus = load_text_sources()
    log_rows = []
    qa_rows = []
    for label in labels:
        if label["artifact_id"] in processed:
            continue
        log_row, qa_pair = run_label(label, args, text_corpus)
        log_rows.append(log_row)
        if qa_pair:
            qa_rows.append(qa_pair)

    append_jsonl(args.curation_log, log_rows)
    append_jsonl(args.qa_pairs, qa_rows)
    print(f"processed={len(log_rows)} shipped={len(qa_rows)} log={args.curation_log} qa_pairs={args.qa_pairs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

