"""Synthetic multi-view images with known geometry, for pipeline sanity checks."""
from __future__ import annotations

from pathlib import Path

from casual3d.reconstruct import import_pycolmap


def make_synthetic_object(
    output_dir: Path, num_views: int = 8, num_points: int = 150, seed: int = 0
) -> Path:
    """Render num_views 640x480 images of a random textured point set into output_dir.

    Defaults are tuned so COLMAP registers every view; denser point sets make the
    rendered feature patches overlap and matching degrades.
    """
    pycolmap = import_pycolmap()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    pycolmap.set_random_seed(seed)

    options = pycolmap.SyntheticDatasetOptions()
    options.num_rigs = 1
    options.num_cameras_per_rig = 1
    options.num_frames_per_rig = num_views
    options.num_points3D = num_points
    options.camera_width = 640
    options.camera_height = 480
    options.camera_params = [800.0, 320.0, 240.0, 0.0]
    ground_truth = pycolmap.synthesize_dataset(options)
    pycolmap.synthesize_images(pycolmap.SyntheticImageOptions(), ground_truth, output_dir)
    return output_dir
