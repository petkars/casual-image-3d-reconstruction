import json
from pathlib import Path

import pytest
from PIL import Image

from casual3d.cli import reconstruct_main
from casual3d.reconstruct import SparseConfig, list_images, list_skipped_files, run_sparse_reconstruction


def test_list_images_skips_hidden_and_unsupported(tmp_path: Path):
    (tmp_path / "sub").mkdir()
    for name in ("b.jpg", "a.PNG", "sub/c.png", "._b.jpg", "notes.txt"):
        (tmp_path / name).write_bytes(b"")

    assert list_images(tmp_path) == ["a.PNG", "b.jpg", "sub/c.png"]
    assert list_skipped_files(tmp_path) == ["notes.txt"]


def test_cli_warns_about_heic_photos(tmp_path: Path, capsys):
    pytest.importorskip("pycolmap")
    from casual3d.synthetic import make_synthetic_object

    images = make_synthetic_object(tmp_path / "images", num_views=8)
    (images / "IMG_0001.HEIC").write_bytes(b"heic data")

    assert reconstruct_main([str(images), "--output", str(tmp_path / "run")]) == 0

    record = json.loads((tmp_path / "run" / "run.json").read_text(encoding="utf-8"))
    assert record["input"]["skipped_files"] == ["IMG_0001.HEIC"]
    assert "Most Compatible" in capsys.readouterr().err


def test_rejects_non_empty_output_dir(tmp_path: Path):
    images = tmp_path / "images"
    images.mkdir()
    output = tmp_path / "run"
    output.mkdir()
    (output / "stale.txt").write_text("old run")

    with pytest.raises(FileExistsError):
        run_sparse_reconstruction(images, output)


def test_rejects_mixed_image_sizes_with_shared_camera(tmp_path: Path):
    images = tmp_path / "images"
    images.mkdir()
    Image.new("RGB", (64, 48)).save(images / "landscape.jpg")
    Image.new("RGB", (48, 64)).save(images / "rotated.jpg")

    with pytest.raises(ValueError, match="per-image-camera"):
        run_sparse_reconstruction(images, tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_rejects_unknown_matcher(tmp_path: Path):
    with pytest.raises(ValueError):
        run_sparse_reconstruction(tmp_path, tmp_path / "run", SparseConfig(matcher="magic"))


def test_synthetic_object_reconstructs_all_views(tmp_path: Path):
    pytest.importorskip("pycolmap")
    from casual3d.synthetic import make_synthetic_object

    images = make_synthetic_object(tmp_path / "images", num_views=8)
    output = tmp_path / "run"

    assert reconstruct_main([str(images), "--output", str(output)]) == 0

    record = json.loads((output / "run.json").read_text(encoding="utf-8"))
    result = record["result"]
    assert result["status"] == "success"
    assert result["best_model"]["registered_images"] == 8
    assert result["unregistered_images"] == []
    assert result["best_model"]["mean_reprojection_error_px"] < 2.0
    assert record["input"]["image_count"] == 8
    assert all(len(image["sha256"]) == 64 for image in record["input"]["images"])
    assert record["input"]["skipped_files"] == []
    assert len(record["result"]["initial_cameras"]) == 1
    assert (output / "points3D.ply").is_file()
    camera_ply = (output / "cameras.ply").read_text(encoding="ascii").splitlines()
    assert "element vertex 8" in camera_ply
    assert len(camera_ply) == camera_ply.index("end_header") + 1 + 8
    assert (output / "sparse" / str(result["best_model_index"])).is_dir()


def test_unrelated_images_are_recorded_as_failure(tmp_path: Path):
    pytest.importorskip("pycolmap")
    images = tmp_path / "images"
    images.mkdir()
    for index in range(3):
        Image.new("RGB", (64, 64), color=(index * 80, 0, 0)).save(images / f"flat_{index}.png")
    output = tmp_path / "run"

    assert reconstruct_main([str(images), "--output", str(output)]) == 1

    record = json.loads((output / "run.json").read_text(encoding="utf-8"))
    assert record["result"]["status"] == "failed"
    assert len(record["result"]["unregistered_images"]) == 3
