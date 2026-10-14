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
