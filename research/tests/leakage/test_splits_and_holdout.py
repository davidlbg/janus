from pathlib import Path

import polars as pl
import pytest

from janus_research.schema import DatasetSplit
from janus_research.splits import (
    HoldoutAccessError,
    SplitAssigner,
    assert_disjoint_assignments,
    assert_no_label_metadata_leakage,
    load_training_responses,
    validate_split_integrity,
)
from janus_research.splits.guard import assert_threshold_selection_split

POLICY = {"discovery": 0.6, "validation": 0.3, "holdout": 0.1}


def test_subject_assignment_is_stable_and_single_split() -> None:
    assigner = SplitAssigner("subjects", POLICY)
    first = assigner.assign("participant-1")
    assert assigner.assign("participant-1") == first
    assert list(assigner.assignments) == ["participant-1"]


def test_overlap_detection_fails_for_subject_or_challenge() -> None:
    with pytest.raises(ValueError, match="overlap"):
        assert_disjoint_assignments(
            {
                DatasetSplit.DISCOVERY: {"same-id"},
                DatasetSplit.VALIDATION: {"same-id"},
                DatasetSplit.HOLDOUT: set(),
            }
        )


def test_holdout_requires_logged_explicit_override(tmp_path: Path) -> None:
    path = tmp_path / "responses.parquet"
    pl.DataFrame(
        {"split": ["discovery", "holdout"], "challenge_split": ["discovery", "holdout"]}
    ).write_parquet(path)
    with pytest.raises(HoldoutAccessError):
        load_training_responses([path])
    log = tmp_path / "audit" / "holdout.jsonl"
    loaded = load_training_responses(
        [path], allow_holdout=True, override_reason="final protocol evaluation", access_log=log
    )
    assert loaded.height == 2
    assert "final protocol evaluation" in log.read_text(encoding="utf-8")


def test_final_holdout_cannot_select_threshold() -> None:
    with pytest.raises(HoldoutAccessError, match="threshold"):
        assert_threshold_selection_split(DatasetSplit.HOLDOUT)


def test_label_path_and_order_leakage_are_rejected(tmp_path: Path) -> None:
    grouped = pl.DataFrame({"population_class": ["human", "human", "ai", "ai"]})
    with pytest.raises(ValueError, match="source path"):
        assert_no_label_metadata_leakage(grouped, [tmp_path / "human" / "responses.parquet"])
    with pytest.raises(ValueError, match="row order"):
        assert_no_label_metadata_leakage(grouped, [tmp_path / "responses.parquet"])


def test_dataset_rejects_subject_and_challenge_split_conflicts() -> None:
    subject_conflict = pl.DataFrame(
        {
            "subject_id": ["p1", "p1"],
            "split": ["discovery", "holdout"],
            "challenge_id": ["c1", "c2"],
            "challenge_split": ["discovery", "holdout"],
        }
    )
    with pytest.raises(ValueError, match="subjects"):
        validate_split_integrity(subject_conflict)
    challenge_conflict = pl.DataFrame(
        {
            "subject_id": ["p1", "p2"],
            "split": ["discovery", "validation"],
            "challenge_id": ["c1", "c1"],
            "challenge_split": ["discovery", "validation"],
        }
    )
    with pytest.raises(ValueError, match="challenge IDs"):
        validate_split_integrity(challenge_conflict)
