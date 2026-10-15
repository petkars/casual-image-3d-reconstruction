# M2 — geometry evaluation

M2 measures how close a reconstruction is to reference geometry. The metrics are implemented and checked on synthetic ground truth. Running them on a real object still needs reference geometry for that object (see [Still needed for real objects](#still-needed-for-real-objects)).

## Pipeline

```bash
casual3d-reconstruct <images> --output results/runs/<id>
casual3d-evaluate-poses results/runs/<id> <reference COLMAP model>        # writes pose_evaluation.json
casual3d-evaluate-geometry results/runs/<id> <reference .ply or model>    # writes geometry_evaluation.json
```

`casual3d-evaluate-geometry` reuses the alignment stored in `pose_evaluation.json`. Pass `--alignment <file>` to use another one, or `--no-alignment` when the run is already in the reference frame.

## Alignment and scale

SfM recovers geometry only up to a similarity transform (rotation, translation, **scale**). Before any comparison, `casual3d-evaluate-poses` fits the least-squares similarity (Umeyama) between estimated and reference camera centres, matched by image name, and stores it as `alignment_transform` (`x_ref = scale * R @ x_est + t`). Every distance is then reported in reference units and **relative to the size of the reference**, so numbers are comparable across objects:

- pose position error: relative to the median camera distance from the camera centroid;
- geometry distances and thresholds: relative to the reference bounding-box diagonal.

The `alignment_scale` value says how the arbitrary SfM scale relates to the reference. It is not a measurement of the object.

## Metrics

| Metric | Definition | Low/high value means |
|---|---|---|
| Rotation error | angle between aligned estimated and reference camera orientation (deg) | camera orientation quality |
| Position error | distance between aligned and reference camera centres | camera placement quality |
| Focal length error | relative difference of mean focal length | intrinsics quality |
| Accuracy | distance from each estimated point to the nearest reference point (mean/median/p90/max) | high: spurious or misplaced points |
| Completeness | distance from each reference point to the nearest estimated point | high: parts of the object not reconstructed |
| Chamfer | mean of mean accuracy and mean completeness | both combined |
| Precision @ τ | share of estimated points within τ of the reference | low: outliers (`outlier_ratio = 1 − precision`) |
| Recall @ τ | share of reference points within τ of the estimate | low: missing geometry |
| F-score @ τ | harmonic mean of precision and recall | overall |

τ is 0.5%, 1% and 2% of the reference bounding-box diagonal.

`--min-track-length N` evaluates only points seen in at least N images. On synthetic_01, points seen in only two images were most of the outliers: N = 3 raised precision @2% from 0.86 to 0.94 while recall dropped only from 0.70 to 0.69. N ≥ 4 removed too many good points. The default keeps all points so results are not silently filtered; report N when it is used.

## Synthetic results

See [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md) (2026-10-14 and 2026-10-15). In short: camera poses are accurate to ~0.1° and ~0.2% of scene size whenever registration succeeds. Point recall is the weak spot, and it improves with more views.

The synthetic images are fixed-size textured squares drawn at projected 3D points, not rendered surfaces. Keypoints on patch edges do not correspond to a single 3D point, which inflates outliers. Treat synthetic geometry numbers as a pipeline check, not as a prediction for real objects.

## Still needed for real objects

- **Reference geometry:** a mesh or scan of at least one real object (a 3D-printed part with a known CAD model is the cleanest option), plus mesh-to-point sampling so a mesh can serve as the reference.
- **Alignment without reference cameras:** real references have no camera poses, so the run must be aligned to the reference by point-set registration (e.g. a coarse manual or marker-based alignment, then ICP).
- **Metric scale:** a scale bar or markers of known size in the capture, so `alignment_scale` can be checked against a real measurement.
- **Dense reconstruction** before surface metrics are meaningful (sparse points are mostly on texture).
