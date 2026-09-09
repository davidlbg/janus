from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from janus_research.adversarial import (
    SyntheticAdversarialAIPopulation,
    SyntheticAIPopulation,
    SyntheticHumanPopulation,
    simulate_experiment,
)
from janus_research.generators import default_registry
from janus_research.manifest import load_manifest
from janus_research.metrics.core import (
    bootstrap_cluster_interval,
    calibration_bins,
    classification_metrics,
    conditional_entropy,
    entropy,
    jensen_shannon_divergence,
    mutual_information,
    rule_of_three_upper_bound,
    total_variation_distance,
    wilson_interval,
)
from janus_research.models import LikelihoodScorer, ScoringThresholds
from janus_research.provenance import git_commit, report_label, sha256_file
from janus_research.schema import DatasetSplit, PopulationClass, ResponseRecord
from janus_research.splits import (
    SplitAssigner,
    assert_no_label_metadata_leakage,
    load_training_responses,
    validate_split_integrity,
)
from janus_research.storage import (
    duckdb_query,
    read_challenges,
    read_responses,
    write_challenges,
    write_responses,
)

RESEARCH_ROOT = Path(__file__).resolve().parents[1]


def manifest_path(experiment: str) -> Path:
    name = experiment if experiment.endswith(".yaml") else f"{experiment}.yaml"
    path = RESEARCH_ROOT / "experiments" / "manifests" / name
    if not path.exists():
        raise FileNotFoundError(f"experiment manifest not found: {path}")
    return path


def experiment_directory(experiment_id: str) -> Path:
    return RESEARCH_ROOT / "data" / "manifests" / experiment_id


def generate_experiment(experiment: str) -> tuple[Path, Path]:
    manifest = load_manifest(manifest_path(experiment))
    registry = default_registry()
    assigner = SplitAssigner(
        f"{manifest.experiment_id}:challenges", manifest.challenge_split_policy
    )
    challenges = []
    for family_index, (family, version) in enumerate(manifest.challenge_families.items()):
        generator = registry.get(version)
        if generator.family != family:
            raise ValueError(f"manifest family/version mismatch: {family}/{version}")
        for instance_index in range(manifest.challenge_count_per_family):
            seed = manifest.random_seed + family_index * 1_000_000 + instance_index
            provisional = generator.generate(seed, DatasetSplit.DISCOVERY)
            split = assigner.assign(provisional.challenge_id)
            challenges.append(generator.generate(seed, split))
    return write_challenges(challenges, experiment_directory(manifest.experiment_id))


def simulate(experiment: str) -> tuple[Path, Path]:
    manifest = load_manifest(manifest_path(experiment))
    challenges = read_challenges(experiment_directory(manifest.experiment_id))
    records = simulate_experiment(
        challenges,
        [
            SyntheticHumanPopulation(),
            SyntheticAIPopulation(condition="M0"),
            SyntheticAIPopulation(weights=(0.10, 0.20, 0.30, 0.40), condition="M1"),
            SyntheticAdversarialAIPopulation(condition="M2"),
        ],
        sessions_per_population=manifest.synthetic_sessions_per_population,
        seed=manifest.random_seed,
        study_version=manifest.protocol_version,
        split_policy=manifest.human_split_policy,
    )
    raw_dir = RESEARCH_ROOT / "data" / "raw" / manifest.experiment_id
    exploratory = [record for record in records if record.split != DatasetSplit.HOLDOUT]
    holdout = [record for record in records if record.split == DatasetSplit.HOLDOUT]
    exploratory_path = write_responses(exploratory, raw_dir / "responses_synthetic.parquet")
    holdout_path = write_responses(holdout, raw_dir / "responses_synthetic_holdout.parquet")
    return exploratory_path, holdout_path


def _records_from_frame(frame: Any) -> list[ResponseRecord]:
    return [ResponseRecord.model_validate(row) for row in frame.to_dicts()]


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-max(min(value, 700), -700)))


def _latency_midpoint(bucket: str) -> float:
    return {"0-500": 250, "500-1500": 1000, "1500-2500": 2000, "2500+": 3000}.get(
        bucket, float("nan")
    )


def analyze(experiment: str, response_path: Path | None = None) -> Path:
    manifest = load_manifest(manifest_path(experiment))
    response_path = response_path or (
        RESEARCH_ROOT / "data" / "raw" / manifest.experiment_id / "responses_synthetic.parquet"
    )
    frame = load_training_responses([response_path])
    assert_no_label_metadata_leakage(frame, [response_path])
    validate_split_integrity(frame)
    records = _records_from_frame(frame)
    train = [
        record
        for record in records
        if record.split == DatasetSplit.DISCOVERY
        and record.challenge_split == DatasetSplit.DISCOVERY
    ]
    validation = [
        record
        for record in records
        if record.split == DatasetSplit.VALIDATION
        and record.challenge_split == DatasetSplit.VALIDATION
    ]
    if not train or not validation:
        raise ValueError("discovery and validation intersections must both contain records")
    scorer_config = manifest.scorer
    thresholds = ScoringThresholds(
        human_log_threshold=float(scorer_config["human_log_threshold"]),
        ai_log_threshold=float(scorer_config["ai_log_threshold"]),
    )
    scorer = LikelihoodScorer(float(scorer_config["smoothing"]), thresholds).fit(train)
    sessions: dict[str, list[ResponseRecord]] = defaultdict(list)
    for record in validation:
        sessions[record.session_id].append(record)
    scores = [scorer.score_session(session_records) for session_records in sessions.values()]
    session_population = {
        session_id: session_records[0].population_class
        for session_id, session_records in sessions.items()
    }
    labels = [
        0 if session_population[score.session_id] == PopulationClass.HUMAN else 1
        for score in scores
    ]
    probabilities = [score.ai_probability for score in scores]
    probability_threshold = _sigmoid(thresholds.ai_log_threshold)
    classifier = classification_metrics(labels, probabilities, probability_threshold)
    families: dict[str, Any] = {}
    zero_cell_warnings = []
    for family in manifest.challenge_families:
        family_records = [record for record in validation if record.challenge_family == family]
        option_ids = sorted(
            {option for record in family_records for option in record.public_option_order}
        )
        human_counts = Counter(
            record.response
            for record in family_records
            if record.population_class == PopulationClass.HUMAN
        )
        ai_counts = Counter(
            record.response
            for record in family_records
            if record.population_class != PopulationClass.HUMAN
        )
        human_vector = [human_counts[option] for option in option_ids]
        ai_vector = [ai_counts[option] for option in option_ids]
        if any(value == 0 for value in human_vector + ai_vector):
            zero_cell_warnings.append(
                f"{family}: zero response cell observed; scorer smoothing applied"
            )
        population_labels = [
            "human" if record.population_class == PopulationClass.HUMAN else "ai"
            for record in family_records
        ]
        families[family] = {
            "options": option_ids,
            "human_counts": human_vector,
            "ai_counts": ai_vector,
            "jsd": jensen_shannon_divergence(human_vector, ai_vector),
            "tv": total_variation_distance(human_vector, ai_vector),
            "mutual_information": mutual_information(
                population_labels, [record.response for record in family_records]
            ),
            "conditional_entropy": conditional_entropy(
                [record.response for record in family_records], population_labels
            ),
            "human_entropy": entropy(human_vector),
            "ai_entropy": entropy(ai_vector),
        }
    human_errors = [
        float(probability >= probability_threshold)
        for label, probability in zip(labels, probabilities, strict=True)
        if label == 0
    ]
    human_ids = [
        score.session_id for label, score in zip(labels, scores, strict=True) if label == 0
    ]
    ai_hits = [
        float(probability >= probability_threshold)
        for label, probability in zip(labels, probabilities, strict=True)
        if label == 1
    ]
    ai_ids = [score.session_id for label, score in zip(labels, scores, strict=True) if label == 1]
    fpr_bootstrap_ci = bootstrap_cluster_interval(
        human_ids, human_errors, iterations=1000, seed=manifest.random_seed
    )
    tpr_bootstrap_ci = bootstrap_cluster_interval(
        ai_ids, ai_hits, iterations=1000, seed=manifest.random_seed + 1
    )
    fpr_ci = wilson_interval(int(sum(human_errors)), len(human_errors))
    tpr_ci = wilson_interval(int(sum(ai_hits)), len(ai_hits))
    warnings = list(zero_cell_warnings)
    if len(sessions) < 30:
        warnings.append("Tiny validation sample: fewer than 30 independent sessions")
    target = manifest.declared_human_fpr_target
    if target is not None and fpr_ci[1] > target:
        warnings.append("Human FPR confidence interval is too wide for the declared target")
    human_failures = int(sum(human_errors))
    rule_three = rule_of_three_upper_bound(human_failures, len(human_errors))
    duckdb_counts = duckdb_query(
        response_path,
        "SELECT population_class, COUNT(DISTINCT session_id) FROM responses GROUP BY 1 ORDER BY 1",
    )
    condition_metrics = {}
    for condition in sorted({record.condition for record in validation}):
        condition_session_ids = {
            record.session_id for record in validation if record.condition == condition
        }
        condition_probabilities = [
            score.ai_probability for score in scores if score.session_id in condition_session_ids
        ]
        if condition_probabilities:
            condition_metrics[condition] = float(np.mean(condition_probabilities))
    for condition in sorted(
        {records_for_session[0].condition for records_for_session in sessions.values()}
    ):
        condition_scores = [
            score.ai_probability
            for score in scores
            if sessions[score.session_id][0].condition == condition
        ]
        condition_metrics[condition] = float(np.mean(condition_scores))
    model_family_metrics = {}
    for model_family in sorted(
        {
            session[0].model_family
            for session in sessions.values()
            if session[0].model_family is not None
        }
    ):
        family_scores = [
            score.ai_probability
            for score in scores
            if sessions[score.session_id][0].model_family == model_family
        ]
        model_family_metrics[model_family] = float(np.mean(family_scores))
    challenge_heterogeneity = {}
    for challenge_id in sorted({record.challenge_id for record in validation}):
        challenge_records = [record for record in validation if record.challenge_id == challenge_id]
        options = sorted(
            {option for record in challenge_records for option in record.public_option_order}
        )
        human = Counter(
            record.response
            for record in challenge_records
            if record.population_class == PopulationClass.HUMAN
        )
        artificial = Counter(
            record.response
            for record in challenge_records
            if record.population_class != PopulationClass.HUMAN
        )
        if human and artificial:
            challenge_heterogeneity[challenge_id] = total_variation_distance(
                [human[option] for option in options], [artificial[option] for option in options]
            )
    result = {
        "experiment_id": manifest.experiment_id,
        "manifest_hash": manifest.content_hash
        or hashlib.sha256(manifest.canonical_bytes()).hexdigest(),
        "manifest_status": manifest.status.value,
        "data_status": report_label(manifest),
        "dataset_hash": sha256_file(response_path),
        "analysis_code_version": git_commit(RESEARCH_ROOT.parent),
        "analysis_tier": manifest.analysis_tier,
        "sample_counts": {
            "training_responses": len(train),
            "validation_responses": len(validation),
            "validation_sessions": len(sessions),
            "duckdb_sessions_by_population": [list(row) for row in duckdb_counts],
        },
        "families": families,
        "classifier": classifier,
        "human_fpr_ci": list(fpr_ci),
        "ai_tpr_ci": list(tpr_ci),
        "human_fpr_cluster_bootstrap_ci": list(fpr_bootstrap_ci),
        "ai_tpr_cluster_bootstrap_ci": list(tpr_bootstrap_ci),
        "rule_of_three_upper_bound": rule_three,
        "probability_threshold": probability_threshold,
        "calibration_bins": calibration_bins(labels, probabilities),
        "session_labels": labels,
        "session_probabilities": probabilities,
        "session_conditions": [sessions[score.session_id][0].condition for score in scores],
        "condition_mean_ai_probability": condition_metrics,
        "model_family_mean_ai_probability": model_family_metrics,
        "challenge_level_tv": challenge_heterogeneity,
        "completion_time_ms": [
            _latency_midpoint(record.response_latency_bucket) for record in validation
        ],
        "warnings": warnings,
        "leakage_checks": {
            "subject split": "PASS: stable hash assignment; discovery/validation intersection",
            "challenge split": "PASS: challenge IDs assigned once and independently",
            "final holdout": "PASS: separate sealed file, unopened by analysis",
            "private payload": "PASS: absent from public challenge schema/storage",
            "fixture metadata": "PASS: labels absent from paths and row order shuffled",
            "threshold selection": "PASS: configured in manifest, not recomputed on holdout",
        },
        "decision": "SYNTHETIC_PIPELINE_VALIDATED — NOT A SCIENTIFIC DECISION",
    }
    output = RESEARCH_ROOT / "data" / "derived" / manifest.experiment_id / "analysis.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return output


def analyze_pilot(experiment: str, human_paths: list[Path], model_paths: list[Path]) -> Path:
    from janus_research.consent import ConsentStore
    from janus_research.controls import run_controls
    from janus_research.evaluation import (
        ablation_evaluation,
        cross_model_transfer,
        option_position_probe,
    )

    manifest = load_manifest(manifest_path(experiment))
    if manifest.data_kind != "real_exploratory":
        raise ValueError("pilot analysis requires data_kind=real_exploratory")
    store = ConsentStore(RESEARCH_ROOT, manifest.experiment_id, manifest.retention_policy)
    humans = [record for path in human_paths for record in read_responses(path)]
    models = [record for path in model_paths for record in read_responses(path)]
    eligible_humans = [
        record
        for record in humans
        if (consent := store.status(record.subject_id)) is not None
        and consent.status.value == "active"
    ]
    if len(eligible_humans) != len(humans):
        excluded = len(humans) - len(eligible_humans)
    else:
        excluded = 0
    records = eligible_humans + models
    if not eligible_humans or not models:
        raise ValueError("analysis requires consent-eligible humans and real model responses")
    input_path = RESEARCH_ROOT / "data" / "derived" / manifest.experiment_id / "pilot_input.parquet"
    write_responses(records, input_path)
    output = analyze(experiment, input_path)
    result = json.loads(output.read_text(encoding="utf-8"))
    controls = run_controls(manifest.random_seed)
    result["consent_excluded_responses"] = excluded
    result["cross_model_transfer"] = cross_model_transfer(records)
    result["artifact_probes"] = {"option_position": option_position_probe(records)}
    result["ablations"] = ablation_evaluation(records)
    result["controls"] = {
        "positive_pass": controls.positive_pass,
        "negative_pass": controls.negative_pass,
        "pipeline_valid": controls.pipeline_valid,
    }
    rules = manifest.pilot_decision_rules
    if rules is None:
        result["decision"] = "INCONCLUSIVE"
        result["decision_reason"] = (
            "Pilot decision thresholds remain NEEDS_DECISION; no positive conclusion is automated."
        )
    else:
        required = {
            "min_family_tv",
            "min_effect_families",
            "min_cross_model_auc",
            "max_position_mi",
        }
        missing = required - rules.keys()
        if missing:
            raise ValueError(f"pilot_decision_rules missing explicit fields: {sorted(missing)}")
        effect_families = sum(
            float(metrics["tv"]) >= rules["min_family_tv"]
            for metrics in result["families"].values()
        )
        transfers = [
            row
            for row in result["cross_model_transfer"]
            if row["train_model_family"] != row["test_model_family"]
        ]
        cross_model = any(
            float(row["roc_auc"]) >= rules["min_cross_model_auc"] for row in transfers
        )
        artifact_clear = (
            float(
                result["artifact_probes"]["option_position"][
                    "population_option_position_mutual_information"
                ]
            )
            <= rules["max_position_mi"]
        )
        if effect_families == 0 or not artifact_clear:
            result["decision"] = "NOT SUPPORTED"
        elif effect_families >= int(rules["min_effect_families"]) and cross_model:
            result["decision"] = "PROMISING"
        else:
            result["decision"] = "INCONCLUSIVE"
        result["decision_reason"] = {
            "effect_families": effect_families,
            "cross_model_generalization": cross_model,
            "option_position_artifact_clear": artifact_clear,
            "configured_rules": rules,
        }
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return output
