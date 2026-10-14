"""Compare estimated camera poses with a reference model (e.g. synthetic ground truth)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from casual3d.reconstruct import import_pycolmap


def umeyama_similarity(source: np.ndarray, target: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """Least-squares similarity (scale, rotation, translation) with target ≈ scale * R @ source + t.

    source and target are (N, 3) arrays of corresponding points, N >= 3 and not collinear.
    """
    source_mean = source.mean(axis=0)
    target_mean = target.mean(axis=0)
    source_centred = source - source_mean
    target_centred = target - target_mean
    covariance = target_centred.T @ source_centred / len(source)
    u, singular_values, vt = np.linalg.svd(covariance)
    sign = np.eye(3)
    if np.linalg.det(u) * np.linalg.det(vt) < 0:
        sign[2, 2] = -1.0
    rotation = u @ sign @ vt
    source_variance = (source_centred ** 2).sum() / len(source)
    scale = float(np.trace(np.diag(singular_values) @ sign) / source_variance)
    translation = target_mean - scale * rotation @ source_mean
    return scale, rotation, translation


def _rotation_angle_deg(rotation: np.ndarray) -> float:
    cosine = (np.trace(rotation) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))


def _stats(values: np.ndarray) -> dict[str, float]:
    return {"mean": float(values.mean()), "median": float(np.median(values)), "max": float(values.max())}


def evaluate_poses(estimated_model_dir: Path, reference_model_dir: Path) -> dict[str, Any]:
    """Align estimated camera centres to the reference (similarity transform) and report errors.

    Images are matched by name. Position errors are given in reference units and relative to
    the reference scene size (median camera distance from the camera centroid), since SfM
    scale is arbitrary.
    """
    pycolmap = import_pycolmap()
    estimated = pycolmap.Reconstruction(estimated_model_dir)
    reference = pycolmap.Reconstruction(reference_model_dir)
    estimated_by_name = {image.name: image for image in estimated.images.values() if image.has_pose}
    reference_by_name = {image.name: image for image in reference.images.values() if image.has_pose}
    common = sorted(estimated_by_name.keys() & reference_by_name.keys())
    if len(common) < 3:
        raise ValueError(f"Need at least 3 images posed in both models, found {len(common)}")

    estimated_centres = np.array([estimated_by_name[name].projection_center() for name in common])
    reference_centres = np.array([reference_by_name[name].projection_center() for name in common])
    scale, rotation, translation = umeyama_similarity(estimated_centres, reference_centres)
    aligned_centres = scale * estimated_centres @ rotation.T + translation
    position_errors = np.linalg.norm(aligned_centres - reference_centres, axis=1)
    scene_size = float(np.median(np.linalg.norm(reference_centres - reference_centres.mean(axis=0), axis=1)))

    rotation_errors = []
    focal_errors = []
    for name in common:
        estimated_image = estimated_by_name[name]
        reference_image = reference_by_name[name]
        # cam_from_world of the aligned estimate is R_est @ rotation.T.
        estimated_rotation = estimated_image.cam_from_world().rotation.matrix() @ rotation.T
        reference_rotation = reference_image.cam_from_world().rotation.matrix()
        rotation_errors.append(_rotation_angle_deg(estimated_rotation @ reference_rotation.T))
        reference_focal = reference.cameras[reference_image.camera_id].mean_focal_length()
        estimated_focal = estimated.cameras[estimated_image.camera_id].mean_focal_length()
        focal_errors.append(abs(estimated_focal - reference_focal) / reference_focal)

    rotation_errors = np.array(rotation_errors)
    focal_errors = np.array(focal_errors)
    return {
        "schema_version": 1,
        "kind": "pose_evaluation",
        "alignment": "similarity (Umeyama) on camera centres, images matched by name",
        "reference_images": len(reference_by_name),
        "common_images": len(common),
        "missing_images": sorted(reference_by_name.keys() - estimated_by_name.keys()),
        "alignment_scale": scale,
        "reference_scene_size": scene_size,
        "rotation_error_deg": _stats(rotation_errors),
        "position_error": _stats(position_errors),
        "position_error_relative": _stats(position_errors / scene_size),
        "focal_length_error_relative": _stats(focal_errors),
        "per_image": [
            {
                "name": name,
                "rotation_error_deg": float(rotation_error),
                "position_error": float(position_error),
            }
            for name, rotation_error, position_error in zip(common, rotation_errors, position_errors)
        ],
    }
