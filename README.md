# Casual-Image 3D Reconstruction

A personal research project exploring 3D object reconstruction from casual, multi-view images, with an emphasis on measurable geometry, occlusion, and reproducible evaluation.

> Independent research project inspired by research directions such as NVIDIA GATOR. This repository is not affiliated with or endorsed by NVIDIA, and does not contain NVIDIA's implementation.

## Goal

Build an experimental pipeline that starts with ordinary images of an object and progressively adds:

1. Dataset validation and reproducible manifests.
2. A baseline multi-view reconstruction workflow.
3. Mesh inspection and quantitative evaluation against reference geometry.
4. Experiments with image-conditioned generative reconstruction when suitable implementations are available.
5. Occlusion tests that distinguish observed geometry from inferred geometry.

## Scope and non-goals

- This is a research prototype, not a production inspection system.
- Generated geometry is not assumed to be dimensionally accurate.
- Do not use generated meshes as metrology references without independent validation.
- Python is used for research and tooling; performance-critical components may move to C++ after profiling. CUDA is considered only when measurements justify it.

## Repository status

**Milestone 1 — classical sparse baseline (waiting for the first real capture); M2 — geometry evaluation (metrics in place).**

- M0 (done): a manifest tool scans a dataset organised by object, checks supported image files, records image dimensions and SHA-256 hashes, and writes a deterministic JSON manifest.
- M1: a COLMAP sparse structure-from-motion baseline recovers camera poses and a sparse point cloud, and records versions, settings, input hashes, timings and failure modes for every run. It is verified against ground-truth camera poses on synthetic data (`casual3d-evaluate-poses`), and a synthetic sweep maps where it breaks (too few views, repetitive texture). The first real-object run is next. See [docs/M1_BASELINE.md](docs/M1_BASELINE.md).
- M2: pose and point-cloud metrics (rotation/position error, accuracy, completeness, Chamfer, precision/recall/F-score) after similarity alignment (`casual3d-evaluate-geometry`). Real objects still need reference geometry. See [docs/M2_EVALUATION.md](docs/M2_EVALUATION.md).

## Quick start

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,recon]"   # recon installs pycolmap
```

Organise images like this:

```text
datasets/
  raw/
    bolt_01/
      view_01.jpg
      view_02.jpg
    plastic_fragment_01/
      front.png
      side.png
```

Build a manifest:

```bash
casual3d-manifest datasets/raw --output results/dataset_manifest.json
```

(`python tools/build_manifest.py ...` does the same.) The command prints the manifest's SHA-256; record it in [docs/EXPERIMENT_LOG.md](docs/EXPERIMENT_LOG.md). Hidden files and folders (names starting with `.`) are skipped.

Reconstruct one object (sparse point cloud and camera poses; scale is arbitrary):

```bash
casual3d-reconstruct datasets/raw/bolt_01 --output results/runs/m1_bolt_01
```

This writes `run.json`, the COLMAP model, `points3D.ply` and `cameras.ply` (camera positions) to the run folder. Capture guidance, assumptions and options are in [docs/M1_BASELINE.md](docs/M1_BASELINE.md).

Run tests:

```bash
pytest
```

Reconstruction tests are skipped if pycolmap is not installed. If pytest fails to start because of plugins from another environment (e.g. ROS), run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest`.

Dense reconstruction and meshing are not implemented yet; see the roadmap.

## Planned milestones

- [x] M0: repository scaffold and reproducible image manifest.
- [ ] M1 (in progress): run a classical multi-view baseline reconstruction on a small object and document its assumptions.
- [ ] M2 (in progress): compare reconstruction with reference geometry.
- [ ] M3: introduce controlled occlusion and quantify reconstruction degradation.
- [ ] M4: evaluate image-conditioned generative reconstruction against the baseline.
- [ ] M5: explore iterative render-and-compare refinement.

See [docs/ROADMAP.md](docs/ROADMAP.md) for details.

## Experiment principles

- Keep raw data out of Git; store only small, non-sensitive sample data when licensing permits.
- Record input hashes, tool versions, settings, and evaluation metrics.
- Separate measured/observed geometry from model-inferred geometry.
- Report failures and uncertainty, not only successful visual examples.

## License

MIT for the original code in this repository. Third-party models, datasets, weights, and tools retain their own licenses and terms.
