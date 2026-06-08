#!/usr/bin/env python3
"""Download source datasets for SGXEM artifact preparation."""

import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent / "artifacts"


def git_clone(url: str, dest: str):
    dest_path = BASE / dest
    if dest_path.exists():
        print(f"  SKIP (exists): {dest}")
        return
    print(f"  Cloning {url} → {dest}")
    subprocess.run(["git", "clone", "--depth", "1", url, str(dest_path)], check=True)


def huggingface_download(dataset_id: str, dest: str):
    dest_path = BASE / dest
    if dest_path.exists():
        print(f"  SKIP (exists): {dest}")
        return
    print(f"  Downloading HF dataset {dataset_id} → {dest}")
    try:
        from datasets import load_dataset
        ds = load_dataset(dataset_id)
        os.makedirs(dest_path, exist_ok=True)
        ds.save_to_disk(str(dest_path))
    except ImportError:
        print("  ERROR: `datasets` package not installed. Run: pip install datasets")
        print(f"  Manual: visit https://huggingface.co/datasets/{dataset_id}")


def main():
    BASE.mkdir(parents=True, exist_ok=True)

    print("=== SGXEM Source Dataset Downloader ===\n")

    print("1. ESC-50 (audio, CC BY-NC 3.0)")
    git_clone("https://github.com/karoldvl/ESC-50.git", "esc50_source")

    print("\n2. DroneAudioDataset (audio, MIT)")
    git_clone("https://github.com/saraalgo/DroneAudioDataset.git", "drone_audio_source")

    print("\n3. NYU Depth V2 (depth, HuggingFace)")
    huggingface_download("sayakpaul/nyu_depth_v2", "nyu_depth_source")

    print("\n4. KITTI (depth/lidar)")
    print("  MANUAL: Download from http://www.cvlibs.net/datasets/kitti/raw_data.php")
    print("  Requires registration. Place synced+rectified data in artifacts/kitti_source/")

    print("\n5. FLIR ADAS (thermal)")
    print("  MANUAL: Register at https://www.flir.com/oem/adas/adas-dataset-form/")
    print("  Place downloaded frames in artifacts/flir_source/")

    print("\n6. NASA FIRMS (thermal, open API)")
    print("  API access: https://firms.modaps.eosdis.nasa.gov/api/area/")
    print("  Run: python -m firms <api_key> to pull thermal anomaly data")
    print("  Place output in artifacts/firms_source/")

    print("\n7. MAD — Military Audio Dataset (audio, CC BY 4.0)")
    print("  Download from https://doi.org/10.6084/m9.figshare.25411495")
    print("  Place in artifacts/mad_source/")

    print("\n=== Done. Place manual downloads in artifacts/ subdirectories. ===")


if __name__ == "__main__":
    main()
