#!/bin/bash
# Overnight T5 pipeline: curate Venezuela -> generate breadth (live answer-dedup) ->
# NLI gate (Spark) -> Kimi+DeepSeek gate -> global curate -> emit 2 files + SHA-256 -> HTML.
# Robust to single-step hiccups; logs everything; writes a DONE summary at the end.
set -u
cd /research/SGXEM
PY=/research/anaconda3/envs/kms/bin/python
RAW=data/t5_raw
SD=/tmp/claude-1000/-research-SGXEM/1a2521ed-c3e0-4e10-b1fe-c8346e7597c5
LOG=$SD/overnight.log
export FIREWORKS_API_KEY=$(grep -h FIREWORKS_API_KEY /research/afwerk/.env | head -1 | cut -d= -f2 | tr -d '"')
say(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

say "=== overnight start ==="

# 1) wait for the Venezuela Kimi+DeepSeek gate (launched separately) to finish
say "waiting for Venezuela gate (all_composed.gated.jsonl)..."
until grep -q "all-green" "$SD/scratch_gate.log" 2>/dev/null; do sleep 30; done
say "Venezuela gate done: $(grep all-green "$SD/scratch_gate.log" | tail -1)"

# 2) generate breadth with live answer-dedup (Iran/Taiwan/Cuba/Brazil)
say "generating breadth (live answer-dedup)..."
$PY scripts/generate_diverse.py --clusters iran,taiwan,cuba,brazil \
    --accept-per-cluster 100 --workers 10 --out $RAW/breadth.jsonl >> "$LOG" 2>&1
say "breadth compose done: $(wc -l < $RAW/breadth.jsonl) raw lines"

# 3) per-hop MiniCheck on breadth (Spark)
say "NLI gate breadth on Spark..."
scp -q scripts/verify_hops_nli.py spark:/home/luis/afwerk/verify_hops_nli.py
scp -q $RAW/breadth.jsonl spark:/tmp/breadth.jsonl
ssh spark 'cd /home/luis/afwerk && HF_HOME=/home/luis/afwerk/.hfcache PYTHONPATH=/home/luis/kms \
    /home/luis/ir-training-venv/bin/python verify_hops_nli.py --in /tmp/breadth.jsonl --out /tmp/breadth.nli.jsonl' >> "$LOG" 2>&1
scp -q spark:/tmp/breadth.nli.jsonl $RAW/breadth.nli.jsonl
say "breadth NLI done"

# 4) Kimi+DeepSeek adversary/judge gate on breadth
say "Kimi+DeepSeek gate breadth..."
$PY scripts/verify_redteam.py --in $RAW/breadth.nli.jsonl --out $RAW/breadth.gated.jsonl --workers 8 >> "$LOG" 2>&1
say "breadth gate done: $(grep all-green "$LOG" | tail -1)"

# 5) merge all gated + global curate (green + <=2/answer + q-dedup, applied across all clusters)
cat $RAW/all_composed.gated.jsonl $RAW/breadth.gated.jsonl > $RAW/all_gated.jsonl
say "global curate of $(wc -l < $RAW/all_gated.jsonl) gated records..."
$PY scripts/curate.py --in $RAW/all_gated.jsonl --out $RAW/final_curated.jsonl >> "$LOG" 2>&1

# 6) emit 2 files + SHA-256, and HTML (survivors only)
$PY scripts/emit_benchmark.py --in $RAW/final_curated.jsonl --outdir data --require-nli >> "$LOG" 2>&1
$PY scripts/build_review_html.py --in $RAW/final_curated.jsonl \
    --out artifacts/review_curated.html --title "SGXEM Defense Benchmark — curated (green-only, deduped)" >> "$LOG" 2>&1

say "=== overnight DONE ==="
{ echo "OVERNIGHT SUMMARY ($(date -u))"; tail -3 "$LOG" | grep -iE "curate|kept|SHA-256" ; \
  $PY - <<'PYEOF'
import json,collections
recs=[json.loads(l) for l in open('data/afwerk_defense_benchmark.jsonl')]
print("final records:",len(recs),"distinct answers:",len({r['answer'].strip().lower() for r in recs}))
print("cluster:",dict(collections.Counter(r['cluster'] for r in recs)))
print("hop:",dict(collections.Counter(r['hop_count'] for r in recs)))
print("temporal:",dict(collections.Counter(r['temporal_sensitivity'] for r in recs)))
PYEOF
} | tee "$SD/OVERNIGHT_SUMMARY.txt" | tee -a "$LOG"
say "summary -> $SD/OVERNIGHT_SUMMARY.txt ; HTML -> artifacts/review_curated.html"
