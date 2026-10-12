import hashlib
import json
from pathlib import Path

from PIL import Image

from casual3d.cli import main


def test_cli_writes_manifest_and_prints_its_hash(tmp_path: Path, capsys):
    root = tmp_path / "raw"
    (root / "bolt_01").mkdir(parents=True)
    Image.new("RGB", (8, 8)).save(root / "bolt_01" / "view_01.png")
    output = tmp_path / "out" / "manifest.json"

    assert main([str(root), "--output", str(output)]) == 0

    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["valid_image_count"] == 1
    expected_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    assert f"Manifest SHA-256: {expected_hash}" in capsys.readouterr().out


def test_cli_reports_missing_dataset(tmp_path: Path, capsys):
    output = tmp_path / "manifest.json"

    assert main([str(tmp_path / "missing"), "--output", str(output)]) == 2

    assert "error:" in capsys.readouterr().err
    assert not output.exists()
