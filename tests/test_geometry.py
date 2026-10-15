import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from casual3d.geometry import apply_similarity, evaluate_geometry  # noqa: E402


def _rotation_z(degrees: float) -> np.ndarray:
    angle = np.radians(degrees)
    return np.array([[np.cos(angle), -np.sin(angle), 0.0],
                     [np.sin(angle), np.cos(angle), 0.0],
                     [0.0, 0.0, 1.0]])


def test_identical_points_score_perfectly():
    points = np.random.default_rng(0).uniform(-1, 1, size=(200, 3))

    evaluation = evaluate_geometry(points, points)

    assert evaluation["chamfer"] == 0.0
    assert all(row["f_score"] == 1.0 for row in evaluation["thresholds"])


def test_outliers_lower_precision_but_not_recall():
    rng = np.random.default_rng(1)
    reference = rng.uniform(-1, 1, size=(200, 3))
    estimated = np.vstack([reference, rng.uniform(5, 6, size=(50, 3))])  # 20% far-away outliers

    row = evaluate_geometry(estimated, reference)["thresholds"][1]

    assert row["precision"] == pytest.approx(0.8)
    assert row["recall"] == 1.0
    assert row["outlier_ratio"] == pytest.approx(0.2)


def test_missing_half_lowers_recall_but_not_precision():
    reference = np.random.default_rng(2).uniform(-1, 1, size=(400, 3))
    estimated = reference[reference[:, 0] < 0]  # only one side observed

    row = evaluate_geometry(estimated, reference)["thresholds"][1]

    assert row["precision"] == 1.0
    assert row["recall"] == pytest.approx(len(estimated) / len(reference))


def test_apply_similarity_undoes_known_transform():
    reference = np.random.default_rng(3).uniform(-1, 1, size=(50, 3))
    rotation = _rotation_z(40.0)
    # estimated = inverse transform of reference; the stored transform maps it back.
    estimated = (reference - np.array([0.5, 0.0, -1.0])) @ rotation / 3.0
    transform = {"scale": 3.0, "rotation": rotation.tolist(), "translation": [0.5, 0.0, -1.0]}

    np.testing.assert_allclose(apply_similarity(estimated, transform), reference, atol=1e-12)


def test_synthetic_run_geometry_against_ground_truth(tmp_path: Path):
    pytest.importorskip("pycolmap")
    from casual3d.cli import evaluate_geometry_main, evaluate_poses_main, reconstruct_main
    from casual3d.synthetic import make_synthetic_object

    images = make_synthetic_object(tmp_path / "images", ground_truth_dir=tmp_path / "ground_truth")
    run = tmp_path / "run"
    assert reconstruct_main([str(images), "--output", str(run)]) == 0
    assert evaluate_geometry_main([str(run), str(tmp_path / "ground_truth")]) == 2  # no alignment yet
    assert evaluate_poses_main([str(run), str(tmp_path / "ground_truth")]) == 0

    assert evaluate_geometry_main([str(run), str(tmp_path / "ground_truth")]) == 0

    all_points = json.loads((run / "geometry_evaluation.json").read_text(encoding="utf-8"))
    assert all_points["chamfer_relative"] < 0.02
    assert all_points["thresholds"][-1]["precision"] > 0.75

    # Two-view points are weakly constrained; requiring 3+ views removes most outliers.
    output = tmp_path / "filtered.json"
    assert evaluate_geometry_main([str(run), str(tmp_path / "ground_truth"),
                                   "--min-track-length", "3", "--output", str(output)]) == 0
    filtered = json.loads(output.read_text(encoding="utf-8"))
    assert filtered["estimated_points"] < all_points["estimated_points"]
    assert filtered["thresholds"][-1]["precision"] > all_points["thresholds"][-1]["precision"]
    assert filtered["thresholds"][-1]["precision"] > 0.9
