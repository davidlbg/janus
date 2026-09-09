from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from janus_research.schema import ConsentRecord, ConsentStatus


class ConsentRequiredError(RuntimeError):
    pass


@dataclass(frozen=True)
class WithdrawalResult:
    subject_id: str
    affected_raw_paths: tuple[str, ...]
    invalidated_derived_paths: tuple[str, ...]
    audit_path: Path


class ConsentStore:
    """Append-only local consent state, intentionally separate from responses."""

    def __init__(self, root: Path, experiment_id: str, retention_policy: str) -> None:
        self.root = root
        self.experiment_id = experiment_id
        self.retention_policy = retention_policy
        self.directory = root / "data" / "raw" / experiment_id / "consent"
        self.records_path = self.directory / "records.jsonl"
        self.audit_path = self.directory / "audit.jsonl"
        self._lock = threading.Lock()

    def _latest(self) -> dict[str, ConsentRecord]:
        if not self.records_path.exists():
            return {}
        latest: dict[str, ConsentRecord] = {}
        for line in self.records_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = ConsentRecord.model_validate_json(line)
                latest[record.subject_id] = record
        return latest

    def status(self, subject_id: str) -> ConsentRecord | None:
        return self._latest().get(subject_id)

    def _append(self, record: ConsentRecord) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.records_path.open("a", encoding="utf-8") as stream:
            stream.write(record.model_dump_json() + "\n")

    def consent(
        self, subject_id: str, study_version: str, consent_document_version: str
    ) -> ConsentRecord:
        with self._lock:
            current = self.status(subject_id)
            if current and current.status == ConsentStatus.WITHDRAWN:
                raise ConsentRequiredError("withdrawn participants cannot be reactivated")
            if current and current.status == ConsentStatus.ACTIVE:
                return current
            consent_id = hashlib.sha256(
                f"{self.experiment_id}:{subject_id}:{consent_document_version}".encode()
            ).hexdigest()[:24]
            record = ConsentRecord(
                consent_id=consent_id,
                subject_id=subject_id,
                study_version=study_version,
                consent_document_version=consent_document_version,
                consented_at=datetime.now(UTC),
                status=ConsentStatus.ACTIVE,
            )
            self._append(record)
            return record

    def require_active(self, subject_id: str) -> ConsentRecord:
        record = self.status(subject_id)
        if record is None or record.status != ConsentStatus.ACTIVE:
            raise ConsentRequiredError("active consent is required before accepting responses")
        return record

    def withdraw(self, subject_id: str) -> WithdrawalResult:
        with self._lock:
            current = self.status(subject_id)
            if current is None:
                raise ConsentRequiredError("no consent record exists for this subject")
            if current.status != ConsentStatus.WITHDRAWN:
                current = ConsentRecord(
                    **current.model_dump(exclude={"status", "withdrawn_at"}),
                    status=ConsentStatus.WITHDRAWN,
                    withdrawn_at=datetime.now(UTC),
                )
                self._append(current)
            affected = self._find_raw_records(subject_id)
            invalidated = self._invalidate_derived(subject_id, affected)
            event = {
                "event": "participant_withdrawal",
                "timestamp": datetime.now(UTC).isoformat(),
                "subject_id": subject_id,
                "consent_id": current.consent_id,
                "retention_policy": self.retention_policy,
                "behavior": "exclude_from_analysis_and_preserve_raw_pending_review",
                "affected_raw_paths": affected,
                "invalidated_derived_paths": invalidated,
            }
            self.directory.mkdir(parents=True, exist_ok=True)
            with self.audit_path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(event, sort_keys=True) + "\n")
            return WithdrawalResult(
                subject_id,
                tuple(affected),
                tuple(invalidated),
                self.audit_path,
            )

    def withdrawn_subjects(self) -> set[str]:
        return {
            subject_id
            for subject_id, record in self._latest().items()
            if record.status == ConsentStatus.WITHDRAWN
        }

    def _find_raw_records(self, subject_id: str) -> list[str]:
        experiment_root = self.root / "data" / "raw" / self.experiment_id
        matches = []
        for path in experiment_root.rglob("*.parquet") if experiment_root.exists() else []:
            try:
                schema = pl.read_parquet_schema(path)
                if "subject_id" not in schema:
                    continue
                found = (
                    pl.scan_parquet(path)
                    .filter(pl.col("subject_id") == subject_id)
                    .limit(1)
                    .collect()
                )
                if found.height:
                    matches.append(str(path.resolve()))
            except (OSError, pl.exceptions.PolarsError):
                continue
        return sorted(matches)

    def _invalidate_derived(self, subject_id: str, affected: list[str]) -> list[str]:
        derived = self.root / "data" / "derived" / self.experiment_id
        if not derived.exists() or not affected:
            return []
        marker = derived / "WITHDRAWAL_INVALIDATION.json"
        payload = {
            "subject_id": subject_id,
            "invalidated_at": datetime.now(UTC).isoformat(),
            "reason": "participant withdrawal; regenerate excluding tombstoned subject",
            "affected_raw_paths": affected,
        }
        marker.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return [str(marker.resolve())]


def exclude_withdrawn(frame: pl.DataFrame, store: ConsentStore) -> pl.DataFrame:
    withdrawn = sorted(store.withdrawn_subjects())
    if not withdrawn or "subject_id" not in frame.columns:
        return frame
    return frame.filter(~pl.col("subject_id").is_in(withdrawn))
