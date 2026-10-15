"""Point-cloud geometry metrics against reference geometry (accuracy, completeness, F-score)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial import cKDTree

from casual3d.reconstruct import import_pycolmap

# Thresholds as fractions of the reference bounding-box diagonal, so results are comparable
# across objects and arbitrary SfM scales.
DEFAULT_RELATIVE_THRESHOLDS = (0.005, 0.01, 0.02)


def load_points(path: Path, min_track_length: int = 0) -> np.ndarray:
    """(N, 3) points from a .ply file or a COLMAP model folder.

    min_track_length keeps only COLMAP points seen in at least that many images; points
    seen in only 2 images are weakly constrained and account for most outliers.
    """
    pycolmap = import_pycolmap()
    if path.is_dir():
        reconstruction = pycolmap.Reconstruction(path)
    elif path.suffix.lower() == ".ply":
        if min_track_length > 0:
            raise ValueError("min_track_length needs a COLMAP model; .ply files have no tracks")
        reconstruction = pycolmap.Reconstruction()
        reconstruction.import_PLY(path)
    else:
        raise ValueError(f"Expected a .ply file or a COLMAP model folder: {path}")
    points = np.array(
        [point.xyz for point in reconstruction.points3D.values() if point.track.length() >= min_track_length],
        dtype=float,
    )
    if len(points) == 0:
        raise ValueError(f"No 3D points in {path}")
    return points.reshape(-1, 3)


def apply_similarity(points: np.ndarray, transform: dict[str, Any]) -> np.ndarray:
    """Apply x' = scale * R @ x + t, with the transform stored in pose_evaluation.json."""
    rotation = np.asarray(transform["rotation"], dtype=float)
    translation = np.asarray(transform["translation"], dtype=float)
    return float(transform["scale"]) * points @ rotation.T + translation


def _stats(values: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "p90": float(np.percentile(values, 90)),
        "max": float(values.max()),
    }


def evaluate_geometry(
    estimated: np.ndarray,
    reference: np.ndarray,
    relative_thresholds: tuple[float, ...] = DEFAULT_RELATIVE_THRESHOLDS,
) -> dict[str, Any]:
    """Compare two point sets that are already in the same frame.

    accuracy: distance from each estimated point to the nearest reference point.
    completeness: distance from each reference point to the nearest estimated point.
    chamfer: mean of the two mean distances.
    At each threshold tau: precision = share of estimated points within tau of the reference,
    recall = share of reference points within tau of the estimate, F-score = harmonic mean,
    outlier_ratio = 1 - precision.
    """
    diagonal = float(np.linalg.norm(reference.max(axis=0) - reference.min(axis=0)))
    accuracy = cKDTree(reference).query(estimated)[0]
    completeness = cKDTree(estimated).query(reference)[0]

    thresholds = []
    for relative in relative_thresholds:
        tau = relative * diagonal
        precision = float((accuracy <= tau).mean())
        recall = float((completeness <= tau).mean())
        f_score = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
        thresholds.append({
            "relative_threshold": relative,
            "threshold": tau,
            "precision": precision,
            "recall": recall,
            "f_score": f_score,
            "outlier_ratio": 1.0 - precision,
        })

    return {
        "estimated_points": len(estimated),
        "reference_points": len(reference),
        "reference_bbox_diagonal": diagonal,
        "accuracy": _stats(accuracy),
        "completeness": _stats(completeness),
        "chamfer": float((accuracy.mean() + completeness.mean()) / 2),
        "chamfer_relative": float((accuracy.mean() + completeness.mean()) / 2 / diagonal),
        "thresholds": thresholds,
    }
