from pathlib import Path

import pytest
from PIL import Image

from casual3d.manifest import build_manifest


def test_manifest_records_object_images_and_hash(tmp_path: Path):
    root = tmp_path / "raw"
    object_dir = root / "bolt_01"
    object_dir.mkdir(parents=True)
    Image.new("RGB", (32, 24), color=(10, 20, 30)).save(object_dir / "view_01.png")

    manifest = build_manifest(root)

    assert manifest["object_count"] == 1
    assert manifest["valid_image_count"] == 1
    item = manifest["objects"][0]["images"][0]
    assert item["path"] == "bolt_01/view_01.png"
    assert item["width"] == 32
    assert item["height"] == 24
    assert len(item["sha256"]) == 64


def test_manifest_is_deterministically_ordered(tmp_path: Path):
    root = tmp_path / "raw"
    for name in ("z_object", "a_object"):
        folder = root / name
        folder.mkdir(parents=True)
        Image.new("RGB", (8, 8)).save(folder / "image.png")

    manifest = build_manifest(root)

    assert [item["object_id"] for item in manifest["objects"]] == ["a_object", "z_object"]


def test_manifest_flags_truncated_and_corrupt_images(tmp_path: Path):
    root = tmp_path / "raw"
    object_dir = root / "bolt_01"
    object_dir.mkdir(parents=True)
    truncated = object_dir / "truncated.jpg"
    Image.effect_noise((64, 64), 50).convert("RGB").save(truncated, "JPEG")
    truncated.write_bytes(truncated.read_bytes()[: truncated.stat().st_size // 2])
    (object_dir / "not_an_image.png").write_bytes(b"not image data")

    manifest = build_manifest(root)

    assert manifest["valid_image_count"] == 0
    assert manifest["objects"][0]["image_count"] == 0
    assert all(not item["valid"] for item in manifest["objects"][0]["images"])


def test_manifest_rejects_missing_root(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        build_manifest(tmp_path / "missing")
