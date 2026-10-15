#!/usr/bin/env python3
"""Sweep view count and texture density on synthetic objects; write CSV and a Markdown summary."""
import argparse
from pathlib import Path

from casual3d.sweep import format_markdown, run_sweep, summarise, write_csv


def _ints(text: str) -> list[int]:
    return [int(value) for value in text.split(",")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="New or empty folder, e.g. results/sweeps/views_points")
    parser.add_argument("--views", type=_ints, default=[3, 4, 5, 6, 8, 12], help="Comma-separated view counts")
    parser.add_argument("--points", type=_ints, default=[50, 150, 400], help="Comma-separated point counts")
    parser.add_argument("--seeds", type=_ints, default=[0, 1, 2])
    parser.add_argument("--min-track-length", type=int, default=0)
    parser.add_argument("--quiet", action="store_true", help="Hide COLMAP log output")
    args = parser.parse_args()

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error(f"output directory is not empty: {args.output_dir}")
    if args.quiet:
        import pycolmap
        pycolmap.logging.minloglevel = pycolmap.logging.Level.ERROR.value

    rows = run_sweep(args.output_dir, args.views, args.points, args.seeds, args.min_track_length)
    write_csv(rows, args.output_dir / "sweep.csv")
    table = format_markdown(summarise(rows))
    (args.output_dir / "summary.md").write_text(table, encoding="utf-8")
    print(table)
    print(f"Per-run results: {args.output_dir / 'sweep.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
