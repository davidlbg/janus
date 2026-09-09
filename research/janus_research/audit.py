from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from janus_research.generators import default_registry
from janus_research.schema import ChallengeDefinition, DatasetSplit, ExperimentManifest

FORBIDDEN_KEYS = {"answer", "correct", "ground_truth", "private_features", "score"}
URL_PATTERN = re.compile(r"https?://[^\"'\s<>]+", re.IGNORECASE)
SAFE_INLINE_NAMESPACES = {"http://www.w3.org/2000/svg"}


@dataclass(frozen=True)
class ChallengeAudit:
    status: str
    challenge_count: int
    duplicate_ids: list[str]
    public_leak_paths: list[str]
    malformed_svg_paths: list[str]
    external_content_paths: list[str]
    position_counts: dict[str, list[int]]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _walk(value: Any, path: str = "public_payload") -> list[str]:
    leaks: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key.lower() in FORBIDDEN_KEYS:
                leaks.append(child_path)
            leaks.extend(_walk(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaks.extend(_walk(child, f"{path}[{index}]"))
    return leaks


def _contains_external(value: Any) -> bool:
    if isinstance(value, str):
        if re.search(r"(?:javascript:|<script\b)", value, re.IGNORECASE):
            return True
        return any(url not in SAFE_INLINE_NAMESPACES for url in URL_PATTERN.findall(value))
    if isinstance(value, dict):
        return any(_contains_external(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_external(child) for child in value)
    return False


def audit_challenges(challenges: list[ChallengeDefinition]) -> ChallengeAudit:
    ids = Counter(challenge.challenge_id for challenge in challenges)
    leaks: list[str] = []
    malformed: list[str] = []
    external: list[str] = []
    positions: dict[str, list[int]] = defaultdict(list)
    for challenge in challenges:
        leaks.extend(f"{challenge.challenge_id}:{path}" for path in _walk(challenge.public_payload))
        if _contains_external(challenge.public_payload):
            external.append(challenge.challenge_id)
        for position, option in enumerate(challenge.public_payload.get("options", [])):
            positions[str(option.get("id"))].append(position)
            svg = option.get("svg")
            if svg:
                try:
                    ET.fromstring(str(svg))
                except ET.ParseError:
                    malformed.append(f"{challenge.challenge_id}:{position}")
    warnings = []
    for option_id, observed in positions.items():
        if len(observed) >= 6 and len(set(observed)) == 1:
            warnings.append(f"option {option_id} occurs in only position {observed[0]}")
    duplicate_ids = sorted(key for key, count in ids.items() if count > 1)
    status = "PASS" if not (duplicate_ids or leaks or malformed or external or warnings) else "FAIL"
    return ChallengeAudit(
        status=status,
        challenge_count=len(challenges),
        duplicate_ids=duplicate_ids,
        public_leak_paths=sorted(leaks),
        malformed_svg_paths=sorted(malformed),
        external_content_paths=sorted(external),
        position_counts={key: value for key, value in sorted(positions.items())},
        warnings=warnings,
    )


def generate_audit_set(
    manifest: ExperimentManifest, seeds_per_family: int = 120
) -> list[ChallengeDefinition]:
    registry = default_registry()
    challenges = []
    for family_index, (family, version) in enumerate(manifest.challenge_families.items()):
        generator = registry.get(version)
        if generator.family != family:
            raise ValueError(f"manifest family/version mismatch: {family}/{version}")
        for offset in range(seeds_per_family):
            challenges.append(
                generator.generate(
                    manifest.random_seed + family_index * 1_000_000 + offset, DatasetSplit.DISCOVERY
                )
            )
    return challenges


def write_audit(
    audit: ChallengeAudit,
    directory: Path,
    provenance: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "challenge_audit.json"
    markdown_path = directory / "challenge_audit.md"
    payload = {**audit.to_dict(), "provenance": provenance or {}}
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(
        "# Challenge audit\n\n"
        f"Status: **{audit.status}**\n\n"
        f"Challenges: {audit.challenge_count}\n\n"
        f"Duplicate IDs: {audit.duplicate_ids or 'none'}\n\n"
        f"Leak paths: {audit.public_leak_paths or 'none'}\n\n"
        f"Malformed SVG: {audit.malformed_svg_paths or 'none'}\n\n"
        f"External content: {audit.external_content_paths or 'none'}\n\n"
        f"Warnings: {audit.warnings or 'none'}\n",
        encoding="utf-8",
    )
    return json_path, markdown_path
