#!/bin/bash
# Breadth run (GLM-5.2 composer + structural gate + live dedup), token-counted.
# generate breadth -> NLI (Spark) -> structural gate -> curate -> merge w/ Venezuela -> emit + HTML.
set -u
cd /research/SGXEM
PY=/research/anaconda3/envs/kms/bin/python
RAW=data/t5_raw
SD=/tmp/claude-1000/-research-SGXEM/5da6f421-4e7f-47a8-87f9-443add00e8dd
LOG=$SD/breadth.log
export SGXEM_COMPOSER=glm
export SGXEM_TOKEN_LEDGER=$RAW/run_ledger.jsonl
say(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }
: > "$SGXEM_TOKEN_LEDGER"          # fresh ledger for this run
rm -f $RAW/breadth2.jsonl
say "=== breadth run start (GLM, token-counted) ==="

say "compose breadth (iran/taiwan/cuba/brazil, accept 80 each, live dedup)..."
$PY scripts/generate_diverse.py --clusters iran,taiwan,cuba,brazil --accept-per-cluster 80 --workers 10 \
    --out $RAW/breadth2.jsonl >> "$LOG" 2>&1
say "composed: $(wc -l < $RAW/breadth2.jsonl) raw lines"

say "NLI gate (Spark)..."
scp -q scripts/verify_hops_nli.py spark:/home/luis/afwerk/verify_hops_nli.py
scp -q $RAW/breadth2.jsonl spark:/tmp/breadth2.jsonl
ssh spark 'cd /home/luis/afwerk && HF_HOME=/home/luis/afwerk/.hfcache PYTHONPATH=/home/luis/kms \
    /home/luis/ir-training-venv/bin/python verify_hops_nli.py --in /tmp/breadth2.jsonl --out /tmp/breadth2.nli.jsonl' >> "$LOG" 2>&1
scp -q spark:/tmp/breadth2.nli.jsonl $RAW/breadth2.nli.jsonl

say "structural gate (Kimi + DeepSeek)..."
$PY scripts/verify_redteam.py --in $RAW/breadth2.nli.jsonl --out $RAW/breadth2.gated.jsonl --workers 8 >> "$LOG" 2>&1
say "$(grep all-green "$LOG" | tail -1)"

# merge Venezuela-valid (gated already) + breadth-gated, then global curate
cat data/t5_raw/venezuela.struct.jsonl $RAW/breadth2.gated.jsonl > $RAW/all5.gated.jsonl
$PY scripts/curate.py --in $RAW/all5.gated.jsonl --out $RAW/all5.valid.jsonl >> "$LOG" 2>&1
$PY scripts/emit_benchmark.py --in $RAW/all5.valid.jsonl --outdir data --require-nli >> "$LOG" 2>&1
$PY scripts/build_review_html.py --in $RAW/all5.valid.jsonl \
    --out artifacts/review_curated.html --title "SGXEM Defense — all 5 clusters (structural gate, GLM)" >> "$LOG" 2>&1

say "=== breadth run DONE ==="
{ echo "FINAL BENCHMARK:"; $PY - <<'PYEOF'
import json,collections,hashlib
recs=[json.loads(l) for l in open('data/afwerk_defense_benchmark.jsonl')]
print("records:",len(recs),"distinct answers:",len({r['answer'].strip().lower() for r in recs}))
print("cluster:",dict(collections.Counter(r['cluster'] for r in recs)))
print("hop:",dict(collections.Counter(r['hop_count'] for r in recs)))
print("temporal:",dict(collections.Counter(r['temporal_sensitivity'] for r in recs)))
print("SHA-256:",hashlib.sha256(open('data/afwerk_defense_benchmark.jsonl','rb').read()).hexdigest())
PYEOF
echo; echo "TOKENS THIS RUN:"; $PY scripts/tokens.py --ledger "$SGXEM_TOKEN_LEDGER"; } | tee "$SD/BREADTH_SUMMARY.txt" | tee -a "$LOG"
