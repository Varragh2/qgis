from pathlib import Path

from download_gps import move_new_gpx_files


def _write_gpx(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_move_new_gpx_files(tmp_path):
    source = tmp_path / "icloud"
    destination = tmp_path / "real_data"
    source.mkdir()

    _write_gpx(source / "walk.gpx", "<gpx>new</gpx>")
    (source / "notes.txt").write_text("ignore me", encoding="utf-8")

    result = move_new_gpx_files(source, destination)

    assert [path.name for path in result.moved] == ["walk.gpx"]
    assert (destination / "walk.gpx").is_file()
    assert not (source / "walk.gpx").exists()
    assert not (destination / "notes.txt").exists()


def test_skip_duplicate_gpx_by_content(tmp_path):
    source = tmp_path / "icloud"
    destination = tmp_path / "real_data"
    source.mkdir()
    destination.mkdir()

    _write_gpx(destination / "already_here.gpx", "<gpx>same</gpx>")
    _write_gpx(source / "renamed_duplicate.gpx", "<gpx>same</gpx>")

    result = move_new_gpx_files(source, destination)

    assert result.moved == []
    assert [path.name for path in result.skipped_duplicates] == [
        "renamed_duplicate.gpx"
    ]
    assert (source / "renamed_duplicate.gpx").is_file()


def test_same_filename_different_content_gets_unique_name(tmp_path):
    source = tmp_path / "icloud"
    destination = tmp_path / "real_data"
    source.mkdir()
    destination.mkdir()

    _write_gpx(destination / "walk.gpx", "<gpx>old</gpx>")
    _write_gpx(source / "walk.gpx", "<gpx>new</gpx>")

    result = move_new_gpx_files(source, destination)

    assert [path.name for path in result.moved] == ["walk_1.gpx"]
    assert (destination / "walk.gpx").read_text(encoding="utf-8") == "<gpx>old</gpx>"
    assert (destination / "walk_1.gpx").read_text(encoding="utf-8") == "<gpx>new</gpx>"
