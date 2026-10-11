"""Create deterministic manifests for multi-view image datasets."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(dataset_root: Path) -> dict[str, Any]:
    """Build a stable manifest from dataset_root/<object_id>/<image_file>."""
    root = dataset_root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Dataset directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Dataset path is not a directory: {root}")

    objects: list[dict[str, Any]] = []
    image_count = 0

    for object_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        images: list[dict[str, Any]] = []
        for image_path in sorted(p for p in object_dir.rglob("*")
                                 if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS):
            try:
                with Image.open(image_path) as image:
                    width, height = image.size
                    image_format = image.format
                    image.verify()
                # verify() only checks structure; a full decode catches truncated data.
                with Image.open(image_path) as image:
                    image.load()
            except Exception as exc:
                images.append({
                    "path": image_path.relative_to(root).as_posix(),
                    "valid": False,
                    "error": str(exc),
                })
                continue

            images.append({
                "path": image_path.relative_to(root).as_posix(),
                "valid": True,
                "width": width,
                "height": height,
                "format": image_format,
                "size_bytes": image_path.stat().st_size,
                "sha256": sha256_file(image_path),
            })
            image_count += 1

        objects.append({
            "object_id": object_dir.name,
            "image_count": sum(1 for item in images if item["valid"]),
            "images": images,
        })

    return {
        "schema_version": 1,
        "dataset_root_name": root.name,
        "object_count": len(objects),
        "valid_image_count": image_count,
        "objects": objects,
    }
