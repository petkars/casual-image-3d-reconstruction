# Roadmap

## M0 — reproducible input inventory (done)
- Define the folder convention.
- Validate image files.
- Record image size, dimensions, format and SHA-256.
- Keep raw images and generated assets out of Git.

## M1 — baseline reconstruction (in progress)
- Select a small object with textured, multi-view photos.
- Evaluate a classical photogrammetry/SfM baseline before adding generative methods.
- Record software versions, camera assumptions, runtime and failure modes.
- Baseline: COLMAP sparse SfM via pycolmap — see [M1_BASELINE.md](M1_BASELINE.md).

## M2 — geometry evaluation
- Obtain a reference mesh or scan for at least one object.
- Align reconstructed and reference geometry carefully.
- Report scale ambiguity where applicable, Chamfer distance, completeness and outlier behaviour.
- Started: camera-pose evaluation against a reference model (`casual3d-evaluate-poses`, similarity alignment), used on synthetic ground truth in M1.

## M3 — controlled occlusion
- Create reproducible view subsets and occlusion conditions.
- Separate visible regions from inferred regions.
- Measure whether additional views improve the result.

## M4 — generative reconstruction
- Evaluate an available image-conditioned 3D model.
- Record model/checkpoint licence and compute requirements.
- Compare visual quality and geometry metrics against the baseline.

## M5 — iterative refinement
- Explore a render/compare/refine loop.
- Prevent unsupported edits from overriding reliable observed geometry.
