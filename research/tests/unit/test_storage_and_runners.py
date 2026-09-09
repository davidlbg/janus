from pathlib import Path

import polars as pl
import pytest

from janus_research.runners.human.server import render_challenge_html
from janus_research.runners.model import FixtureModelRunner, MockModelRunner
from janus_research.schema import ParserStatus
from janus_research.storage import read_challenges, write_challenges


def test_public_and_private_challenge_storage_are_separate(tmp_path: Path, challenge) -> None:
    public_path, private_path = write_challenges([challenge], tmp_path)
    public = pl.read_parquet(public_path)
    private = pl.read_parquet(private_path)
    assert "private_features" not in public.columns
    assert "public_payload" not in private.columns
    assert read_challenges(tmp_path) == [challenge]


def test_challenge_registry_rejects_duplicate_ids(tmp_path: Path, challenge) -> None:
    duplicate = challenge.model_copy(update={"split": "validation"})
    with pytest.raises(ValueError, match="unique"):
        write_challenges([challenge, duplicate], tmp_path)


def test_human_page_never_renders_private_features(challenge) -> None:
    marker = "DO_NOT_RENDER_SECRET"
    challenge.private_features["marker"] = marker
    page = render_challenge_html(challenge, 0)
    assert marker not in page
    assert 'type="radio"' in page
    assert "keydown" in page


def test_model_runners_are_provider_neutral_and_validate_fixture(challenge) -> None:
    public = challenge.to_public()
    mock = MockModelRunner().run(public, "M5", seed=1)
    assert mock.response in {option["id"] for option in public.public_payload["options"]}
    assert mock.metadata.provider_runtime == "local/mock"
    missing = FixtureModelRunner({}).run(public, "M0")
    assert missing.response is None
    assert missing.metadata.parser_status == ParserStatus.INVALID
