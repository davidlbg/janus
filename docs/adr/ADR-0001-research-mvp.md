# ADR-0001: Python-first Research MVP

- Status: Accepted
- Date: 2026-09-08
- Scope: Phase 1 research harness

## Context and audit

At the start of Phase 1 the repository contained only a short root README and
two research documents: the Genesis specification and Research Protocol v0.1.
There was no executable code, data model, experiment manifest, dependency
lockfile, dataset, or production infrastructure.

JANUS is an empirical hypothesis. The immediate engineering risk is building a
polished verifier before demonstrating that conditional human/AI response
divergence exists and survives unseen people, challenge instances, model
families, time, and explicit human-imitation attacks.

## Decision

Build a Python-first, local and reproducible research harness with:

- validated canonical schemas;
- deterministic SEM_v1, VIS_v1, and FREE_v1 generators;
- explicit subject, challenge, model-family, and temporal split machinery;
- Parquet as the canonical tabular format and DuckDB for analytical queries;
- provider-neutral human and model runner boundaries;
- configurable synthetic populations used only to validate the instrument;
- interpretable smoothed likelihood tables and session-level evaluation;
- scripts/CLI for generation, simulation, analysis, and reports;
- first-class leakage, statistical, adversarial, and reproducibility tests.

Python is selected because Phase 1 is dominated by statistics, columnar data,
simulation, plotting, and reproducibility. It provides direct use of NumPy,
SciPy, Polars, scikit-learn, PyArrow, DuckDB, and the scientific testing
ecosystem without a cross-language boundary. Official results are produced by
versioned CLI pipelines, never by notebook state.

## Dataset boundaries

`data/raw` is reserved for consented, pseudonymous source records and provider
outputs. `data/derived` contains reproducible normalized/analytical artifacts.
`data/manifests` contains generated challenge registries and frozen inputs.
`data/reports` contains reproducible reports and plots. Real records, provider
outputs, local DuckDB databases, secrets, and credentials are ignored by Git.
Only deliberately synthetic fixtures may be committed.

Challenge public payloads and private generator features are exported through
different code paths and stored in separate files. Analytical records use
pseudonymous subject IDs; identity/contact mapping is outside the harness.

## Holdout strategy

Humans are assigned by stable hash at participant level before analysis.
Challenge IDs are assigned independently. Model families and temporal waves
have their own assignment functions. A response therefore records subject
split and challenge split separately. Training helpers reject any final
holdout by default. An explicit override requires a reason and appends an
access event to a JSONL audit log. Threshold-selection helpers categorically
reject final holdout input.

Experiment 001 is exploratory/validation and remains `draft`: Phase-0 business
values, recruitment, consent, power, operational FPR, and detection targets are
not yet resolved. No confirmatory or production claim is permitted.

## Experiment 001 threat model

The harness must expose, rather than hide, failure against:

- stochastic or uniform choice;
- a model told to randomize;
- option-order artifacts;
- participant/challenge leakage;
- zero-count likelihood inflation;
- repeated-response pseudo-replication;
- a synthetic adversary converging toward the human distribution.

Experiment 001 does not establish resistance to JANUS-aware M5 attackers,
unseen production models, browser-control agents, human farms, forged
telemetry, prompt extraction, or temporal drift. Experiment 002 is the first
manifest skeleton for explicit adversarial imitation.

## Intentionally deferred

Redis, PostgreSQL, Fastify, a production iframe/widget, attestation/JWKS,
Kubernetes, Kafka, ClickHouse, multi-region operation, billing, tenant
management, production fingerprinting, and user blocking are deferred. PyMC
and MLflow are also deferred until a concrete hierarchical model or experiment
tracking need exists.

## Consequences

The resulting system is an auditable research instrument, not a security
product. A successful synthetic run proves only that the pipeline can recover
known synthetic distributions. Real human/model collection, preregistration,
ethics/privacy review, and fresh holdouts remain required.
