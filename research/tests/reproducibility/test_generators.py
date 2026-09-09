import pytest

from janus_research.generators import FreeChoiceGenerator, SemanticGenerator, VisualGenerator
from janus_research.schema import DatasetSplit


@pytest.mark.parametrize(
    "generator", [SemanticGenerator(), VisualGenerator(), FreeChoiceGenerator()]
)
def test_same_version_seed_and_parameters_reproduce_identical_challenge(generator) -> None:
    first = generator.generate(9917, DatasetSplit.VALIDATION, {"wave": "T0"})
    second = generator.generate(9917, DatasetSplit.VALIDATION, {"wave": "T0"})
    assert first == second


@pytest.mark.parametrize(
    "generator", [SemanticGenerator(), VisualGenerator(), FreeChoiceGenerator()]
)
def test_different_seed_changes_challenge(generator) -> None:
    first = generator.generate(1, DatasetSplit.DISCOVERY)
    second = generator.generate(2, DatasetSplit.DISCOVERY)
    assert first.challenge_id != second.challenge_id


def test_visual_assets_are_local_svg() -> None:
    challenge = VisualGenerator().generate(3, DatasetSplit.DISCOVERY)
    for option in challenge.public_payload["options"]:
        assert option["svg"].startswith("<svg")
        assert "http://" not in option["svg"].replace("http://www.w3.org/2000/svg", "")
