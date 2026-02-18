# Product Requirements Document: Patient Management

**Document ID:** PRD-PMS-PR-001
**Version:** 1.0
**Date:** February 18, 2026
**Status:** Draft
**Requirements:** SUB-PR-0001 through SUB-PR-0008

---

## 1. Executive Summary

This PRD defines the backend capabilities for the Patient Records subsystem (SUB-PR). Patient Records is the foundational data layer for all other PMS subsystems — Clinical Workflow, Medication Management, and Reporting & Analytics all depend on it.

This document covers the full scope of backend patient management: CRUD operations, authentication, RBAC, PHI encryption, audit logging, email uniqueness, patient search, and paginated listing. Vision/AI capabilities (SUB-PR-0009 through SUB-PR-0012) are covered separately in [Vision Capabilities](vision-capabilities.md).

---

## 2. Current State

The following backend requirements are already implemented and verified:

| Req ID | Description | Status | Module(s) |
|---|---|---|---|
| SUB-PR-0001-BE | JWT auth on all patient API endpoints | Implemented | `middleware/auth.py`, `routers/patients.py` |
| SUB-PR-0002-BE | Role-based access control (admin/physician/nurse read & create; admin/physician update; admin deactivate) | Implemented | `middleware/auth.py:require_role`, `routers/patients.py` |
| SUB-PR-0003-BE | REST CRUD for patient demographics with optimistic locking and deactivation guard | Verified | `routers/patients.py`, `services/patient_service.py`, `models/patient.py` |
| SUB-PR-0004-BE | SSN encryption at rest via Fernet (AES-128-CBC); AES-256-GCM migration pending | Verified (dev) | `services/encryption_service.py`, `services/patient_service.py` |
| SUB-PR-0005-BE | Audit log all patient record access and modifications | Implemented | `services/audit_service.py`, `routers/patients.py` |
| SUB-PR-0006-BE | Unique email constraint with IntegrityError → 409 handling | Verified | `models/patient.py`, `services/patient_service.py` |

---

## 3. Scope of This Feature Branch

This feature branch (`feature/patient-search-pagination`) implements the two remaining non-AI backend requirements:

| Req ID | Description | Status | Target |
|---|---|---|---|
| SUB-PR-0007-BE | Patient search API endpoint (last name, DOB, ID) | Not Started | This branch |
| SUB-PR-0008-BE | Paginated patient list API endpoint (default 20/page) | Not Started | This branch |

**Conflict resolution:** Per DC-PR-02, SUB-PR-0008 supersedes the unbounded list behavior of SUB-PR-0003. The existing `GET /patients/` endpoint must be refactored to return paginated results by default.

---

## 4. Functional Requirements

### 4.1 Patient Search (SUB-PR-0007-BE)

**Endpoint:** `GET /patients/search`

**Description:** Search for patients by last name, date of birth, or patient ID. Results are paginated (reuses the pagination contract from SUB-PR-0008-BE).

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `last_name` | string | No | Case-insensitive partial match (e.g., `smi` matches `Smith`, `Smithson`) |
| `date_of_birth` | date (YYYY-MM-DD) | No | Exact match |
| `patient_id` | UUID | No | Exact match |
| `page` | integer | No | Page number (default: 1, minimum: 1) |
| `page_size` | integer | No | Results per page (default: 20, minimum: 1, maximum: 100) |

**Validation Rules:**
- At least one search parameter (`last_name`, `date_of_birth`, or `patient_id`) must be provided. Return 422 if none are supplied.
- Search parameters are combinable (AND logic). Providing `last_name=Smith&date_of_birth=1990-01-15` returns patients matching both.
- Only active patients (`is_active = true`) are returned.

**Response Schema:**
```json
{
  "items": [
    {
      "id": "uuid",
      "first_name": "string",
      "last_name": "string",
      "date_of_birth": "date",
      "gender": "string",
      "email": "string | null",
      "phone": "string | null",
      "address": "string | null",
      "is_active": true,
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

**Auth:** Requires JWT with role `admin`, `physician`, or `nurse` (same as existing read endpoints).

**Audit:** Each search request is logged via `audit_service.log_action` with action `search`, resource_type `patient`, and details containing the search parameters used.

### 4.2 Paginated Patient List (SUB-PR-0008-BE)

**Endpoint:** `GET /patients/` (refactor of existing endpoint)

**Description:** The existing unbounded list endpoint is refactored to return paginated results. Default page size is 20 per the requirement.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page` | integer | No | Page number (default: 1, minimum: 1) |
| `page_size` | integer | No | Results per page (default: 20, minimum: 1, maximum: 100) |

**Behavior:**
- Returns only active patients (`is_active = true`), consistent with the current implementation.
- Results are ordered by `last_name ASC, first_name ASC` for deterministic pagination.
- Response uses the same paginated envelope schema as the search endpoint (Section 4.1).

**Auth:** Requires JWT with role `admin`, `physician`, or `nurse` (unchanged).

**Audit:** Logged with action `read`, resource_type `patient`, details `list_patients` (unchanged).

**Breaking Change:** The response shape changes from `PatientResponse[]` to a paginated envelope `{ items, total, page, page_size, total_pages }`. API consumers must update accordingly.

---

## 5. Shared Pagination Contract

Both endpoints share a common pagination schema to avoid duplication:

**Request parameters:** `page` (int, default 1) and `page_size` (int, default 20, max 100).

**Response envelope:**

| Field | Type | Description |
|---|---|---|
| `items` | `PatientResponse[]` | The page of results |
| `total` | integer | Total matching records |
| `page` | integer | Current page number |
| `page_size` | integer | Requested page size |
| `total_pages` | integer | Ceiling of `total / page_size` |

**Implementation:** A reusable `PaginatedResponse` Pydantic schema in `schemas/patient.py` and a shared pagination utility in the service layer.

---

## 6. Non-Functional Requirements

| Concern | Requirement |
|---|---|
| Performance | Search and list queries must respond within 2 seconds for up to 10,000 patient records (SYS-REQ-0007) |
| Database indexing | Add indexes on `last_name` and `date_of_birth` to support search performance |
| Security | No PHI (SSN) is exposed in search results — `ssn_encrypted` is excluded from `PatientResponse` (existing behavior) |
| HIPAA audit | All search and list requests are audit-logged (SUB-PR-0005-BE) |

---

## 7. API Summary

| Method | Endpoint | Description | Roles | Req ID |
|---|---|---|---|---|
| GET | `/patients/` | Paginated list of active patients | admin, physician, nurse | SUB-PR-0008-BE |
| GET | `/patients/search` | Search patients by name, DOB, or ID | admin, physician, nurse | SUB-PR-0007-BE |
| POST | `/patients/` | Create a new patient | admin, physician, nurse | SUB-PR-0003-BE |
| GET | `/patients/{id}` | Get patient by ID | admin, physician, nurse | SUB-PR-0003-BE |
| PATCH | `/patients/{id}` | Update patient demographics | admin, physician | SUB-PR-0003-BE |
| DELETE | `/patients/{id}` | Deactivate patient (soft delete) | admin | SUB-PR-0003-BE |

---

## 8. Acceptance Criteria

### SUB-PR-0007-BE — Patient Search
1. `GET /patients/search?last_name=smi` returns patients whose last name starts with "smi" (case-insensitive).
2. `GET /patients/search?date_of_birth=1990-01-15` returns patients born on that date.
3. `GET /patients/search?patient_id={uuid}` returns the matching patient.
4. Combined filters use AND logic.
5. Deactivated patients are excluded from results.
6. Request with no search parameters returns 422.
7. Results are paginated with the shared envelope schema.
8. Each search is audit-logged.
9. Unauthenticated requests return 401; unauthorized roles return 403.

### SUB-PR-0008-BE — Paginated Patient List
1. `GET /patients/` returns the first page of 20 active patients by default.
2. `GET /patients/?page=2&page_size=10` returns the second page of 10 results.
3. Response includes `total`, `page`, `page_size`, and `total_pages`.
4. Results are ordered by `last_name ASC, first_name ASC`.
5. `page_size` exceeding 100 is clamped or returns 422.
6. Each request is audit-logged.

---

## 9. Out of Scope

| Item | Reason | Tracked By |
|---|---|---|
| Optimistic locking (`version` column) | Resolved in requirements (RC-BE-01) but already verified in SUB-PR-0003-BE | — |
| Deactivation guard (block if active encounters) | Resolved in requirements (RC-BE-06) but requires encounter subsystem coordination | SUB-PR-0003-BE |
| AES-256-GCM encryption migration | Separate infrastructure concern (DC-PR-01, PC-BE-01) | SUB-PR-0004-BE |
| Vision/AI endpoints | Separate feature branch | SUB-PR-0009 through SUB-PR-0012 |
| Web and Android frontend | Separate repositories | SUB-PR-0007-WEB, SUB-PR-0008-WEB, SUB-PR-0007-AND, SUB-PR-0008-AND |

---

## 10. Traceability

| Requirement | Test Case | Module(s) |
|---|---|---|
| SUB-PR-0007-BE | TST-PR-0007-BE | `routers/patients.py`, `services/patient_service.py` |
| SUB-PR-0008-BE | TST-PR-0008-BE | `routers/patients.py`, `services/patient_service.py`, `schemas/patient.py` |
