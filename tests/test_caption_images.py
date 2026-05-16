from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from caption_images_with_codex import iter_image_files, needs_caption  # noqa: E402
from lib.extract import caption_path_for_image  # noqa: E402


def test_iter_image_files_dedupes_roots(tmp_path: Path) -> None:
    image_path = tmp_path / "resources" / "quiz.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"image")

    roots = {"quizzes": [str(tmp_path / "resources"), str(tmp_path / "resources")]}

    assert list(iter_image_files(roots)) == [image_path.resolve()]


def test_needs_caption_detects_missing_stub_and_existing_caption(tmp_path: Path) -> None:
    image_path = tmp_path / "quiz.png"
    image_path.write_bytes(b"image")
    caption_root = tmp_path / "captions"

    assert needs_caption(image_path, caption_root, overwrite=False)

    caption_path = caption_path_for_image(image_path, caption_root)
    caption_path.parent.mkdir(parents=True)
    caption_path.write_text("# Caption needed for quiz.png\n\nDescribe it.", encoding="utf-8")
    assert needs_caption(image_path, caption_root, overwrite=False)

    caption_path.write_text("A diagram showing a split criterion.", encoding="utf-8")
    assert not needs_caption(image_path, caption_root, overwrite=False)
    assert needs_caption(image_path, caption_root, overwrite=True)
