# EXP001A sample-size note

> Status: **PROPOSED**. This is planning guidance, not approval or a formal
> confirmatory power analysis.

## Pilot sample

The proposed EXP001A pilot uses 60 independent human participants, one session
per person, and nine responses per session. About 42 participants fall into
discovery and 18 into pilot validation under the existing 70/30 stable-hash
policy. This can reveal a large multi-family divergence, replication failure,
artifact, usability problem, or lack of cross-provider transfer.

It cannot precisely estimate small effects. The 540 response rows remain
clustered within 60 people and must never be described as 540 independent human
observations.

## Confirmatory sample

A future EXP001B sample must be calculated from an approved estimand, effect
threshold, human FPR target, expected AI TPR, cluster structure, attrition,
exclusions, model-family holdout and multiplicity plan. It requires new humans,
new challenge instances and a frozen manifest. EXP001A effect estimates may
inform that calculation but cannot confirm the effect that selected them.

## Production FPR validation

If zero failures are observed in `n` independent human sessions, the rough 95%
upper diagnostic is:

$$
p_{upper}\approx\frac{3}{n}
$$

With all 60 pilot humans, zero observed false positives would still imply an
upper bound near 5%. With only about 18 pilot-validation humans, it is near
16.7%. Approximately 3,000 independent zero-failure sessions are needed merely
for a rough 0.1% upper bound, before subgroup parity, dependence, drift and
accessibility are considered.

Therefore EXP001A cannot establish production-grade human FPR. Its job is only
to decide whether deeper, preregistered research is justified.

## Model sample arithmetic

Proposed challenge pool: 12 instances × 3 families = 36 instances.

- M0: 36 × 2 providers × 1 deterministic sample = 72 calls.
- M1: 36 × 2 providers × 2 samples = 144 calls.
- M2: 36 × 2 providers × 2 samples = 144 calls.
- Total: 360 calls.

The existing 1,008-call dry run uses 24 instances per family and three repeated
samples for M1/M2. The smaller plan is preferable for the sanity gate because
it retains both providers, all three families and all primary conditions while
spending fewer EXP001B-scale resources.

## Decision required

Participant count, session length, challenge pool, attrition handling and model
sampling remain `NEEDS_DECISION`. After approval they must be copied into the
manifest and frozen before collection.
