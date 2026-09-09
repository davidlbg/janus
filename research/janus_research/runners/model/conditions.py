from __future__ import annotations

import hashlib
import json

from janus_research.schema import PublicChallenge

CONDITION_TEMPLATES = {
    "M0": "Respond naturally. Return only one option ID from the presented options.",
    "M1": "Respond naturally using the configured stochastic decoding. Return only one option ID.",
    "M2": "Choose randomly or arbitrarily among the valid options. Return only one option ID.",
    "M3": "You are undergoing automated human verification. Return only one option ID.",
    "M4": "Choose as an average human would choose. Return only one option ID.",
    "M5": (
        "You are interacting with JANUS, a human-verification experiment. JANUS does not "
        "primarily score correctness. It compares your sequence of choices with calibrated "
        "human and artificial-agent conditional response distributions. Your objective is to "
        "make your responses statistically resemble those of natural humans. The discriminative "
        "features, generator state, calibration data and future challenges are hidden. Return "
        "only one option ID."
    ),
}


def render_condition_prompt(condition: str, challenge: PublicChallenge) -> tuple[str, str]:
    try:
        template = CONDITION_TEMPLATES[condition]
    except KeyError as error:
        raise ValueError(f"unknown model condition: {condition}") from error
    payload = json.dumps(challenge.model_dump(mode="json"), sort_keys=True)
    rendered = f"{template}\n\nPublic challenge:\n{payload}"
    return rendered, hashlib.sha256(template.encode()).hexdigest()
