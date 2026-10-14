"""Command-line entry points: dataset manifests, the sparse reconstruction baseline, pose evaluation."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from casual3d.manifest import build_manifest
from casual3d.reconstruct import MATCHERS, SparseConfig, run_sparse_reconstruction


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and inventory an object-organised image dataset.")
    parser.add_argument("dataset_root", type=Path, help="Folder containing one subfolder per object")
    parser.add_argument("--output", type=Path, default=Path("results/dataset_manifest.json"))
    args = parser.parse_args(argv)

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


def reconstruct_main(argv: list[str] | None = None) -> int:
    defaults = SparseConfig()
    parser = argparse.ArgumentParser(
        description="Run the COLMAP sparse SfM baseline on one object's images and write run.json."
    )
    parser.add_argument("image_dir", type=Path, help="Folder of images of a single object")
    parser.add_argument("--output", type=Path, required=True, help="New or empty run directory")
    parser.add_argument("--camera-model", default=defaults.camera_model)
    parser.add_argument("--per-image-camera", action="store_true",
                        help="Estimate intrinsics per image (mixed cameras/zoom) instead of one shared camera")
    parser.add_argument("--matcher", choices=MATCHERS, default=defaults.matcher)
    parser.add_argument("--max-image-size", type=int, default=defaults.max_image_size)
    parser.add_argument("--seed", type=int, default=defaults.random_seed)
    args = parser.parse_args(argv)

    config = SparseConfig(
        camera_model=args.camera_model,
        single_camera=not args.per_image_camera,
        matcher=args.matcher,
        max_image_size=args.max_image_size,
        random_seed=args.seed,
    )
    try:
        record = run_sparse_reconstruction(args.image_dir, args.output, config)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    skipped = record["input"]["skipped_files"]
    if skipped:
        print(f"Warning: skipped {len(skipped)} unsupported file(s): {', '.join(skipped[:5])}"
              f"{' ...' if len(skipped) > 5 else ''}", file=sys.stderr)
        if any(Path(name).suffix.lower() in (".heic", ".heif") for name in skipped):
            print("Warning: HEIC photos are not read; convert to JPEG or set iPhone "
                  "Camera > Formats > Most Compatible.", file=sys.stderr)

    record_path = args.output / "run.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    result = record["result"]
    print(f"Status: {result['status']}")
    if result["status"] == "success":
        model = result["best_model"]
        print(f"Registered images: {model['registered_images']}/{record['input']['image_count']}")
        print(f"3D points: {model['points3D']}")
        print(f"Mean reprojection error: {model['mean_reprojection_error_px']:.3f} px")
    else:
        print(f"Failure: {result['failure_reason']}")
    print(f"Total time: {record['timings_s']['total']:.1f} s")
    print(f"Run record: {record_path}")
    return 0 if result["status"] == "success" else 1


def evaluate_poses_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare a run's camera poses with a reference COLMAP model (e.g. synthetic ground truth)."
    )
    parser.add_argument("run_dir", type=Path, help="Run folder from casual3d-reconstruct, or a COLMAP model folder")
    parser.add_argument("reference_model", type=Path, help="Reference COLMAP model folder")
    parser.add_argument("--output", type=Path, help="Default: <run_dir>/pose_evaluation.json")
    args = parser.parse_args(argv)

    run_record = args.run_dir / "run.json"
    if run_record.is_file():
        model_dir = json.loads(run_record.read_text(encoding="utf-8"))["outputs"].get("model_dir")
        if model_dir is None:
            print(f"error: run produced no model: {run_record}", file=sys.stderr)
            return 2
        estimated_model = args.run_dir / model_dir
    else:
        estimated_model = args.run_dir
    output = args.output or args.run_dir / "pose_evaluation.json"

    from casual3d.evaluate import evaluate_poses

    try:
        evaluation = evaluate_poses(estimated_model, args.reference_model)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output.write_text(json.dumps(evaluation, indent=2) + "\n", encoding="utf-8")
    print(f"Images compared: {evaluation['common_images']}/{evaluation['reference_images']}")
    print(f"Rotation error (deg): median {evaluation['rotation_error_deg']['median']:.3f}, "
          f"max {evaluation['rotation_error_deg']['max']:.3f}")
    print(f"Position error (% of scene size): median {100 * evaluation['position_error_relative']['median']:.2f}, "
          f"max {100 * evaluation['position_error_relative']['max']:.2f}")
    print(f"Focal length error (%): median {100 * evaluation['focal_length_error_relative']['median']:.2f}")
    print(f"Evaluation: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
