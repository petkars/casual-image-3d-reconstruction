# Experiment log

Use one section per run. Keep failed runs.

## Template

- Date:
- Experiment ID:
- Goal:
- Dataset ID / manifest hash:
- Code commit:
- Hardware:
- Software/model versions:
- Configuration:
- Procedure:
- Results:
- Failure cases:
- Next action:

## 2026-10-13 — M1 synthetic sanity check

- Date: 2026-10-13
- Experiment ID: m1_synthetic_01
- Goal: confirm the sparse SfM pipeline and run record work end to end before capturing a real object.
- Dataset ID / manifest hash: synthetic_01 — 8 rendered 640×480 views of 150 random textured points (`tools/make_synthetic_object.py`, seed 0); ground-truth focal length 800 px.
- Code commit: a9f9a86 + uncommitted M1 changes (committed in the M1 commit that adds this entry)
- Hardware: AMD Ryzen 7 7435HS, CPU only (pycolmap wheel has no CUDA)
- Software/model versions: pycolmap 4.2.1 / COLMAP 4.2.1, Python 3.10.12, Linux 6.8
- Configuration: SIMPLE_RADIAL, single shared camera, exhaustive matching, max image size 3200, seed 0
- Procedure: `casual3d-reconstruct datasets/raw/synthetic_01 --output results/runs/m1_synthetic_01`
- Results: 8/8 images registered, 256 sparse points, mean reprojection error 0.58 px, mean track length 3.6; estimated focal length 798.3 px (0.2% from ground truth). Total 0.56 s (extraction 0.41 s, matching 0.05 s, mapping 0.10 s).
- Failure cases: with 400 points at 640×480 the rendered feature patches overlap and only 2/8 views registered — dense, repetitive texture can break matching. Uniform images (test suite) register nothing and are recorded as `failed`.
- Next action: capture a real textured object per docs/M1_BASELINE.md and log it here.

## 2026-10-14 — M1 synthetic pose accuracy vs ground truth

- Date: 2026-10-14
- Experiment ID: m1_synthetic_01 (re-run with ground truth)
- Goal: measure pose accuracy of the sparse baseline against known cameras, not only registration count.
- Dataset ID / manifest hash: synthetic_01, regenerated with `--ground-truth datasets/ground_truth/synthetic_01`, seed 0. Images are byte-identical to the 2026-10-13 run (same combined SHA-256), so synthetic data is reproducible from the seed.
- Code commit: 5c13aa5 + pose-evaluation changes (committed with this entry)
- Hardware: AMD Ryzen 7 7435HS, CPU only
- Software/model versions: pycolmap 4.2.1 / COLMAP 4.2.1, Python 3.10.12
- Configuration: as 2026-10-13 (SIMPLE_RADIAL, shared camera, exhaustive matching, seed 0); evaluation by Umeyama similarity on camera centres
- Procedure: `casual3d-reconstruct ...` then `casual3d-evaluate-poses results/runs/m1_synthetic_01 datasets/ground_truth/synthetic_01`
- Results: 8/8 images compared. Rotation error median 0.124°, max 0.187°. Position error median 0.20%, max 0.31% of scene size (0.009 / 0.015 units; scene size 4.75). Focal length error 0.21%. Reconstruction 256 points, 0.583 px reprojection error, 0.5 s.
- Failure cases: none on this easy synthetic scene; it says nothing yet about real texture, lighting or blur.
- Next action: capture a real object per docs/M1_BASELINE.md (no ground truth: judge by registration rate, reprojection error and cameras.ply).

## 2026-10-15 — M2 synthetic geometry metrics

- Date: 2026-10-15
- Experiment ID: m1_synthetic_01 (geometry evaluation)
- Goal: first point-cloud metrics against ground-truth geometry; check what drives outliers.
- Dataset ID / manifest hash: synthetic_01 (seed 0, same images as 2026-10-13/14)
- Code commit: b49c42c
- Hardware: AMD Ryzen 7 7435HS, CPU only
- Software/model versions: pycolmap 4.2.1 / COLMAP 4.2.1, scipy 1.15.3, Python 3.10.12
- Configuration: alignment from pose_evaluation.json; thresholds 0.5/1/2% of reference diagonal (3.41 units)
- Procedure: `casual3d-evaluate-geometry results/runs/m1_synthetic_01 datasets/ground_truth/synthetic_01 [--min-track-length 3]`
- Results:

  | points used | estimated pts | Chamfer (% diag) | P / R / F @0.5% | P / R / F @2% |
  |---|---:|---:|---|---|
  | all | 256 | 1.12 | 0.668 / 0.600 / 0.632 | 0.855 / 0.700 / 0.770 |
  | track ≥ 3 | 223 | 1.01 | 0.767 / 0.600 / 0.673 | 0.937 / 0.687 / 0.793 |

  171/256 points lie within 0.5% of a true point (median 0.14%). Off points have short tracks (mean 2.5 images vs 4.0) and higher reprojection error (0.9–1.3 px vs 0.3 px). Most true points produce two estimated points (SIFT keeps up to 2 orientations per keypoint).
- Failure cases: 45/150 true points never reconstructed although visible in all 8 views. These are matching failures, not visibility. Outliers come largely from keypoints on synthetic patch edges (a renderer artefact).
- Next action: robustness sweep (below); reference geometry for a real object.

## 2026-10-15 — M1 synthetic robustness sweep (views × texture density)

- Date: 2026-10-15
- Experiment ID: sweep_views_points
- Goal: find where the sparse baseline breaks down, i.e. the failure modes required by M1.
- Dataset ID / manifest hash: synthetic, generated per case from seeds 0, 1, 2
- Code commit: 390669e
- Hardware: AMD Ryzen 7 7435HS, CPU only; whole sweep 31 s
- Software/model versions: pycolmap 4.2.1 / COLMAP 4.2.1, Python 3.10.12
- Configuration: views 3, 4, 5, 6, 8, 12 × points 50, 150, 400 × seeds 0, 1, 2 (54 runs); default reconstruction settings; all points evaluated
- Procedure: `python tools/sweep_synthetic.py results/sweeps/views_points --quiet`
- Results (medians over seeds; errors over successful runs only):

| points | views | fully registered | registered (median) | rotation err (deg) | position err (% scene) | F-score @2% |
|---:|---:|---:|---:|---:|---:|---:|
| 50 | 3 | 3/3 | 100% | 0.166 | 0.11 | 0.462 |
| 50 | 4 | 3/3 | 100% | 0.249 | 0.22 | 0.761 |
| 50 | 5 | 3/3 | 100% | 0.125 | 0.20 | 0.830 |
| 50 | 6 | 3/3 | 100% | 0.126 | 0.15 | 0.807 |
| 50 | 8 | 3/3 | 100% | 0.092 | 0.12 | 0.815 |
| 50 | 12 | 3/3 | 100% | 0.141 | 0.19 | 0.727 |
| 150 | 3 | 1/3 | 0% | 0.246 | 0.35 | 0.180 |
| 150 | 4 | 3/3 | 100% | 0.283 | 0.25 | 0.337 |
| 150 | 5 | 3/3 | 100% | 0.196 | 0.22 | 0.511 |
| 150 | 6 | 3/3 | 100% | 0.141 | 0.19 | 0.639 |
| 150 | 8 | 3/3 | 100% | 0.116 | 0.20 | 0.768 |
| 150 | 12 | 3/3 | 100% | 0.089 | 0.16 | 0.863 |
| 400 | 3 | 0/3 | 0% | – | – | – |
| 400 | 4 | 0/3 | 0% | – | – | – |
| 400 | 5 | 0/3 | 0% | – | – | – |
| 400 | 6 | 0/3 | 33% | – | – | – |
| 400 | 8 | 0/3 | 25% | – | – | – |
| 400 | 12 | 0/3 | 17% | – | – | – |

- Failure cases: 150 points × 3 views failed in 2/3 runs (no initial pair). 400 points failed everywhere: 0 images at 3–6 views, and only the initial pair (2 images) at 6–12 views (`too_few_registered`). Overlapping feature patches behave like repetitive texture.
- Observations: rotation error stays at 0.09–0.28° whenever registration succeeds. The F-score rises with view count for 150 points (0.34 at 4 views to 0.86 at 12), because extra views triangulate more points (recall). With 50 points the F-score is high even at 4 views but drops at 3 views (0.46).
- Next action: real capture; check whether real objects follow the same trends (views needed, texture sensitivity).
