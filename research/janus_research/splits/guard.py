from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import polars as pl

from janus_research.schema import DatasetSplit


class HoldoutAccessError(RuntimeError):
    pass


def _log_override(log_path: Path, paths: list[Path], reason: str) -> None:
    if not reason.strip():
        raise ValueError("a non-empty reason is required for holdout access")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": "holdout_access_override",
        "paths": [str(path.resolve()) for path in paths],
        "reason": reason,
    }
    with log_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True) + "\n")


def load_training_responses(
    paths: Iterable[Path],
    *,
    allow_holdout: bool = False,
    override_reason: str | None = None,
    access_log: Path | None = None,
) -> pl.DataFrame:
    resolved = [Path(path) for path in paths]
    if not resolved:
        raise ValueError("at least one response path is required")
    frame = pl.concat([pl.read_parquet(path) for path in resolved], how="diagonal_relaxed")
    split_columns = [column for column in ("split", "challenge_split") if column in frame.columns]
    contains_holdout = any(
        frame.filter(pl.col(column) == DatasetSplit.HOLDOUT.value).height > 0
        for column in split_columns
    )
    if contains_holdout and not allow_holdout:
        raise HoldoutAccessError("final holdout is blocked from ordinary training helpers")
    if contains_holdout:
        if access_log is None:
            raise ValueError("access_log is required for holdout override")
        _log_override(access_log, resolved, override_reason or "")
    return frame


def assert_no_label_metadata_leakage(frame: pl.DataFrame, source_paths: Iterable[Path]) -> None:
    forbidden_tokens = {"human", "artificial", "adversarial_ai", "label_0", "label_1"}
    for path in source_paths:
        lowered_parts = {part.lower() for part in Path(path).parts}
        if lowered_parts.intersection(forbidden_tokens):
            raise ValueError(f"population label is encoded in source path: {path}")
    if "population_class" not in frame.columns or frame.height < 4:
        return
    labels = frame.get_column("population_class").to_list()
    transitions = sum(left != right for left, right in pairwise(labels))
    unique = len(set(labels))
    if unique > 1 and transitions < unique:
        raise ValueError("row order appears grouped by population label; shuffle fixture order")


def assert_threshold_selection_split(split: DatasetSplit) -> None:
    if split == DatasetSplit.HOLDOUT:
        raise HoldoutAccessError("thresholds cannot be selected or recomputed from final holdout")


def validate_split_integrity(frame: pl.DataFrame) -> None:
    required = {"subject_id", "split", "challenge_id", "challenge_split"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"dataset is missing split-integrity columns: {sorted(missing)}")
    subject_conflicts = frame.group_by("subject_id").agg(pl.col("split").n_unique().alias("n"))
    if subject_conflicts.filter(pl.col("n") > 1).height:
        raise ValueError("one or more subjects occur in multiple participant splits")
    challenge_conflicts = frame.group_by("challenge_id").agg(
        pl.col("challenge_split").n_unique().alias("n")
    )
    if challenge_conflicts.filter(pl.col("n") > 1).height:
        raise ValueError("one or more challenge IDs occur in multiple challenge splits")
