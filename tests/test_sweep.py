import csv
from pathlib import Path

import pytest

from casual3d.sweep import CSV_FIELDS, format_markdown, summarise, write_csv


def _row(views, seed, registered, rotation=None):
    row = {"views": views, "points": 150, "seed": seed, "status": "success",
           "registered": registered, "registered_ratio": registered / views, "total_s": 0.5}
    if rotation is not None:
        row.update(rotation_error_median_deg=rotation, position_error_median_rel=0.002,
                   chamfer_rel=0.01, precision_2pct=0.9, recall_2pct=0.7, f_score_2pct=0.8)
    return row


def test_summary_counts_full_registration_and_takes_medians():
    rows = [_row(8, 0, 8, 0.1), _row(8, 1, 8, 0.3), _row(8, 2, 6, 0.2), _row(3, 0, 0)]

    summary = summarise(rows)

    assert [(row["views"], row["fully_registered"], row["runs"]) for row in summary] == [(3, 0, 1), (8, 2, 3)]
    assert summary[1]["rotation_error_deg"] == pytest.approx(0.2)
    assert summary[0]["rotation_error_deg"] is None
    table = format_markdown(summary)
    assert "| 150 | 3 | 0/1 | 0% | – |" in table
    assert "| 150 | 8 | 2/3 |" in table


def test_csv_has_stable_columns_and_blank_metrics_for_failures(tmp_path: Path):
    path = tmp_path / "sweep.csv"
    write_csv([_row(3, 0, 0), _row(8, 0, 8, 0.1)], path)

    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))

    assert tuple(rows[0].keys()) == CSV_FIELDS
    assert rows[0]["rotation_error_median_deg"] == ""
    assert float(rows[1]["rotation_error_median_deg"]) == pytest.approx(0.1)


def test_run_one_on_easy_case(tmp_path: Path):
    pytest.importorskip("pycolmap")
    pytest.importorskip("scipy")
    from casual3d.sweep import run_one

    row = run_one(tmp_path, views=8, points=150, seed=0)

    assert row["status"] == "success"
    assert row["registered"] == 8
    assert row["rotation_error_median_deg"] < 1.0
