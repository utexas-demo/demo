# ADR-0023: Kintsugi Open-Source Voice Biomarker Integration

**Date:** 2026-03-06
**Status:** Accepted
**Deciders:** Development Team

---

## Context

The US Preventive Services Task Force recommends universal depression screening in primary care, but PHQ-9 questionnaires are time-consuming (5-10 minutes per patient), subject to self-report bias, and frequently skipped during busy clinical encounters. An estimated 50% of depression cases go undetected in primary care.

Kintsugi Health developed AI models that detect signs of clinical depression and anxiety from 20 seconds of free-form speech by analyzing acoustic features (pitch, intonation, tone, pauses) rather than speech content. After FDA regulatory costs made their venture-backed model unsustainable, Kintsugi open-sourced their entire technology stack — models, methodologies, and formative research — in February 2026.

The PMS needs a passive mental health screening capability that can operate during routine clinical encounters (phone calls, telehealth visits, intake conversations) without adding questionnaire burden or recording patient speech content.

## Options Considered

### 1. Kintsugi Open-Source Voice Biomarker Models (Self-Hosted)

Deploy Kintsugi's open-source depression and anxiety detection models as a self-hosted service within the PMS backend. Analyze acoustic features only — no speech content processed or stored.

- **Pros:**
  - Privacy by design — analyzes acoustic features, never speech content
  - Free and open-source — no per-analysis API fees
  - Self-hosted — zero data egress, ideal for HIPAA environments
  - Clinically validated — published in Annals of Family Medicine (71.3% sensitivity, 73.5% specificity)
  - CPU-only inference — no GPU required
  - Passive screening — works during routine interactions without dedicated questionnaire time
- **Cons:**
  - No commercial entity maintaining the models long-term
  - FDA De Novo submission was not completed before company closure
  - Clinical validation was English-only (US/Canadian speakers)
  - Moderate accuracy — ~29% miss rate for true depression cases

### 2. Commercial Voice Biomarker API (e.g., Sonde Health, Ellipsis Health)

Use a commercial cloud-based voice biomarker platform with per-analysis pricing and managed model updates.

- **Pros:**
  - Commercially maintained with regular model updates
  - Some platforms have active FDA submissions
  - Dedicated support and SLAs
- **Cons:**
  - Per-analysis pricing scales poorly for high-volume screening ($0.10-0.50 per analysis)
  - Audio data sent to external cloud — HIPAA BAA required, data egress risk
  - Vendor lock-in with proprietary APIs
  - Less transparency into model internals and training data

### 3. PHQ-9/GAD-7 Digital Questionnaires Only

Implement standard screening questionnaires as digital forms within the PMS without any voice analysis.

- **Pros:**
  - Regulatory clarity — well-established, accepted by insurers
  - No AI model risk — deterministic scoring
  - No audio processing infrastructure needed
- **Cons:**
  - Requires active patient participation (5-10 minutes)
  - Subject to self-report bias
  - Often skipped during busy encounters — the core problem remains unsolved
  - No passive screening capability

## Decision

Use **Kintsugi's open-source voice biomarker models** as a self-hosted screening layer in the PMS backend, integrated as an optional module behind feature flags. Position results as clinical decision support (advisory only) — never as automated diagnosis.

### Key Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| PyTorch | >= 2.0 | Deep learning inference |
| librosa | >= 0.10 | Audio feature extraction |
| numpy | >= 1.24 | Numerical computation |
| scipy | >= 1.11 | Signal processing |

## Rationale

1. **Privacy advantage is decisive.** Kintsugi's content-free analysis (acoustic features only) dramatically reduces HIPAA exposure compared to any approach that processes speech content. No audio is recorded, transmitted, or stored — only numerical feature vectors and screening results.

2. **Self-hosted open-source eliminates cost and data egress.** Commercial voice biomarker APIs charge per-analysis and require sending audio to external clouds. Kintsugi runs entirely on-premise with zero ongoing licensing cost.

3. **Clinical validation provides credibility.** The peer-reviewed study (Annals of Family Medicine) with 71.3% sensitivity and 73.5% specificity for moderate-to-severe depression (PHQ-9 >= 10) provides a published evidence base that digital questionnaires alone cannot offer for passive screening.

4. **Passive screening solves the real problem.** The core issue is that screening gets skipped — not that screening tools don't exist. Kintsugi enables screening during routine interactions without requiring dedicated time or patient effort.

5. **Feature-flagged integration limits risk.** Deploying behind feature flags allows controlled rollout, easy rollback, and the ability to disable screening without code changes if regulatory or accuracy concerns arise.

## Trade-offs

1. **Open-source maintenance risk** — No commercial entity maintains the models. Mitigation: fork the repository, assign internal ownership, and monitor the open-source community for contributions.

2. **Regulatory ambiguity** — FDA clearance status is unclear for voice biomarker screening. Mitigation: position strictly as clinical decision support (not a diagnostic device), require clinician review for all results, and monitor FDA guidance on voice biomarkers and SaMD classification.

3. **Moderate accuracy** — 71.3% sensitivity means approximately 29% of true depression cases will be missed. Mitigation: use as a supplementary screening layer alongside (not replacing) PHQ-9 when administered; clearly communicate limitations to clinicians.

4. **English-only validation** — Model accuracy for non-English speakers is unvalidated. Mitigation: document this limitation, restrict use to English-speaking patient populations initially, and validate internally before expanding.

5. **Additional infrastructure** — Adds PyTorch and librosa as backend dependencies, increasing container size. Mitigation: CPU-only inference keeps hardware requirements modest (1-2 GB RAM, no GPU), and the biomarker engine can run as a separate Docker service if isolation is needed.

## Consequences

- New `integrations/kintsugi/` package in `pms-backend` with config, feature extractor, and inference engine
- New `routers/screening.py` with `/api/screening/analyze`, `/api/screening/analyze-features`, `/api/screening/trend/{patient_id}`, and `/api/screening/health` endpoints
- New `models/screening.py` with `VoiceBiomarkerScreening` SQLAlchemy model for storing screening results
- New `services/mood_tracking.py` for longitudinal trend analysis across encounters
- New feature flags: `FEATURE_SUB_CW_0008_VOICE_SCREENING` and `FEATURE_SUB_CW_0009_MOOD_TRACKING`
- New Python dependencies: `torch`, `librosa`, `numpy`, `scipy`
- Alembic migration to create `voice_biomarker_screenings` table
- Frontend `VoiceBiomarkerScreen` and `MoodTimeline` components (separate ADR if needed)
- Patient consent must be documented before screening activation
- All screening results displayed with "advisory only — clinical judgment required" disclaimer

## References

- PRD: [Kintsugi Open-Source PMS Integration](../experiments/35-PRD-KintsugiOpenSource-PMS-Integration.md)
- Setup Guide: [Kintsugi Developer Setup Guide](../experiments/35-KintsugiOpenSource-PMS-Developer-Setup-Guide.md)
- Tutorial: [Kintsugi Developer Tutorial](../experiments/35-KintsugiOpenSource-Developer-Tutorial.md)
- Clinical Validation: [Evaluation of AI-Based Voice Biomarker Tool (PubMed 39805690)](https://pubmed.ncbi.nlm.nih.gov/39805690/)
- Kintsugi Open-Source: [GitHub — KintsugiMindfulWellness](https://github.com/KintsugiMindfulWellness)
- Related: [ADR-0003: Backend Tech Stack](0003-backend-tech-stack.md) — FastAPI + SQLAlchemy foundation
- Related: [ADR-0020: Feature Flags](0020-derm-cds-feature-flags.md) — Feature flag pattern for gating new capabilities
