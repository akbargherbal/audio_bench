#!/usr/bin/env python3
"""
Auxiliary runner for AudioBench.
Sequentially processes all 4 maqam batches (Hijaz, Ajam, Kurd, Nahawand),
automatically fixes JSON Unicode encoding (ensure_ascii=False),
and saves clean, human-readable Arabic JSON files.
"""

import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import List, Set

# Import all 4 song lists from all_songs.py
from all_songs import hijaz_songs, ajam_songs, kurd_songs, nahawand_songs

# ==========================================
# TASKS CONFIGURATION (All 4 Sets)
# ==========================================

REF_DIR = Path("/content/REF")  # Use Path("D:/MUSIC_GCP_UPLOAD/REF") if running locally

TASKS = [
    {
        "name": "Hijaz (حجاز)",
        "reference": REF_DIR / "حجاز_03-مشهد-الذئاب_SONG_B.mp3",
        "files": hijaz_songs,
        "output_json": "hijaz_results.json",
        "output_txt": "hijaz_results.txt",
    },
    {
        "name": "Ajam (عجم)",
        "reference": REF_DIR / "عجم_ليس-الجمال-بمئزر.mp3",
        "files": ajam_songs,
        "output_json": "ajam_results.json",
        "output_txt": "ajam_results.txt",
    },
    {
        "name": "Kurd (كرد)",
        "reference": REF_DIR / "كرد_02-تعب-الحياة-ونواح-بنات-الهديل_SONG_B.mp3",
        "files": kurd_songs,
        "output_json": "kurd_results.json",
        "output_txt": "kurd_results.txt",
    },
    {
        "name": "Nahawand (نهاوند)",
        "reference": REF_DIR / "نهاوند_RETAKE_02-وحشة-الاغتراب-ووفاء-السلاح_SONG_B.mp3",
        "files": nahawand_songs,
        "output_json": "nahawand_results.json",
        "output_txt": "nahawand_results.txt",
    },
]

AUDIO_EXTENSIONS: Set[str] = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}
PYTHON_BIN = sys.executable


# ==========================================
# HELPER FUNCTIONS
# ==========================================


def fix_json_utf8_encoding(json_file_path: str):
    """
    Reads the generated JSON file and rewrites it with ensure_ascii=False
    so Arabic characters appear as real Arabic text rather than unicode escapes.
    """
    p = Path(json_file_path)
    if not p.exists():
        return

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[✓] Fixed UTF-8 Arabic text in: {json_file_path}")
    except Exception as e:
        print(f"[!] Warning: Could not re-encode {json_file_path}: {e}")


def collect_valid_files(file_list: List[str]) -> List[Path]:
    """Filters and validates explicit files."""
    valid_files = set()
    for file_path in file_list:
        p = Path(file_path).expanduser().resolve()
        if p.exists() and p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
            valid_files.add(p)
        else:
            print(f"  [!] Warning: Missing or invalid file: {file_path}")
    return sorted(list(valid_files))


def run_single_task(task: dict, extra_args: List[str]) -> bool:
    name = task["name"]
    ref_path = Path(task["reference"]).expanduser().resolve()
    raw_files = task["files"]
    output_json = task["output_json"]
    output_txt = task.get("output_txt")

    print("\n" + "=" * 70)
    print(f"STARTING BATCH: {name}")
    print("=" * 70)
    print(f"Reference Audio : {ref_path}")

    # Validate Reference
    if not ref_path.exists():
        print(f"[ERROR] Reference file does not exist: {ref_path}")
        return False

    # Validate Audio Files
    audio_files = collect_valid_files(raw_files)
    if not audio_files:
        print(f"[ERROR] No valid audio files found for {name}.")
        return False

    print(f"Discovered      : {len(audio_files)} audio chunks.")

    # Create temporary batch staging
    with tempfile.TemporaryDirectory(
        prefix=f"audiobench_{task['name'][:4]}_"
    ) as tmp_dir:
        tmp_path = Path(tmp_dir)

        for idx, file in enumerate(audio_files):
            link_name = tmp_path / f"{idx:04d}_{file.name}"
            try:
                os.symlink(file, link_name)
            except OSError:
                import shutil

                shutil.copyfile(file, link_name)

        print(f"Staged in       : {tmp_path}")
        print("Executing audio-qa benchmark...\n")

        # Build CLI command
        cmd = [
            PYTHON_BIN,
            "main.py",
            "--reference",
            str(ref_path),
            "--batch",
            str(tmp_path),
            "--save-json",
            output_json,
        ]

        if output_txt:
            cmd.extend(["--output", output_txt])

        cmd.extend(extra_args)

        start_time = time.time()
        try:
            process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
            process.communicate()

            elapsed = round(time.time() - start_time, 2)
            if process.returncode != 0:
                print(
                    f"\n[!] Task '{name}' failed with status code: {process.returncode}"
                )
                return False
            else:
                print(f"\n[✓] Finished '{name}' successfully in {elapsed}s.")
                # Automatically fix the Unicode escapes to readable Arabic
                fix_json_utf8_encoding(output_json)
                return True

        except KeyboardInterrupt:
            print("\n[!] Pipeline interrupted by user.")
            sys.exit(130)


# ==========================================
# MAIN ENTRYPOINT
# ==========================================


def main():
    extra_args = sys.argv[1:]
    total_tasks = len(TASKS)
    successful = 0

    print("=" * 70)
    print(f"AUTOMATED QUEUE: Processing all {total_tasks} maqam sets")
    print("=" * 70)

    for idx, task in enumerate(TASKS, 1):
        print(f"\n>>> Processing Queue Item [{idx}/{total_tasks}]: {task['name']}")
        ok = run_single_task(task, extra_args)
        if ok:
            successful += 1

    print("\n" + "=" * 70)
    print(f"ALL TASKS COMPLETED: {successful}/{total_tasks} succeeded.")
    print("=" * 70)


if __name__ == "__main__":
    main()
