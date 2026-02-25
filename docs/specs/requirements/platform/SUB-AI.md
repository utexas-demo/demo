# Platform Requirements: AI Infrastructure (SUB-AI)

**Version:** 1.1
**Date:** 2026-02-25
**Platform:** AI Infrastructure (AI) — 9 requirements across 2 domains
**Repository:** pms-derm-cds
**Technology:** Python, ONNX Runtime, TensorRT (Jetson), TFLite (Android), pgvector, EfficientNet-B4, MobileNetV3

---

## Summary

| Domain | Req Count | Status Breakdown |
|--------|-----------|-----------------|
| Patient Records (PR) | 8 | 8 Not Started |
| Prompt Management (PM) | 1 | 1 Not Started |
| **Total** | **9** | |

---

## Patient Records (SUB-PR)

**Parent:** [SUB-PR (Domain)](../domain/SUB-PR.md)

| Platform Req ID | Parent | Description | Module(s) | Test Case(s) | Status |
|---|---|---|---|---|---|
| SUB-PR-0009-AI | SUB-PR-0009 | Wound severity classification model (edge deployment) | — | TST-PR-0009-AI | Not Started |
| SUB-PR-0010-AI | SUB-PR-0010 | Face/ID verification embedding model (edge deployment) | — | TST-PR-0010-AI | Not Started |
| SUB-PR-0011-AI | SUB-PR-0011 | Document OCR model (edge deployment) | — | TST-PR-0011-AI | Not Started |
| SUB-PR-0013-AI | SUB-PR-0013 | EfficientNet-B4 classification model deployment via ONNX Runtime in `pms-derm-cds` Docker service. Model accepts 380x380 image tensor, outputs probability distribution across 9 ISIC diagnostic categories. Must maintain a model compatibility matrix in `model-manifest.json` (ADR-0013): server EfficientNet-B4 and mobile MobileNetV3 must be trained on the same ISIC dataset version and validated to produce concordant top-1 predictions on a reference test set (target: ≥90% agreement rate). When server classification differs from on-device result, the API response must include a `classification_changed` flag (PC-AI-01). | `services/derm-cds/classifier.py`, `services/derm-cds/model-manifest.json` | TST-PR-0013-AI | Not Started |
| SUB-PR-0014-AI | SUB-PR-0014 | Image embedding generation (512-dim float32 vector from penultimate CNN layer) and pgvector index management for ISIC reference cache (IVFFlat index, cosine distance) | `services/derm-cds/embedder.py`, `services/derm-cds/similarity.py` | TST-PR-0014-AI | Not Started |
| SUB-PR-0015-AI | SUB-PR-0015 | Risk scoring algorithm within the CDS service. Accepts EfficientNet-B4 probability distribution, patient age, and anatomical site. Computes a composite risk score mapped to three severity tiers (low / medium / high) using configurable clinical thresholds (default: low < 0.3, medium 0.3–0.7, high > 0.7 aggregate malignant probability across melanoma + BCC + SCC classes). Returns referral urgency (routine / expedited / urgent) derived from severity tier and anatomical site (head/neck sites escalate one urgency level). Thresholds must be externally configurable via environment variables or config file without code changes. | `services/derm-cds/risk_scorer.py`, `services/derm-cds/config.py` | TST-PR-0015-AI | Not Started |
| SUB-PR-0016-AI | SUB-PR-0016 | Longitudinal change detection within the CDS service. Accepts a current 512-dim image embedding and a patient+anatomical-site key, retrieves the most recent prior embedding from pgvector, and computes cosine distance. Returns a `change_detected` boolean (true if cosine distance exceeds a configurable threshold, default 0.15), the raw cosine distance value, and the prior assessment date. If no prior embedding exists for the site, returns `change_detected = null` (first assessment). Change detection is invoked as a post-classification step and does not block the DermaCheck fan-out pipeline. | `services/derm-cds/change_detector.py`, `services/derm-cds/similarity.py` | TST-PR-0016-AI | Not Started |
| SUB-PR-0017-AI | SUB-PR-0017 | DermaCheck parallel fan-out orchestration inside the CDS service (`POST /classify`). EfficientNet-B4 classification runs first, producing probabilities and a 512-dim embedding. Then `asyncio.gather()` runs three concurrent stages: (1) Gemma 3 clinical narrative via AI Gateway (:8001), (2) pgvector similarity search using the embedding, (3) risk score calculation from probabilities and patient history. Per-stage timeouts: Gemma 3 = 5s, similarity = 2s, risk = 1s. Assemble results into atomic `DermaCheckResult` payload. If a non-critical stage fails or times out, set its field to null and `degraded = true`. EfficientNet-B4 failure returns HTTP 500 (hard-fail). **Narrative generation acceptance criteria:** The Gemma 3 clinical narrative must include (a) a plain-language summary of the top-3 classification results with confidence percentages, (b) clinical significance of the dominant diagnosis, and (c) a standard disclaimer that results are AI-assisted and require physician review. The narrative prompt template is defined in the AI Gateway configuration and must be versioned alongside model updates. Maximum narrative length: 500 tokens. | `services/derm-cds/orchestrator.py`, `services/derm-cds/classifier.py`, `services/derm-cds/similarity.py`, `services/derm-cds/risk_scorer.py` | TST-PR-0017-AI | Not Started |

---

## Prompt Management (SUB-PM)

**Parent:** [SUB-PM (Domain)](../domain/SUB-PM.md)

| Platform Req ID | Parent | Description | Module(s) | Test Case(s) | Status |
|---|---|---|---|---|---|
| SUB-PM-0007-AI | SUB-PM-0007 | Anthropic Claude API integration for prompt version comparison. Uses `claude-sonnet-4-20250514` model. Prompt text is NOT PHI — external API calls are acceptable. The comparison template is itself a managed prompt bootstrapped via migration. | `services/llm_service.py` | TST-PM-0007-AI | Not Started |
