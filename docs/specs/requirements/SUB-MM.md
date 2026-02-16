# Subsystem Requirements: Medication Management (SUB-MM)

**Document ID:** PMS-SUB-MM-001
**Version:** 1.2
**Date:** 2026-02-16
**Parent:** [System Requirements](SYS-REQ.md)

---

## Scope

The Medication Management subsystem handles the medication catalog, prescriptions, drug interaction checking, and formulary management. It is the critical safety layer for prescription workflows.

## Requirements

| Req ID | Parent | Description | Verification | Status |
|---|---|---|---|---|
| SUB-MM-0001 | SYS-REQ-0006 | Check new prescriptions against patient's active medications for interactions within 5 seconds | Test | Placeholder |
| SUB-MM-0002 | SYS-REQ-0006 | Classify drug interactions by severity: contraindicated, major, moderate, minor | Test | Placeholder |
| SUB-MM-0003 | SYS-REQ-0002 | Encrypt all prescription data containing PHI using AES-256 | Test / Inspection | Placeholder |
| SUB-MM-0004 | SYS-REQ-0003 | Log all prescription events (create, modify, dispense) with prescriber ID and timestamp | Test | Placeholder |
| SUB-MM-0005 | SYS-REQ-0004 | Support FHIR R4 MedicationRequest and MedicationDispense resources | Test / Demo | Not Started |
| SUB-MM-0006 | SYS-REQ-0001 | Require authenticated session for all medication operations | Test | Placeholder |
| SUB-MM-0007 | SYS-REQ-0005 | Enforce RBAC: only physicians can prescribe; nurses can view; pharmacists can dispense | Test | Placeholder |
| SUB-MM-0008 | — | Support prescription status lifecycle: active → completed/cancelled | Test | Placeholder |
| SUB-MM-0009 | — | Track remaining refills and prevent prescriptions with zero refills from being filled | Test | Not Started |

## Platform Decomposition

### Backend (BE) — 9 requirements

| Platform Req ID | Parent | Description | Module(s) | Test Case(s) | Status |
|---|---|---|---|---|---|
| SUB-MM-0001-BE | SUB-MM-0001 | Drug interaction check API endpoint (< 5 sec response) | `services/interaction_checker.py` | TST-MM-0001-BE | Placeholder |
| SUB-MM-0002-BE | SUB-MM-0002 | Interaction severity classification logic | `services/interaction_checker.py` | TST-MM-0002-BE | Placeholder |
| SUB-MM-0003-BE | SUB-MM-0003 | Encrypt prescription PHI at rest using AES-256 | `services/encryption_service.py` | TST-MM-0003-BE | Placeholder |
| SUB-MM-0004-BE | SUB-MM-0004 | Audit log all prescription events | `services/audit_service.py` | TST-MM-0004-BE | Placeholder |
| SUB-MM-0005-BE | SUB-MM-0005 | FHIR R4 MedicationRequest/MedicationDispense endpoints | — | TST-MM-0005-BE | Not Started |
| SUB-MM-0006-BE | SUB-MM-0006 | Enforce JWT auth on all medication API endpoints | `middleware/auth.py` | TST-MM-0006-BE | Placeholder |
| SUB-MM-0007-BE | SUB-MM-0007 | Enforce RBAC on medication endpoints (physician prescribe, nurse view, pharmacist dispense) | `middleware/auth.py:require_role` | TST-MM-0007-BE | Placeholder |
| SUB-MM-0008-BE | SUB-MM-0008 | Prescription status lifecycle API (active → completed/cancelled) | `models/medication.py` | TST-MM-0008-BE | Placeholder |
| SUB-MM-0009-BE | SUB-MM-0009 | Refill tracking and zero-refill prevention logic | — | TST-MM-0009-BE | Not Started |

### Web Frontend (WEB) — 2 requirements

| Platform Req ID | Parent | Description | Module(s) | Test Case(s) | Status |
|---|---|---|---|---|---|
| SUB-MM-0001-WEB | SUB-MM-0001 | Drug interaction warning display on medication page | `app/medications/page.tsx` | TST-MM-0001-WEB | Not Started |
| SUB-MM-0006-WEB | SUB-MM-0006 | Auth guard for medication pages | `lib/auth.ts` | TST-MM-0006-WEB | Scaffolded |

### Android (AND) — 2 requirements

| Platform Req ID | Parent | Description | Module(s) | Test Case(s) | Status |
|---|---|---|---|---|---|
| SUB-MM-0001-AND | SUB-MM-0001 | Drug interaction warning display on medications screen | `ui/medications/MedicationsScreen.kt` | TST-MM-0001-AND | Not Started |
| SUB-MM-0006-AND | SUB-MM-0006 | Auth interceptor for medication API calls | `data/api/AuthInterceptor.kt` | TST-MM-0006-AND | Scaffolded |
