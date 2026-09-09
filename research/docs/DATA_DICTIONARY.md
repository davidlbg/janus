# Research Data Dictionary

## Phase 2 consent records (`records.jsonl`)

`consent_id` is an opaque consent key; `subject_id` is the pseudonymous
analytical identifier; study/document versions establish what was accepted;
timestamps and `status` record the lifecycle. Consent is separate from responses.

## Phase 2 model checkpoint (`checkpoint.jsonl`)

`ModelCallRecord` contains idempotent run/call IDs, challenge provenance,
condition, sample index and ordering. Metadata preserves provider and model
identifiers, provider-reported version, timestamp, prompt/challenge hashes,
decoding controls, seed, raw/parsed output, parser state, retries, error and
latency. Failures remain records but never become choices.

## Phase 2 derived analysis

Pilot artifacts add consent exclusion counts, dataset/manifest/code hashes,
cross-model transfer, position probes, ablations, challenge heterogeneity and
control status. These are derived fields and add no participant telemetry.

## ChallengeDefinition

| Field | Meaning |
|---|---|
| `challenge_id` | Deterministic opaque ID derived from version, seed and parameters |
| `family` | SEM, VIS, or FREE |
| `generator_version` | Immutable generator grammar version |
| `seed` | Local reconstruction seed; never included in the public export |
| `split` | Independent challenge assignment: discovery, validation, or holdout |
| `public_payload` | Instruction and randomized display options safe for presentation |
| `private_features` | Latent generator annotations, stored separately and never presented |
| `created_at` | Generation timestamp; not part of deterministic stimulus semantics |

## ResponseRecord

| Field | Meaning |
|---|---|
| `study_version` | Research Protocol version |
| `subject_id` | Pseudonymous participant or agent identifier |
| `population_class` | `human`, `ai`, or `adversarial_ai` |
| `model_version` / `model_family` | Versioned artificial cohort; null for humans |
| `condition` | Human collection or M0–M8 model condition |
| `session_id` | Pseudonymous independent interaction session |
| `challenge_*` | Challenge ID, family, and generator version |
| `seed_reference` | One-way reference used for audit, not the raw seed |
| `sequence` | Zero-based order within session |
| `public_option_order` | Option IDs in the exact order presented |
| `response` | Selected public option ID; there is no correctness label |
| `response_latency_bucket` | Quantized client-observed decision latency |
| `revision_count` | Number of selection changes before submit |
| `input_modality` | Coarse keyboard/pointer/touch/unknown modality |
| `timestamp` | UTC collection time |
| `split` | Subject/model split, assigned before analysis |
| `challenge_split` | Independently assigned challenge-instance split |
| `temporal_wave` | Versioned collection wave such as T0/T1 |

## ModelRunMetadata

Captures provider/runtime, exact model identifier, run time, hashes of system,
template, and rendered prompts, decoding settings, supported seed, retries,
parser status, and explicit error state. A provider failure is not a response.

## ExperimentManifest

Defines the hypothesis, analysis tier, generator versions, split policies,
model conditions, metrics, seed, scorer configuration, data kind, and lifecycle
status. `content_hash` is absent in draft and mandatory after freezing.

## Derived artifacts

`analysis.json` is machine-readable and contains session-level metrics, family
divergence, bootstrap confidence intervals, warnings, leakage results, and plot
inputs. `report.md.sha256` protects report integrity but is not an identity or
cryptographic authorship signature.
