from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
import numpy as np
from sklearn.metrics import roc_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from janus_research.manifest import load_manifest
from janus_research.pipeline import RESEARCH_ROOT, manifest_path


def _save_plot(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def _plots(result: dict, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    families = result["families"]
    _figure, axes = plt.subplots(1, len(families), figsize=(5 * len(families), 4), squeeze=False)
    for axis, (family, metrics) in zip(axes[0], families.items(), strict=True):
        positions = np.arange(len(metrics["options"]))
        human = np.asarray(metrics["human_counts"], dtype=float)
        ai = np.asarray(metrics["ai_counts"], dtype=float)
        axis.bar(positions - 0.18, human / max(human.sum(), 1), 0.36, label="Human")
        axis.bar(positions + 0.18, ai / max(ai.sum(), 1), 0.36, label="AI")
        axis.set_title(family)
        axis.set_xticks(positions, metrics["options"])
        axis.set_ylabel("Response proportion")
    axes[0][0].legend()
    path = output_dir / "response-distributions.png"
    _save_plot(path)
    paths.append(path)

    plt.figure(figsize=(7, 4))
    x = np.arange(len(families))
    plt.bar(x - 0.18, [families[name]["human_entropy"] for name in families], 0.36, label="Human")
    plt.bar(x + 0.18, [families[name]["ai_entropy"] for name in families], 0.36, label="AI")
    plt.xticks(x, list(families))
    plt.ylabel("Response entropy")
    plt.legend()
    path = output_dir / "response-entropy.png"
    _save_plot(path)
    paths.append(path)

    model_families = result.get("model_family_mean_ai_probability", {})
    plt.figure(figsize=(7, 4))
    plt.bar(list(model_families), list(model_families.values()))
    plt.ylim(0, 1)
    plt.ylabel("Mean predicted AI probability")
    plt.xlabel("Model family")
    path = output_dir / "model-family-comparison.png"
    _save_plot(path)
    paths.append(path)

    heterogeneity = result.get("challenge_level_tv", {})
    plt.figure(figsize=(9, 4))
    plt.scatter(range(len(heterogeneity)), list(heterogeneity.values()), s=12)
    plt.xlabel("Challenge (sorted ID)")
    plt.ylabel("Human-model TV distance")
    path = output_dir / "challenge-level-heterogeneity.png"
    _save_plot(path)
    paths.append(path)

    plt.figure(figsize=(7, 4))
    names = list(families)
    x = np.arange(len(names))
    plt.bar(x - 0.18, [families[name]["jsd"] for name in names], 0.36, label="JSD")
    plt.bar(x + 0.18, [families[name]["tv"] for name in names], 0.36, label="TV")
    plt.xticks(x, names)
    plt.ylabel("Divergence")
    plt.legend()
    path = output_dir / "divergence.png"
    _save_plot(path)
    paths.append(path)

    labels = np.asarray(result["session_labels"])
    probabilities = np.asarray(result["session_probabilities"])
    fpr, tpr, _ = roc_curve(labels, probabilities)
    plt.figure(figsize=(5, 5))
    plt.plot(fpr, tpr, label=f"AUC={result['classifier']['roc_auc']:.3f}")
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
    plt.xlabel("Human false-positive rate")
    plt.ylabel("AI true-positive rate")
    plt.legend()
    path = output_dir / "roc.png"
    _save_plot(path)
    paths.append(path)

    plt.figure(figsize=(6, 4))
    point = result["classifier"]
    plt.scatter([point["human_fpr"]], [point["ai_tpr"]], s=80)
    plt.xscale("symlog", linthresh=0.001)
    plt.xlim(0, 1)
    plt.ylim(0, 1.02)
    plt.xlabel("Human FPR (symlog)")
    plt.ylabel("AI TPR")
    plt.title("Configured operating point")
    path = output_dir / "operating-point.png"
    _save_plot(path)
    paths.append(path)

    bins = result["calibration_bins"]
    plt.figure(figsize=(5, 5))
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray")
    plt.plot(
        [item["mean_predicted"] for item in bins],
        [item["observed_fraction"] for item in bins],
        marker="o",
    )
    plt.xlabel("Mean predicted AI probability")
    plt.ylabel("Observed AI fraction")
    path = output_dir / "calibration.png"
    _save_plot(path)
    paths.append(path)

    condition_means = result["condition_mean_ai_probability"]
    plt.figure(figsize=(7, 4))
    plt.bar(list(condition_means), list(condition_means.values()))
    plt.ylim(0, 1)
    plt.ylabel("Mean predicted AI probability")
    plt.xlabel("Condition")
    path = output_dir / "model-condition-comparison.png"
    _save_plot(path)
    paths.append(path)

    completion = [value for value in result["completion_time_ms"] if np.isfinite(value)]
    plt.figure(figsize=(7, 4))
    plt.hist(completion, bins=8)
    plt.xlabel("Per-response latency midpoint (ms)")
    plt.ylabel("Count")
    path = output_dir / "completion-time.png"
    _save_plot(path)
    paths.append(path)
    return paths


def generate_report(experiment: str) -> tuple[Path, Path]:
    manifest = load_manifest(manifest_path(experiment))
    analysis_path = RESEARCH_ROOT / "data" / "derived" / manifest.experiment_id / "analysis.json"
    result = json.loads(analysis_path.read_text(encoding="utf-8"))
    output_dir = RESEARCH_ROOT / "data" / "reports" / manifest.experiment_id
    plot_paths = _plots(result, output_dir)
    lines = [
        f"# JANUS Research Report — {manifest.experiment_id}",
        "",
        f"> **{result['data_status']}**",
        "",
        f"- Manifest hash: `{result['manifest_hash']}`",
        f"- Dataset hash: `{result['dataset_hash']}`",
        f"- Analysis code version/git commit: `{result['analysis_code_version']}`",
        f"- Manifest status: `{result['manifest_status']}`",
        f"- Analysis tier: `{result['analysis_tier']}`",
        f"- Hypothesis: {manifest.hypothesis}",
        f"- Decision: **{result['decision']}**",
        "",
        "## Dataset and split summary",
        "",
        f"- Training responses: {result['sample_counts']['training_responses']}",
        f"- Validation responses: {result['sample_counts']['validation_responses']}",
        f"- Independent validation sessions: {result['sample_counts']['validation_sessions']}",
        "- Holdout: excluded and unopened",
        "- Exclusions: none (synthetic harness validation)",
        f"- Challenge versions: {', '.join(manifest.challenge_families.values())}",
        f"- Model conditions: {', '.join(manifest.model_conditions)}",
        "",
        "## Distribution metrics",
        "",
        "| Family | JSD | TV | MI | Conditional entropy |",
        "|---|---:|---:|---:|---:|",
    ]
    for family, metrics in result["families"].items():
        lines.append(
            f"| {family} | {metrics['jsd']:.4f} | {metrics['tv']:.4f} | "
            f"{metrics['mutual_information']:.4f} | {metrics['conditional_entropy']:.4f} |"
        )
    classifier = result["classifier"]
    lines.extend(
        [
            "",
            "## Session classification",
            "",
            f"- ROC-AUC: {classifier['roc_auc']:.4f}",
            f"- PR-AUC: {classifier['pr_auc']:.4f}",
            f"- Brier score: {classifier['brier_score']:.4f}",
            f"- Human FPR: {classifier['human_fpr']:.4f} "
            f"(Wilson CI {result['human_fpr_ci'][0]:.4f}-"
            f"{result['human_fpr_ci'][1]:.4f})",
            f"- AI TPR: {classifier['ai_tpr']:.4f} "
            f"(Wilson CI {result['ai_tpr_ci'][0]:.4f}-"
            f"{result['ai_tpr_ci'][1]:.4f})",
            "- Subject/session-cluster bootstrap FPR CI: "
            f"{result['human_fpr_cluster_bootstrap_ci'][0]:.4f}-"
            f"{result['human_fpr_cluster_bootstrap_ci'][1]:.4f}",
            "- Subject/session-cluster bootstrap TPR CI: "
            f"{result['ai_tpr_cluster_bootstrap_ci'][0]:.4f}-"
            f"{result['ai_tpr_cluster_bootstrap_ci'][1]:.4f}",
            f"- Confusion matrix [[TN, FP], [FN, TP]]: `{classifier['confusion_matrix']}`",
        ]
    )
    if result["rule_of_three_upper_bound"] is not None:
        lines.append(
            "- Zero observed human false positives; rule-of-three upper bound: "
            f"{result['rule_of_three_upper_bound']:.4f}. This is not an FPR=0 claim."
        )
    lines.extend(
        ["", "## Calibration", "", "| Bin | Count | Predicted | Observed |", "|---|---:|---:|---:|"]
    )
    for item in result["calibration_bins"]:
        lines.append(
            f"| {item['lower']:.1f}-{item['upper']:.1f} | {item['count']} | "
            f"{item['mean_predicted']:.4f} | {item['observed_fraction']:.4f} |"
        )
    lines.extend(["", "## Warnings and negative findings", ""])
    if result["warnings"]:
        lines.extend(f"- {warning}" for warning in result["warnings"])
    else:
        lines.append("- No automated warning fired. This does not establish external validity.")
    lines.extend(
        [
            "- The adversarial synthetic population intentionally approaches the human "
            "distribution; "
            "reduced discrimination is expected and demonstrates falsification capability.",
            "- Cognitive-only data were used. No motor/fingerprinting telemetry was added.",
            "- Subgroup/modality and held-out-model analysis are UNKNOWN because the data "
            "are synthetic.",
            "",
            "## Leakage checks",
            "",
        ]
    )
    lines.extend(f"- {key}: {value}" for key, value in result["leakage_checks"].items())
    lines.extend(["", "## Reproducible plots", ""])
    lines.extend(f"![{path.stem}]({path.name})" for path in plot_paths)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This report validates software behavior against deliberately configured synthetic "
            "distributions. It cannot establish that human/AI divergence exists in reality. "
            "Promotion, redesign, or retirement decisions require consented human data and "
            "versioned model runs under the frozen Research Protocol.",
        ]
    )
    report_path = output_dir / "report.md"
    report_bytes = ("\n".join(lines) + "\n").encode()
    report_path.write_bytes(report_bytes)
    digest = hashlib.sha256(report_bytes).hexdigest()
    digest_path = output_dir / "report.md.sha256"
    digest_path.write_text(f"{digest}  report.md\n", encoding="utf-8")
    return report_path, digest_path
