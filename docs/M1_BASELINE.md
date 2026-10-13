# M1 — classical sparse baseline

## Choice of baseline

**COLMAP incremental structure-from-motion**, driven through the `pycolmap` Python bindings (pinned to `>=4.2,<5`).

- Widely used, well documented reference for multi-view geometry; BSD licensed.
- Installs with `pip` (no system build), so runs are reproducible from `pyproject.toml`.
- Produces camera poses, intrinsics and a sparse point cloud with per-point reprojection error, which later milestones build on.

M1 covers **sparse** reconstruction only. COLMAP's dense multi-view stereo (PatchMatch) needs a CUDA build; the pip wheel is CPU-only (`run.json` records `"cuda": false`). Dense reconstruction and meshing are deferred until a CUDA build is set up and measured.

## Assumptions

- One rigid, static object per image folder; the object does not move between shots.
- One camera, fixed focal length (no zoom) — default `SIMPLE_RADIAL`, intrinsics shared across images. Use `--per-image-camera` when mixing cameras or zoom levels.
- Lambertian, textured surfaces. Shiny, transparent or uniform objects are expected failure cases and should be logged as such.
- **Scale is arbitrary.** SfM recovers geometry only up to a similarity transform; no metric dimensions until a known reference (scale bar, marker) is added in M2.

## Capture protocol (first real object)

1. Pick a small, matte, textured object (e.g. a painted figurine or a textured mug). Avoid chrome, glass and plain white plastic for the first run.
2. Place it on a textured surface (newspaper works) in even, diffuse light; avoid hard shadows and flash.
3. Lock focus/zoom if possible. Take 30–60 photos in 2–3 rings at different heights, ~10–15° apart, overlapping by more than 60%.
4. Keep the object large in frame and sharp. Discard blurred shots before running.
5. Copy to `datasets/raw/<object_id>/`.

## Running

```bash
python -m pip install -e ".[dev,recon]"
casual3d-manifest datasets/raw --output results/dataset_manifest.json
casual3d-reconstruct datasets/raw/<object_id> --output results/runs/<experiment_id>
```

Use `--matcher sequential` for video frames or strictly ordered captures. Exit code 0 means a model was built, 1 means the run completed but registered no images (still recorded), 2 means invalid input or setup.

To sanity-check the pipeline without photos:

```bash
python tools/make_synthetic_object.py datasets/raw/synthetic_01
casual3d-reconstruct datasets/raw/synthetic_01 --output results/runs/m1_synthetic_01
```

## What each run records

`results/runs/<experiment_id>/` contains `database.db`, `sparse/<model>/` (COLMAP binary model), `points3D.ply` for the largest model, and `run.json` with:

- software: pycolmap/COLMAP, Python and platform versions, CUDA availability;
- config: camera model, camera sharing, matcher, image size cap, random seed;
- input: every image path with its SHA-256;
- timings per stage (feature extraction, matching, mapping);
- result: registered images, 3D points, mean reprojection error (px), mean track length, estimated intrinsics, and the list of **unregistered images** — or the failure reason when no model is built.

Copy the key numbers into [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md).

## M1 is done when

- [x] Pipeline implemented, tested, and verified on synthetic data.
- [ ] A real object captured per the protocol above and reconstructed.
- [ ] Run logged with runtime, registration rate, reprojection error and observed failure modes.
- [ ] At least one deliberately hard capture (e.g. low texture or shiny) logged as a failure case.
