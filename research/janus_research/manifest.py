from __future__ import annotations

from pathlib import Path

import yaml

from janus_research.schema import ExperimentManifest


def load_manifest(path: Path) -> ExperimentManifest:
    manifest = ExperimentManifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    if not manifest.verify_hash():
        raise ValueError(f"manifest content hash verification failed: {path}")
    return manifest


def save_manifest(manifest: ExperimentManifest, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.model_dump(mode="json")
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path
