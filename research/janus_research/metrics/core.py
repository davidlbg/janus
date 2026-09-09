from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np
from scipy.stats import entropy as scipy_entropy
from scipy.stats import norm
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    mutual_info_score,
    roc_auc_score,
)


def _probabilities(values: Sequence[float]) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError("probability vectors must be non-empty and one-dimensional")
    if np.any(array < 0) or not np.isfinite(array).all():
        raise ValueError("probability vectors must be finite and non-negative")
    total = array.sum()
    if total <= 0:
        raise ValueError("probability vector must have positive mass")
    return array / total


def entropy(values: Sequence[float], *, base: float = 2.0) -> float:
    return float(scipy_entropy(_probabilities(values), base=base))


def jensen_shannon_divergence(
    left: Sequence[float], right: Sequence[float], *, base: float = 2.0
) -> float:
    p = _probabilities(left)
    q = _probabilities(right)
    if p.shape != q.shape:
        raise ValueError("probability vectors must have equal length")
    midpoint = (p + q) / 2
    divergence = scipy_entropy(p, midpoint, base=base) + scipy_entropy(q, midpoint, base=base)
    return float(divergence / 2)


def total_variation_distance(left: Sequence[float], right: Sequence[float]) -> float:
    p = _probabilities(left)
    q = _probabilities(right)
    if p.shape != q.shape:
        raise ValueError("probability vectors must have equal length")
    return float(0.5 * np.abs(p - q).sum())


def mutual_information(labels: Sequence[str | int], responses: Sequence[str | int]) -> float:
    if len(labels) != len(responses) or not labels:
        raise ValueError("labels and responses must be non-empty and equally sized")
    return float(mutual_info_score(labels, responses))


def conditional_entropy(
    outcomes: Sequence[str | int], conditions: Sequence[str | int], *, base: float = 2.0
) -> float:
    if len(outcomes) != len(conditions) or not outcomes:
        raise ValueError("outcomes and conditions must be non-empty and equally sized")
    groups: dict[str | int, list[str | int]] = {}
    for outcome, condition in zip(outcomes, conditions, strict=True):
        groups.setdefault(condition, []).append(outcome)
    result = 0.0
    for values in groups.values():
        _, counts = np.unique(values, return_counts=True)
        result += (len(values) / len(outcomes)) * entropy(counts.tolist(), base=base)
    return result


def brier_score(labels: Sequence[int], probabilities: Sequence[float]) -> float:
    y = np.asarray(labels, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    if y.shape != p.shape or y.size == 0:
        raise ValueError("labels and probabilities must be non-empty and equally sized")
    return float(np.mean((p - y) ** 2))


def human_fpr(labels: Sequence[int], probabilities: Sequence[float], threshold: float) -> float:
    y = np.asarray(labels, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    human = y == 0
    if not human.any():
        raise ValueError("human FPR requires at least one human session")
    return float(np.mean(p[human] >= threshold))


def classification_metrics(
    labels: Sequence[int], probabilities: Sequence[float], threshold: float
) -> dict[str, float | list[list[int]]]:
    y = np.asarray(labels, dtype=int)
    p = np.asarray(probabilities, dtype=float)
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("classification metrics require both human (0) and AI (1) labels")
    predicted = (p >= threshold).astype(int)
    matrix = confusion_matrix(y, predicted, labels=[0, 1])
    true_human, false_ai, false_human, true_ai = matrix.ravel()
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "confusion_matrix": matrix.tolist(),
        "human_fpr": float(false_ai / (true_human + false_ai)),
        "ai_tpr": float(true_ai / (true_ai + false_human)),
        "brier_score": brier_score(y.tolist(), p.tolist()),
    }


def calibration_bins(
    labels: Sequence[int], probabilities: Sequence[float], bins: int = 10
) -> list[dict[str, float | int]]:
    if bins < 2:
        raise ValueError("at least two calibration bins are required")
    y = np.asarray(labels, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    edges = np.linspace(0, 1, bins + 1)
    output = []
    for index in range(bins):
        upper = p <= edges[index + 1] if index == bins - 1 else p < edges[index + 1]
        mask = (p >= edges[index]) & upper
        if mask.any():
            output.append(
                {
                    "lower": float(edges[index]),
                    "upper": float(edges[index + 1]),
                    "count": int(mask.sum()),
                    "mean_predicted": float(p[mask].mean()),
                    "observed_fraction": float(y[mask].mean()),
                }
            )
    return output


def bootstrap_cluster_interval(
    cluster_ids: Sequence[str],
    values: Sequence[float],
    statistic: Callable[[np.ndarray], float] = np.mean,
    *,
    confidence: float = 0.95,
    iterations: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    if len(cluster_ids) != len(values) or not values:
        raise ValueError("cluster IDs and values must be non-empty and equally sized")
    clusters: dict[str, list[float]] = {}
    for cluster_id, value in zip(cluster_ids, values, strict=True):
        clusters.setdefault(cluster_id, []).append(float(value))
    names = sorted(clusters)
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(iterations):
        selected = rng.choice(names, size=len(names), replace=True)
        sample = np.asarray([value for name in selected for value in clusters[name]])
        samples.append(float(statistic(sample)))
    alpha = 1 - confidence
    return float(np.quantile(samples, alpha / 2)), float(np.quantile(samples, 1 - alpha / 2))


def rule_of_three_upper_bound(failures: int, independent_units: int) -> float | None:
    if independent_units <= 0:
        raise ValueError("independent_units must be positive")
    return 3 / independent_units if failures == 0 else None


def wilson_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    if trials <= 0 or not 0 <= successes <= trials:
        raise ValueError("successes/trials are invalid")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    z = float(norm.ppf(1 - (1 - confidence) / 2))
    observed = successes / trials
    denominator = 1 + z**2 / trials
    center = (observed + z**2 / (2 * trials)) / denominator
    half_width = (
        z * math.sqrt((observed * (1 - observed) / trials) + z**2 / (4 * trials**2)) / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)
