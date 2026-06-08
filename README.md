# SGXEM — SGX Exotic Modalities Benchmark

Cross-modal multi-hop QA dataset for evaluating RAG systems on non-text evidence.

## What it tests

Every question requires:
1. **Hop 1:** Read a **non-text artifact** (thermal image, audio clip, depth map) to recover a bridge entity
2. **Hop 2:** Use that bridge entity to look up a fact in a **text source**

Text-only RAG systems (GraphRAG, KET-RAG, vanilla RAG) structurally cannot answer these questions — the bridge entity is hidden and only recoverable from the non-text modality.

## Modality Coverage

| Modality | Source Dataset | Artifacts | AF Relevance |
|----------|---------------|-----------|--------------|
| Thermal/IR | FLIR ADAS, NASA FIRMS | ~30 | Vehicle/equipment ID, fire anomaly |
| Acoustic | ESC-50, DroneAudioDataset, MAD | ~30 | C-UAS rotor ID, gunshot/engine detection |
| Depth | NYU Depth V2, KITTI | ~20 | Obstacle/spatial reasoning |
| Mixed chains | Thermal+Audio→text, Depth+Thermal→text | ~20 | Force protection scenarios |
| **Total** | | **~100** | |

## Key Design Properties

- **Hidden bridge:** The bridge entity (hop-1 answer) never appears in the question text
- **Distractor-rich text sources:** Each text document contains 4+ entities of the same type, so no uniqueness shortcut exists
- **Adversarial validated:** Every question passes a 3-stage pipeline:
  1. **Generation** (Prompt 01) — compose hidden-bridge question
  2. **Red-team** (Prompt 02) — 5-axis shortcut hunt
  3. **Text-only ablation** (Prompt 03) — strong text-only model must return "INSUFFICIENT EVIDENCE"

## Dataset Structure

```
SGXEM/
├── README.md
├── LICENSE                    # CC BY-NC 4.0
├── sources.json               # Dataset pointers + metadata
├── qa_pairs.jsonl              # Verified QA pairs (1 per line)
├── artifacts/                 # Non-text artifacts (thermal, audio, depth)
│   ├── thermal/
│   ├── audio/
│   └── depth/
├── text_sources/              # Distractor-rich text documents
│   ├── sensor_handbook.md
│   ├── ir_cooling_reference.md
│   ├── platform_registry.md
│   ├── urban_threat_playbook.md
│   ├── spectral_guide.md
│   └── perimeter_spec.md
├── prompts/                   # Curation prompts
│   ├── 01_generation.md
│   ├── 02_red_team.md
│   └── 03_text_only_ablation.md
├── build.py                   # Validator + stats
└── download_sources.py         # Fetch source datasets
```

## Quick Start

```bash
# Download source datasets (ESC-50, DroneAudioDataset, NYU Depth V2)
python download_sources.py

# Validate all QA pairs
python build.py

# Use in your eval harness
import json
with open("qa_pairs.jsonl") as f:
    qa = [json.loads(line) for line in f]
```

## QA Pair Schema

```json
{
  "id": "T-0001",
  "question": "Given thermal frame T-0001, what is the acoustic detection range of the identified vehicle class?",
  "answer": "800 m",
  "bridge_entity": "wheeled APC",
  "modality": "thermal",
  "text_source": "sensor_handbook.md",
  "artifact_path": "artifacts/thermal/T-0001.png",
  "ablation_result": "INSUFFICIENT EVIDENCE",
  "red_team_verdict": "KEEP",
  "difficulty": "2-hop"
}
```

## Citation

```bibtex
@dataset{sgxem2026,
  title={SGXEM: SGX Exotic Modalities Benchmark for Cross-Modal Multi-Hop QA},
  author={Anchustegui, Luis M.},
  year={2026},
  url={https://github.com/lmsanch/SGXEM}
}
```

## License

CC BY-NC 4.0 — see [LICENSE](LICENSE). Source datasets retain their own licenses (see `sources.json`).
