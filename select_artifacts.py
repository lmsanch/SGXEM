#!/usr/bin/env python3
"""Select SGXEM candidate artifacts from downloaded open-source datasets.

This script creates artifacts/labels.csv from dataset metadata and copies a
small curated candidate set into artifacts/{audio,thermal,depth}. Copied media
stays local and is ignored by git. Rows include verification_status and
redistribution_status so final shipping can distinguish human-verified,
redistributable artifacts from local-only candidates.
"""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

BASE = Path(__file__).parent
ARTIFACTS = BASE / "artifacts"
LABELS_PATH = ARTIFACTS / "labels.csv"

ESC50_CLASSES = {
    "helicopter": 2,
    "airplane": 2,
    "siren": 2,
    "engine": 2,
    "gunshot": 2,
}

TEXT_FACTS = {
    "helicopter": ("spectral_guide.md", "Helicopter rotor detection range = 3000 m", "3000 m"),
    "airplane": ("spectral_guide.md", "Fixed-wing propeller detection range = 2500 m", "2500 m"),
    "siren": ("spectral_guide.md", "Siren (emergency) detection range = 1000 m", "1000 m"),
    "engine": ("spectral_guide.md", "Diesel engine (heavy) detection range = 1200 m", "1200 m"),
    "gunshot": ("spectral_guide.md", "Gunshot (handgun) detection range = 800 m", "800 m"),
    "drone": ("platform_registry.md", "Quadcopter rotor count = 4", "4"),
}


def esc50_redistribution_status(row: dict) -> str:
    if row.get("esc10", "").lower() == "true":
        return "esc10_redistributable_cc_by"
    return "esc50_full_noncommercial_local_only"


def read_existing_labels() -> dict[str, dict]:
    if not LABELS_PATH.exists():
        return {}
    with LABELS_PATH.open(newline="", encoding="utf-8") as handle:
        return {row["artifact_id"]: row for row in csv.DictReader(handle)}


def esc50_candidates() -> list[dict]:
    meta_path = ARTIFACTS / "esc50_source" / "meta" / "esc50.csv"
    audio_dir = ARTIFACTS / "esc50_source" / "audio"
    if not meta_path.exists():
        return []

    selected = []
    counts = {label: 0 for label in ESC50_CLASSES}
    with meta_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            category = row["category"]
            if category not in counts or counts[category] >= ESC50_CLASSES[category]:
                continue
            counts[category] += 1
            artifact_id = f"A-ESC-{category.upper()}-{counts[category]:02d}"
            src = audio_dir / row["filename"]
            dst = ARTIFACTS / "audio" / f"{artifact_id}.wav"
            selected.append(
                {
                    "artifact_id": artifact_id,
                    "modality": "audio",
                    "ground_truth_label": category,
                    "source_dataset": "esc50",
                    "notes": f"ESC-50 metadata label; source_file={row['filename']}; esc10={row.get('esc10', '')}; pending human listening verification",
                    "artifact_path": str(dst.relative_to(BASE)),
                    "text_source": TEXT_FACTS[category][0],
                    "text_fact": TEXT_FACTS[category][1],
                    "answer": TEXT_FACTS[category][2],
                    "verification_status": "dataset_metadata_pending_human",
                    "redistribution_status": esc50_redistribution_status(row),
                    "local_only": "false" if row.get("esc10", "").lower() == "true" else "true",
                    "_source_path": src,
                    "_dest_path": dst,
                }
            )
    return selected


def drone_candidates(limit: int = 10) -> list[dict]:
    root = ARTIFACTS / "drone_audio_source"
    if not root.exists():
        return []
    wavs = sorted(path for path in root.rglob("*.wav") if path.is_file())
    selected = []
    for idx, src in enumerate(wavs[:limit], 1):
        artifact_id = f"A-DRONE-{idx:04d}"
        dst = ARTIFACTS / "audio" / f"{artifact_id}.wav"
        selected.append(
            {
                "artifact_id": artifact_id,
                "modality": "audio",
                "ground_truth_label": "drone",
                "source_dataset": "drone_audio",
                "notes": f"DroneAudioDataset file; source_file={src.relative_to(root)}; pending human listening verification",
                "artifact_path": str(dst.relative_to(BASE)),
                "text_source": TEXT_FACTS["drone"][0],
                "text_fact": TEXT_FACTS["drone"][1],
                "answer": TEXT_FACTS["drone"][2],
                "verification_status": "dataset_metadata_pending_human",
                "redistribution_status": "blocked_unlicensed",
                "local_only": "true",
                "_source_path": src,
                "_dest_path": dst,
            }
        )
    return selected


def write_labels(rows: list[dict]) -> None:
    fields = [
        "artifact_id",
        "modality",
        "ground_truth_label",
        "source_dataset",
        "notes",
        "artifact_path",
        "text_source",
        "text_fact",
        "answer",
        "verification_status",
        "redistribution_status",
        "local_only",
    ]
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LABELS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> int:
    existing = read_existing_labels()
    rows = list(existing.values())
    seen = set(existing)

    for row in esc50_candidates() + drone_candidates():
        if row["artifact_id"] in seen:
            continue
        row["_dest_path"].parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(row["_source_path"], row["_dest_path"])
        rows.append(row)
        seen.add(row["artifact_id"])

    rows.sort(key=lambda row: row["artifact_id"])
    for row in rows:
        if row.get("source_dataset") == "drone_audio":
            if not row.get("redistribution_status"):
                row["redistribution_status"] = "blocked_unlicensed"
            if not row.get("local_only"):
                row["local_only"] = "true"
        elif row.get("source_dataset") == "esc50":
            if not row.get("redistribution_status"):
                row["redistribution_status"] = "esc50_full_noncommercial_local_only"
            if not row.get("local_only"):
                row["local_only"] = "true"
    write_labels(rows)
    print(f"wrote {LABELS_PATH} with {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
