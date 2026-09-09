# ADR-0002: Real-world signal pilot

- Status: Accepted
- Date: 2026-09-08
- Scope: Phase 2A research operations

## Purpose

Phase 2A equips JANUS to compare consented real humans with versioned real
artificial models. It is designed to detect whether a real signal appears worth
pursuing, not to estimate production CAPTCHA error rates.

> Phase 2A is designed to detect whether a real signal appears worth pursuing, not to estimate production CAPTCHA error rates.

Synthetic success validates the instrument only. Naive-model separation is
also insufficient: a useful effect must later survive participant and challenge
validation, artifact probes, model-family transfer, JANUS-aware imitation, and
an unseen model.

## Exploratory versus confirmatory evidence

`exp001a_real_signal_pilot` is an exploratory sanity pilot. Its thresholds and
analysis may be inspected and revised, so its results cannot be called
confirmatory. A separate proposed `exp001b_confirmatory` manifest may be
generated only as a human-review template containing unresolved decisions. It
is never frozen automatically. Confirmatory status requires a frozen manifest
before collection and a new experiment version after any change.

## Recruitment and consent assumptions

Participants are knowingly recruited under a consent document reviewed by a
qualified human/legal/ethics owner. The repository supplies a template, not
legal language or approval. A pseudonymous subject ID is created only after the
study introduction; an active consent record is required before any response
is accepted. Recruitment channel, compensation, minimum age, jurisdiction,
sample-size plan, exclusions, and withdrawal communications remain
`NEEDS_DECISION` before real collection.

## Privacy and withdrawal

No name, email, IP address, fingerprint, raw pointer path, biometric, or
cross-site identifier is required. Consent and append-only audit records are
stored separately from response Parquet files. Withdrawal changes consent to
`withdrawn`, immediately blocks new responses, identifies affected raw files,
and writes a tombstone/audit record. Raw records are preserved pending the
human-reviewed retention policy so reproducibility is not silently destroyed;
analysis loaders exclude withdrawn subject IDs and derived outputs are marked
invalid for regeneration.

## Model-provider architecture and data handling

The domain remains provider-neutral. Optional HTTP adapters implement two
independent API families behind an injected transport boundary. Credentials are
read only from named environment variables at execution time and are never
serialized. Each call records deterministic call/run IDs, model/runtime,
provider-reported version when available, prompt and challenge hashes,
condition, decoding parameters, raw and parsed response, parser state, retries,
latency, and explicit failure. Checkpoints are append-only and make restarts
idempotent.

Provider retention/training policies are external and mutable. A researcher
must review them before enabling a target. Public challenge payloads and prompts
may leave the machine during an authorized run; private features and calibration
must not.

## Sample size and stopping

Phase 2A plans for signal sanity, not a 0.1% FPR claim. Planning reports both
precision approximations and the rule-of-three bound. Collection stops on the
manifest's participant/call limits, consent withdrawal, unexpected control
failure, material protocol deviation, provider cost cap, or safety/privacy
incident. There is no optional stopping based on whether results look positive.

## What Phase 2 can and cannot establish

Phase 2A can establish that selected populations under documented conditions
show an exploratory, artifact-audited divergence worth preregistering. It cannot
establish universal AI detection, production FPR, adversarial robustness,
consciousness, biological humanity, accessibility parity, or durable CAPTCHA
security. `PROMISING`, `INCONCLUSIVE`, and `NOT SUPPORTED` are pilot decisions,
not product claims.

## Deferred production infrastructure

Fastify, production iframe/widget, Redis, PostgreSQL tenant services,
attestation/JWKS, billing, multi-region operation, Kafka, ClickHouse,
Kubernetes, production blocking, and cross-site fingerprinting remain deferred.
The bottleneck is scientific validity, not request throughput.
