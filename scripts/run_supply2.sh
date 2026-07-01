#!/bin/bash
# Supply-chain BATCH 2: new source articles -> ingest -> compose (avoid batch-1 answers, 50/50
# recency) -> NLI (Spark) -> structural gate -> curate (2-3 hop) -> merge with batch1 -> HTML.
set -u
cd /research/SGXEM
PY=/research/anaconda3/envs/kms/bin/python
RAW=data/t5_raw
SD=/tmp/claude-1000/-research-SGXEM/5da6f421-4e7f-47a8-87f9-443add00e8dd
LOG=$SD/supply2.log
export SGXEM_COMPOSER=glm
export SGXEM_TOKEN_LEDGER=$RAW/supply2_ledger.jsonl
say(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }
: > "$SGXEM_TOKEN_LEDGER"
say "=== supply-chain batch 2 start ==="

# 1) fetch new full articles + chunk
say "fetch 42 new articles..."
$PY scripts/fetch_supply_chain.py --entities data/defense_corpus/supply_chain2_entities.jsonl \
    --corpus-dir data/defense_corpus --delay 0.3 >> "$LOG" 2>&1
say "chunk new articles (SmartChunker)..."
PYTHONPATH=/research/afwerk:/research/kms $PY - >> "$LOG" 2>&1 <<'PYEOF'
import json
from pathlib import Path
from sgxem.text_ingestion import chunk_registry_sources
reg=Path("data/defense_corpus/supply_chain_registry.jsonl").resolve()   # fetch wrote the new 42 here
corpus=Path("data/defense_corpus/corpus/supply_chain").resolve()
chunks,summary=chunk_registry_sources(reg, corpus)
Path("data/defense_corpus/sgxem_chunks.jsonl").write_text("\n".join(json.dumps(c,ensure_ascii=False) for c in chunks)+"\n")
print("batch2 chunks:",summary["total_chunks"],"from",summary["sources_chunked"])
PYEOF

# 2) build records + ingest (resume-skips existing; adds new supply2 chunks)
$PY /research/afwerk/scripts/build_sgxem_hotspot_kms_records.py --root data/defense_corpus \
    --output-dir data/defense_corpus/kms_records >> "$LOG" 2>&1
cp data/defense_corpus/kms_records/sgxem_hotspot_all.records.jsonl data/defense_corpus/kms_records/afwerk_defense_corpus.records.jsonl
say "ingest new chunks..."
QDRANT_HOST=localhost $PY /research/afwerk/scripts/ingest_sgxem_hotspot_kms.py \
    --records-dir data/defense_corpus/kms_records --collections afwerk_defense_corpus \
    --progress-dir data/defense_corpus/kms_records/progress \
    --summary data/defense_corpus/kms_records/ingest_summary_sc2.json >> "$LOG" 2>&1
QDRANT_HOST=localhost $PY scripts/set_source_tier.py --collection afwerk_defense_corpus >> "$LOG" 2>&1

# 3) compose batch 2 (fresh file; avoid batch-1 answers; 50/50 recency; 2-3 hop target)
say "compose batch 2 (accept 45, avoid batch-1 answers, recency 0.5)..."
rm -f $RAW/supply2.jsonl
$PY scripts/generate_diverse.py --clusters supply_chain --accept-per-cluster 45 --workers 10 \
    --recency-frac 0.5 --seed-avoid $RAW/supply_batch1_answers.json --out $RAW/supply2.jsonl >> "$LOG" 2>&1
say "composed: $(wc -l < $RAW/supply2.jsonl) raw"

# 4) NLI (Spark)
scp -q scripts/verify_hops_nli.py spark:/home/luis/afwerk/verify_hops_nli.py
scp -q $RAW/supply2.jsonl spark:/tmp/supply2.jsonl
ssh spark 'cd /home/luis/afwerk && HF_HOME=/home/luis/afwerk/.hfcache PYTHONPATH=/home/luis/kms \
    /home/luis/ir-training-venv/bin/python verify_hops_nli.py --in /tmp/supply2.jsonl --out /tmp/supply2.nli.jsonl' >> "$LOG" 2>&1
scp -q spark:/tmp/supply2.nli.jsonl $RAW/supply2.nli.jsonl

# 5) structural gate
say "structural gate..."
$PY scripts/verify_redteam.py --in $RAW/supply2.nli.jsonl --out $RAW/supply2.gated.jsonl --workers 8 >> "$LOG" 2>&1

# 6) keep 2-3 hop, curate batch2, then MERGE batch1(valid) + batch2(valid) -> full supply set
$PY - <<'PYEOF'
import json
recs=[json.loads(l) for l in open('data/t5_raw/supply2.gated.jsonl')]
keep=[r for r in recs if r.get('rejection') or r.get('hop_count') in (2,3)]
open('data/t5_raw/supply2.23.jsonl','w').write(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in keep))
PYEOF
$PY scripts/curate.py --in $RAW/supply2.23.jsonl --out $RAW/supply2.valid.jsonl >> "$LOG" 2>&1
cat $RAW/supply.valid.jsonl $RAW/supply2.valid.jsonl > $RAW/supply_all.valid.jsonl
$PY scripts/build_review_html.py --in $RAW/supply2.valid.jsonl \
    --out artifacts/review_supply2.html --title "SGXEM — Supply Chain BATCH 2 (new sources, 50/50 recency)" >> "$LOG" 2>&1
$PY scripts/build_review_html.py --in $RAW/supply_all.valid.jsonl \
    --out artifacts/review_supply_all.html --title "SGXEM — Supply Chain ALL (batch 1 + 2)" >> "$LOG" 2>&1

say "=== batch 2 DONE ==="
{ echo "=== BATCH 2 ==="; $PY - <<'PYEOF'
import json,collections
b2=[json.loads(l) for l in open('data/t5_raw/supply2.valid.jsonl')]
allr=[json.loads(l) for l in open('data/t5_raw/supply_all.valid.jsonl')]
print("batch2 valid:",len(b2),"| combined supply-chain:",len(allr))
print("batch2 hop:",dict(collections.Counter(x['hop_count'] for x in b2)),"temporal:",dict(collections.Counter(x['temporal_sensitivity'] for x in b2)))
print("combined temporal:",dict(collections.Counter(x['temporal_sensitivity'] for x in allr)))
for x in b2[:3]: print(" e.g.",x['question'][:120],"->",x['answer'][:40])
PYEOF
echo; echo "=== cost ==="; $PY scripts/tokens.py --ledger data/t5_raw/supply2_ledger.jsonl | tail -4; } | tee "$SD/SUPPLY2_FINAL.txt" | tee -a "$LOG"
echo DONE > $SD/supply2.done
