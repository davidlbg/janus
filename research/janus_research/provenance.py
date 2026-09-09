from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from janus_research.schema import ExperimentManifest, ManifestStatus


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def report_label(manifest: ExperimentManifest) -> str:
    if manifest.data_kind == "synthetic":
        return "SYNTHETIC — NOT EVIDENCE"
    if manifest.data_kind == "real_exploratory":
        return "EXPLORATORY REAL-WORLD PILOT\nNOT CONFIRMATORY EVIDENCE"
    if manifest.data_kind == "real_confirmatory":
        if not manifest.confirmatory or manifest.status != ManifestStatus.FROZEN:
            raise ValueError("confirmatory report label requires a frozen confirmatory manifest")
        return "PREREGISTERED CONFIRMATORY EXPERIMENT"
    raise ValueError(f"unsupported data_kind: {manifest.data_kind}")
