#!/usr/bin/env python3
"""
Auxiliary runner for AudioBench.
Runs benchmarks against audio chunks distributed across multiple directories
without modifying any existing repository code.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import List, Set


# ==========================================
# CONFIGURATION
# ==========================================

# 1. Reference Audio Path
REFERENCE_AUDIO = "data/audio/REF_01.mp3"

# 2. Add all directories where your chunks/mp3s are scattered
SEARCH_DIRECTORIES = [
    "data/audio/WAV",
    "data/audio/other_folder",
    "experiments/recordings/speaker_1",
    "/absolute/path/to/another/batch_dir",
]

# 3. (Optional) Explicit list of individual files to include
EXPLICIT_FILES = [
    # "data/special_cases/sample_99.mp3",
]

# 4. Audio formats to collect
AUDIO_EXTENSIONS: Set[str] = {".mp3", ".wav", ".flac", ".ogg", ".m4a"}

# 5. Python executable / command to run
PYTHON_BIN = sys.executable  # Uses the currently active virtualenv/python


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def collect_audio_files(directories: List[str], explicit_files: List[str]) -> List[Path]:
    """Recursively collects and deduplicates audio files from directories and file lists."""
    collected = set()

    # Search in directories
    for dir_path in directories:
        p = Path(dir_path).expanduser().resolve()
        if not p.exists():
            print(f"[!] Warning: Directory not found, skipping: {dir_path}")
            continue

        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
            collected.add(p)
        elif p.is_dir():
            for file_path in p.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in AUDIO_EXTENSIONS:
                    collected.add(file_path.resolve())

    # Add explicit individual files
    for file_path in explicit_files:
        p = Path(file_path).expanduser().resolve()
        if p.exists() and p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
            collected.add(p)
        else:
            print(f"[!] Warning: Explicit file not found or invalid format: {file_path}")

    return sorted(list(collected))


def main():
    # 1. Validate Reference File
    ref_path = Path(REFERENCE_AUDIO).expanduser().resolve()
    if not ref_path.exists():
        print(f"[ERROR] Reference file not found: {ref_path}")
        sys.exit(1)

    print("=" * 60)
    print("AUDIOBENCH - SCATTERED BATCH RUNNER")
    print("=" * 60)
    print(f"Reference Audio : {ref_path}")

    # 2. Collect all scattered audio files
    audio_files = collect_audio_files(SEARCH_DIRECTORIES, EXPLICIT_FILES)
    if not audio_files:
        print("[ERROR] No audio files found in the specified paths.")
        sys.exit(1)

    print(f"Discovered      : {len(audio_files)} audio chunks across folders.")

    # 3. Create isolated staging directory with symlinks
    with tempfile.TemporaryDirectory(prefix="audiobench_batch_") as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create unique symlinks to avoid name collisions across folders
        for idx, file in enumerate(audio_files):
            # Format: 0001_original_name.mp3
            link_name = tmp_path / f"{idx:04d}_{file.name}"
            try:
                os.symlink(file, link_name)
            except OSError:
                # Fallback for Windows without symlink privileges
                import shutil
                shutil.copyfile(file, link_name)

        print(f"Staged in       : {tmp_path}")
        print("=" * 60)
        print("Executing benchmark...\n")

        # 4. Run main.py unmodified
        cmd = [
            PYTHON_BIN,
            "main.py",
            "--reference", str(ref_path),
            "--batch", str(tmp_path),
        ]

        # Pass along any extra CLI flags passed to this script (e.g. --device cuda)
        if len(sys.argv) > 1:
            cmd.extend(sys.argv[1:])

        try:
            # Stream output directly to the terminal in real-time
            process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)
            process.communicate()
            
            if process.returncode != 0:
                print(f"\n[!] Process exited with status code: {process.returncode}")
            else:
                print("\n[✓] Benchmark completed successfully.")

        except KeyboardInterrupt:
            print("\n[!] Execution interrupted by user.")
            sys.exit(130)


if __name__ == "__main__":
    main()