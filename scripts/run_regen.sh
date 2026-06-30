#!/bin/bash
# Full T5 regeneration (path B): o4-mini composer + structural Kimi/DeepSeek gate + live dedup.
# generate (VZ-weighted, 40% recency) -> NLI (Spark) -> structural gate -> global curate -> emit + HTML.
set -u
cd /research/SGXEM
PY=/research/anaconda3/envs/kms/bin/python
RAW=data/t5_raw
SD=/tmp/claude-1000/-research-SGXEM/5da6f421-4e7f-47a8-87f9-443add00e8dd
LOG=$SD/regen.log
export SGXEM_COMPOSER=o4-mini
say(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }
say "=== regen start (o4-mini + structural gate) ==="

# 1) generate — Venezuela weighted ~40%, then breadth; live answer-dedup; 40% recency
say "compose Venezuela (accept 180)..."
$PY scripts/generate_diverse.py --clusters venezuela --accept-per-cluster 180 --workers 10 \
    --out $RAW/regen.jsonl >> "$LOG" 2>&1
say "compose breadth (accept 80 each)..."
$PY scripts/generate_diverse.py --clusters iran,taiwan,cuba,brazil --accept-per-cluster 80 --workers 10 \
    --out $RAW/regen.jsonl >> "$LOG" 2>&1
say "composed: $(grep -c '"rejection"' $RAW/regen.jsonl 2>/dev/null) rej lines / $(wc -l < $RAW/regen.jsonl) total"

# 2) per-hop MiniCheck (Spark)
say "NLI gate (Spark)..."
scp -q scripts/verify_hops_nli.py spark:/home/luis/afwerk/verify_hops_nli.py
scp -q $RAW/regen.jsonl spark:/tmp/regen.jsonl
ssh spark 'cd /home/luis/afwerk && HF_HOME=/home/luis/afwerk/.hfcache PYTHONPATH=/home/luis/kms \
    /home/luis/ir-training-venv/bin/python verify_hops_nli.py --in /tmp/regen.jsonl --out /tmp/regen.nli.jsonl' >> "$LOG" 2>&1
scp -q spark:/tmp/regen.nli.jsonl $RAW/regen.nli.jsonl

# 3) structural Kimi+DeepSeek gate
say "structural gate (Kimi adversary + DeepSeek judge)..."
$PY scripts/verify_redteam.py --in $RAW/regen.nli.jsonl --out $RAW/regen.gated.jsonl --workers 8 >> "$LOG" 2>&1
say "$(grep all-green "$LOG" | tail -1)"

# 4) global curate (green + <=2/answer + q-dedup) + emit + HTML
$PY scripts/curate.py --in $RAW/regen.gated.jsonl --out $RAW/regen_curated.jsonl >> "$LOG" 2>&1
$PY scripts/emit_benchmark.py --in $RAW/regen_curated.jsonl --outdir data --require-nli >> "$LOG" 2>&1
$PY scripts/build_review_html.py --in $RAW/regen_curated.jsonl \
    --out artifacts/review_curated.html --title "SGXEM Defense — curated v2 (o4-mini + structural gate)" >> "$LOG" 2>&1

say "=== regen DONE ==="
$PY - <<'PYEOF' | tee "$SD/REGEN_SUMMARY.txt" | tee -a "$LOG"
import json,collections
recs=[json.loads(l) for l in open('data/afwerk_defense_benchmark.jsonl')]
print("REGEN SUMMARY")
print("final records:",len(recs),"distinct answers:",len({r['answer'].strip().lower() for r in recs}))
print("cluster:",dict(collections.Counter(r['cluster'] for r in recs)))
print("hop:",dict(collections.Counter(r['hop_count'] for r in recs)))
print("temporal:",dict(collections.Counter(r['temporal_sensitivity'] for r in recs)))
import hashlib
print("SHA-256:",hashlib.sha256(open('data/afwerk_defense_benchmark.jsonl','rb').read()).hexdigest())
PYEOF
say "summary -> $SD/REGEN_SUMMARY.txt ; HTML -> artifacts/review_curated.html"
