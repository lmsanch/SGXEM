#!/bin/bash
# Supply-chain cluster: wait for ingest -> set tier -> compose (GLM, 2-3 hop) -> NLI (Spark) ->
# structural gate -> curate (green + <=2/answer, keep 2-3 hop) -> review HTML. Token-counted.
set -u
cd /research/SGXEM
PY=/research/anaconda3/envs/kms/bin/python
RAW=data/t5_raw
SD=/tmp/claude-1000/-research-SGXEM/5da6f421-4e7f-47a8-87f9-443add00e8dd
LOG=$SD/supply.log
export SGXEM_COMPOSER=glm
export SGXEM_TOKEN_LEDGER=$RAW/supply_ledger.jsonl
say(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }
: > "$SGXEM_TOKEN_LEDGER"
say "=== supply-chain run start ==="

# 1) wait for supply-chain ingest to finish
until grep -q "newly_ingested" $SD/sc_ingest.log 2>/dev/null; do sleep 15; done
say "ingest done"
# 2) stamp source_tier (supply-chain chunks are source_type=wikipedia -> wikipedia)
QDRANT_HOST=localhost $PY scripts/set_source_tier.py --collection afwerk_defense_corpus >> "$LOG" 2>&1

# 3) compose supply_chain (2-3 hop; recency low), live dedup
say "compose supply_chain (accept 90, GLM)..."
rm -f $RAW/supply.jsonl
$PY scripts/generate_diverse.py --clusters supply_chain --accept-per-cluster 90 --workers 10 \
    --out $RAW/supply.jsonl >> "$LOG" 2>&1
say "composed: $(wc -l < $RAW/supply.jsonl) raw"

# 4) NLI (Spark)
scp -q scripts/verify_hops_nli.py spark:/home/luis/afwerk/verify_hops_nli.py
scp -q $RAW/supply.jsonl spark:/tmp/supply.jsonl
ssh spark 'cd /home/luis/afwerk && HF_HOME=/home/luis/afwerk/.hfcache PYTHONPATH=/home/luis/kms \
    /home/luis/ir-training-venv/bin/python verify_hops_nli.py --in /tmp/supply.jsonl --out /tmp/supply.nli.jsonl' >> "$LOG" 2>&1
scp -q spark:/tmp/supply.nli.jsonl $RAW/supply.nli.jsonl

# 5) structural gate
say "structural gate (Kimi + DeepSeek)..."
$PY scripts/verify_redteam.py --in $RAW/supply.nli.jsonl --out $RAW/supply.gated.jsonl --workers 8 >> "$LOG" 2>&1
say "$(grep all-green "$LOG" | tail -1)"

# 6) keep only 2-3 hop, then curate
$PY - <<'PYEOF'
import json
recs=[json.loads(l) for l in open('data/t5_raw/supply.gated.jsonl')]
keep=[r for r in recs if r.get('rejection') or r.get('hop_count') in (2,3)]
open('data/t5_raw/supply.23.jsonl','w').write(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in keep))
PYEOF
$PY scripts/curate.py --in $RAW/supply.23.jsonl --out $RAW/supply.valid.jsonl >> "$LOG" 2>&1
$PY scripts/build_review_html.py --in $RAW/supply.valid.jsonl \
    --out artifacts/review_supply.html --title "SGXEM — Global Supply Chain (2-3 hop, structural gate)" >> "$LOG" 2>&1

say "=== supply-chain DONE ==="
{ echo "=== SUPPLY-CHAIN FINAL ==="; $PY - <<'PYEOF'
import json,collections
r=[json.loads(l) for l in open('data/t5_raw/supply.valid.jsonl')]
print("valid:",len(r),"distinct answers:",len({x['answer'].strip().lower() for x in r}))
print("sub_topic:",dict(collections.Counter(x['sub_topic'] for x in r)))
print("hop:",dict(collections.Counter(x['hop_count'] for x in r)),"temporal:",dict(collections.Counter(x['temporal_sensitivity'] for x in r)))
for x in r[:3]: print(" e.g. Q:",x['question'][:130],"-> A:",x['answer'][:50])
PYEOF
echo; echo "=== token cost ==="; $PY scripts/tokens.py --ledger data/t5_raw/supply_ledger.jsonl | tail -3; } | tee "$SD/SUPPLY_FINAL.txt" | tee -a "$LOG"
echo DONE > $SD/supply.done
