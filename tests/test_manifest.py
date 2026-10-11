import json
from pathlib import Path

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
