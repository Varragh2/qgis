"""Move new GPX uploads into the project's real_data folder."""

from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REAL_DATA_DIR = PROJECT_ROOT / "real_data"

# Update this value if you switch from iCloud Drive to another upload mechanism.
UPLOAD_SOURCE_DIR = Path(
    os.environ.get(
        "GPX_UPLOAD_DIR",
        "~/Library/Mobile Documents/com~apple~CloudDocs/GPX",
    )
).expanduser()


@dataclass
class DownloadResult:
    moved: list[Path] = field(default_factory=list)
    skipped_duplicates: list[Path] = field(default_factory=list)
    skipped_unavailable: list[Path] = field(default_factory=list)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _existing_digests(folder: Path) -> set[str]:
    if not folder.is_dir():
        return set()
    return {_sha256(path) for path in folder.glob("*.gpx") if path.is_file()}


def _unique_destination(path: Path, destination_folder: Path) -> Path:
    destination = destination_folder / path.name
    if not destination.exists():
        return destination

    counter = 1
    while True:
        candidate = destination_folder / f"{path.stem}_{counter}{path.suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def move_new_gpx_files(
    source_folder: Path = UPLOAD_SOURCE_DIR,
    destination_folder: Path = REAL_DATA_DIR,
) -> DownloadResult:
    """Move GPX files whose contents are not already in destination_folder."""
    result = DownloadResult()
    source_folder = source_folder.expanduser()
    destination_folder.mkdir(parents=True, exist_ok=True)

    if not source_folder.is_dir():
        raise FileNotFoundError(f"GPX upload folder not found: {source_folder}")

    known_digests = _existing_digests(destination_folder)

    for source in sorted(source_folder.iterdir()):
        if not source.is_file() or source.name.startswith("."):
            continue
        if source.suffix.lower() != ".gpx":
            continue

        try:
            source_digest = _sha256(source)
        except OSError:
            result.skipped_unavailable.append(source)
            continue

        if source_digest in known_digests:
            result.skipped_duplicates.append(source)
            continue

        destination = _unique_destination(source, destination_folder)
        shutil.move(str(source), str(destination))
        known_digests.add(source_digest)
        result.moved.append(destination)

    return result


def main() -> DownloadResult:
    result = move_new_gpx_files()

    print("=" * 30)
    print("GPX DOWNLOAD SUMMARY")
    print(f"Source: {UPLOAD_SOURCE_DIR}")
    print(f"Destination: {REAL_DATA_DIR}")
    print(f"Moved: {len(result.moved)}")
    for path in result.moved:
        print(f"  + {path.name}")
    print(f"Duplicates skipped: {len(result.skipped_duplicates)}")
    for path in result.skipped_duplicates:
        print(f"  - {path.name}")
    if result.skipped_unavailable:
        print(f"Unavailable files skipped: {len(result.skipped_unavailable)}")
        for path in result.skipped_unavailable:
            print(f"  ! {path.name}")
    print("=" * 30)

    return result


if __name__ == "__main__":
    main()
