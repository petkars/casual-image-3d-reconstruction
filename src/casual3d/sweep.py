"""Robustness sweep on synthetic objects: where does the sparse baseline break down?"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from casual3d.reconstruct import SparseConfig, run_sparse_reconstruction

CSV_FIELDS = (
    "views", "points", "seed", "status", "registered", "registered_ratio",
    "rotation_error_median_deg", "position_error_median_rel", "chamfer_rel",
    "precision_2pct", "recall_2pct", "f_score_2pct", "total_s",
)


def run_one(output_dir: Path, views: int, points: int, seed: int,
            min_track_length: int = 0) -> dict[str, Any]:
    """Generate one synthetic object, reconstruct it and evaluate poses and geometry."""
    from casual3d.evaluate import evaluate_poses
    from casual3d.geometry import apply_similarity, evaluate_geometry, load_points
    from casual3d.synthetic import make_synthetic_object

    case_dir = output_dir / f"v{views:02d}_p{points:04d}_s{seed}"
    images = make_synthetic_object(case_dir / "images", num_views=views, num_points=points,
                                   seed=seed, ground_truth_dir=case_dir / "ground_truth")
    record = run_sparse_reconstruction(images, case_dir / "run", SparseConfig(random_seed=seed))
    result = record["result"]
    row: dict[str, Any] = {
        "views": views, "points": points, "seed": seed, "status": result["status"],
        "registered": 0, "registered_ratio": 0.0, "total_s": record["timings_s"]["total"],
    }
    if result["status"] != "success":
        return row

    registered = result["best_model"]["registered_images"]
    row.update(registered=registered, registered_ratio=registered / views)
    model_dir = case_dir / "run" / record["outputs"]["model_dir"]
    try:
        poses = evaluate_poses(model_dir, case_dir / "ground_truth")
    except ValueError:  # fewer than 3 registered images: poses cannot be aligned
        row["status"] = "too_few_registered"
        return row
    estimated = apply_similarity(load_points(model_dir, min_track_length), poses["alignment_transform"])
    geometry = evaluate_geometry(estimated, load_points(case_dir / "ground_truth"))
    at_2pct = next(t for t in geometry["thresholds"] if t["relative_threshold"] == 0.02)
    row.update(
        rotation_error_median_deg=poses["rotation_error_deg"]["median"],
        position_error_median_rel=poses["position_error_relative"]["median"],
        chamfer_rel=geometry["chamfer_relative"],
        precision_2pct=at_2pct["precision"],
        recall_2pct=at_2pct["recall"],
        f_score_2pct=at_2pct["f_score"],
    )
    return row


def run_sweep(output_dir: Path, view_counts: Iterable[int], point_counts: Iterable[int],
              seeds: Iterable[int], min_track_length: int = 0) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        run_one(output_dir, views, points, seed, min_track_length)
        for points in point_counts
        for views in view_counts
        for seed in seeds
    ]


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _median(values: list[float]) -> float | None:
    values = sorted(values)
    if not values:
        return None
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def summarise(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (points, views): success count and medians over seeds of successful runs."""
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["points"], row["views"]), []).append(row)
    summary = []
    for (points, views), group in sorted(groups.items()):
        evaluated = [row for row in group if "rotation_error_median_deg" in row]
        summary.append({
            "points": points,
            "views": views,
            "runs": len(group),
            "fully_registered": sum(row["registered"] == views for row in group),
            "registered_ratio": _median([row["registered_ratio"] for row in group]),
            "rotation_error_deg": _median([row["rotation_error_median_deg"] for row in evaluated]),
            "position_error_pct": _median([100 * row["position_error_median_rel"] for row in evaluated]),
            "f_score_2pct": _median([row["f_score_2pct"] for row in evaluated]),
        })
    return summary


def format_markdown(summary: list[dict[str, Any]]) -> str:
    def cell(value: float | None, digits: int) -> str:
        return "–" if value is None else f"{value:.{digits}f}"

    lines = [
        "| points | views | fully registered | registered (median) | rotation err (deg) | position err (% scene) | F-score @2% |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['points']} | {row['views']} | {row['fully_registered']}/{row['runs']} "
            f"| {cell(row['registered_ratio'] * 100, 0)}% | {cell(row['rotation_error_deg'], 3)} "
            f"| {cell(row['position_error_pct'], 2)} | {cell(row['f_score_2pct'], 3)} |"
        )
    return "\n".join(lines) + "\n"
