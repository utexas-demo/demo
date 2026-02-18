# Lab Specimen Management

**Status:** Draft
**Branch:** `feature/lab-specimen-management`
**Date:** 2026-02-18
**Subsystem Code:** SUB-LS

---

## Overview

This feature adds lab specimen tracking and management capabilities to the PMS, enabling clinicians to order lab tests, track specimen collection and processing, and view results within patient records. Lab Specimen Management introduces a new subsystem (SUB-LS) that integrates deeply with Patient Records (SUB-PR), Clinical Workflow (SUB-CW), Medication Management (SUB-MM), and Reporting & Analytics (SUB-RA).

---

## System Context — Block Diagram

The block diagram below shows where Lab Specimen Management sits within the overall PMS architecture and its interactions with existing subsystems and external systems.

```mermaid
block-beta
    columns 5

    block:clients:5
        columns 4
        WebUI["Web UI\n(Next.js)"]
        AndroidApp["Android App\n(Kotlin/Compose)"]
        SMSGateway["SMS Gateway\n(Twilio)"]
        ExtLIS["External LIS\n(HL7/FHIR)"]
    end

    space:5

    block:api:5
        columns 1
        APIGateway["Backend API Gateway (FastAPI)\nAuth · RBAC · Audit · SMS Webhook"]
    end

    space:5

    block:subsystems:5
        columns 5
        SUBPR["SUB-PR\nPatient\nRecords"]
        SUBCW["SUB-CW\nClinical\nWorkflow"]
        SUBLS["SUB-LS\nLab Specimen\nManagement"]
        SUBMM["SUB-MM\nMedication\nMgmt"]
        SUBRA["SUB-RA\nReporting &\nAnalytics"]
    end

    space:5

    block:ai:5
        columns 2
        OCR["AI OCR Service\nDocument Extraction\n(SUB-PR-0011)"]
        Validation["Order Validation\nPhysician · Patient\nInsurance · Tests"]
    end

    space:5

    block:data:5
        columns 3
        DB["PostgreSQL\nPatients · Encounters\nSpecimens · Results\nSMS Intake"]
        AuditLog["Audit Log\nArchive"]
        FHIR["External EHR\n(FHIR R4)"]
    end

    WebUI --> APIGateway
    AndroidApp --> APIGateway
    SMSGateway --> APIGateway
    ExtLIS --> APIGateway
    APIGateway --> SUBPR
    APIGateway --> SUBCW
    APIGateway --> SUBLS
    APIGateway --> SUBMM
    APIGateway --> SUBRA
    SUBLS --> OCR
    SUBLS --> Validation
    OCR --> Validation
    SUBLS --> DB
    SUBLS --> AuditLog
    SUBPR --> DB
    SUBCW --> DB
    SUBMM --> DB
    SUBRA --> DB

    style SUBLS fill:#4CAF50,color:#fff
    style SMSGateway fill:#2196F3,color:#fff
    style OCR fill:#FF9800,color:#fff
    style Validation fill:#FF9800,color:#fff
```

### Subsystem Interactions

| Interaction | Direction | Description |
|---|---|---|
| SUB-LS ↔ SUB-PR | Bidirectional | Lab orders reference a patient (patient_id FK). Results are attached to the patient record. |
| SUB-LS ↔ SUB-CW | Bidirectional | Lab orders originate from encounters. Results may trigger encounter status updates or clinical notes. |
| SUB-LS → SUB-MM | Outbound | Critical lab results (e.g., renal function, drug levels) trigger medication review alerts. |
| SUB-LS → SUB-RA | Outbound | Lab volumes, turnaround times, and abnormal result rates feed reporting dashboards. |
| SUB-LS ↔ SYS-REQ-0003 | Bidirectional | All specimen operations are logged to the audit trail. |
| SUB-LS ↔ SYS-REQ-0006 | Bidirectional | Abnormal/critical lab values generate real-time clinical alerts within 30 seconds. |
| SUB-LS ↔ External LIS | Bidirectional | Inbound: receive results from external laboratory systems via HL7/FHIR. Outbound: send electronic orders. |
| SUB-LS ↔ SMS Gateway | Bidirectional | Inbound: nurse sends photo of lab order via SMS. Outbound: system replies with pickup time and clarifications. |
| SUB-LS → AI OCR (SUB-PR-0011) | Outbound | Photo of lab order is processed by AI OCR to extract structured data (physician, patient, insurance, tests). |
| SUB-LS ↔ Order Validation | Bidirectional | Extracted JSON is validated against PMS records: ordering physician, patient identity, insurance eligibility, and test catalog. |

---

## Specimen Lifecycle — State Machine

```mermaid
stateDiagram-v2
    [*] --> Ordered : Clinician places lab order (in-app)
    [*] --> SMSReceived : Nurse sends photo via SMS
    SMSReceived --> PendingValidation : AI OCR extracts structured data
    PendingValidation --> Ordered : All fields validated ✓
    PendingValidation --> ClarificationSent : Missing/ambiguous fields
    ClarificationSent --> PendingValidation : Nurse replies with corrections
    ClarificationSent --> Cancelled : No response within timeout
    Ordered --> Collected : Specimen drawn / received
    Ordered --> Cancelled : Order cancelled
    Collected --> InTransit : Sent to lab
    Collected --> Cancelled : Specimen rejected
    InTransit --> Processing : Lab begins analysis
    Processing --> ResultAvailable : Results finalized
    Processing --> Cancelled : Sample compromised
    ResultAvailable --> Reviewed : Clinician reviews result
    Reviewed --> [*]
    Cancelled --> [*]
```

| State | Description |
|---|---|
| SMSReceived | Lab order photo received via SMS from nurse; queued for AI OCR processing |
| PendingValidation | AI OCR has extracted JSON; system is validating physician, patient, insurance, and order details against PMS records |
| ClarificationSent | System sent SMS reply requesting clarifications (e.g., illegible fields, unknown physician, missing insurance) |
| Ordered | Lab test order validated and created in PMS (from in-app or after SMS validation completes) |
| Collected | Specimen physically collected and labeled |
| InTransit | Specimen dispatched to processing lab |
| Processing | Lab actively analyzing the specimen |
| ResultAvailable | Results finalized, pending clinician review |
| Reviewed | Clinician has reviewed and acknowledged results |
| Cancelled | Order or specimen cancelled at any pre-result stage, or SMS intake timed out |

---

## Sequence Diagrams

### 1. Lab Order Placement (During Encounter)

```mermaid
sequenceDiagram
    actor Clinician
    participant WebUI as Web UI / Android
    participant API as Backend API
    participant Auth as Auth Middleware
    participant CW as Clinical Workflow (SUB-CW)
    participant LS as Lab Specimen (SUB-LS)
    participant PR as Patient Records (SUB-PR)
    participant DB as PostgreSQL
    participant Audit as Audit Service

    Clinician->>WebUI: Select lab tests for patient
    WebUI->>API: POST /lab-orders (patient_id, encounter_id, tests[])
    API->>Auth: Validate JWT + RBAC (physician, nurse)
    Auth-->>API: Authorized

    API->>CW: Validate encounter exists & is in_progress
    CW->>DB: SELECT encounter WHERE id = encounter_id
    DB-->>CW: Encounter record
    CW-->>API: Encounter valid

    API->>PR: Validate patient exists & is active
    PR->>DB: SELECT patient WHERE id = patient_id
    DB-->>PR: Patient record
    PR-->>API: Patient valid

    API->>LS: Create lab order
    LS->>DB: INSERT lab_order (status=ordered)
    DB-->>LS: Order created
    LS->>DB: INSERT lab_order_tests (one per test)
    DB-->>LS: Tests linked

    LS->>Audit: Log CREATE lab_order
    Audit->>DB: INSERT audit_log
    LS-->>API: Order confirmation

    API-->>WebUI: 201 Created (order_id, status, tests)
    WebUI-->>Clinician: Order confirmed
```

### 2. Specimen Collection and Tracking

```mermaid
sequenceDiagram
    actor Nurse
    participant App as Web UI / Android
    participant API as Backend API
    participant Auth as Auth Middleware
    participant LS as Lab Specimen (SUB-LS)
    participant DB as PostgreSQL
    participant Audit as Audit Service

    Nurse->>App: Scan specimen barcode / enter collection details
    App->>API: PATCH /lab-orders/{id}/collect (collected_at, collector_id, barcode)
    API->>Auth: Validate JWT + RBAC (physician, nurse)
    Auth-->>API: Authorized

    API->>LS: Update specimen status
    LS->>DB: SELECT lab_order WHERE id = order_id FOR UPDATE
    DB-->>LS: Current state = ordered
    LS->>LS: Validate transition: ordered → collected
    LS->>DB: UPDATE lab_order SET status=collected, collected_at, collector_id, barcode
    DB-->>LS: Updated

    LS->>Audit: Log UPDATE lab_order (ordered → collected)
    Audit->>DB: INSERT audit_log
    LS-->>API: Updated order

    API-->>App: 200 OK (updated status)
    App-->>Nurse: Collection confirmed
```

### 3. Lab Result Ingestion (External LIS)

```mermaid
sequenceDiagram
    participant LIS as External Lab System (LIS)
    participant API as Backend API
    participant Auth as Auth Middleware
    participant LS as Lab Specimen (SUB-LS)
    participant PR as Patient Records (SUB-PR)
    participant Alert as Alert Service (SYS-REQ-0006)
    participant MM as Medication Mgmt (SUB-MM)
    participant DB as PostgreSQL
    participant Audit as Audit Service
    actor Clinician

    LIS->>API: POST /lab-results (order_id, results[], HL7/FHIR payload)
    API->>Auth: Validate API key / service auth
    Auth-->>API: Authorized

    API->>LS: Process lab results
    LS->>DB: SELECT lab_order WHERE id = order_id FOR UPDATE
    DB-->>LS: Order (status = processing)
    LS->>LS: Validate transition: processing → result_available
    LS->>DB: INSERT lab_results (values, units, reference_ranges, flags)
    LS->>DB: UPDATE lab_order SET status = result_available
    DB-->>LS: Stored

    LS->>LS: Check for abnormal/critical values
    alt Critical values detected
        LS->>Alert: Trigger critical lab alert (SYS-REQ-0006)
        Alert->>DB: INSERT alert (severity=critical, type=lab_critical)
        Alert-->>Clinician: Push notification / in-app alert (< 30s)

        LS->>MM: Check medication implications
        MM->>DB: SELECT active prescriptions for patient
        MM-->>LS: Medication review flag (if applicable)
    end

    LS->>PR: Attach results to patient record
    PR->>DB: Link lab_result to patient timeline
    LS->>Audit: Log CREATE lab_result
    Audit->>DB: INSERT audit_log
    LS-->>API: Results stored

    API-->>LIS: 201 Created (result_id, status)
```

### 4. Clinician Reviews Lab Results

```mermaid
sequenceDiagram
    actor Clinician
    participant UI as Web UI / Android
    participant API as Backend API
    participant Auth as Auth Middleware
    participant LS as Lab Specimen (SUB-LS)
    participant PR as Patient Records (SUB-PR)
    participant RA as Reporting (SUB-RA)
    participant DB as PostgreSQL
    participant Audit as Audit Service

    Clinician->>UI: Open patient lab results
    UI->>API: GET /patients/{id}/lab-results?status=result_available
    API->>Auth: Validate JWT + RBAC
    Auth-->>API: Authorized
    API->>LS: Fetch pending results
    LS->>DB: SELECT lab_results WHERE patient_id AND status
    DB-->>LS: Results list
    LS->>Audit: Log READ lab_results
    LS-->>API: Results
    API-->>UI: 200 OK (results[])
    UI-->>Clinician: Display results with reference ranges & flags

    Clinician->>UI: Acknowledge/review result
    UI->>API: PATCH /lab-orders/{id}/review (reviewer_notes)
    API->>Auth: Validate JWT + RBAC (physician)
    Auth-->>API: Authorized
    API->>LS: Mark as reviewed
    LS->>DB: UPDATE lab_order SET status=reviewed, reviewed_by, reviewed_at
    DB-->>LS: Updated
    LS->>PR: Update patient timeline
    LS->>RA: Update lab turnaround metrics
    LS->>Audit: Log UPDATE lab_order (result_available → reviewed)
    LS-->>API: Confirmed
    API-->>UI: 200 OK
    UI-->>Clinician: Result marked as reviewed
```

### 5. SMS Photo Lab Order Intake

The nurse photographs a paper lab order and texts it to the lab's dedicated phone number. The system extracts structured data via AI OCR, validates it against PMS records, and replies with the proposed specimen pickup time or clarification requests.

```mermaid
sequenceDiagram
    actor Nurse
    participant Phone as Nurse's Phone (SMS)
    participant Twilio as SMS Gateway (Twilio)
    participant API as Backend API
    participant LS as Lab Specimen (SUB-LS)
    participant OCR as AI OCR Service (SUB-PR-0011)
    participant PR as Patient Records (SUB-PR)
    participant DB as PostgreSQL
    participant Audit as Audit Service

    Note over Nurse,Phone: Nurse photographs paper lab order

    Nurse->>Phone: Take photo of lab order
    Phone->>Twilio: MMS to lab phone number (image + sender phone)
    Twilio->>API: POST /sms/webhook (from, to, media_url, body)
    API->>LS: Process inbound SMS lab order

    LS->>DB: INSERT sms_intake (status=received, from_phone, media_url)
    DB-->>LS: intake_id

    rect rgb(255, 243, 224)
        Note over LS,OCR: Phase 1 — AI OCR Extraction
        LS->>OCR: Extract structured data from lab order image
        OCR->>OCR: AI model processes image
        OCR-->>LS: Extracted JSON
    end

    Note over LS: Extracted fields:<br/>ordering_physician (name, NPI)<br/>patient (name, DOB, MRN)<br/>insurance (carrier, policy_id, group)<br/>tests[] (code, name, priority)<br/>clinical_notes / diagnosis (ICD-10)

    LS->>DB: UPDATE sms_intake SET extracted_data, status=pending_validation

    rect rgb(232, 245, 233)
        Note over LS,PR: Phase 2 — Cross-System Validation
        LS->>PR: Look up patient by name + DOB or MRN
        PR->>DB: SELECT patient WHERE match criteria
        DB-->>PR: Patient record (or not found)
        PR-->>LS: patient_id or UNRESOLVED

        LS->>DB: SELECT physician WHERE npi = extracted_npi
        DB-->>LS: Physician record (or not found)

        LS->>LS: Validate insurance against patient record
        LS->>LS: Validate test codes against lab test catalog
        LS->>LS: Compile validation results
    end

    alt All fields validated successfully
        LS->>DB: UPDATE sms_intake SET status=validated
        LS->>LS: Calculate proposed pickup time
        LS->>DB: INSERT lab_order (status=ordered, source=sms_intake)
        LS->>DB: INSERT lab_order_tests (one per test)

        LS->>Audit: Log CREATE lab_order (source: sms_intake)
        Audit->>DB: INSERT audit_log

        LS->>API: Compose confirmation SMS
        API->>Twilio: Send SMS reply
        Twilio->>Phone: SMS reply
        Phone-->>Nurse: Confirmation with pickup time

    else Validation issues found
        LS->>DB: UPDATE sms_intake SET status=clarification_needed, issues[]

        LS->>API: Compose clarification SMS
        API->>Twilio: Send SMS reply
        Twilio->>Phone: SMS reply
        Phone-->>Nurse: Clarification request with specific issues

        Note over Nurse,Phone: Nurse replies with corrections

        Nurse->>Phone: Reply SMS with corrections
        Phone->>Twilio: SMS (text reply or new photo)
        Twilio->>API: POST /sms/webhook (reply)
        API->>LS: Process clarification reply

        LS->>DB: SELECT sms_intake WHERE conversation matches
        LS->>OCR: Re-extract if new photo, or parse text corrections
        LS->>LS: Re-validate with corrected data
        LS->>DB: UPDATE sms_intake SET status=validated

        LS->>DB: INSERT lab_order (status=ordered, source=sms_intake)
        LS->>Audit: Log CREATE lab_order (source: sms_intake)

        LS->>API: Compose confirmation SMS
        API->>Twilio: Send SMS reply
        Twilio->>Phone: Confirmation with pickup time
        Phone-->>Nurse: Order confirmed
    end
```

#### SMS Confirmation Example

On successful validation, the system replies:

> Lab order confirmed
> Patient: Jane Doe (DOB 1985-03-15)
> Ordering MD: Dr. Smith (NPI 1234567890)
> Tests: CBC, BMP, TSH
> Insurance: Aetna — verified
> Proposed pickup: Today 2:30 PM
> Order #: LS-2026-00847

#### SMS Clarification Example

When validation issues are found:

> Lab order needs clarification:
> 1. Patient DOB is illegible — please confirm
> 2. Insurance policy # not found — please verify
> 3. Test "Lipid Panel" requires fasting — confirm fasting status
>
> Reply with corrections or send a clearer photo.

#### SMS Intake Validation Rules

| Field | Validation | On Failure |
|---|---|---|
| Ordering Physician | Match NPI against physician registry; confirm active/licensed status | Request physician name or NPI clarification |
| Patient Identity | Match (last_name + DOB) or MRN against SUB-PR patient records | Request patient DOB or MRN confirmation |
| Insurance | Verify carrier + policy ID against patient's insurance on file | Request insurance card photo or policy number |
| Test Codes | Match against lab test catalog; check special requirements (fasting, specimen type) | Flag unknown tests; ask for clarification |
| Clinical Notes / ICD-10 | Validate diagnosis codes if present; check medical necessity | Flag invalid ICD-10 codes |
| Specimen Priority | Parse STAT / Routine / Timed; apply scheduling rules | Default to Routine if unclear |

#### Pickup Time Calculation

The proposed specimen pickup time considers:

1. **Priority level** — STAT orders get next available slot; Routine follows standard schedule
2. **Nurse location** — Derived from registered phone number mapped to facility/unit
3. **Phlebotomy schedule** — Available collection rounds for the unit
4. **Test requirements** — Fasting tests may defer to morning collection windows
5. **Current queue depth** — Number of pending pickups in the same facility

---

## Proposed API Endpoints

| Method | Path | Description | Auth | Roles |
|---|---|---|---|---|
| POST | `/lab-orders` | Create a lab order for a patient encounter | Yes | physician, nurse |
| GET | `/lab-orders` | List lab orders (filterable by patient, encounter, status) | Yes | physician, nurse, admin |
| GET | `/lab-orders/{id}` | Get lab order details with results | Yes | physician, nurse, admin |
| PATCH | `/lab-orders/{id}/collect` | Record specimen collection | Yes | physician, nurse |
| PATCH | `/lab-orders/{id}/status` | Update order status (in_transit, processing) | Yes | physician, nurse, admin |
| PATCH | `/lab-orders/{id}/review` | Clinician acknowledges and reviews results | Yes | physician |
| PATCH | `/lab-orders/{id}/cancel` | Cancel a lab order | Yes | physician, admin |
| POST | `/lab-results` | Ingest results from external LIS | Yes | service_account |
| GET | `/patients/{id}/lab-results` | Get all lab results for a patient | Yes | physician, nurse, admin |
| POST | `/sms/webhook` | Twilio webhook — receive inbound MMS/SMS (lab order photo or clarification reply) | Twilio signature | — |
| GET | `/sms/intake` | List SMS intake records (filterable by status, phone, date) | Yes | admin, nurse |
| GET | `/sms/intake/{id}` | Get SMS intake details with extracted data and validation status | Yes | admin, nurse |
| POST | `/sms/intake/{id}/reprocess` | Re-trigger AI OCR extraction on an existing intake | Yes | admin |

---

## Data Model

```mermaid
erDiagram
    PATIENT ||--o{ LAB_ORDER : "has"
    ENCOUNTER ||--o{ LAB_ORDER : "originates"
    LAB_ORDER ||--o{ LAB_ORDER_TEST : "contains"
    LAB_ORDER_TEST ||--o| LAB_RESULT : "produces"
    SMS_INTAKE ||--o| LAB_ORDER : "creates"

    PATIENT {
        uuid id PK
        string first_name
        string last_name
        date date_of_birth
    }

    ENCOUNTER {
        uuid id PK
        uuid patient_id FK
        string status
    }

    SMS_INTAKE {
        uuid id PK
        string from_phone
        string media_url
        string status
        json extracted_data
        json validation_issues
        uuid resolved_patient_id FK
        uuid resolved_physician_id FK
        uuid lab_order_id FK
        int clarification_round
        timestamp proposed_pickup_at
        timestamp received_at
        timestamp validated_at
        timestamp created_at
    }

    LAB_ORDER {
        uuid id PK
        uuid patient_id FK
        uuid encounter_id FK
        uuid sms_intake_id FK
        string source
        string status
        string barcode
        uuid ordered_by FK
        uuid collected_by FK
        uuid reviewed_by FK
        timestamp ordered_at
        timestamp collected_at
        timestamp reviewed_at
        timestamp created_at
        timestamp updated_at
    }

    LAB_ORDER_TEST {
        uuid id PK
        uuid lab_order_id FK
        string test_code
        string test_name
        string category
    }

    LAB_RESULT {
        uuid id PK
        uuid lab_order_test_id FK
        string value
        string unit
        string reference_range
        string flag
        string interpretation
        timestamp resulted_at
    }
```

---

## Requirements

_To be defined. This PRD will be expanded with:_

- System-level requirements linking to SYS-REQ-0006 (clinical alerts) and SYS-REQ-0003 (audit)
- Subsystem requirements (SUB-LS-*) for lab specimen workflows
- Platform decomposition (BE, WEB, AND)
- Acceptance criteria and verification methods

### Preliminary Requirement Areas

| Area | Description | Related SYS-REQ |
|---|---|---|
| Authentication | Require authenticated session for all lab operations | SYS-REQ-0001 |
| RBAC | Enforce role-based access: physician/nurse order & collect; physician reviews | SYS-REQ-0005 |
| Order Management | CRUD for lab orders with state machine validation | — |
| Specimen Tracking | Barcode-based specimen identification and status tracking | — |
| Result Ingestion | Ingest results from external LIS via HL7/FHIR | SYS-REQ-0004 |
| Critical Alerts | Trigger real-time alerts for abnormal/critical lab values within 30 seconds | SYS-REQ-0006 |
| Medication Impact | Flag results that affect active prescriptions (e.g., renal function, drug levels) | SYS-REQ-0006 |
| Audit Trail | Log all lab order and result operations | SYS-REQ-0003 |
| Patient Timeline | Attach lab results to the patient record timeline | — |
| Reporting | Feed lab metrics (volumes, turnaround, abnormal rates) to dashboards | — |
| SMS Photo Intake | Receive lab order photos via MMS, extract data with AI OCR, validate, and reply with pickup time | — |
| OCR Extraction | Convert lab order image to structured JSON (physician, patient, insurance, tests, ICD-10) using AI OCR | SUB-PR-0011 |
| Order Validation | Cross-validate extracted fields against PMS records (physician registry, patient records, insurance, test catalog) | — |
| SMS Clarification | Request and process clarification replies when extracted data is incomplete or ambiguous | — |
| Pickup Scheduling | Calculate proposed specimen pickup time based on priority, location, phlebotomy schedule, and queue depth | — |
| Phone-to-Facility Mapping | Map registered nurse phone numbers to facility/unit for location-aware pickup scheduling | — |

---

## Key Workflows

- **Specimen collection ordering** — Clinician places lab order during an encounter
- **Specimen labeling and tracking** — Barcode-based collection, transport, and processing tracking
- **Lab result ingestion and display** — External LIS pushes results via HL7/FHIR; clinician views in patient record
- **Abnormal result alerting** — Critical values trigger real-time alerts to ordering clinician (SYS-REQ-0006)
- **Medication review trigger** — Critical lab results prompt medication interaction review (SUB-MM)
- **SMS photo lab order intake** — Nurse photographs paper lab order, texts it to lab phone number; AI OCR extracts structured data, system validates against PMS records (physician, patient, insurance, tests), and replies with proposed pickup time or clarification requests

---

## Known Limitations and Open Questions

- External LIS integration protocol (HL7 v2 vs FHIR R4) to be finalized with SYS-REQ-0004 implementation
- Offline specimen collection on Android requires offline-sync strategy (see SUB-PR-0003-AND pattern)
- Barcode format standard (Code 128, QR, etc.) TBD
- Whether lab results should be encrypted at rest like other PHI (likely yes per SYS-REQ-0002)
- SMS Gateway provider selection (Twilio assumed; alternatives: AWS SNS, Vonage) — needs HIPAA BAA
- PHI in SMS messages — MMS images and reply text may contain PHI; requires HIPAA-compliant SMS provider with BAA and message encryption
- AI OCR model selection — reuse SUB-PR-0011 document OCR or train/fine-tune a lab-order-specific model for higher accuracy on handwritten orders
- Clarification timeout policy — how long to wait for nurse reply before auto-cancelling the intake (proposed: 4 hours)
- Maximum clarification rounds before requiring in-app order entry (proposed: 3 rounds)
- Nurse phone number registration and verification flow — how are phone numbers mapped to authenticated PMS users and facilities
- Support for multiple images per SMS (e.g., multi-page lab orders)

---

## Related Documents

- [System Specification](../specs/system-spec.md)
- [System Requirements](../specs/requirements/SYS-REQ.md)
- [Patient Records (SUB-PR)](../specs/requirements/SUB-PR.md)
- [Clinical Workflow (SUB-CW)](../specs/requirements/SUB-CW.md)
- [Medication Management (SUB-MM)](../specs/requirements/SUB-MM.md)
- [Reporting & Analytics (SUB-RA)](../specs/requirements/SUB-RA.md)
- [Backend API Endpoints](../api/backend-endpoints.md)
- [Testing Strategy](../testing/testing-strategy.md)
