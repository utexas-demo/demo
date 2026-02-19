# Product Requirements Document: MedASR Integration into Patient Management System (PMS)

**Document ID:** PRD-PMS-MEDASR-001
**Version:** 1.0
**Date:** February 19, 2026
**Author:** Ammar (CEO, MPS Inc.)
**Status:** Draft

---

## 1. Executive Summary

MedASR is an open-source, Conformer-based medical speech-to-text model developed by Google Health AI. With 105 million parameters, it delivers state-of-the-art accuracy on medical dictation — achieving 4.6% word error rate (WER) on radiology dictation, outperforming OpenAI Whisper v3 Large by 5x and even Google's own Gemini 2.5 Pro on medical speech. The model is purpose-built for healthcare terminology: medication names, anatomical structures, diagnostic codes, and clinical measurements.

Integrating MedASR into the PMS will enable clinicians to dictate patient encounter notes, medication orders, and clinical observations directly into the system using voice. This eliminates the documentation bottleneck that consumes an estimated 2+ hours per clinician per day, allowing staff to focus on patient care rather than keyboard entry.

MedASR's lightweight 105M-parameter design runs efficiently on consumer-grade GPUs and can be self-hosted entirely within the MPS network boundary — ensuring that no patient audio or transcribed PHI ever leaves our infrastructure. Combined with MedGemma for downstream summarization, this creates a fully on-premise clinical documentation pipeline.

---

## 2. Problem Statement

The current PMS workflow suffers from several documentation-related bottlenecks:

- **Manual encounter documentation:** Clinicians spend 15-30 minutes per patient encounter typing notes, vital signs, observations, and medication changes into the PMS. With 30+ encounters per day per provider, this represents 7-15 hours per week of pure documentation time.
- **Transcription errors from general-purpose tools:** Staff who use generic speech-to-text (Siri, Google Speech, Whisper) frequently encounter misrecognized medical terms — "Lisinopril" becomes "listening pill," "ileum" becomes "ilium" — requiring manual correction that negates time savings.
- **Delayed note completion:** Because documentation is burdensome, clinicians often defer note completion to after hours ("pajama time"), leading to recall errors, incomplete records, and clinician burnout.
- **Android app limitations:** Field staff using the PMS Android app currently have no voice input capability, forcing manual typing on mobile keyboards during home visits and RPM device checks.
- **No structured extraction:** Even when dictation tools are used, the output is unstructured text that must be manually parsed into PMS fields (chief complaint, assessment, plan, medications).

---

## 3. Proposed Solution

Deploy MedASR as a **self-hosted medical speech recognition service** accessible to PMS users via the web frontend, Android app, and backend API. Audio is captured on the client, streamed to the MedASR service over WebSocket, and transcribed text is returned in real-time for insertion into PMS forms. Downstream, the transcription can be fed to MedGemma for structured extraction (SOAP notes, medication lists, ICD codes).

### 3.1 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                       MPS Network Boundary                       │
│                                                                  │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐ │
│  │   PMS Web Frontend   │    │   PMS Android App                │ │
│  │   (Next.js 15)       │    │   (Kotlin / Jetpack Compose)     │ │
│  │   :3000              │    │                                   │ │
│  │                       │    │   [Microphone capture]            │ │
│  │   [Microphone capture]│    │   [Audio streaming via WebSocket] │ │
│  │   [Voice dictation UI]│    │   [Real-time transcript display]  │ │
│  └──────────┬────────────┘    └──────────────┬───────────────────┘ │
│             │ WebSocket (wss://)              │ WebSocket (wss://) │
│             └──────────────┬─────────────────┘                    │
│                            ▼                                      │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              MedASR Service (Docker Container)                │ │
│  │                                                               │ │
│  │  ┌──────────────────┐  ┌──────────────────┐                  │ │
│  │  │  MedASR Model     │  │  6-gram Language  │                  │ │
│  │  │  (105M Conformer) │  │  Model (optional) │                  │ │
│  │  └────────┬─────────┘  └────────┬─────────┘                  │ │
│  │           │                      │                             │ │
│  │  ┌────────▼──────────────────────▼─────────┐                  │ │
│  │  │  FastAPI Inference Server (:8001)         │                  │ │
│  │  │  - POST /transcribe (batch)              │                  │ │
│  │  │  - WS   /ws/transcribe (streaming)       │                  │ │
│  │  │  - GET  /health                          │                  │ │
│  │  └────────┬────────────────────────────────┘                  │ │
│  └───────────┼───────────────────────────────────────────────────┘ │
│              │                                                     │
│  ┌───────────▼───────────────┐  ┌──────────────────────────────┐  │
│  │  PMS Backend (FastAPI)     │  │  PostgreSQL                   │  │
│  │  :8000                     │  │  :5432                        │  │
│  │                            │  │                               │  │
│  │  - /api/patients           │  │  - transcription_logs table   │  │
│  │  - /api/encounters         │  │  - encounter_notes table      │  │
│  │  - /api/prescriptions      │  │  - audit_trail table          │  │
│  │  - /api/reports            │  │                               │  │
│  │  - /api/transcriptions     │  │                               │  │
│  └────────────────────────────┘  └──────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Deployment Model

- **Self-hosted in Docker:** MedASR runs inside a GPU-enabled Docker container on MPS infrastructure. No cloud API calls are required — all inference happens locally.
- **Network isolation:** The MedASR container is attached to an internal Docker network. Only the PMS backend can reach it; it has no outbound internet access.
- **HIPAA compliance:** Audio data and transcriptions never leave the MPS network boundary. All audio is processed in-memory and discarded after transcription (no persistent audio storage by default). Transcription logs are stored in PostgreSQL with encryption at rest.
- **Resource requirements:** MedASR's 105M parameters require approximately 500MB VRAM. A single NVIDIA T4 or consumer RTX 3060 can handle real-time inference for multiple concurrent sessions.

---

## 4. PMS Data Sources

MedASR integrates with the following existing PMS APIs:

| API Endpoint | Interaction | Description |
|---|---|---|
| `/api/encounters` | **Primary** | Transcribed dictation is attached to encounter records as clinical notes. Voice-dictated SOAP notes are parsed and stored against the active encounter. |
| `/api/patients` | **Context** | Patient context (name, medications, allergies, recent diagnoses) is loaded before dictation to improve post-processing accuracy and enable structured extraction. |
| `/api/prescriptions` | **Extraction** | Medication names and dosages mentioned in dictation are extracted and cross-referenced against the patient's medication list for reconciliation. |
| `/api/reports` | **Analytics** | Transcription usage metrics (sessions per provider, average dictation length, WER estimates) are surfaced in the reporting dashboard. |

A new API group will be introduced:

| New Endpoint | Method | Description |
|---|---|---|
| `/api/transcriptions` | POST | Submit audio for batch transcription |
| `/api/transcriptions/stream` | WebSocket | Real-time streaming transcription |
| `/api/transcriptions/{id}` | GET | Retrieve transcription result and metadata |
| `/api/transcriptions/{id}/feedback` | POST | Submit correction feedback for model improvement |

---

## 5. Component/Module Definitions

### 5.1 MedASR Inference Service

| Property | Value |
|---|---|
| **Description** | Standalone FastAPI service wrapping the MedASR model for inference |
| **Input** | 16kHz mono WAV audio (batch) or audio chunks (streaming) |
| **Output** | JSON with transcribed text, confidence scores, word-level timestamps |
| **PMS APIs Used** | None (standalone inference) |
| **Port** | 8001 |

### 5.2 Transcription API Gateway

| Property | Value |
|---|---|
| **Description** | Extension to the PMS backend that proxies transcription requests, manages sessions, and stores results |
| **Input** | Audio from web/mobile clients via WebSocket or HTTP |
| **Output** | Transcribed text with metadata (timestamps, confidence, speaker ID) |
| **PMS APIs Used** | `/api/encounters`, `/api/patients` |

### 5.3 Voice Dictation UI Component (Web)

| Property | Value |
|---|---|
| **Description** | React component for the Next.js frontend providing microphone capture, real-time transcript display, and inline editing |
| **Input** | User voice via browser MediaRecorder API |
| **Output** | Finalized text inserted into encounter note fields |
| **PMS APIs Used** | `/api/transcriptions/stream`, `/api/encounters` |

### 5.4 Voice Dictation Module (Android)

| Property | Value |
|---|---|
| **Description** | Kotlin module for the Android app using AudioRecord API for capture and OkHttp WebSocket for streaming |
| **Input** | User voice via device microphone |
| **Output** | Transcribed text displayed in-app and synced to PMS backend |
| **PMS APIs Used** | `/api/transcriptions/stream`, `/api/encounters` |

### 5.5 Transcription Post-Processor

| Property | Value |
|---|---|
| **Description** | Pipeline component that takes raw transcription and extracts structured data (SOAP note sections, medication mentions, ICD codes) |
| **Input** | Raw transcription text + patient context |
| **Output** | Structured JSON (chief_complaint, assessment, plan, medications_mentioned, icd_codes) |
| **PMS APIs Used** | `/api/patients`, `/api/prescriptions` |

---

## 6. Non-Functional Requirements

### 6.1 Security and HIPAA Compliance

| Requirement | Implementation |
|---|---|
| **PHI isolation** | All audio processing occurs within the MPS Docker network. No audio or transcription data is transmitted externally. |
| **Encryption in transit** | WebSocket connections use WSS (TLS 1.3). Internal service-to-service calls use mTLS. |
| **Encryption at rest** | Transcription logs in PostgreSQL use AES-256 column-level encryption for PHI fields. |
| **Access control** | Role-based access: only authenticated clinicians can initiate dictation. Transcription endpoints require valid JWT with `transcription:write` scope. |
| **Audit logging** | Every transcription request is logged with: user ID, patient ID (if linked), timestamp, duration, and a hash of the audio. Audio itself is not persisted. |
| **Data retention** | Raw audio is discarded after transcription. Transcription text follows the same retention policy as encounter notes (7 years per HIPAA). |
| **BAA coverage** | Self-hosted deployment eliminates need for third-party BAA. Model weights are downloaded once and stored locally. |

### 6.2 Performance

| Metric | Target |
|---|---|
| **Transcription latency (streaming)** | < 500ms from utterance to displayed text |
| **Transcription latency (batch)** | < 3 seconds for 60-second audio clip |
| **Word Error Rate (WER)** | < 7% on general medical dictation; < 5% on radiology |
| **Concurrent sessions** | 10+ simultaneous dictation sessions per GPU |
| **Uptime** | 99.5% during clinic hours (7am-7pm) |

### 6.3 Infrastructure

| Requirement | Specification |
|---|---|
| **GPU** | NVIDIA T4 (16GB) minimum; RTX 3060 (12GB) for development |
| **RAM** | 8GB dedicated to MedASR container |
| **Storage** | 2GB for model weights + 6-gram LM; 50GB for transcription logs |
| **Docker** | GPU-enabled Docker runtime (nvidia-docker2) |
| **Network** | Internal Docker network, no outbound internet from inference container |

---

## 7. Implementation Phases

### Phase 1: Foundation (Sprints 1-2)

- Deploy MedASR in Docker with GPU support
- Build FastAPI inference service with `/transcribe` and `/health` endpoints
- Implement batch transcription API in PMS backend
- Create transcription_logs table in PostgreSQL
- Set up audit logging for all transcription events
- Write integration tests with sample medical audio

### Phase 2: Core Integration (Sprints 3-4)

- Implement WebSocket streaming endpoint (`/ws/transcribe`)
- Build Voice Dictation UI component for Next.js frontend
- Integrate dictation into Encounter Notes form
- Build Android voice dictation module with WebSocket streaming
- Add patient context loading for improved post-processing
- Deploy 6-gram language model for enhanced accuracy

### Phase 3: Advanced Features (Sprints 5-6)

- Build Transcription Post-Processor for structured extraction (SOAP notes, medications, ICD codes)
- Add correction feedback loop for model fine-tuning
- Implement provider-specific vocabulary adaptation
- Build transcription analytics dashboard
- Add multi-speaker diarization support
- Fine-tune model on MPS-specific terminology

---

## 8. Success Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| Documentation time per encounter | 50% reduction (from 15 min to 7.5 min) | Time tracking comparison study |
| Clinician adoption rate | 80% of providers using voice dictation within 90 days | Usage analytics from transcription logs |
| Word Error Rate (medical terms) | < 5% on medication names and diagnoses | Automated comparison against corrected transcriptions |
| Note completion timeliness | 90% of notes completed within 1 hour of encounter | Encounter note timestamp analysis |
| Clinician satisfaction | > 4.0/5.0 on voice dictation survey | Quarterly provider satisfaction survey |
| Android adoption | 60% of field staff using voice input within 60 days | Mobile transcription session analytics |

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Medical terminology errors in transcription | Incorrect medications or diagnoses in patient records | Human-in-the-loop review: all dictated notes require clinician confirmation before saving. Correction feedback improves model over time. |
| GPU availability on all dev/prod machines | Cannot run inference locally | Provide CPU fallback mode (slower but functional). Production uses dedicated GPU server accessible via internal API. |
| English-only limitation | Non-English-speaking patients or providers cannot use dictation | Document as known limitation. Evaluate multilingual medical ASR alternatives for future phases. |
| Noisy clinical environments degrade accuracy | Higher WER in exam rooms with equipment noise | Recommend directional/noise-canceling microphones. Test and document WER under various noise conditions. Implement audio quality scoring before transcription. |
| Model staleness (new medications, procedures) | Unrecognized new drug names or procedures | Quarterly fine-tuning cycle using correction feedback data. Subscribe to FDA drug name updates for vocabulary expansion. |
| Speaker accent variability | Higher WER for non-US English accents | Fine-tune on accent-diverse audio. MedASR supports accent adaptation via few-shot fine-tuning. |

---

## 10. Dependencies

| Dependency | Type | Notes |
|---|---|---|
| MedASR model weights (`google/medasr`) | Model | Downloaded from Hugging Face Hub. ~500MB. Health AI Developer Foundations license. |
| Hugging Face Transformers >= 5.0.0 | Library | Required for MedASR inference pipeline |
| PyTorch >= 2.0 | Library | Backend for model inference |
| librosa | Library | Audio preprocessing (resampling, normalization) |
| NVIDIA GPU + CUDA drivers | Hardware | Required for real-time inference. CPU fallback available but slower. |
| nvidia-docker2 | Runtime | GPU passthrough to Docker containers |
| FastAPI + uvicorn | Framework | Inference service API |
| WebSocket support (Next.js + OkHttp) | Client | Real-time audio streaming from web and Android clients |
| 6-gram language model (optional) | Model | Beam search decoding for improved WER. ~200MB. |
| PMS Backend running on :8000 | Service | Required for patient context and encounter storage |
| PostgreSQL running on :5432 | Database | Transcription log storage |

---

## 11. Comparison with Existing Experiments

| Dimension | MedASR (07) | OpenClaw (05) | Tambo (00) |
|---|---|---|---|
| **Category** | Medical Speech Recognition | Agentic AI Workflow Automation | Conversational Analytics |
| **Primary function** | Convert clinician speech to structured text | Automate multi-step clinical workflows | Natural language querying of PMS data |
| **User interaction** | Voice input during patient encounters | Chat-based task delegation | Conversational sidebar |
| **PHI handling** | Processes audio containing PHI on-premise | Processes PHI via skill-based API calls | Queries aggregated/anonymized data |
| **Complementarity** | MedASR transcriptions feed into OpenClaw documentation skills and Tambo analytics | OpenClaw can use MedASR output to auto-populate encounter records | Tambo can analyze dictation patterns and provider productivity |

MedASR is **complementary** to both OpenClaw and Tambo. The transcription output from MedASR can serve as input to OpenClaw's clinical documentation skills (auto-generating SOAP notes, prior auth letters) and Tambo can surface analytics on dictation usage, transcription accuracy trends, and provider productivity gains.

---

## 12. Appendix: Related Documents

- [MedASR Setup Guide](07-MedASR-PMS-Developer-Setup-Guide.md) — Self-hosted deployment, Docker configuration, PMS integration
- [MedASR Developer Tutorial](07-MedASR-Developer-Tutorial.md) — Hands-on onboarding: build your first dictation integration
- [OpenClaw PRD](05-PRD-OpenClaw-PMS-Integration.md) — Agentic workflow automation (complementary)
- [Tambo PRD](00-PRD-Tambo-PMS-Integration.md) — Conversational analytics (complementary)
- [MedASR Official Documentation](https://developers.google.com/health-ai-developer-foundations/medasr)
- [MedASR on Hugging Face](https://huggingface.co/google/medasr)
- [MedASR GitHub Repository](https://github.com/Google-Health/medasr)
- [MedASR Model Card](https://developers.google.com/health-ai-developer-foundations/medasr/model-card)
- [Google Research Blog: MedGemma 1.5 and MedASR](https://research.google/blog/next-generation-medical-image-interpretation-with-medgemma-15-and-medical-speech-to-text-with-medasr/)
