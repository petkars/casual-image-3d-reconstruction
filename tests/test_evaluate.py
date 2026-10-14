import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")

from casual3d.evaluate import umeyama_similarity  # noqa: E402


def test_umeyama_recovers_known_similarity():
    rng = np.random.default_rng(0)
    source = rng.normal(size=(10, 3))
    angle = np.radians(30.0)
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0],
                         [np.sin(angle), np.cos(angle), 0.0],
                         [0.0, 0.0, 1.0]])
    target = 2.5 * source @ rotation.T + np.array([1.0, -2.0, 0.5])

    scale, estimated_rotation, translation = umeyama_similarity(source, target)

    assert scale == pytest.approx(2.5)
    np.testing.assert_allclose(estimated_rotation, rotation, atol=1e-9)
    np.testing.assert_allclose(translation, [1.0, -2.0, 0.5], atol=1e-9)


def test_umeyama_never_returns_a_reflection():
    rng = np.random.default_rng(1)
    source = rng.normal(size=(6, 3))
    target = source * np.array([1.0, 1.0, -1.0])  # mirror image: best proper rotation, not a reflection

    _, rotation, _ = umeyama_similarity(source, target)

    assert np.linalg.det(rotation) == pytest.approx(1.0)


def test_synthetic_reconstruction_matches_ground_truth(tmp_path: Path):
    pytest.importorskip("pycolmap")
    from casual3d.cli import evaluate_poses_main, reconstruct_main
    from casual3d.synthetic import make_synthetic_object

    images = make_synthetic_object(tmp_path / "images", ground_truth_dir=tmp_path / "ground_truth")
    run = tmp_path / "run"
    assert reconstruct_main([str(images), "--output", str(run)]) == 0

    assert evaluate_poses_main([str(run), str(tmp_path / "ground_truth")]) == 0

    evaluation = json.loads((run / "pose_evaluation.json").read_text(encoding="utf-8"))
    assert evaluation["common_images"] == 8
    assert evaluation["missing_images"] == []
    assert evaluation["rotation_error_deg"]["max"] < 1.0
    assert evaluation["position_error_relative"]["max"] < 0.02
    assert evaluation["focal_length_error_relative"]["median"] < 0.02


def test_model_compared_with_itself_has_zero_error(tmp_path: Path):
    pytest.importorskip("pycolmap")
    from casual3d.evaluate import evaluate_poses
    from casual3d.synthetic import make_synthetic_object

    make_synthetic_object(tmp_path / "images", ground_truth_dir=tmp_path / "ground_truth")

    evaluation = evaluate_poses(tmp_path / "ground_truth", tmp_path / "ground_truth")

    assert evaluation["alignment_scale"] == pytest.approx(1.0)
    assert evaluation["rotation_error_deg"]["max"] < 1e-3
    assert evaluation["position_error"]["max"] < 1e-9
