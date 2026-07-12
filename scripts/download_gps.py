"""Move new GPX uploads into the project's real_data folder."""

from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from constants import REAL_DATA_DIR, UPLOAD_SOURCE_DIR

LOGGER = logging.getLogger(__name__)


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
    try:
        result = move_new_gpx_files()
    except FileNotFoundError:
        LOGGER.warning("GPX upload folder not found; continuing without new downloads: %s", UPLOAD_SOURCE_DIR)
        result = DownloadResult()

    LOGGER.info("GPX DOWNLOAD SUMMARY")
    LOGGER.info("Source: %s", UPLOAD_SOURCE_DIR)
    LOGGER.info("Destination: %s", REAL_DATA_DIR)
    LOGGER.info("Moved: %s", len(result.moved))
    for path in result.moved:
        LOGGER.info("  + %s", path.name)
    LOGGER.info("Duplicates skipped: %s", len(result.skipped_duplicates))
    for path in result.skipped_duplicates:
        LOGGER.info("  - %s", path.name)
    if result.skipped_unavailable:
        LOGGER.warning("Unavailable files skipped: %s", len(result.skipped_unavailable))
        for path in result.skipped_unavailable:
            LOGGER.warning("  ! %s", path.name)

    return result


if __name__ == "__main__":
    main()
