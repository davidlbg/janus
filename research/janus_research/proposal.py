from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from janus_research.schema import ExperimentManifest


def propose_confirmatory(source: ExperimentManifest, destination: Path) -> Path:
    source_hash = source.content_hash or hashlib.sha256(source.canonical_bytes()).hexdigest()
    proposal = {
        "experiment_id": "exp001b_confirmatory",
        "source_experiment_id": source.experiment_id,
        "source_manifest_hash": source_hash,
        "status": "draft",
        "confirmatory": True,
        "data_kind": "real_confirmatory",
        "protocol_version": "NEEDS_DECISION",
        "hypothesis": "NEEDS_DECISION",
        "primary_estimand": "NEEDS_DECISION",
        "human_fpr_target": "NEEDS_DECISION",
        "expected_ai_tpr": "NEEDS_DECISION",
        "sample_size_and_power": "NEEDS_DECISION",
        "model_cohort_and_versions": "NEEDS_DECISION",
        "challenge_versions": "NEEDS_DECISION",
        "split_policy": "NEEDS_DECISION",
        "exclusion_criteria": "NEEDS_DECISION",
        "abandonment_criteria": "NEEDS_DECISION",
        "threshold_selection_procedure": "NEEDS_DECISION",
        "consent_document_version": "NEEDS_HUMAN_REVIEW",
        "retention_policy": "NEEDS_DECISION",
        "content_hash": None,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(proposal, sort_keys=False), encoding="utf-8")
    return destination
