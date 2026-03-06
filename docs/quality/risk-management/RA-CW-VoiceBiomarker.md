# Risk Assessment: Voice Biomarker Mental Health Screening

**Document ID:** PMS-RA-CW-001
**Subsystem:** SUB-CW (Clinical Workflow)
**Feature:** SYS-REQ-0014 — Voice Biomarker Mental Health Screening
**Date:** 2026-03-06
**Author:** AI Agent (reviewed by Yuliya Makarenko)
**Standard:** ISO 14971:2019 — Application of risk management to medical devices
**Related QMS:** ISO 13485:2016 Clause 7.1 (Planning of product realization), Clause 7.3.3 (Design and development inputs)

---

## Scope

This risk assessment covers the voice biomarker screening and longitudinal mood tracking feature (SYS-REQ-0014), which decomposes into:

- **SUB-CW-0010** — Voice biomarker screening during encounters
  - SUB-CW-0010-BE (Screening API, Kintsugi engine, audit logging)
  - SUB-CW-0010-WEB (VoiceBiomarkerScreen component with recording controls)
- **SUB-CW-0011** — Longitudinal mood tracking across encounters
  - SUB-CW-0011-BE (Mood trend API)
  - SUB-CW-0011-WEB (MoodTimeline visualization component)

**Architecture references:** ADR-0023 (Kintsugi voice biomarker integration), ADR-0020 (feature flags)

**Governance cross-references:** DC-CW-04 (encounter status constraint), DC-CW-05 (mood alert vs clinical alert), PC-BE-09 (audit catalog extension), PC-WEB-04 (microphone contention), RC-BE-13 (concurrent screening), RC-WEB-03 (recording navigation interrupt)

---

## Risk Acceptability Matrix

| Probability / Severity | 1 (Negligible) | 2 (Minor) | 3 (Moderate) | 4 (Major) | 5 (Catastrophic) |
|---|---|---|---|---|---|
| **5 (Frequent)** | 5 | 10 | 15 | 20 | 25 |
| **4 (Probable)** | 4 | 8 | 12 | 16 | 20 |
| **3 (Occasional)** | 3 | 6 | 9 | 12 | 15 |
| **2 (Remote)** | 2 | 4 | 6 | 8 | 10 |
| **1 (Improbable)** | 1 | 2 | 3 | 4 | 5 |

Risk levels: **1–4 = Acceptable** (green), **5–9 = ALARP** (yellow), **10–25 = Unacceptable** (red)

---

## Risk Register

### Clinical Safety

| Risk ID | Description | Related Req(s) | Severity | Probability | Risk Level | Mitigation | Residual Risk |
|---|---|---|---|---|---|---|---|
| RISK-CW-001 | **False-negative depression screening** — Kintsugi model fails to detect clinically significant depression (71.3% sensitivity = 28.7% miss rate), causing a depressed patient to receive a "normal" screening result. Clinician may not pursue further evaluation based on the negative screen. | SUB-CW-0010, SYS-REQ-0014 | 4 (Major) | 4 (Probable) | **16 (Unacceptable)** | (1) All results displayed with "advisory only — clinical judgment required" disclaimer (SYS-REQ-0014 AC#7). (2) Screening positioned as supplementary to — not replacing — PHQ-9/GAD-7 when administered. (3) ADR-0023 documents 28.7% miss rate transparently to all clinicians. (4) Feature flag allows instant disablement if concerns arise. (5) System never labels a patient as "not depressed" — only risk categories (normal/elevated/high-risk). | S4 × P2 = **8 (ALARP)** |
| RISK-CW-002 | **False-positive depression screening** — Model incorrectly flags a non-depressed patient as elevated/high-risk (73.5% specificity = 26.5% false-positive rate), leading to unnecessary follow-up, patient anxiety, or stigmatization in the medical record. | SUB-CW-0010, SYS-REQ-0014 | 3 (Moderate) | 4 (Probable) | **12 (Unacceptable)** | (1) Results are advisory only — physician makes all clinical decisions. (2) Configurable thresholds allow tuning sensitivity/specificity trade-off (KintsugiSettings). (3) Results labeled with confidence score to indicate model certainty. (4) Screening result does not auto-generate referrals or prescriptions — requires explicit physician action. (5) Mood timeline shows longitudinal context to distinguish transient elevations from persistent patterns. | S3 × P2 = **6 (ALARP)** |
| RISK-CW-003 | **Over-reliance on automated screening** — Clinicians begin relying solely on voice biomarker results and stop conducting standard depression screening (PHQ-9), leading to systemic under-diagnosis across the practice. | SUB-CW-0010, SYS-REQ-0014 | 4 (Major) | 2 (Remote) | **8 (ALARP)** | (1) "Advisory only — clinical judgment required" disclaimer on every result. (2) Clinical documentation does not accept voice biomarker results as standalone diagnostic evidence. (3) Training materials (experiment 35 developer tutorial) emphasize supplementary nature. (4) Feature flag allows disabling if misuse patterns emerge. | S4 × P1 = **4 (Acceptable)** |
| RISK-CW-004 | **Mood trend false alarm** — Score jump >0.2 between consecutive encounters triggers a trend alert, but the change is due to noise (ambient sound, different speaking pace, illness-related voice changes) rather than genuine mood deterioration. Clinician investigates unnecessarily or loses trust in the system. | SUB-CW-0011, SYS-REQ-0014 | 2 (Minor) | 4 (Probable) | **8 (ALARP)** | (1) Mood trend alerts are informational only — do not block encounter completion (DC-CW-05). (2) Trend calculated from last 5 data points, smoothing single-encounter noise. (3) MoodTimeline visualization shows full history for clinical context. (4) Minimum 2 data points required before trend calculation (SUB-CW-0011-BE). | S2 × P3 = **6 (ALARP)** |
| RISK-CW-005 | **Screening on non-English speaker** — Model was validated on English-speaking (US/Canadian) populations only. Using it on non-English speakers produces unreliable results that may be clinically misleading. | SUB-CW-0010, SYS-REQ-0014 | 3 (Moderate) | 3 (Occasional) | **9 (ALARP)** | (1) ADR-0023 documents English-only validation limitation. (2) Consent dialog should note language limitation. (3) Advisory disclaimer on all results. (4) Clinician retains discretion to disregard results for non-English speakers. (5) Future validation for other languages can be added without architecture changes. | S3 × P2 = **6 (ALARP)** |
| RISK-CW-006 | **Screening during encounter with wrong status** — Clinician initiates screening on a scheduled (patient not present), completed, or cancelled encounter, producing clinically meaningless results attached to an inappropriate encounter. | SUB-CW-0010 vs SUB-CW-0007 | 3 (Moderate) | 3 (Occasional) | **9 (ALARP)** | (1) SUB-CW-0010-BE validates encounter status — return 422 if not `in_progress` (DC-CW-04). (2) Web UI only shows screening button on in-progress encounters. (3) Backend enforcement prevents bypass regardless of client behavior. | S3 × P1 = **3 (Acceptable)** |

### Data Integrity

| Risk ID | Description | Related Req(s) | Severity | Probability | Risk Level | Mitigation | Residual Risk |
|---|---|---|---|---|---|---|---|
| RISK-CW-007 | **Raw audio persisted or leaked** — Implementation bug causes raw audio to be written to disk, database, or logs instead of being discarded immediately after feature extraction. HIPAA violation if audio contains speech content. | SUB-CW-0010-BE, SYS-REQ-0014 | 5 (Catastrophic) | 1 (Improbable) | **5 (ALARP)** | (1) SUB-CW-0010-BE explicitly requires raw audio discarded immediately after feature extraction. (2) Audio processed as in-memory buffer only — never written to filesystem or database. (3) Only numerical feature vectors (35 floats) and screening results stored. (4) Code review checklist must verify no audio persistence paths exist. (5) Audit trail records screening events without any audio content. | S5 × P1 = **5 (ALARP)** |
| RISK-CW-008 | **Patient consent not obtained** — Screening performed without documented patient consent, violating SYS-REQ-0014 AC#5 and potentially patient autonomy rights. | SUB-CW-0010-BE, SUB-CW-0010-WEB, SYS-REQ-0014 | 4 (Major) | 2 (Remote) | **8 (ALARP)** | (1) SUB-CW-0010-BE requires consent verification before storing results. (2) SUB-CW-0010-WEB displays consent confirmation dialog before first recording. (3) Backend returns 403 if consent flag not set for patient. (4) Consent status tracked per patient in the database. (5) Audit trail logs consent verification check. | S4 × P1 = **4 (Acceptable)** |
| RISK-CW-009 | **Screening result linked to wrong patient** — Implementation error or API misuse causes a screening result to be associated with a different patient's encounter, creating incorrect clinical records and potential HIPAA violation. | SUB-CW-0010-BE, SUB-CW-0008 | 5 (Catastrophic) | 1 (Improbable) | **5 (ALARP)** | (1) SUB-CW-0008 enforces patient_id FK constraint on encounters at DB level. (2) Screening API derives patient_id from the encounter record — not from client input. (3) Encounter-patient consistency validated server-side (follows DC-PR-07 pattern). (4) Web UI derives encounter_id from URL navigation context. | S5 × P1 = **5 (ALARP)** |
| RISK-CW-010 | **Audit trail missing patient_id hash** — SUB-CW-0010-BE specifies patient_id hashed in audit log, but if hashing is implemented incorrectly (or omitted), cleartext patient_id appears in audit logs for screening events, creating inconsistency with the privacy design. | SUB-CW-0010-BE, SYS-REQ-0003 | 3 (Moderate) | 2 (Remote) | **6 (ALARP)** | (1) PC-BE-09 defines `subject_hash` field for screening audit events — separate from `resource_id`. (2) Audit event catalog extension provides a clear implementation pattern. (3) Unit tests must verify patient_id is never stored in cleartext for screening audit entries. | S3 × P1 = **3 (Acceptable)** |
| RISK-CW-011 | **Duplicate screening per encounter** — Two concurrent submissions for the same patient-encounter create duplicate records, corrupting longitudinal mood trend calculation. | SUB-CW-0010-BE, SUB-CW-0011-BE | 3 (Moderate) | 2 (Remote) | **6 (ALARP)** | (1) Unique constraint on (patient_id, encounter_id) — second request returns 409 (RC-BE-13). (2) Web UI disables submit button after first submission. (3) Mood trend service uses single screening per encounter for clean longitudinal data. | S3 × P1 = **3 (Acceptable)** |

### Availability

| Risk ID | Description | Related Req(s) | Severity | Probability | Risk Level | Mitigation | Residual Risk |
|---|---|---|---|---|---|---|---|
| RISK-CW-012 | **Kintsugi engine unavailable** — The voice biomarker engine fails to load models (corrupt model files, missing dependencies, OOM), blocking all screening across all clients. | SUB-CW-0010-BE | 3 (Moderate) | 2 (Remote) | **6 (ALARP)** | (1) `GET /api/screening/health` endpoint reports engine status — UI can proactively hide screening button when unhealthy. (2) Feature flag `FEATURE_SUB_CW_0008_VOICE_SCREENING` disables screening gracefully. (3) Screening is supplementary — no clinical workflow is blocked by its unavailability. (4) Health check at startup validates model loading. | S3 × P1 = **3 (Acceptable)** |
| RISK-CW-013 | **Insufficient audio duration** — Patient speaks for less than 20 seconds, producing unreliable acoustic features. The system either returns a low-confidence result or rejects the sample. | SUB-CW-0010-BE, SUB-CW-0010-WEB | 2 (Minor) | 3 (Occasional) | **6 (ALARP)** | (1) SUB-CW-0010-BE enforces minimum 20-second audio duration — returns 422 for shorter clips. (2) SUB-CW-0010-WEB shows countdown timer with real-time duration indicator. (3) UI prevents submission until 20-second minimum is reached. | S2 × P1 = **2 (Acceptable)** |
| RISK-CW-014 | **Microphone contention with telehealth** — Voice screening requested during an active telehealth encounter that is already using the browser microphone, causing recording failure or interrupting the telehealth call. | SUB-CW-0010-WEB, SUB-CW-0006 | 3 (Moderate) | 3 (Occasional) | **9 (ALARP)** | (1) SUB-CW-0010-WEB detects active microphone use before requesting access (PC-WEB-04). (2) Warning displayed: "Microphone in use by telehealth — pause call before screening." (3) Screening failure is non-critical — clinician can retry after call. | S3 × P1 = **3 (Acceptable)** |

### Concurrency

| Risk ID | Description | Related Req(s) | Severity | Probability | Risk Level | Mitigation | Residual Risk |
|---|---|---|---|---|---|---|---|
| RISK-CW-015 | **Recording interrupted by page navigation** — Clinician starts recording then navigates away, leaving MediaRecorder running in background (resource leak, audio captured without UI context) or losing the recording silently. | SUB-CW-0010-WEB | 2 (Minor) | 3 (Occasional) | **6 (ALARP)** | (1) Navigation guard shows confirmation dialog during active recording (RC-WEB-03). (2) React useEffect cleanup stops MediaRecorder and releases MediaStream on unmount. (3) Audio buffer discarded on navigation — no background submission. | S2 × P1 = **2 (Acceptable)** |
| RISK-CW-016 | **Mood trend alert during encounter blocks completion** — Mood trend alert (score jump >0.2) is mistakenly treated as a clinical alert by the pre-transition gate (SUB-CW-0005 / DC-CW-03), blocking encounter completion until acknowledged. | SUB-CW-0011 vs SUB-CW-0005 | 3 (Moderate) | 2 (Remote) | **6 (ALARP)** | (1) Mood trend alerts are informational only — explicitly excluded from SUB-CW-0005 pre-transition gate (DC-CW-05). (2) Different alert types: clinical alerts use `alert_type = clinical`, mood alerts use `alert_type = informational`. (3) Pre-transition gate queries only `alert_type = clinical`. | S3 × P1 = **3 (Acceptable)** |
| RISK-CW-017 | **Feature extraction latency under load** — Multiple concurrent screening requests cause librosa/PyTorch feature extraction to consume excessive CPU, degrading response times for other backend endpoints (patient CRUD, encounters, medications). | SUB-CW-0010-BE | 2 (Minor) | 2 (Remote) | **4 (Acceptable)** | (1) CPU-only inference is bounded (ADR-0023: 1-2 GB RAM, no GPU). (2) Feature extraction is I/O-light, CPU-moderate (~2-5 seconds per request). (3) Backend async architecture prevents blocking of other endpoints. (4) If load is a concern, biomarker engine can be extracted to a separate Docker service. | S2 × P1 = **2 (Acceptable)** |

### Regulatory & Privacy

| Risk ID | Description | Related Req(s) | Severity | Probability | Risk Level | Mitigation | Residual Risk |
|---|---|---|---|---|---|---|---|
| RISK-CW-018 | **Regulatory ambiguity — SaMD classification** — FDA may classify voice biomarker screening as a Software as a Medical Device (SaMD), requiring regulatory clearance that has not been obtained. Using the feature without clearance could expose the organization to regulatory enforcement. | SYS-REQ-0014 | 4 (Major) | 2 (Remote) | **8 (ALARP)** | (1) Positioned strictly as clinical decision support, not a diagnostic device (ADR-0023). (2) "Advisory only — clinical judgment required" disclaimer on all interfaces. (3) No automated diagnosis or treatment recommendations — clinician makes all decisions. (4) Feature flag allows instant disablement if regulatory guidance changes. (5) Monitor FDA guidance on voice biomarkers and SaMD classification. | S4 × P1 = **4 (Acceptable)** |
| RISK-CW-019 | **Speech content inadvertently captured** — A bug in the audio processing pipeline processes speech content (via ASR or similar) instead of only acoustic features, violating the privacy-by-design principle. | SUB-CW-0010-BE, SYS-REQ-0014 | 5 (Catastrophic) | 1 (Improbable) | **5 (ALARP)** | (1) Kintsugi models process only MFCCs, pitch, energy, and spectral features — no ASR component exists in the pipeline. (2) librosa feature extraction produces numerical arrays, not text. (3) No speech-to-text dependency in the codebase. (4) Code review must verify no ASR libraries are imported. (5) Only 35-float feature vectors are transmitted and stored. | S5 × P1 = **5 (ALARP)** |
| RISK-CW-020 | **Open-source model supply chain compromise** — Forked Kintsugi model files are tampered with (malicious weights, backdoor in feature extraction), producing intentionally wrong results or exfiltrating data. | SUB-CW-0010-BE | 4 (Major) | 1 (Improbable) | **4 (Acceptable)** | (1) Model files checksummed at deployment — hash verified against known-good baseline. (2) Internal fork with controlled access — not pulling from upstream automatically. (3) Model weights are numerical tensors — limited attack surface for data exfiltration. (4) No outbound network calls from the inference pipeline. | S4 × P1 = **4 (Acceptable)** |

---

## Summary

| Metric | Count |
|---|---|
| **Total risks identified** | **20** |
| Acceptable (1–4) before mitigation | 2 |
| ALARP (5–9) before mitigation | 12 |
| Unacceptable (10–25) before mitigation | 6 |

### After Mitigation (Residual Risk)

| Residual Level | Count | Risk IDs |
|---|---|---|
| **Acceptable (1–4)** | **13** | RISK-CW-003, 006, 008, 010, 011, 012, 013, 014, 015, 016, 017, 018, 020 |
| **ALARP (5–9)** | **7** | RISK-CW-001 (8), 002 (6), 004 (6), 005 (6), 007 (5), 009 (5), 019 (5) |
| **Unacceptable (10–25)** | **0** | — |
| **Residual unacceptable risks** | **0** | Must be 0 before release |

### Residual ALARP Justification

The 7 residual ALARP risks are accepted under the following rationale:

| Risk ID | Residual | Acceptance Rationale |
|---|---|---|
| RISK-CW-001 | 8 | False-negative depression screening is inherent to any AI screening tool with sub-100% sensitivity. The 71.3% sensitivity is published and transparent. The system is positioned as supplementary screening — never as the sole screening method. The "advisory only" disclaimer ensures clinician judgment remains authoritative. Residual risk is comparable to current practice where 50% of depression cases go undetected in primary care without any screening. |
| RISK-CW-002 | 6 | False-positive rate (26.5%) will generate unnecessary follow-ups. However, clinical practice already manages false positives from PHQ-9 screening. The physician retains full decision authority. Longitudinal mood tracking reduces isolated false-positive impact by showing pattern context. |
| RISK-CW-004 | 6 | Noisy trend alerts are expected with any longitudinal tracking system. The informational-only alert design (DC-CW-05) ensures no clinical workflow is disrupted. Clinicians learn to interpret trends in context via the MoodTimeline visualization. |
| RISK-CW-005 | 6 | English-only validation is documented transparently (ADR-0023). Clinician discretion is the primary safeguard for non-English speakers. Future multi-language validation can be added without architectural changes. |
| RISK-CW-007 | 5 | Raw audio persistence is prevented by design — in-memory processing only. Code review and testing provide verification. The improbable probability reflects that this would require an implementation bug in the core feature extraction pipeline. |
| RISK-CW-009 | 5 | Screening-patient mismatch is prevented by deriving patient_id from the encounter record server-side, not from client input. DB FK constraints provide a hard backstop. |
| RISK-CW-019 | 5 | Speech content capture would require adding an ASR dependency that doesn't exist in the design. librosa produces numerical feature arrays only. The probability is improbable because the pipeline has no mechanism to produce text from audio. |

---

## Traceability to Governance Mitigations

The following conflicts from [requirements-governance.md](../processes/requirements-governance.md) serve as mitigations referenced in this risk assessment:

| Governance ID | Status | Description | Risks Mitigated |
|---|---|---|---|
| DC-CW-04 | Open | Encounter status constraint — restrict screening to `in_progress` | RISK-CW-006 |
| DC-CW-05 | Open | Mood alert vs clinical alert — informational only, no completion blocking | RISK-CW-004, RISK-CW-016 |
| PC-BE-09 | Open | Audit catalog extension — `VOICE_SCREENING` action, `subject_hash` field | RISK-CW-010 |
| PC-WEB-04 | Open | Microphone contention — detect and block during telehealth | RISK-CW-014 |
| RC-BE-13 | Open | Concurrent screening — unique constraint (patient_id, encounter_id) | RISK-CW-011 |
| RC-WEB-03 | Open | Recording navigation interrupt — navigation guard + cleanup | RISK-CW-015 |

> **Note:** All 6 governance conflicts are currently **Open** (identified in v1.7). They must be resolved (requirements updated) before implementation proceeds.

---

## Regulatory Mapping

| Regulatory Requirement | Risk IDs | Compliance Status |
|---|---|---|
| HIPAA §164.312(b) — Audit Controls | RISK-CW-010 | Mitigated via SUB-CW-0010-BE audit requirements and PC-BE-09 catalog extension |
| HIPAA §164.312(a)(2)(iv) — Encryption of ePHI | RISK-CW-007, RISK-CW-019 | Mitigated by design: no audio stored, only numerical feature vectors and screening results |
| HIPAA §164.312(a)(1) — Access Controls | RISK-CW-009, RISK-CW-008 | Mitigated via JWT auth (SUB-CW-0001), RBAC (SUB-CW-0002), consent verification |
| HIPAA §164.530(d) — Patient Right to Privacy | RISK-CW-008, RISK-CW-019 | Mitigated via consent requirement (SYS-REQ-0014 AC#5), acoustic-only processing |
| FDA SaMD Guidance (2019) | RISK-CW-018 | Mitigated by CDS positioning — "advisory only," no automated diagnosis |
| ISO 13485 §7.3.3 — Design Inputs (risk) | All | This document fulfills the risk assessment input requirement |
| ISO 13485 §7.3.4 — Design Outputs | All | Mitigations trace to specific requirements, ADRs, and governance conflicts |
| ISO 14971 §4.4 — Risk Analysis | All 20 risks | Severity and probability estimated per risk acceptability matrix |
| ISO 14971 §5 — Risk Evaluation | All 20 risks | Evaluated against acceptability criteria (Acceptable/ALARP/Unacceptable) |
| ISO 14971 §6 — Risk Control | 18 risks ≥ ALARP | Mitigations specified with residual risk re-evaluation |

---

## References

- [SYS-REQ-0014](../../specs/requirements/SYS-REQ.md) — Voice Biomarker Mental Health Screening
- [SUB-CW-0010](../../specs/requirements/domain/SUB-CW.md) — Voice screening during encounters
- [SUB-CW-0011](../../specs/requirements/domain/SUB-CW.md) — Longitudinal mood tracking
- [ADR-0023](../../architecture/0023-kintsugi-voice-biomarker-integration.md) — Kintsugi open-source voice biomarker integration
- [ADR-0020](../../architecture/0020-derm-cds-feature-flags.md) — Feature flag strategy
- [Requirements Governance v1.7](../processes/requirements-governance.md) — Conflicts DC-CW-04/05, PC-BE-09, PC-WEB-04, RC-BE-13, RC-WEB-03
- [Clinical Validation: Annals of Family Medicine (PubMed 39805690)](https://pubmed.ncbi.nlm.nih.gov/39805690/) — 71.3% sensitivity, 73.5% specificity
- [Kintsugi PRD](../../experiments/35-PRD-KintsugiOpenSource-PMS-Integration.md)
- [Kintsugi Developer Tutorial](../../experiments/35-KintsugiOpenSource-Developer-Tutorial.md)
