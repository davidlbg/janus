from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from janus_research.schema import ChallengeDefinition, ResponseRecord


def _json_safe(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def write_responses(records: Iterable[ResponseRecord], path: Path) -> Path:
    rows = [record.model_dump(mode="json") for record in records]
    if not rows:
        raise ValueError("cannot write an empty response dataset")
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(path)
    return path


def read_responses(path: Path) -> list[ResponseRecord]:
    return [ResponseRecord.model_validate(row) for row in pl.read_parquet(path).to_dicts()]


def write_challenges(
    challenges: Iterable[ChallengeDefinition], directory: Path
) -> tuple[Path, Path]:
    challenge_list = list(challenges)
    if not challenge_list:
        raise ValueError("cannot write an empty challenge registry")
    challenge_ids = [challenge.challenge_id for challenge in challenge_list]
    if len(challenge_ids) != len(set(challenge_ids)):
        raise ValueError("challenge IDs must be unique across the registry")
    directory.mkdir(parents=True, exist_ok=True)
    public_path = directory / "challenges_public.parquet"
    private_path = directory / "challenges_private.parquet"
    public_rows = []
    private_rows = []
    for challenge in challenge_list:
        public = challenge.to_public().model_dump(mode="json")
        public["public_payload"] = _json_safe(public["public_payload"])
        public_rows.append(public)
        private_rows.append(
            {
                "challenge_id": challenge.challenge_id,
                "seed": challenge.seed,
                "private_features": _json_safe(challenge.private_features),
            }
        )
    pl.DataFrame(public_rows).write_parquet(public_path)
    pl.DataFrame(private_rows).write_parquet(private_path)
    return public_path, private_path


def read_challenges(directory: Path) -> list[ChallengeDefinition]:
    public_rows = {
        row["challenge_id"]: row
        for row in pl.read_parquet(directory / "challenges_public.parquet").to_dicts()
    }
    private_rows = {
        row["challenge_id"]: row
        for row in pl.read_parquet(directory / "challenges_private.parquet").to_dicts()
    }
    if public_rows.keys() != private_rows.keys():
        raise ValueError("public/private challenge registries do not contain identical IDs")
    challenges = []
    for challenge_id, public in public_rows.items():
        private = private_rows[challenge_id]
        challenges.append(
            ChallengeDefinition(
                challenge_id=challenge_id,
                family=public["family"],
                generator_version=public["generator_version"],
                seed=int(private["seed"]),
                split=public["split"],
                public_payload=json.loads(public["public_payload"]),
                private_features=json.loads(private["private_features"]),
                created_at=public["created_at"],
            )
        )
    return challenges


def duckdb_query(parquet_path: Path, sql: str) -> list[tuple[Any, ...]]:
    with duckdb.connect(":memory:") as connection:
        escaped = str(parquet_path.resolve()).replace("'", "''")
        connection.execute(f"CREATE VIEW responses AS SELECT * FROM read_parquet('{escaped}')")
        return connection.execute(sql).fetchall()
