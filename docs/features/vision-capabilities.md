# Vision Capabilities

**Date:** 2026-02-15
**Related ADR:** [ADR-0007: Jetson Thor Edge Deployment](../architecture/0007-jetson-thor-edge-deployment.md)
**Requirements:** SUB-PR-0009, SUB-PR-0010, SUB-PR-0011

---

## Overview

Three AI-powered vision capabilities are added to the PMS backend, all running on-device via the Jetson Thor GPU. Each capability is exposed as a REST endpoint, gated behind a feature flag, and returns stub data until TensorRT-optimized models are deployed.

## Capabilities

### 1. Wound / Condition Assessment (SUB-PR-0009)

**Endpoint:** `POST /vision/wound-assessment`
**Feature flag:** `FEATURE_SUB_PR_0009_WOUND_ASSESSMENT`

**Flow:**
1. Clinician captures wound photo on Android app
2. App uploads image to `/vision/wound-assessment`
3. Backend runs MONAI segmentation pipeline on GPU:
   - Wound boundary segmentation (U-Net variant)
   - Severity classification (mild / moderate / severe / critical)
   - Area estimation as percentage of image
4. Response includes severity, area percentage, description, and confidence score

**Response schema:**
```json
{
  "severity": "moderate",
  "area_percentage": 12.5,
  "description": "Partial-thickness wound with granulation tissue",
  "confidence": 0.87
}
```

**Model stack:** MONAI + TensorRT (FP16/INT8 quantization)

### 2. Patient Identity Verification (SUB-PR-0010)

**Endpoint:** `POST /vision/patient-id-verify`
**Feature flag:** `FEATURE_SUB_PR_0010_PATIENT_ID_VERIFY`

**Flow:**
1. Clinician takes photo of patient's face on Android app
2. App uploads image + `patient_id` to `/vision/patient-id-verify`
3. Backend generates face embedding via ArcFace on GPU
4. Compares embedding against stored embedding for the given `patient_id`
5. Returns match result and confidence score

**Response schema:**
```json
{
  "match": true,
  "confidence": 0.94
}
```

**Model stack:** ArcFace + TensorRT (FP16)

### 3. Document OCR (SUB-PR-0011)

**Endpoint:** `POST /vision/document-ocr`
**Feature flag:** `FEATURE_SUB_PR_0011_DOCUMENT_OCR`

**Flow:**
1. Clinician photographs a paper document (insurance card, referral, etc.)
2. App uploads image to `/vision/document-ocr`
3. Backend runs PaddleOCR pipeline on GPU:
   - Text detection (DB detector)
   - Text recognition (CRNN recognizer)
   - Field extraction from structured text
4. Returns raw extracted text and parsed key-value fields

**Response schema:**
```json
{
  "extracted_text": "Patient Name: John Doe\nDOB: 01/15/1980\nInsurance ID: XYZ-123456",
  "fields": {
    "patient_name": "John Doe",
    "date_of_birth": "01/15/1980",
    "insurance_id": "XYZ-123456"
  }
}
```

**Model stack:** PaddleOCR + TensorRT (FP16)

## Key Files

| File | Purpose |
|---|---|
| `pms-backend/src/pms/schemas/vision.py` | Pydantic response schemas |
| `pms-backend/src/pms/services/vision_service.py` | Vision service (stubs, will integrate models) |
| `pms-backend/src/pms/routers/vision.py` | REST endpoints with auth + feature flag guards |

## Design Choices

1. **Stubs first** — All endpoints return realistic mock data until TensorRT models are deployed. This allows frontend/Android integration to proceed in parallel with model optimization.
2. **Feature-flagged** — Each capability has its own flag so they can be enabled independently as models are validated.
3. **Image upload via `UploadFile`** — Standard FastAPI file upload with `python-multipart`. Images are processed in-memory (no disk persistence of raw uploads).
4. **Authentication required** — All vision endpoints require a valid JWT token via the existing `require_auth` middleware.

## Known Limitations

- Stub implementations return hardcoded data — no actual inference
- No image validation (format, size, resolution) in initial implementation
- Patient ID verification requires pre-stored embeddings (not yet implemented)
- No batch processing — one image per request
