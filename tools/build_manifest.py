#!/usr/bin/env python3
"""Validate and inventory an object-organised image dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from casual3d.manifest import build_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_root", type=Path, help="Folder containing one subfolder per object")
    parser.add_argument("--output", type=Path, default=Path("results/dataset_manifest.json"))
    args = parser.parse_args()

    try:
        manifest = build_manifest(args.dataset_root)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, indent=2) + "\n"
    args.output.write_text(text, encoding="utf-8")
    print(f"Objects: {manifest['object_count']}")
    print(f"Valid images: {manifest['valid_image_count']}")
    print(f"Manifest: {args.output}")
    print(f"Manifest SHA-256: {hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
