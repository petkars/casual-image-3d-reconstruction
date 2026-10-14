#!/usr/bin/env python3
"""Render a synthetic object with known geometry, for sanity-checking the reconstruction pipeline."""
import argparse
from pathlib import Path

from casual3d.synthetic import make_synthetic_object


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="New or empty folder, e.g. datasets/raw/synthetic_01")
    parser.add_argument("--views", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ground-truth", type=Path,
                        help="New or empty folder for the true COLMAP model, "
                             "e.g. datasets/ground_truth/synthetic_01")
    args = parser.parse_args()
    make_synthetic_object(args.output_dir, num_views=args.views, seed=args.seed,
                          ground_truth_dir=args.ground_truth)
    print(f"Synthetic images: {args.output_dir}")
    if args.ground_truth:
        print(f"Ground truth: {args.ground_truth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
