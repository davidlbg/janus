import pytest

from janus_research.metrics.core import (
    bootstrap_cluster_interval,
    brier_score,
    calibration_bins,
    conditional_entropy,
    entropy,
    jensen_shannon_divergence,
    mutual_information,
    rule_of_three_upper_bound,
    total_variation_distance,
    wilson_interval,
)


def test_distribution_metrics_known_values() -> None:
    assert jensen_shannon_divergence([1, 0], [0, 1]) == pytest.approx(1.0)
    assert total_variation_distance([1, 0], [0, 1]) == pytest.approx(1.0)
    assert entropy([0.5, 0.5]) == pytest.approx(1.0)
    assert mutual_information([0, 0, 1, 1], ["a", "a", "b", "b"]) > 0.6
    assert conditional_entropy(["a", "b", "a", "b"], [0, 0, 1, 1]) == pytest.approx(1.0)


def test_calibration_and_brier() -> None:
    assert brier_score([0, 1], [0.0, 1.0]) == pytest.approx(0.0)
    bins = calibration_bins([0, 1], [0.1, 0.9], bins=5)
    assert sum(item["count"] for item in bins) == 2


def test_cluster_bootstrap_resamples_clusters_not_rows() -> None:
    low, high = bootstrap_cluster_interval(
        ["p1", "p1", "p2", "p2"], [0, 0, 1, 1], iterations=300, seed=3
    )
    assert low == pytest.approx(0.0)
    assert high == pytest.approx(1.0)


def test_rule_of_three_never_claims_zero() -> None:
    assert rule_of_three_upper_bound(0, 3000) == pytest.approx(0.001)
    assert rule_of_three_upper_bound(1, 3000) is None


def test_wilson_interval_has_nonzero_upper_bound_for_zero_events() -> None:
    low, high = wilson_interval(0, 22)
    assert low == pytest.approx(0.0)
    assert high > 0.1
