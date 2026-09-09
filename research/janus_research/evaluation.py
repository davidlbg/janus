from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression

from janus_research.metrics.core import classification_metrics, mutual_information
from janus_research.models import LikelihoodScorer, ScoringThresholds
from janus_research.schema import DatasetSplit, PopulationClass, ResponseRecord


@dataclass(frozen=True)
class TransferResult:
    train_model_family: str
    test_model_family: str
    validation_sessions: int
    roc_auc: float
    pr_auc: float
    brier_score: float


def cross_model_transfer(
    records: list[ResponseRecord],
    *,
    smoothing: float = 1.0,
    threshold: float = 0.5,
) -> list[dict[str, str | int | float]]:
    model_families = sorted(
        {
            record.model_family
            for record in records
            if record.population_class != PopulationClass.HUMAN and record.model_family
        }
    )
    output = []
    for train_family in model_families:
        training = [
            record
            for record in records
            if record.split == DatasetSplit.DISCOVERY
            and (
                record.population_class == PopulationClass.HUMAN
                or record.model_family == train_family
            )
        ]
        scorer = LikelihoodScorer(smoothing, ScoringThresholds(-2, 2)).fit(training)
        for test_family in model_families:
            testing = [
                record
                for record in records
                if record.split == DatasetSplit.VALIDATION
                and (
                    record.population_class == PopulationClass.HUMAN
                    or record.model_family == test_family
                )
            ]
            sessions: dict[str, list[ResponseRecord]] = defaultdict(list)
            for record in testing:
                sessions[record.session_id].append(record)
            labels = [
                0 if session[0].population_class == PopulationClass.HUMAN else 1
                for session in sessions.values()
            ]
            probabilities = [
                scorer.score_session(session).ai_probability for session in sessions.values()
            ]
            if len(set(labels)) != 2:
                continue
            metrics = classification_metrics(labels, probabilities, threshold)
            roc_auc = metrics["roc_auc"]
            pr_auc = metrics["pr_auc"]
            brier_score = metrics["brier_score"]
            assert isinstance(roc_auc, float)
            assert isinstance(pr_auc, float)
            assert isinstance(brier_score, float)
            output.append(
                asdict(
                    TransferResult(
                        train_model_family=train_family,
                        test_model_family=test_family,
                        validation_sessions=len(sessions),
                        roc_auc=roc_auc,
                        pr_auc=pr_auc,
                        brier_score=brier_score,
                    )
                )
            )
    return output


def option_position_probe(
    records: list[ResponseRecord], threshold: float = 0.05
) -> dict[str, float | bool]:
    populations = [
        "human" if record.population_class == PopulationClass.HUMAN else "ai" for record in records
    ]
    positions = [str(record.public_option_order.index(record.response)) for record in records]
    information = mutual_information(populations, positions)
    return {
        "population_option_position_mutual_information": information,
        "flagged": information >= threshold,
        "threshold": threshold,
    }


def ablation_evaluation(
    records: list[ResponseRecord],
) -> dict[str, dict[str, float | list[list[int]]]]:
    training = [record for record in records if record.split == DatasetSplit.DISCOVERY]
    scorer = LikelihoodScorer(1.0, ScoringThresholds(-2, 2)).fit(training)
    grouped: dict[DatasetSplit, dict[str, list[ResponseRecord]]] = {
        DatasetSplit.DISCOVERY: defaultdict(list),
        DatasetSplit.VALIDATION: defaultdict(list),
    }
    for record in records:
        if record.split in grouped:
            grouped[record.split][record.session_id].append(record)

    def matrix(split: DatasetSplit, width: int) -> tuple[np.ndarray, np.ndarray]:
        rows = []
        labels = []
        latency_map = {
            "0-500": 250.0,
            "500-1500": 1000.0,
            "1500-2500": 2000.0,
            "2500+": 3000.0,
            "provider_call": 0.0,
        }
        for session in grouped[split].values():
            score = scorer.score_session(session)
            weighted = sum((index + 1) * value for index, value in enumerate(score.contributions))
            features = [score.log_likelihood_ratio, weighted]
            features.append(
                float(
                    np.mean(
                        [latency_map.get(item.response_latency_bucket, 0.0) for item in session]
                    )
                )
            )
            features.extend(
                [
                    float(np.mean([item.revision_count for item in session])),
                    float(np.mean([item.input_modality == "keyboard" for item in session])),
                ]
            )
            rows.append(features[:width])
            labels.append(0 if session[0].population_class == PopulationClass.HUMAN else 1)
        return np.asarray(rows), np.asarray(labels)

    output = {}
    for name, width in {
        "choice_only": 1,
        "choice_sequence": 2,
        "choice_latency": 3,
        "choice_minimal_telemetry": 5,
    }.items():
        train_x, train_y = matrix(DatasetSplit.DISCOVERY, width)
        test_x, test_y = matrix(DatasetSplit.VALIDATION, width)
        if len(set(train_y)) != 2 or len(set(test_y)) != 2:
            continue
        model = LogisticRegression(random_state=0).fit(train_x, train_y)
        probabilities = model.predict_proba(test_x)[:, 1]
        output[name] = classification_metrics(test_y.tolist(), probabilities.tolist(), 0.5)
    return output
