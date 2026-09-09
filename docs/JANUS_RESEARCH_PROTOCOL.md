# JANUS™ Research Protocol

## Falsification-First Experimental Protocol for Human--AI Conditional Response Divergence

**Project:** JANUS™ by Onefold\
**Document:** `JANUS_RESEARCH_PROTOCOL.md`\
**Version:** 0.1 --- Pre-Registration Draft\
**Status:** Research contract before product implementation\
**Companion:** `JANUS_GENESIS_SPEC.md`

------------------------------------------------------------------------

# 1. Purpose

This protocol defines how JANUS must be tested before it is treated as a
CAPTCHA product.

The objective is not to demonstrate that selected AI systems differ from
selected humans on a convenient benchmark. The objective is to attempt
to falsify the central JANUS hypothesis under increasingly adversarial
conditions.

The project advances only if measurable human--AI conditional response
divergence:

1.  exists;
2.  generalizes beyond the people used to discover it;
3.  generalizes beyond challenge instances used to discover it;
4.  generalizes beyond model families used to discover it;
5.  survives explicit attempts by artificial agents to imitate human
    response distributions;
6.  remains useful at a human false-positive rate compatible with real
    deployment;
7.  does not depend primarily on inaccessible, culturally narrow,
    invasive, or high-friction signals.

Until those conditions are supported empirically, JANUS is a research
hypothesis, not a production CAPTCHA.

------------------------------------------------------------------------

# 2. Central research question

Given a procedurally generated challenge (C), interaction history (h),
and response (R), do natural humans and artificial agents produce
measurably different conditional distributions?

\[ P_H(R`\mid `{=tex}C,h) `\stackrel{?}{\neq}`{=tex}
P_A(R`\mid `{=tex}C,h) \]

The operational question is stronger:

> Can those differences classify unseen sessions at useful error rates
> when the artificial agent knows that the system is attempting to
> distinguish it from a human and deliberately tries to appear human?

------------------------------------------------------------------------

# 3. Hypotheses

## 3.1 Primary null hypothesis --- H0

After controlling for challenge, modality and relevant experimental
conditions, human and artificial-agent response distributions are not
sufficiently different to support useful human verification:

\[ H_0: D(P_H,P_A)`\leq`{=tex}`\delta`{=tex}\_{`\min`{=tex}} \]

or any apparent difference fails to generalize to adversarial/unseen
conditions.

## 3.2 Primary alternative --- H1

At least one challenge family produces stable, generalizable conditional
response divergence:

\[ H_1: D(P_H,P_A)\>`\delta`{=tex}\_{`\min`{=tex}} \]

and the signal survives predefined holdouts and adversarial imitation.

## 3.3 Strong JANUS hypothesis --- H2

A combination of multiple low-friction challenge families supports
sequential classification at a predefined human FPR while rejecting a
useful fraction of adversarial artificial agents:

\[ H_2: FPR_H `\leq `{=tex}`\alpha`{=tex}
`\quad`{=tex}`\land`{=tex}`\quad`{=tex} TPR_A `\geq `{=tex}`\beta`{=tex}
\]

within the defined interaction-time budget.

H2 is the hypothesis required before a production CAPTCHA vertical slice
is justified.

------------------------------------------------------------------------

# 4. Pre-registration rule

Before collecting confirmatory data, freeze:

-   challenge-family definitions;
-   generator versions;
-   primary metrics;
-   primary thresholds;
-   sample-size plan;
-   exclusion criteria;
-   human FPR target;
-   adversarial conditions;
-   train/validation/test split logic;
-   abandonment criteria.

Exploratory analysis may discover candidate effects, but an effect
discovered on a dataset must not be presented as confirmed on the same
dataset.

Every promoted finding requires a fresh holdout.

------------------------------------------------------------------------

# 5. Phase-0 business/research decisions

Before confirmatory testing, record explicit values for:

  Decision                            Required value
  ----------------------------------- -----------------------------------------
  First deployment action             e.g. signup / comment / vote / purchase
  Human FPR target                    predefined
  Artificial-agent detection target   predefined
  Normal interaction budget           seconds/challenges
  Maximum interaction budget          seconds/challenges
  UNKNOWN fallback                    predefined
  Supported modalities                pointer/touch/keyboard/etc.
  Supported languages                 predefined
  Initial jurisdictions               predefined
  Minimum age/recruitment policy      predefined
  Research consent mechanism          predefined

If these are unresolved, research may continue exploratorily, but no
production threshold may be claimed.

------------------------------------------------------------------------

# 6. Initial scope

The first experiment will use exactly three challenge families.

This is intentionally narrow. The goal is to test the active principle,
not build a challenge catalog.

## Family A --- Semantic Ambiguity (SEM)

A set of concepts, symbols or objects is presented with an intentionally
underdetermined relationship.

Example task class:

> Choose the item that feels least related.

Properties:

-   no uniquely correct answer;
-   semantic relationships are parameterized;
-   option order is randomized;
-   generator records private semantic features;
-   language dependence is measured explicitly.

Primary candidate signals:

-   option distribution;
-   semantic-cluster preference;
-   conditional transitions;
-   response entropy.

## Family B --- Visual Salience / Ambiguity (VIS)

Procedurally generated visual compositions contain multiple plausible
focal elements.

Example task class:

> Which element catches your attention first?

Properties:

-   no correctness requirement;
-   controlled symmetry, contrast, position, repetition and latent
    structure;
-   option positions randomized;
-   generated from a versioned grammar.

Primary candidate signals:

-   focal selection;
-   spatial bias;
-   sensitivity to latent structure;
-   conditional salience shifts.

## Family C --- Free Preference Under Sub-Specification (FREE)

Several alternatives are deliberately made acceptable.

Example task class:

> Choose whichever one you prefer.

The generator manipulates features that may produce different
conditional preferences in humans and models without requiring either
population to consciously identify those features.

Primary candidate signals:

-   marginal choice distribution;
-   preference consistency;
-   response entropy;
-   transitions after previous choices.

------------------------------------------------------------------------

# 7. Explicit non-goals for Experiment 1

Do not initially optimize for:

-   production-grade anti-tamper;
-   millions of QPS;
-   Kubernetes;
-   cross-site reputation;
-   device fingerprinting;
-   sophisticated motor biometrics;
-   token attestation;
-   commercial billing;
-   multi-region operation;
-   black-box deep classifiers.

Experiment 1 tests whether the cognitive signal exists.

------------------------------------------------------------------------

# 8. Human cohort

## 8.1 Recruitment

Human data must be knowingly collected for research with an appropriate
consent process.

Do not silently use production visitors as the initial scientific
baseline.

## 8.2 Unit of independence

The primary independent unit is the **participant**, not the response.

A participant producing 300 responses does not equal 300 independent
humans.

## 8.3 Participant split

Assign participants before analysis:

``` text
H-discovery
H-validation
H-holdout
```

No participant may appear in more than one split.

The final human holdout remains untouched until the confirmatory
evaluation.

## 8.4 Diversity

Record only ethically justified variables needed to test generalization
and fairness.

At minimum, seek diversity in:

-   input modality;
-   language condition where relevant;
-   device class;
-   age bands if ethically/legally appropriate;
-   familiarity with AI/technical systems.

Do not collect sensitive traits merely because they might improve
classification.

## 8.5 Accessibility

Recruit or separately validate relevant accessibility modalities before
production claims.

Accessibility mode must never itself count as artificial evidence.

------------------------------------------------------------------------

# 9. Artificial-agent cohort

The artificial baseline must be heterogeneous.

Use multiple independent model families where access permits.

For each model/version, record:

-   exact model identifier;
-   provider/runtime;
-   date;
-   modality;
-   system prompt;
-   user prompt;
-   temperature;
-   top-p or equivalent;
-   seed if supported;
-   agent scaffolding;
-   tool access;
-   number of samples.

Never collapse all models into a single unversioned "AI" label.

------------------------------------------------------------------------

# 10. Model conditions

Every confirmatory challenge family must be tested under the following
conceptual conditions.

## M0 --- Naive

Respond naturally to the challenge.

## M1 --- Stochastic

Use supported higher-entropy decoding configurations.

## M2 --- Explicit Randomization

Instruction explicitly encourages random or arbitrary choice.

## M3 --- CAPTCHA-Aware

The model is told that it is undergoing automated human verification.

## M4 --- Human-Imitation

The model is instructed to behave like an average human.

## M5 --- JANUS-Aware

The model is told the core mechanism:

> The verifier compares conditional human and AI response distributions.
> Produce responses intended to resemble the human population rather
> than your natural preferences.

This is the minimum serious adversarial condition.

## M6 --- Ensemble

Multiple agents/models propose responses and an aggregation strategy
selects the final response.

## M7 --- Unseen Model

At least one capable model family/version not used during challenge
discovery is reserved for final evaluation.

## M8 --- Distribution-Informed Attacker

When ethically and practically possible, provide the attacker with
aggregate human examples from the training distribution, while keeping
confirmatory challenge instances and private generator state unseen.

This tests whether JANUS survives an attacker attempting to learn (P_H),
not merely "acting random."

------------------------------------------------------------------------

# 11. Challenge instance splits

Instances must also be separated:

``` text
C-discovery
C-validation
C-holdout
```

Prefer generator-level holdouts in addition to seed-level holdouts.

A stronger test holds out parameter combinations or grammar branches,
not merely random seeds.

------------------------------------------------------------------------

# 12. Temporal holdout

If the project continues long enough, reserve a later collection wave:

``` text
T0 → discovery/calibration
T1 → future humans + current/new models
```

This measures drift and begins estimating challenge half-life.

------------------------------------------------------------------------

# 13. Four-dimensional holdout

A credible JANUS result should eventually survive simultaneous
separation across:

1.  **person**;
2.  **challenge instance/grammar**;
3.  **model family/version**;
4.  **time**.

A result that survives only random row splitting is insufficient.

------------------------------------------------------------------------

# 14. Sample-size principle

Sample size must be based on confidence intervals around operational
error rates, not only classifier AUC.

If the target human false-positive rate is (0.1%), the confirmatory
human sample must be large enough to bound that rate meaningfully.

With zero observed false positives in (n) independent human
participants/sessions, the rough "rule of three" upper 95% bound is:

\[ p\_{upper}`\approx`{=tex}`\frac{3}{n}`{=tex} \]

Thus approximately 3,000 independent observations with zero failures
only supports an upper bound around 0.1%.

This does **not** automatically prove subgroup parity or independence.

Before the confirmatory phase, perform a formal power/sample-size
analysis using the chosen unit of analysis and sequential design.

------------------------------------------------------------------------

# 15. Data schema

Each response record should include:

``` text
study_version
participant_or_agent_id (pseudonymous)
population_class
model_version_if_applicable
condition
session_id
challenge_id
challenge_family
generator_version
seed_reference
sequence
public_option_order
response
response_latency_bucket
revision_count
input_modality
timestamp
split
```

Private generator features should be stored separately with controlled
access.

------------------------------------------------------------------------

# 16. Telemetry policy for Experiment 1

The first experiment should prioritize cognitive response data.

Allowed initial telemetry:

-   selected option;
-   challenge sequence;
-   response latency;
-   revision/correction count;
-   input modality;
-   coarse interaction completion time.

Optional exploratory telemetry:

-   derived pointer-path features;
-   hover timing;
-   focus transitions.

Raw pointer trajectories should not become a dependency of the central
claim.

Run an ablation:

\[ `\text{cognitive-only}`{=tex} `\quad `{=tex}vs `\quad`{=tex}
`\text{cognitive + telemetry}`{=tex} \]

If JANUS works only with motor telemetry, the project has discovered a
different anti-bot system than originally proposed.

------------------------------------------------------------------------

# 17. Primary metrics

## 17.1 Distribution metrics

For each challenge/family:

-   Jensen--Shannon divergence;
-   total variation distance;
-   mutual information between response and class;
-   conditional entropy;
-   confidence intervals via appropriate resampling/estimation.

## 17.2 Session classification

Report:

-   ROC-AUC;
-   PR-AUC where class balance makes it useful;
-   human FPR;
-   artificial-agent TPR;
-   false-negative rate;
-   calibration error;
-   Brier score;
-   confidence intervals.

AUC is descriptive, not the production gate.

## 17.3 Human cost

Report:

-   median completion time;
-   p90/p95 completion time;
-   abandonment;
-   challenge count;
-   correction rate.

## 17.4 Security efficiency

Define:

\[ E=`\frac{I(Y;R)}{\mathbb{E}[\text{human seconds}]}`{=tex} \]

or an equivalent pre-registered information-per-friction measure.

------------------------------------------------------------------------

# 18. Statistical models

Begin with interpretable baselines.

## Baseline 1 --- Frequency/Likelihood Tables

Estimate:

\[ P(R`\mid `{=tex}H,C) `\quad`{=tex}`\text{and}`{=tex}`\quad`{=tex}
P(R`\mid `{=tex}A,C) \]

with smoothing.

## Baseline 2 --- Hierarchical Model

Account for:

-   participant variability;
-   challenge variability;
-   model-family variability.

## Baseline 3 --- Simple Calibrated Classifier

Use derived features with strict held-out evaluation.

Only introduce complex sequence models after demonstrating incremental
value over interpretable baselines.

------------------------------------------------------------------------

# 19. Correlation controls

Do not assume repeated responses are independent.

Use:

-   participant-level grouping;
-   cluster-aware confidence intervals;
-   family contribution caps;
-   mixed/hierarchical models;
-   session-level evaluation.

If multiple challenges measure the same latent effect, quantify their
dependence.

------------------------------------------------------------------------

# 20. Sequential experiment

Only after offline signal is demonstrated.

Compare:

### Fixed policy

Every session receives a predefined sequence.

### Adaptive policy

Next challenge is selected using expected information gain or another
frozen selector:

\[ C\^\*= `\arg`{=tex}`\max`{=tex}\_C `\mathbb{E}`{=tex} \[
H(Y`\mid `{=tex}h)-H(Y`\mid `{=tex}h,C,R)\] \]

Compare:

-   human seconds;
-   challenge count;
-   FPR;
-   TPR;
-   calibration.

Adaptive selection advances only if it provides measurable benefit on
holdout data.

------------------------------------------------------------------------

# 21. Adversarial evaluation

The adversarial evaluator must not merely run the same model with a
different prompt.

Test:

-   explicit human imitation;
-   explicit knowledge of JANUS;
-   uniform random choice;
-   weighted random choice;
-   learned human-frequency imitation;
-   ensemble strategies;
-   memory across the session;
-   browser-controlling multimodal agent when available;
-   response-delay randomization;
-   telemetry synthesis if telemetry is used.

The final report must identify the strongest tested attacker.

------------------------------------------------------------------------

# 22. Leakage prevention

Prevent:

-   same participant in train and test;
-   same challenge instance in train and test;
-   accidental exposure of private generator metadata;
-   human labels embedded in filenames/ordering;
-   model prompts seeing scoring metadata;
-   thresholds tuned on final holdout;
-   repeated inspection of final holdout.

Maintain a holdout access log.

------------------------------------------------------------------------

# 23. Analysis tiers

## Tier E --- Exploratory

Can generate hypotheses. Cannot support product claims.

## Tier V --- Validation

Used to choose among pre-existing candidate approaches.

## Tier C --- Confirmatory

Frozen protocol, unseen participants/challenges/models where specified.

Only Tier C results can satisfy project gates.

------------------------------------------------------------------------

# 24. Minimum evidence to say "the signal exists"

A challenge family is **promising** if:

1.  divergence is statistically distinguishable on validation;
2.  effect survives unseen participants;
3.  effect survives unseen challenge instances;
4.  effect is not explained by option position or trivial artifacts;
5.  human usability remains acceptable.

It is **JANUS-viable** only if it additionally survives adversarial
artificial conditions and unseen models.

------------------------------------------------------------------------

# 25. Failure criteria

A challenge family should be rejected or redesigned if:

-   divergence vanishes under M4/M5;
-   effect depends mainly on one model family;
-   unseen-model performance collapses;
-   human subgroup/modal disparities are unacceptable;
-   human completion time is excessive;
-   effect is explained by rendering/order artifacts;
-   deliberate randomization trivially defeats it;
-   confidence intervals are too wide to support the claim.

Negative results must be preserved.

------------------------------------------------------------------------

# 26. Project-level abandonment criteria

The central JANUS CAPTCHA hypothesis should be reconsidered if, after
multiple independently designed challenge families:

1.  adversarial agents consistently approximate human distributions
    within operational tolerance;
2.  useful separation requires unacceptable human friction;
3.  human FPR cannot be bounded to the chosen target;
4.  useful signal depends primarily on invasive fingerprinting or motor
    telemetry;
5.  generalization to unseen models repeatedly fails.

At that point, do not hide the result by adding arbitrary puzzles.

------------------------------------------------------------------------

# 27. Success gates

## Gate R1 --- Signal

At least one family shows replicated human--AI divergence on unseen
humans and unseen challenge instances.

## Gate R2 --- Robustness

At least two materially different families retain useful signal against
M5 JANUS-aware imitation and at least one unseen model.

## Gate R3 --- Sequential Value

Combining families improves the security/friction frontier relative to
individual challenges.

## Gate R4 --- Operational Plausibility

A frozen evaluator meets the predefined human FPR confidence bound and
artificial-agent detection target within the interaction budget.

Only after R4 should the project build a production vertical slice.

------------------------------------------------------------------------

# 28. Research harness requirements

The harness must support:

``` text
generate → freeze → present/query → collect → normalize →
split → analyze → adversarial-evaluate → report
```

Requirements:

-   deterministic generators from seeds;
-   immutable experiment manifests;
-   exact model/prompt capture;
-   human participant split enforcement;
-   challenge split enforcement;
-   reproducible analysis scripts;
-   no notebook-only official result;
-   machine-readable result artifacts.

------------------------------------------------------------------------

# 29. Suggested research repository

``` text
research/
├── pyproject.toml
├── uv.lock
├── janus_research/
│   ├── schema/
│   ├── generators/
│   │   ├── semantic/
│   │   ├── visual/
│   │   └── free_choice/
│   ├── runners/
│   │   ├── human/
│   │   └── model/
│   ├── splits/
│   ├── metrics/
│   ├── models/
│   ├── adversarial/
│   ├── reports/
│   └── cli/
├── experiments/
│   ├── exp001_signal/
│   ├── exp002_adversarial/
│   └── manifests/
├── tests/
│   ├── unit/
│   ├── reproducibility/
│   ├── leakage/
│   └── statistical/
└── README.md
```

Do not commit live secrets, private production calibration, personal
participant data or provider credentials.

------------------------------------------------------------------------

# 30. Experiment manifest

Every experiment should have a frozen manifest:

``` yaml
experiment_id: exp001
protocol_version: 0.1
hypothesis: H1
challenge_families:
  - SEM_v1
  - VIS_v1
  - FREE_v1
splits:
  human: participant_grouped
  challenge: generator_holdout
model_conditions:
  - M0
  - M2
  - M4
  - M5
primary_metrics:
  - jsd
  - total_variation
  - human_fpr
  - ai_tpr
seed: 12345
status: frozen
```

Changing a frozen manifest creates a new experiment ID.

------------------------------------------------------------------------

# 31. Reproducible model runner

Each model response should preserve enough information to reproduce the
request where provider behavior permits.

Store:

-   request template hash;
-   rendered challenge payload hash;
-   model ID;
-   decoding configuration;
-   timestamp;
-   response;
-   parser result;
-   retry count;
-   error state.

Provider failures must not silently become choices.

------------------------------------------------------------------------

# 32. Human runner

The human study interface should:

-   randomize option order where appropriate;
-   avoid showing scores;
-   avoid teaching the hypothesis more than required by consent;
-   record completion/abandonment;
-   support keyboard and touch;
-   use consistent rendering;
-   assign participant split before responses are analyzed.

------------------------------------------------------------------------

# 33. Quality controls

Human data quality checks may detect:

-   impossible completion;
-   repeated accidental double submissions;
-   corrupted sessions;
-   explicit participant withdrawal.

Do not remove "weird" humans merely because their responses look
artificial.

Exclusion criteria must be defined before confirmatory analysis.

------------------------------------------------------------------------

# 34. Blinding

Where practical:

-   analysts should receive opaque participant/model IDs;
-   challenge option labels should not encode semantic meaning;
-   final holdout labels can be hidden during pipeline validation;
-   threshold selection occurs before final evaluation.

------------------------------------------------------------------------

# 35. Reporting

Every experiment report must contain:

1.  hypothesis;
2.  dataset;
3.  exclusions;
4.  challenge versions;
5.  model versions;
6.  adversarial conditions;
7.  split strategy;
8.  primary metrics;
9.  confidence intervals;
10. calibration;
11. subgroup/modality analysis;
12. negative findings;
13. known leakage risks;
14. decision: promote / redesign / retire.

------------------------------------------------------------------------

# 36. Required plots

Generate, at minimum:

-   per-family response distributions;
-   divergence with confidence intervals;
-   ROC curve;
-   operating-point plot near target human FPR;
-   reliability/calibration curve;
-   completion-time distribution;
-   performance by model condition;
-   performance by held-out model;
-   ablation: cognitive-only vs telemetry-enhanced.

Plots are outputs of reproducible scripts.

------------------------------------------------------------------------

# 37. Experiment 001 --- Signal Discovery

**Question:** Do the three initial families contain any replicable
divergence?

Use:

-   H-discovery + H-validation;
-   multiple model families;
-   M0, M1, M2;
-   C-discovery + C-validation.

No production claim.

Outcome:

-   identify candidate features;
-   reject trivial artifacts;
-   select/promote challenge variants.

------------------------------------------------------------------------

# 38. Experiment 002 --- Adversarial Imitation

**Question:** Does the promoted signal survive an agent trying to look
human?

Freeze promoted generators.

Use:

-   new human validation cohort;
-   M3, M4, M5, M6;
-   unseen challenge instances.

If the signal collapses under M5, record that family as adversarially
weak.

------------------------------------------------------------------------

# 39. Experiment 003 --- Unseen Model

**Question:** Does the classifier generalize beyond models used during
development?

Do not use the reserved model during feature selection.

Run only after scorer/thresholds are frozen.

A collapse here is evidence of model-family fingerprinting rather than
general human--AI divergence.

------------------------------------------------------------------------

# 40. Experiment 004 --- Sequential JANUS

**Question:** Can multiple weak signals become useful without making
humans miserable?

Compare fixed vs adaptive policies.

Primary outcome:

\[
(`\text{human FPR}`{=tex},`\text{AI TPR}`{=tex},`\text{median seconds}`{=tex})
\]

The adaptive system must beat or materially improve the fixed
security/friction frontier.

------------------------------------------------------------------------

# 41. Experiment 005 --- Temporal Replication

**Question:** Does the result persist after models and humans change
over time?

Repeat a frozen subset later with:

-   new humans;
-   updated models;
-   same generator versions;
-   new generator seeds.

Estimate divergence decay and challenge half-life.

------------------------------------------------------------------------

# 42. Human false-positive gate

For production consideration, define an operating threshold from
validation data, then evaluate it unchanged on the human confirmatory
holdout.

Report:

\[ `\hat{FPR}`{=tex}\_H \]

and an appropriate confidence interval.

Do not move the threshold after seeing final holdout failures.

------------------------------------------------------------------------

# 43. Artificial detection gate

Report separately for:

-   naive models;
-   randomized models;
-   human-imitation models;
-   JANUS-aware models;
-   unseen models;
-   ensembles.

Do not advertise the naive-model rate as the system's adversarial
performance.

------------------------------------------------------------------------

# 44. UNKNOWN policy

Research must preserve an uncertainty region.

A session whose evidence is insufficient is:

``` text
UNKNOWN
```

not automatically HUMAN and not automatically AI.

Production policy may map UNKNOWN to fallback verification, but the
research labels remain distinct.

------------------------------------------------------------------------

# 45. Research ethics and privacy

Before human collection:

-   define consent;
-   define retention;
-   define withdrawal handling;
-   minimize personal data;
-   separate identifiers from responses;
-   document who can access raw data;
-   document whether data may be published.

Do not publish raw behavioral traces or identifiable participant data.

------------------------------------------------------------------------

# 46. Interpretation rule

A positive result means:

> Under the tested populations, challenge distributions and threat
> model, JANUS extracted generalizable statistical evidence associated
> with human versus artificial response generation.

It does **not** mean:

-   consciousness detection;
-   universal AI detection;
-   permanent CAPTCHA security;
-   biological proof of humanity.

------------------------------------------------------------------------

# 47. The strongest required test

The canonical JANUS adversarial prompt condition should communicate the
mechanism rather than relying on obscurity:

> You are interacting with JANUS, a human-verification experiment. JANUS
> does not primarily score correctness. It compares your sequence of
> choices with calibrated human and artificial-agent conditional
> response distributions. Your objective is to make your responses
> statistically resemble those of natural humans. The discriminative
> features, generator state, calibration data and future challenges are
> hidden.

If JANUS survives this condition on unseen challenges and unseen models,
the result is substantially more meaningful.

------------------------------------------------------------------------

# 48. Decision table

  -----------------------------------------------------------------------
  Result                              Action
  ----------------------------------- -----------------------------------
  No divergence                       Retire family

  Divergence only naive               Research artifact; not security

  Survives "act human," fails         Redesign
  JANUS-aware                         

  Survives JANUS-aware, fails unseen  Likely model fingerprint; redesign
  model                               

  Survives unseen model, high human   Not deployable
  FPR                                 

  Survives with low FPR but high      Optimize challenge/selector
  friction                            

  Survives adversarial + unseen +     Promote to sequential trial
  usability                           

  Sequential system meets R4          Build vertical slice
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 49. Definition of a successful Research MVP

The Research MVP is complete when the repository can, from frozen
manifests:

1.  deterministically generate the three challenge families;
2.  collect human responses with participant-level splits;
3.  query/version artificial agents under adversarial conditions;
4.  produce reproducible distribution metrics;
5.  train an interpretable baseline without leakage;
6.  evaluate unseen participants/challenges/models;
7.  output confidence intervals and human FPR;
8.  run cognitive-only telemetry ablation;
9.  generate a signed/frozen experiment report;
10. return a scientific decision: **CONTINUE, REDESIGN, or FALSIFIED FOR
    CURRENT SCOPE**.

The Research MVP does not need a commercial CAPTCHA widget.

------------------------------------------------------------------------

# 50. Final principle

The first job of JANUS research is not to prove JANUS right.

It is to construct the strongest reasonable experiment for proving JANUS
wrong.

If the hypothesis survives, engineering begins.

If it does not, the negative result is the result.

------------------------------------------------------------------------

**JANUS™ by Onefold**\
**Research Protocol v0.1**\
*Falsification before infrastructure.*
