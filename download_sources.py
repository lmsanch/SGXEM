#!/usr/bin/env python3
"""Download source datasets for local SGXEM artifact preparation.

Downloaded source trees and selected media artifacts are intentionally ignored
by git. This script prepares local data for curation; it does not create a
redistributable benchmark package.
"""

import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent / "artifacts"
FAILURES = []


def local_path_from_env(dataset_name: str, env_var: str, dest: str) -> None:
    source = os.environ.get(env_var)
    dest_path = BASE / dest
    if not source:
        print(f"  LOCAL ONLY: set {env_var}=/path/to/{dest} after accepting upstream terms")
        return
    source_path = Path(source).expanduser()
    if not source_path.exists():
        FAILURES.append((dest, env_var, f"path does not exist: {source_path}"))
        print(f"  ERROR: {env_var} points to missing path: {source_path}")
        return
    dest_path.mkdir(parents=True, exist_ok=True)
    marker = dest_path / "LOCAL_SOURCE_PATH.txt"
    marker.write_text(str(source_path.resolve()) + "\n", encoding="utf-8")
    print(f"  Registered local {dataset_name} path in {marker}")


def git_clone(url: str, dest: str):
    dest_path = BASE / dest
    if dest_path.exists():
        print(f"  SKIP (exists): {dest}")
        return
    print(f"  Cloning {url} → {dest}")
    try:
        subprocess.run(["git", "clone", "--depth", "1", url, str(dest_path)], check=True)
    except subprocess.CalledProcessError as exc:
        FAILURES.append((dest, url, str(exc)))
        print(f"  ERROR: failed to clone {dest}: {exc}")


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
        FAILURES.append((dest, dataset_id, "datasets package not installed"))
    except Exception as exc:
        print(f"  ERROR: failed to download {dataset_id}: {exc}")
        FAILURES.append((dest, dataset_id, str(exc)))


def main():
    BASE.mkdir(parents=True, exist_ok=True)

    print("=== SGXEM Source Dataset Downloader ===\n")
    print("Policy: downloaded datasets stay local under artifacts/ and are not tracked by git.")
    print("Policy: DroneAudio is local-only until upstream publishes an explicit license.")
    print("Policy: FLIR and KITTI are manual/local-path only; no SGXEM redistribution.\n")

    print("1. ESC-50 (audio, full dataset CC BY-NC; ESC-10 subset CC BY)")
    print("  Use ESC-10 rows for redistributable SGXEM subsets where possible.")
    git_clone("https://github.com/karoldvl/ESC-50.git", "esc50_source")

    print("\n2. DroneAudioDataset (audio, unlicensed; local experiments only)")
    print("  WARNING: no explicit upstream LICENSE file. Do not redistribute wavs,")
    print("  selected subsets, transformed media, or embeddings until licensing is fixed.")
    git_clone("https://github.com/saraalemadi/DroneAudioDataset.git", "drone_audio_source")

    print("\n3. NYU Depth V2 (depth, HuggingFace; redistributable per issue #601)")
    if os.environ.get("HF_TOKEN"):
        print("  HF_TOKEN detected.")
    else:
        print("  HF_TOKEN not set; continuing because it is usually optional.")
    huggingface_download("sayakpaul/nyu_depth_v2", "nyu_depth_source")

    print("\n4. KITTI (depth/lidar; academic/non-commercial manual-only)")
    print("  MANUAL: register/download from http://www.cvlibs.net/datasets/kitti/raw_data.php")
    print("  SGXEM records only your local path and must not redistribute KITTI data.")
    local_path_from_env("KITTI", "KITTI_RAW_DIR", "kitti_source")

    print("\n5. FLIR ADAS (thermal; proprietary EULA manual-only)")
    print("  MANUAL: Register at https://www.flir.com/oem/adas/adas-dataset-form/")
    print("  SGXEM records only your local path and must not redistribute FLIR data.")
    local_path_from_env("FLIR ADAS", "FLIR_ADAS_DIR", "flir_source")

    print("\n6. NASA FIRMS (thermal, open API; redistributable)")
    print("  API access: https://firms.modaps.eosdis.nasa.gov/api/area/")
    if os.environ.get("NASA_FIRMS_MAP_KEY"):
        print("  NASA_FIRMS_MAP_KEY detected. FIRMS downloader can be added/run here.")
    else:
        print("  Set NASA_FIRMS_MAP_KEY to enable FIRMS API downloads.")

    print("\n7. MAD - Military Audio Dataset (audio, CC BY 4.0; redistributable)")
    print("  Download from https://doi.org/10.6084/m9.figshare.25411495")
    print("  If using a Kaggle mirror, set KAGGLE_USERNAME and KAGGLE_KEY.")
    print("  Place or download files into artifacts/mad_source/ before selection.")

    print("\n=== Done. Local downloads live under artifacts/ and remain untracked. ===")
    if FAILURES:
        print("\nAutomated download failures:")
        for dest, source, reason in FAILURES:
            print(f"  - {dest}: {source} ({reason})")
        sys.exit(1)


if __name__ == "__main__":
    main()
