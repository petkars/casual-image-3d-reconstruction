"""Classical sparse structure-from-motion baseline (COLMAP via pycolmap)."""
from __future__ import annotations

import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from casual3d.manifest import SUPPORTED_EXTENSIONS, is_hidden, sha256_file

MATCHERS = ("exhaustive", "sequential")


@dataclass(frozen=True)
class SparseConfig:
    """Settings recorded with every run; defaults suit a few dozen photos of one object."""

    camera_model: str = "SIMPLE_RADIAL"
    single_camera: bool = True
    matcher: str = "exhaustive"
    max_image_size: int = 3200
    random_seed: int = 0
    num_threads: int = -1


def import_pycolmap():
    try:
        import pycolmap
    except ImportError as exc:
        raise RuntimeError(
            'pycolmap is not installed; run: python -m pip install -e ".[recon]"'
        ) from exc
    return pycolmap


def list_images(image_dir: Path) -> list[str]:
    """Supported, non-hidden images below image_dir as sorted POSIX paths relative to it."""
    return sorted(
        p.relative_to(image_dir).as_posix()
        for p in image_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS and not is_hidden(p, image_dir)
    )


def list_skipped_files(image_dir: Path) -> list[str]:
    """Non-hidden files that list_images ignores, e.g. iPhone .HEIC photos or .AAE sidecars."""
    return sorted(
        p.relative_to(image_dir).as_posix()
        for p in image_dir.rglob("*")
        if p.is_file() and p.suffix.lower() not in SUPPORTED_EXTENSIONS and not is_hidden(p, image_dir)
    )


def _check_single_image_size(image_dir: Path, image_names: list[str]) -> None:
    """COLMAP silently drops images whose size differs from the shared camera's; fail loudly instead."""
    sizes: dict[tuple[int, int], list[str]] = {}
    for name in image_names:
        with Image.open(image_dir / name) as image:
            sizes.setdefault(image.size, []).append(name)
    if len(sizes) > 1:
        summary = "; ".join(
            f"{width}x{height}: {len(names)} image(s), e.g. {names[0]}"
            for (width, height), names in sorted(sizes.items(), key=lambda item: -len(item[1]))
        )
        raise ValueError(
            f"Images have different sizes ({summary}). A shared camera needs one size: "
            "remove or re-export the odd images, or use --per-image-camera."
        )


def _camera_record(camera: Any) -> dict[str, Any]:
    return {
        "model": camera.model.name,
        "width": camera.width,
        "height": camera.height,
        "params": [float(value) for value in camera.params],
    }


def _summarise_model(reconstruction: Any) -> dict[str, Any]:
    return {
        "registered_images": reconstruction.num_reg_images(),
        "points3D": reconstruction.num_points3D(),
        "mean_reprojection_error_px": reconstruction.compute_mean_reprojection_error(),
        "mean_track_length": reconstruction.compute_mean_track_length(),
        "cameras": [_camera_record(camera) for _, camera in sorted(reconstruction.cameras.items())],
    }


def run_sparse_reconstruction(
    image_dir: Path, output_dir: Path, config: SparseConfig = SparseConfig()
) -> dict[str, Any]:
    """Run feature extraction, matching and incremental mapping; return the run record.

    Writes database.db, sparse/<model>/, points3D.ply (largest model) to output_dir.
    A run that registers no images is returned with status "failed", not raised.
    """
    image_dir = image_dir.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not image_dir.is_dir():
        raise NotADirectoryError(f"Image directory does not exist: {image_dir}")
    if config.matcher not in MATCHERS:
        raise ValueError(f"matcher must be one of {MATCHERS}, got {config.matcher!r}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output_dir}")
    image_names = list_images(image_dir)
    if len(image_names) < 2:
        raise ValueError(f"Need at least 2 images, found {len(image_names)} in {image_dir}")

    if config.single_camera:
        _check_single_image_size(image_dir, image_names)

    pycolmap = import_pycolmap()
    pycolmap.set_random_seed(config.random_seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    database_path = output_dir / "database.db"
    sparse_dir = output_dir / "sparse"
    sparse_dir.mkdir()

    reader_options = pycolmap.ImageReaderOptions()
    reader_options.camera_model = config.camera_model
    extraction_options = pycolmap.FeatureExtractionOptions()
    extraction_options.max_image_size = config.max_image_size
    extraction_options.num_threads = config.num_threads
    mapping_options = pycolmap.IncrementalPipelineOptions()
    mapping_options.random_seed = config.random_seed
    mapping_options.num_threads = config.num_threads

    timings: dict[str, float] = {}
    start = time.perf_counter()
    pycolmap.extract_features(
        database_path,
        image_dir,
        image_names=image_names,
        camera_mode=pycolmap.CameraMode.SINGLE if config.single_camera else pycolmap.CameraMode.PER_IMAGE,
        reader_options=reader_options,
        extraction_options=extraction_options,
    )
    timings["feature_extraction"] = time.perf_counter() - start
    # Starting intrinsics; the focal length comes from EXIF when has_prior_focal_length is true.
    with pycolmap.Database.open(database_path) as database:
        initial_cameras = [
            {**_camera_record(camera), "has_prior_focal_length": bool(camera.has_prior_focal_length)}
            for camera in sorted(database.read_all_cameras(), key=lambda camera: camera.camera_id)
        ]

    stage_start = time.perf_counter()
    if config.matcher == "exhaustive":
        pycolmap.match_exhaustive(database_path)
    else:
        pycolmap.match_sequential(database_path)
    timings["matching"] = time.perf_counter() - stage_start

    stage_start = time.perf_counter()
    models = pycolmap.incremental_mapping(database_path, image_dir, sparse_dir, options=mapping_options)
    timings["mapping"] = time.perf_counter() - stage_start
    timings["total"] = time.perf_counter() - start

    result: dict[str, Any] = {"num_models": len(models), "initial_cameras": initial_cameras}
    outputs: dict[str, str] = {"database": database_path.name}
    if models:
        best_index, best = max(models.items(), key=lambda item: (item[1].num_reg_images(), -item[0]))
        registered = {image.name for image in best.images.values() if image.has_pose}
        best.export_PLY(output_dir / "points3D.ply")
        result.update(
            status="success",
            best_model_index=best_index,
            best_model=_summarise_model(best),
            unregistered_images=[name for name in image_names if name not in registered],
        )
        outputs.update(model_dir=f"sparse/{best_index}", points_ply="points3D.ply")
    else:
        result.update(
            status="failed",
            failure_reason="no model: too few verified matches to initialise reconstruction",
            unregistered_images=image_names,
        )

    return {
        "schema_version": 1,
        "kind": "sparse_sfm",
        "method": "COLMAP incremental SfM (SIFT features)",
        "software": {
            "pycolmap": pycolmap.__version__,
            "colmap": pycolmap.COLMAP_version,
            "cuda": bool(pycolmap.has_cuda),
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "config": asdict(config),
        "input": {
            "image_dir_name": image_dir.name,
            "image_count": len(image_names),
            "images": [{"path": name, "sha256": sha256_file(image_dir / name)} for name in image_names],
            "skipped_files": list_skipped_files(image_dir),
        },
        "timings_s": timings,
        "result": result,
        "outputs": outputs,
    }
