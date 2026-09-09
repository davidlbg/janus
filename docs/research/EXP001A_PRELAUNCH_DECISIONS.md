# EXP001A — Pre-Launch Decision Sheet

> Authoritative decision sheet for the exploratory real-world pilot.
> Preparing this document does not authorize collection. Every proposal below
> requires an explicit owner decision before it enters the frozen manifest.

Allowed decision states are `PROPOSED`, `APPROVED`, `REJECTED`,
`NEEDS_DECISION`, and `NEEDS_HUMAN_REVIEW`.

## Scientific purpose and boundary

**Status: PROPOSED**

Determine whether any real human–AI conditional response divergence exists
strongly enough to justify a separately preregistered EXP001B. EXP001A does not
test or establish production FPR below 0.1%, adversarial robustness, universal
AI detection, or production CAPTCHA fitness.

## Proposed pilot design

| Item | Status | Proposal | Why sufficient for sanity | Why insufficient for production |
|---|---|---:|---|---|
| Eligible human participants | PROPOSED | 60 | Can reveal large, repeatable effects and gross usability failures | Only about 18 validation participants under a 70/30 split; error-rate intervals remain very wide |
| Sessions per participant | PROPOSED | 1 | Preserves participant as the independent unit | Does not estimate within-person temporal stability |
| Challenges per session | PROPOSED | 9: 3 SEM, 3 VIS, 3 FREE | Covers all families with limited fatigue | Too few observations for reliable individual classification |
| Generated instances per family | PROPOSED | 12; 36 total | Gives seed/instance variation in a small pilot | Does not hold out grammar branches and gives few validation instances |
| Human allocation | PROPOSED | Stable participant hash, approximately 70% discovery / 30% pilot validation | Prevents participant overlap and permits a first replication check | Approximately 42/18 participants is not confirmatory |
| Challenge allocation | PROPOSED | Stable challenge hash, approximately 70% discovery / 30% pilot validation | Tests unseen instances | The validation pool remains small and seed-level only |
| Expected human responses | PROPOSED | 60 × 1 × 9 = 540 completed responses | Roughly 180 responses per family before exclusions | Responses are clustered within 60 people, not 540 independent observations |
| M0 samples | PROPOSED | 1 per challenge/model | Repeating deterministic decoding adds no independent evidence | Does not characterize service nondeterminism |
| M1 samples | PROPOSED | 2 per challenge/model | Provides a minimal stochastic distribution | Too few samples for precise per-challenge probabilities |
| M2 samples | PROPOSED | 2 per challenge/model | Tests prompt-induced randomization cheaply | Does not cover stronger imitation attacks |
| Total model calls | PROPOSED | 36 × 2 × (1 + 2 + 2) = 360 | Materially smaller than the current 1,008-call plan while answering the sanity question | Insufficient for a high-resolution model benchmark |
| Approximate duration | PROPOSED | 6–10 minutes per participant; collection window up to 14 calendar days | Short enough to limit fatigue and expose recruitment feasibility | Does not measure drift or long-term repeatability |

The study runner currently takes the first nine split-eligible challenges rather
than enforcing three per family. **Status: NEEDS_DECISION** — either approve the
balanced 3/3/3 proposal and make that technical correction before launch, or
reject this session design. No unbalanced real session should be launched by
accident.

## Human pilot policy

| Topic | Type | Status | Recommended option | Alternatives / consequence |
|---|---|---|---|---|
| Language | research policy | PROPOSED | Brazilian Portuguese only in this pilot | English/multilingual increases generality but confounds a small cohort |
| Minimum age | legal/research policy | PROPOSED | 18 years | Including minors requires a separate consent/legal design |
| Recruitment source | research policy | PROPOSED | Closed convenience panel recruited explicitly for research, not production visitors | Open links increase duplication and consent-control risk |
| Compensation | business/legal | NEEDS_DECISION | Fixed compensation based on a documented fair local hourly rate, paid for participation rather than outcome | Unpaid participation may bias recruitment; amount and payment process need approval |
| Supported devices | technical recommendation | PROPOSED | Current desktop and mobile browsers after a short compatibility check | Narrowing to desktop improves consistency but reduces applicability |
| Supported modalities | technical/research policy | PROPOSED | Pointer, touch, and keyboard; record only coarse modality | Excluding accessibility methods would narrow the target population |
| Session duration | research policy | PROPOSED | Target 6–10 minutes; allow up to 15 minutes without penalizing slowness | A shorter cap risks excluding normal variance |
| Maximum challenges | research policy | PROPOSED | 9 submitted challenges | More increases fatigue; fewer weakens family coverage |
| Repeat participation | research policy | PROPOSED | One completed session per pseudonymous participant | Repeats break the primary independence assumption |
| Participant split | technical recommendation | PROPOSED | Stable 70/30 participant-level discovery/validation assignment | Row-level splitting is rejected because it leaks participants |
| Withdrawal | legal/privacy review | PROPOSED | Immediate tombstone, block new responses, exclude from analysis, preserve raw record pending reviewed retention | Silent destructive deletion breaks auditability |
| Raw retention | legal/privacy review | NEEDS_HUMAN_REVIEW | 90 days after pilot close, then delete or irreversibly aggregate according to approved policy | Shorter is more private; longer needs necessity and access justification |
| Derived aggregate retention | legal/privacy review | NEEDS_HUMAN_REVIEW | Retain non-identifying aggregates and provenance with the research report | Permanent row-level retention is not proposed |

## Pre-analysis exclusion criteria

**Status: PROPOSED**

Exclude only the affected session/record, with reason and count reported, when:

1. consent was withdrawn;
2. the stored record is corrupt or fails schema/integrity validation;
3. a duplicate submission is attributable to a documented technical retry;
4. a challenge did not render or its response options were unavailable;
5. the participant submitted fewer than six challenges, meaning fewer than two
   planned observations per family;
6. participant or challenge split integrity is violated by a technical defect.

Do not exclude based on answer pattern, classification score, speed, slowness,
outlier status, model-likeness, or whether removal improves a metric.

> **HUMAN ATYPICALITY IS NOT AN EXCLUSION CRITERION.**

## Model recommendation

The following are recommendations, not approved manifest values. Access must be
verified in the owner's accounts before approval.

| Provider | Status | Proposed model / exact ID | Access date | Modality | Reason | Versioning limitation |
|---|---|---|---|---|---|---|
| OpenAI Responses | PROPOSED | GPT-5.4 Mini, `gpt-5.4-mini-2026-03-17` | 2026-09-09 | Text input/output; image input | Contemporary, Responses-compatible, snapshot available, materially cheaper than the flagship | Snapshot can later be deprecated; account access is not verified |
| Anthropic Messages | PROPOSED | Claude Sonnet 4.6, `claude-sonnet-4-6` | 2026-09-09 | Text and image input; text output | Active capable family, independent provider, supports a no-thinking baseline and current stochastic parameters | The documented ID is an alias rather than a dated snapshot; provider behavior may change |

The OpenAI documentation lists Responses and image input for GPT-5.4 Mini,
the dated snapshot, and prices of USD 0.75/M input tokens and USD 4.50/M output
tokens. The Anthropic lifecycle documentation lists Claude Sonnet 4.6 as active;
its migration guidance states USD 3/M input and USD 15/M output tokens and notes
that newer Sonnet 5 rejects non-default temperature/top-p, which makes 4.6 the
less disruptive stochastic-pilot choice as of the access date.

Sources: [OpenAI GPT-5.4 Mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
[Anthropic model lifecycle](https://docs.anthropic.com/en/docs/about-claude/model-deprecations),
[Anthropic migration guidance](https://platform.claude.com/docs/en/about-claude/models/migration-guide).

**Status: NEEDS_DECISION** — `VIS_v1` is rendered graphically for humans but is
currently serialized as SVG markup in model prompts. Models with image support
do not by themselves make these stimuli equivalent. The owner must approve a
representation, and its adapter/audit must pass, before VIS results are treated
as human–model comparisons.

## Model conditions and sampling

**Status: PROPOSED**

- M0 naive: temperature 0 where accepted, top-p 1, one call per challenge.
- M1 stochastic: temperature 1, top-p 1, two calls per challenge.
- M2 explicit randomization: temperature 1, top-p 1, two calls per challenge.
- Reasoning/thinking: disabled where supported so hidden reasoning configuration
  does not vary across providers; exact provider payload must be captured.
- Output: exactly one option ID, with provider failures retained as failures.
- M4/M5: excluded from the primary EXP001A claim.
- Optional M5 probe: **PROPOSED — OPTIONAL / EXPLORATORY / NOT A GATE**; at most
  one call per challenge/model only after primary collection and separate budget
  approval. It cannot replace EXP001B/EXP002 adversarial evaluation.

Provider-specific support for temperature/top-p must be rechecked immediately
before launch. Unsupported parameters must be omitted and the condition marked
non-comparable rather than silently substituted.

The current `model_split_policy` assigns an entire model family to one stable
split. With only two providers, that does not guarantee two valid directional
cross-provider transfer tests and can leave one direction undefined. **Status:
NEEDS_DECISION** — approve one predeclared directional holdout, or revise the
runner so each provider has leakage-safe challenge-level discovery and
validation records. The preflight must remain blocked until the approved design
is represented in the manifest and executable pipeline.

## Model cost plan

**Status: PROPOSED** for assumptions; **Status: NEEDS_DECISION** for authorized
spend.

Planning scenario: 180 calls/provider, at most 1,500 input tokens and 16 output
tokens per call. Actual prompt/image token counts must be measured in a zero-call
local payload/tokenization review before approval.

| Provider | Calls | Input estimate | Output estimate | Dated unit price | Scenario cost |
|---|---:|---:|---:|---:|---:|
| OpenAI | 180 | 270,000 tokens | 2,880 tokens | $0.75/M in, $4.50/M out | $0.22 |
| Anthropic | 180 | 270,000 tokens | 2,880 tokens | $3/M in, $15/M out | $0.85 |
| Total | 360 | 540,000 tokens | 5,760 tokens | 2026-09-09 | about $1.07 |

Formula per provider:
`calls × input_tokens_per_call × input_price/M + calls × output_tokens_per_call × output_price/M`.

Recommended safety margin: 3× the scenario. Recommended hard cap: USD 10.
Both are `PROPOSED`; the approved cap remains `NEEDS_DECISION`. Pricing is
external, dated evidence and must not be permanent application logic.

## Primary endpoints

**Status: PROPOSED**

Primary, calculated per family and combined on pilot validation:

1. Jensen–Shannon divergence;
2. Total Variation distance;
3. mutual information between population and response.

Secondary/exploratory: ROC-AUC, PR-AUC, human FPR with confidence interval, AI
TPR with confidence interval, Brier score, calibration, entropy, latency and
minimal-telemetry ablations.

> **A high ROC-AUC alone cannot make EXP001A successful.**

## Pilot decision rule

**Status: PROPOSED**

The rule must be approved and stored before collection.

- `PROMISING`: required controls and leakage/audit checks pass; validation TV is
  at least 0.10 in at least two families, or at least 0.20 in one family with the
  same directional pattern in discovery and validation; the automated position
  artifact probe is below MI 0.05 and no rendering artifact explains the effect;
  and cross-provider transfer ROC-AUC is at least 0.60 in at least one strictly
  held-out-family direction. Classifier metrics are supporting evidence only.
- `INCONCLUSIVE`: controls pass, but sample loss, wide uncertainty, provider
  coverage, representation differences, family disagreement, or transfer data
  are insufficient to apply the other outcomes defensibly.
- `NOT SUPPORTED`: controls pass, but no family reaches validation TV 0.10; or an
  apparent effect disappears on pilot validation; or all qualifying effects are
  explained by position/rendering/parser artifacts. This is a valid result.
- If a required control, leakage check, or data-integrity check fails, the
  analysis is invalid and the reported pilot decision is `INCONCLUSIVE` until
  the pipeline is understood; it is not converted into a flattering outcome.

These cutoffs are pragmatic large-effect screens for a small pilot, not
production thresholds or claims of statistical significance.

## Stopping rules

**Status: PROPOSED**

Technical stop/pause:

- any consent gate bypass or identity-bearing data capture;
- participant/challenge split contamination;
- failed positive/negative control or challenge audit;
- malformed challenge or unrecoverable response corruption;
- provider parser invalid/error rate above 5% after the first 20 calls;
- stimulus representation mismatch between planned and executed modality.

Financial stop:

- stop before a provider call that would exceed the approved hard cap;
- no automatic retry beyond the configured limit.

Scientific stop:

- stop at 60 eligible completed participants or the approved 14-day window,
  whichever occurs first;
- do not repeatedly inspect outcomes and do not stop because divergence or a
  p-value looks favorable;
- early futility stopping is not proposed for this small pilot.

## Required controls for every real analysis

**Status: PROPOSED**

- positive synthetic pipeline control;
- negative near-identical synthetic control;
- current challenge audit;
- participant/challenge leakage checks.

Failure invalidates the associated real analysis until explained and rerun.

## Privacy minimization review

| Field | Purpose | Required? | Form | Proposed retention | Analysis use | Privacy risk |
|---|---|---:|---|---|---|---|
| pseudonymous subject ID | grouping/split/withdrawal | yes | raw | NEEDS_HUMAN_REVIEW; proposal 90 days | cluster/split | medium |
| consent ID, status, document version, times | prove consent lifecycle | yes | raw, separate | NEEDS_HUMAN_REVIEW | eligibility only | medium |
| response and option order | cognitive endpoint/artifact audit | yes | raw | NEEDS_HUMAN_REVIEW; proposal 90 days | primary | low–medium |
| challenge ID/family/version/seed reference | reconstruction/splits | yes | raw | experiment lifetime | primary/provenance | low |
| sequence | conditional pattern/session integrity | yes | raw | proposal 90 days, aggregate thereafter | primary ablation | low |
| bucketed latency | usability and secondary ablation | yes, coarse | raw | proposal 90 days | secondary | medium |
| revision count | detect correction, secondary ablation | yes, count only | raw | proposal 90 days | secondary | medium |
| coarse input modality | accessibility/stratification | yes | raw | proposal 90 days | secondary | medium |
| completion timestamp | audit/wave attribution | yes | raw | proposal 90 days | operational/temporal | medium |
| model call raw output/error/latency | parser and provider audit | yes for models | raw | provider-policy window, NEEDS_HUMAN_REVIEW | quality control | medium |
| manifest/dataset/code hashes | provenance | yes | derived | retain with report | provenance | low |

No name, email, IP retention, exact location, cross-site identifier, browser or
canvas fingerprint, raw pointer path, biometric, sensor stream, personality
inference, or medical/psychological conclusion is justified for EXP001A.

## Outstanding owner decisions

1. Consent/legal/privacy text — `NEEDS_HUMAN_REVIEW`.
2. Raw and derived retention — `NEEDS_HUMAN_REVIEW`.
3. Recruitment, eligibility and compensation — `NEEDS_DECISION`.
4. Human sample/session design — `NEEDS_DECISION`.
5. Exclusions — `NEEDS_DECISION`.
6. Model IDs/account availability — `NEEDS_DECISION`.
7. VIS stimulus representation and modality comparability — `NEEDS_DECISION`.
8. M0/M1/M2 decoding support and conditions — `NEEDS_DECISION`.
9. Model sampling and split/transfer design — `NEEDS_DECISION`.
10. Budget assumptions and hard cap — `NEEDS_DECISION`.
11. Pilot decision rule — `NEEDS_DECISION`.
12. Technical/financial/scientific stopping rules — `NEEDS_DECISION`.
13. Final manifest review and freeze — `NEEDS_DECISION`.

## Final human approval checklist

- [ ] Consent reviewed
- [ ] Retention approved
- [ ] Recruitment approved
- [ ] Human sample approved
- [ ] Exclusions approved
- [ ] Models approved
- [ ] Model conditions approved
- [ ] Sampling approved
- [ ] Budget approved
- [ ] Decision rule approved
- [ ] Stopping rules approved
- [ ] Challenge audit passing
- [ ] Controls passing
- [ ] Manifest reviewed
- [ ] Manifest frozen

No box is checked because the repository contains no explicit owner approval.
