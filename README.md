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

**Milestone 0 — project scaffold and dataset manifest tool.**

The first tool scans a dataset organised by object, checks supported image files, records image dimensions and SHA-256 hashes, and writes a deterministic JSON manifest.

## Quick start

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
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
python tools/build_manifest.py datasets/raw --output results/dataset_manifest.json
```

Run tests:

```bash
pytest
```

The tool records files and image metadata only. It does **not** reconstruct a 3D model yet.

## Planned milestones

- [x] M0: repository scaffold and reproducible image manifest.
- [ ] M1: choose a baseline and document setup/reconstruction assumptions.
- [ ] M2: run a first multi-view reconstruction on a small object.
- [ ] M3: compare reconstruction with reference geometry.
- [ ] M4: introduce controlled occlusion and quantify reconstruction degradation.
- [ ] M5: evaluate generative reconstruction and iterative render-and-compare refinement.

## Experiment principles

- Keep raw data out of Git; store only small, non-sensitive sample data when licensing permits.
- Record input hashes, tool versions, settings, and evaluation metrics.
- Separate measured/observed geometry from model-inferred geometry.
- Report failures and uncertainty, not only successful visual examples.

## License

MIT for the original code in this repository. Third-party models, datasets, weights, and tools retain their own licenses and terms.
