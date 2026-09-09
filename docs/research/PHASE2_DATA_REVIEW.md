# Phase 2 data review

> Operational draft requiring privacy/legal/ethics review before real
> participant or provider collection.

The authoritative EXP001A field-by-field disposition and retention statuses are
in [EXP001A_PRELAUNCH_DECISIONS.md](EXP001A_PRELAUNCH_DECISIONS.md#data-and-privacy-review).
This general Phase 2 table remains a design inventory, not launch approval.

| Field | Purpose | Sensitivity | Primary analysis | Exported | Retention recommendation |
|---|---|---:|---:|---:|---|
| pseudonymous subject ID | grouping, split, withdrawal | medium | yes | controlled | policy window |
| consent ID/status/version/times | lawful research operation | medium | no | no | policy/audit window |
| response and public option order | cognitive distribution | low-medium | yes | aggregate preferred | study policy |
| challenge/grammar/seed reference | reproducibility | low | yes | controlled | experiment lifetime |
| sequence | conditional analysis | low | yes | aggregate | study policy |
| bucketed latency/completion time | friction/ablation | medium | secondary | aggregate | short/derived |
| revision count | correction behavior | medium | secondary | aggregate | short/derived |
| coarse input modality | accessibility/generalization | medium | stratification | aggregate | study policy |
| model/provider/version/condition | cohort provenance | low | yes | report | experiment lifetime |
| prompt/challenge hashes | reproducibility | low | provenance | report | experiment lifetime |
| rendered/raw model output | parser/failure audit | medium | controlled | no by default | provider policy window |
| provider latency/retries/errors | quality control | low | secondary | aggregate | operational window |
| dataset/manifest/code hashes | provenance | low | yes | report | permanent with report |

No IP address, contact identity, browser fingerprint, canvas fingerprint, raw
pointer trace, biometric, invasive sensor, or cross-site identifier is collected.

## Separation and access

Consent/audit records are append-only JSONL outside analytical Parquet files.
Raw participant collections are per opaque subject directory. Provider
credentials remain environment-only. Public payloads may be sent to authorized
providers; private generator features and calibration do not leave the research
boundary.

## Withdrawal behavior

Withdrawal immediately blocks collection. The system records affected raw
paths, writes an immutable tombstone and invalidates derived artifacts. Raw
records are not silently destroyed: final deletion, retention, or anonymized
preservation follows the reviewed policy. Analytical loaders exclude withdrawn
IDs before regeneration.

No additional telemetry field may enter Phase 2 until this table is updated and
reviewed.
