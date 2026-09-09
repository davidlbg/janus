from conftest import make_response

from janus_research.models import LikelihoodScorer, ScoringThresholds
from janus_research.schema import Decision, PopulationClass


def test_interpretable_scorer_accumulates_evidence_and_preserves_unknown(challenge) -> None:
    options = [option["id"] for option in challenge.public_payload["options"]]
    training = []
    for index in range(20):
        training.append(
            make_response(challenge, PopulationClass.HUMAN, options[0], session_id=f"h{index}")
        )
        training.append(
            make_response(
                challenge, PopulationClass.AI, options[-1], session_id=f"a{index}", condition="M0"
            )
        )
    scorer = LikelihoodScorer(1.0, ScoringThresholds(-1.0, 1.0)).fit(training)
    human = scorer.score_session(
        [make_response(challenge, PopulationClass.HUMAN, options[0], session_id="test-h")]
    )
    ai = scorer.score_session(
        [
            make_response(
                challenge, PopulationClass.AI, options[-1], session_id="test-a", condition="M0"
            )
        ]
    )
    assert human.decision == Decision.HUMAN_COMPATIBLE
    assert ai.decision == Decision.AI_COMPATIBLE

    conservative = LikelihoodScorer(1.0, ScoringThresholds(-10.0, 10.0)).fit(training)
    assert (
        conservative.score_session(
            [make_response(challenge, PopulationClass.HUMAN, options[0], session_id="unknown")]
        ).decision
        == Decision.UNKNOWN
    )
