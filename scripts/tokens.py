#!/usr/bin/env python3
"""tokens.py — tiny shared token ledger (SGXEM-owned). Tracks LLM in/out tokens + cost.

Every composer/gate call appends one line via add(); token_report() tallies by model+stage.
Ledger path = $SGXEM_TOKEN_LEDGER (default data/t5_raw/token_ledger.jsonl). Thread-safe-ish
(append-only line writes). Prices are per-1M-token estimates; override via PRICES if needed.
"""
from __future__ import annotations

import json
import os
import threading
from collections import defaultdict
from pathlib import Path

_LOCK = threading.Lock()

# rough $/1M tokens (input, output) — adjust to your actual contract
PRICES = {
    "accounts/fireworks/models/glm-5p2": (0.55, 2.19),
    "accounts/fireworks/models/kimi-k2p6": (0.60, 2.50),
    "accounts/fireworks/models/deepseek-v4-pro": (0.56, 1.68),
    "openai/o4-mini": (1.10, 4.40),
}


def ledger_path() -> Path:
    return Path(os.getenv("SGXEM_TOKEN_LEDGER", "data/t5_raw/token_ledger.jsonl"))


def add(stage: str, model: str, usage: dict | None) -> None:
    if not usage:
        return
    rec = {"stage": stage, "model": model,
           "in": usage.get("prompt_tokens", 0),
           "out": usage.get("completion_tokens", 0),
           "cost": usage.get("cost", 0.0)}
    p = ledger_path()
    with _LOCK:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")


def report(path: Path | None = None) -> str:
    p = path or ledger_path()
    if not p.exists():
        return "no token ledger"
    by = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0})
    tot = {"calls": 0, "in": 0, "out": 0, "cost": 0.0}
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        key = (r["stage"], r["model"].split("/")[-1])
        b = by[key]
        b["calls"] += 1; b["in"] += r["in"]; b["out"] += r["out"]
        pin, pout = PRICES.get(r["model"], (0, 0))
        c = r["cost"] or (r["in"] * pin + r["out"] * pout) / 1e6
        b["cost"] += c
        tot["calls"] += 1; tot["in"] += r["in"]; tot["out"] += r["out"]; tot["cost"] += c
    lines = [f"{'stage/model':38s} {'calls':>6} {'in_tok':>10} {'out_tok':>10} {'~$cost':>9}"]
    for (stage, model), b in sorted(by.items()):
        lines.append(f"{stage+'/'+model:38s} {b['calls']:>6} {b['in']:>10,} {b['out']:>10,} {b['cost']:>9.3f}")
    lines.append(f"{'TOTAL':38s} {tot['calls']:>6} {tot['in']:>10,} {tot['out']:>10,} {tot['cost']:>9.3f}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", type=Path, default=None)
    print(report(ap.parse_args().ledger))
