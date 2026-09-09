# JANUS Research Harness

> Synthetic output is always **SYNTHETIC — NOT EVIDENCE**. A successful
> software run does not demonstrate that JANUS works on humans or real models.

This directory implements the Phase 1 harness and Phase 2A pilot infrastructure. It
generates three deterministic challenge families, enforces independent splits,
collects local human responses, abstracts model execution, simulates synthetic
populations, fits an interpretable likelihood scorer, and creates reproducible
reports.

## Clean installation

Install `uv`, then from this directory:

```powershell
uv sync --extra dev --frozen
uv run pytest
```

Python 3.12 or newer is supported. `uv.lock` pins the complete environment.

## Synthetic Experiment 001

```powershell
uv run janus generate --experiment exp001_signal
uv run janus simulate --experiment exp001_signal
uv run janus analyze --experiment exp001_signal
uv run janus report --experiment exp001_signal
```

Generated datasets and reports are deliberately ignored by Git. The simulation
creates an exploratory dataset and a separately sealed synthetic holdout. The
ordinary analyzer opens only the exploratory dataset.

## Phase 2A preflight

EXP001A is an exploratory real-world pilot and remains draft. Before collection:

```powershell
uv run janus audit-challenges -e exp001a_real_signal_pilot
uv run janus controls -e exp001a_real_signal_pilot
uv run janus power-plan --human-fpr-target 0.01 --expected-ai-tpr 0.70
uv run janus run-models -e exp001a_real_signal_pilot
```

`run-models` is a dry run unless `--execute` is supplied. Provider targets are
disabled and model IDs, token estimates and prices remain decisions. Prices are
configuration, never timeless constants. Large call sets require
`--approve-large-batch`. OpenAI Responses and Anthropic Messages adapters read
credentials only from the environment variables named in the manifest, retain
failed calls, and resume through an append-only checkpoint.

M0, M1 and M2 are primary. The prompt registry already supports M4 and M5 for
later exploratory/adversarial work without exposing calibration data.

## Local human collection

Human collection requires an approved consent/recruitment process outside this
software. After generating challenges, start the keyboard-operable local runner:

```powershell
uv run janus study start --experiment exp001a_real_signal_pilot --subject PSEUDONYM_001
```

The consent document is a template, not approved language. The pilot manifest
deliberately says `NEEDS_HUMAN_REVIEW`, so collection is blocked until an
accountable researcher records a reviewed version. Consent precedes responses.
Withdrawal is available in-page and by command:

```powershell
uv run janus study withdraw -e exp001a_real_signal_pilot --subject PSEUDONYM_001
```

Withdrawal tombstones the participant, prevents more responses, inventories raw
records, writes an audit event, and invalidates derived data for regeneration.
Raw data are preserved pending the reviewed retention policy.

Pilot analysis accepts explicit human/model Parquet inputs, filters ineligible
humans, and runs controls, cross-model transfer, artifact probes and ablations:

```powershell
uv run janus analyze-pilot -e exp001a_real_signal_pilot `
  --human path/to/human.parquet --model path/to/model.parquet
uv run janus report -e exp001a_real_signal_pilot
```

The output is labeled `EXPLORATORY REAL-WORLD PILOT — NOT CONFIRMATORY
EVIDENCE`. Unresolved decision thresholds produce `INCONCLUSIVE`.

`janus propose-confirmatory --from exp001a_real_signal_pilot` writes a reviewed
draft with unresolved fields and never freezes it.

Open the printed localhost URL. The subject is assigned once through a stable
participant-level hash. The page receives only `PublicChallenge`; private
features cannot be represented in that schema. Client timing/modality values
remain untrusted research observations.

## Experiment lifecycle

1. Edit only a `draft` manifest.
2. Resolve hypotheses, power, consent, exclusions, thresholds, and abandonment
   criteria before confirmatory collection.
3. Freeze with `uv run janus freeze-manifest -e <id>`. The manifest receives a
   SHA-256 content hash and project APIs reject subsequent updates.
4. Generate and collect without changing generator versions or split policies.
5. Analyze discovery/validation data. Final holdout access is blocked by the
   ordinary loader and requires a logged override with a reason.
6. Preserve negative results. A changed frozen design requires a new experiment
   ID.

Experiment 001 remains draft because the Phase-0 business decisions, human FPR
target, sample-size plan, consent, and real model cohort are unresolved.

## Adding a challenge family

Implement the `ChallengeGenerator` protocol in `janus_research/generators`, use
a versioned generator name, derive all randomness from version + seed + explicit
parameters, and register it in `default_registry`. Keep presentation in
`public_payload`; record latent annotations only in `private_features`. Add
reproducibility and public-export leakage tests.

## Adding a model adapter

Implement `ModelRunner` under an optional provider module. The domain model must
remain vendor-neutral. Capture exact model ID/runtime, prompt hashes, decoding
configuration, timestamp, parser result, retries, and failures. Provider errors
must never become choices. Never commit credentials or raw sensitive outputs.

## Data layout

```text
data/raw/        consented/pseudonymous source responses (ignored)
data/derived/    reproducible analyses (ignored)
data/manifests/  generated public/private challenge registries (ignored)
data/reports/    Markdown, plots, and SHA-256 report digest (ignored)
```

See [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) for field definitions.

## Scientific boundaries

- Participant/session is the resampling unit, never an individual response row.
- Subject and challenge splits are independent and both must match for baseline
  discovery/validation evaluation.
- Thresholds come from experiment configuration and cannot be recomputed from a
  final holdout.
- No raw pointer stream, fingerprinting, production anti-tamper, or production
  infrastructure exists here.
- `UNKNOWN` is a normal scorer result.
- Experiment 002 is a template only; it contains no fabricated result.
