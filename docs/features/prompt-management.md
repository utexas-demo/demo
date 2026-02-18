# Prompt Management — Product Requirements Document

**Document ID:** PRD-PMS-PM-001
**Version:** 1.0
**Date:** 2026-02-18
**Parent Requirements:** [SUB-PM](../specs/requirements/SUB-PM.md), [SYS-REQ-0011](../specs/requirements/SYS-REQ.md)
**Status:** Draft

---

## 1. Overview

The Prompt Management feature provides a centralized web interface for creating, editing, versioning, and comparing AI prompts used across the PMS — including OpenClaw skills, MiniMax M2.5 agents, and clinical document drafting templates. Administrators manage prompts through a dedicated CRUD interface with automatic version tracking, while physicians have read-only access. An LLM-powered comparison tool generates natural-language diff summaries between any two versions of a prompt.

This document serves as the implementation reference for the SUB-PM subsystem, covering user stories, UI specifications, API contracts, data model, and acceptance criteria.

---

## 2. Problem Statement

- **Prompts scattered across code and config** — AI prompts are currently hardcoded in application code or buried in configuration files. There is no centralized place to discover, read, or manage them.
- **No version history** — When a prompt is changed, the previous version is lost. There is no way to audit what changed, when, or by whom. Reverting a bad change requires code archaeology.
- **No way to compare iterations** — Teams iterating on prompt quality have no tooling to see what changed between versions or understand the semantic impact of edits.

---

## 3. User Stories

| ID | Role | Story | Req ID |
|----|------|-------|--------|
| US-PM-01 | Admin | As an admin, I can create a new prompt with a name and text so that prompts are centrally managed | SUB-PM-0003 |
| US-PM-02 | Admin | As an admin, I can edit a prompt's text, which automatically creates a new immutable version | SUB-PM-0003, SUB-PM-0004 |
| US-PM-03 | Admin, Physician | As an admin or physician, I can view the list of all prompts | SUB-PM-0002, SUB-PM-0003 |
| US-PM-04 | Admin, Physician | As an admin or physician, I can view a prompt's details and current text | SUB-PM-0002, SUB-PM-0003 |
| US-PM-05 | Admin, Physician | As an admin or physician, I can view the paginated version history for a prompt | SUB-PM-0006 |
| US-PM-06 | Admin, Physician | As an admin or physician, I can select two versions and get an LLM-generated diff summary | SUB-PM-0007 |
| US-PM-07 | Admin | As an admin, I can delete a prompt that is no longer needed | SUB-PM-0003 |

---

## 4. User Interface (Web Frontend)

All prompt management pages live under `/prompts` in the Next.js web frontend. Authentication is enforced via the `requireRole` guard (follows PC-WEB-01 / PC-WEB-03 precedent).

### 4.1 Prompt List Page — `/prompts`

**Auth:** Admin (full access), Physician (read-only — no "Create Prompt" button)
**Req:** SUB-PM-0003-WEB

**Layout:**
- Page title: "Prompt Management"
- "Create Prompt" button (top-right, admin-only)
- Table with columns:
  - **Name** — clickable link to detail page
  - **Current Version** — integer version number (e.g., "v3")
  - **Last Updated** — relative timestamp (e.g., "2 hours ago")
  - **Actions** — "Edit" and "Delete" buttons (admin-only)
- Empty state: "No prompts yet. Create your first prompt to get started."

### 4.2 Create Prompt Page — `/prompts/new`

**Auth:** Admin only
**Req:** SUB-PM-0003-WEB

**Layout:**
- Page title: "Create Prompt"
- Form fields:
  - **Name** — text input, required, must be unique
  - **Text** — textarea or code editor (monospaced), required
- "Create" submit button
- On success: redirect to prompt detail page
- On 409 (duplicate name): display inline error "A prompt with this name already exists"

### 4.3 Prompt Detail / Edit Page — `/prompts/[id]`

**Auth:** Admin (edit), Physician (read-only view)
**Req:** SUB-PM-0003-WEB, SUB-PM-0004-WEB

**Layout:**
- Page title: prompt name
- Version indicator badge: "Version 5" (current version number)
- **Prompt text** — displayed in a textarea (editable for admin, read-only for physician)
- Notice below textarea (admin-only): "Saving creates a new version"
- "Save" button (admin-only) — submits PUT request, creates new version
- Sidebar or tab links:
  - "Version History" → `/prompts/[id]/versions`
  - "Compare Versions" → `/prompts/[id]/compare`
- "Delete" button (admin-only, with confirmation dialog)

### 4.4 Version History Page — `/prompts/[id]/versions`

**Auth:** Admin, Physician
**Req:** SUB-PM-0006-WEB

**Layout:**
- Page title: "Version History — {prompt name}"
- Paginated list (default 20 per page, ordered newest first):
  - **Version** — version number (e.g., "v3")
  - **Created At** — ISO 8601 timestamp
  - **Created By** — username
- Checkboxes to select exactly two versions
- "Compare Selected" button (enabled when exactly 2 versions are checked) → navigates to comparison page with selected versions

### 4.5 Version Comparison Page — `/prompts/[id]/compare`

**Auth:** Admin, Physician
**Req:** SUB-PM-0007-WEB

**Layout:**
- Page title: "Compare Versions — {prompt name}"
- Two version selectors (dropdowns), pre-populated if navigated from history page
- Side-by-side display of both version texts (monospaced, read-only)
- "Generate Diff Summary" button → calls `POST /prompts/{id}/versions/compare`
- Loading state while LLM processes (up to 30 seconds)
- Natural-language diff summary displayed below in a card/panel
- Error handling: timeout message, rate limit message (10 req/min/user)

---

## 5. API Contracts (Backend)

**Base path:** `/prompts`
**Auth:** JWT Bearer token via `require_auth` middleware
**Req:** SUB-PM-0001-BE, SUB-PM-0002-BE

### 5.1 Endpoint Summary

| Method | Path | Description | Auth | Req ID |
|--------|------|-------------|------|--------|
| POST | `/prompts/` | Create a new prompt | admin | SUB-PM-0003-BE |
| GET | `/prompts/` | List all prompts | admin, physician | SUB-PM-0003-BE |
| GET | `/prompts/{id}` | Get prompt detail | admin, physician | SUB-PM-0003-BE |
| PUT | `/prompts/{id}` | Update prompt text (auto-versions) | admin | SUB-PM-0003-BE, SUB-PM-0004-BE |
| DELETE | `/prompts/{id}` | Delete a prompt | admin | SUB-PM-0003-BE |
| GET | `/prompts/{id}/versions` | Paginated version history | admin, physician | SUB-PM-0006-BE |
| POST | `/prompts/{id}/versions/compare` | LLM version comparison | admin, physician | SUB-PM-0007-BE |

### 5.2 POST `/prompts/` — Create Prompt

**Request:**
```json
{
  "name": "string (required, unique)",
  "text": "string (required)"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "name": "string",
  "current_text": "string",
  "current_version": 1,
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601",
  "created_by": "string"
}
```

**Error (409):**
```json
{ "detail": "A prompt with this name already exists" }
```

### 5.3 GET `/prompts/` — List Prompts

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "string",
    "current_version": 3,
    "updated_at": "ISO 8601"
  }
]
```

### 5.4 GET `/prompts/{id}` — Get Prompt Detail

**Response (200):**
```json
{
  "id": "uuid",
  "name": "string",
  "current_text": "string",
  "current_version": 5,
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601",
  "created_by": "string"
}
```

**Error (404):**
```json
{ "detail": "Prompt not found" }
```

### 5.5 PUT `/prompts/{id}` — Update Prompt Text

Creates a new immutable version. The version number is serialized via `SELECT MAX(version) ... FOR UPDATE` to prevent concurrent conflicts.

**Request:**
```json
{
  "text": "string (required)"
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "name": "string",
  "current_text": "string",
  "current_version": 6,
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601",
  "created_by": "string"
}
```

**Error (404):**
```json
{ "detail": "Prompt not found" }
```

### 5.6 DELETE `/prompts/{id}` — Delete Prompt

**Response (204):** No content

**Error (404):**
```json
{ "detail": "Prompt not found" }
```

### 5.7 GET `/prompts/{id}/versions` — Version History

**Query params:** `page` (int, default 1), `size` (int, default 20)

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "version": 5,
      "text": "string",
      "created_at": "ISO 8601",
      "created_by": "string"
    }
  ],
  "total": 42,
  "page": 1,
  "size": 20
}
```

### 5.8 POST `/prompts/{id}/versions/compare` — LLM Version Comparison

Accepts two version numbers, retrieves both texts, calls the Anthropic Claude API with the managed comparison prompt, and returns a natural-language diff summary.

**Request:**
```json
{
  "version_a": 3,
  "version_b": 5
}
```

**Response (200):**
```json
{
  "version_a": 3,
  "version_b": 5,
  "summary": "Version 5 adds explicit patient safety guardrails to the discharge summary template. The tone instructions were softened from 'strictly clinical' to 'empathetic but professional'. The medication reconciliation section was expanded with a new bullet requiring allergy cross-reference."
}
```

**Error (400):**
```json
{ "detail": "Both versions must belong to this prompt" }
```

**Error (429):**
```json
{ "detail": "Rate limit exceeded. Maximum 10 comparisons per minute." }
```

**Error (504):**
```json
{ "detail": "LLM comparison timed out. Please try again." }
```

---

## 6. Data Model

### 6.1 `prompts` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default gen_random_uuid() | Prompt identifier |
| `name` | VARCHAR(255) | UNIQUE, NOT NULL | Human-readable prompt name |
| `current_text` | TEXT | NOT NULL | Current prompt text (denormalized from latest version for fast reads) |
| `created_at` | TIMESTAMPTZ | NOT NULL, default NOW() | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | NOT NULL, default NOW() | Last update timestamp |
| `created_by` | VARCHAR(255) | NOT NULL | Username of the creator |

### 6.2 `prompt_versions` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, default gen_random_uuid() | Version record identifier |
| `prompt_id` | UUID | FK → prompts.id, NOT NULL | Parent prompt |
| `version` | INTEGER | NOT NULL | Auto-incremented version number (per prompt) |
| `text` | TEXT | NOT NULL | Immutable snapshot of prompt text at this version |
| `created_at` | TIMESTAMPTZ | NOT NULL, default NOW() | Version creation timestamp |
| `created_by` | VARCHAR(255) | NOT NULL | Username of the editor |

**Constraints:**
- UNIQUE(`prompt_id`, `version`) — no duplicate version numbers per prompt
- Version serialization: `SELECT MAX(version) FROM prompt_versions WHERE prompt_id = ? FOR UPDATE` (DC-PM-02)
- Versions are immutable once created — no UPDATE or DELETE on `prompt_versions` rows

### 6.3 Entity Relationship

```
prompts 1 ──── * prompt_versions
  (id)            (prompt_id FK)
```

---

## 7. LLM Integration

**Req:** SUB-PM-0007-BE, SUB-PM-0007-AI

### 7.1 Provider & Model

- **Provider:** Anthropic Claude API (already configured for OpenClaw integration)
- **Model:** `claude-sonnet-4-20250514` — cost-effective for comparison tasks
- **Prompt text is NOT PHI** — external API calls to Anthropic are acceptable

### 7.2 Comparison Prompt Template

The comparison template is itself stored as a managed prompt, bootstrapped via database migration (DC-PM-03). This allows the comparison prompt to be iterated on through the same versioning system.

**Bootstrap migration seed:**
```
You are a prompt engineering assistant. Compare these two versions of an AI prompt and provide a clear, concise summary of the differences.

Version A:
{version_a_text}

Version B:
{version_b_text}

Summarize the key differences in 2-4 sentences. Focus on:
- What was added, removed, or changed
- How the tone or style shifted
- Any changes to instructions, constraints, or guardrails
- Whether the scope of the prompt expanded or narrowed

Be specific and reference concrete changes. Do not restate the full prompt text.
```

### 7.3 Operational Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Timeout | 30 seconds | Prevents hung requests from blocking the UI |
| Rate limit | 10 requests/min/user | Prevents abuse and controls API costs (RC-BE-10) |
| Max tokens | 500 | Comparison summaries should be concise |
| Temperature | 0.3 | Consistent, factual output |

---

## 8. Design Decisions

These decisions are documented in [SUB-PM.md](../specs/requirements/SUB-PM.md) and summarized here for implementation context:

1. **No Android (AND) requirements** — Prompt management is an administrative activity, not a mobile clinical workflow. Android requirements can be added later via governance procedure 2.1.

2. **Anthropic Claude API as LLM provider** — Already configured for the OpenClaw integration. Model `claude-sonnet-4-20250514` is cost-effective for comparison tasks. Prompt text is NOT PHI, so external API calls are acceptable.

3. **Version serialization via `SELECT MAX(version) ... FOR UPDATE`** — Prevents concurrent version number conflicts. Mirrors the RC-BE-01 pattern used in other subsystems.

4. **Prompt name uniqueness via DB constraint** — The database unique constraint is authoritative. The service layer catches `IntegrityError` and returns HTTP 409. Mirrors the SUB-PR-0006 pattern.

5. **Comparison prompt as managed prompt** — The LLM comparison template is itself stored as a managed prompt and bootstrapped via database migration. This allows the comparison prompt to be versioned and improved through the same system it powers.

---

## 9. Acceptance Criteria

Each criterion maps to a SUB-PM domain requirement and defines a testable condition.

### SUB-PM-0001 — Authentication

| ID | Criterion |
|----|-----------|
| AC-PM-01 | All prompt management API endpoints return 401 when no JWT token is provided |
| AC-PM-02 | All prompt management API endpoints return 401 when an expired or invalid JWT token is provided |
| AC-PM-03 | All prompt management web pages redirect unauthenticated users to the login page |

### SUB-PM-0002 — Role-Based Access Control

| ID | Criterion |
|----|-----------|
| AC-PM-04 | Admin users can create, read, update, and delete prompts |
| AC-PM-05 | Physician users can read prompts and view version history but cannot create, update, or delete |
| AC-PM-06 | Users with other roles receive 403 on all prompt endpoints |
| AC-PM-07 | The "Create Prompt" button is not rendered for physician users |

### SUB-PM-0003 — CRUD Operations

| ID | Criterion |
|----|-----------|
| AC-PM-08 | Creating a prompt with a unique name and text returns 201 and the prompt object with version 1 |
| AC-PM-09 | Creating a prompt with a duplicate name returns 409 with an error message |
| AC-PM-10 | Listing prompts returns all prompts with name, current version, and last updated |
| AC-PM-11 | Getting a prompt by ID returns the full prompt object including current text |
| AC-PM-12 | Getting a non-existent prompt ID returns 404 |
| AC-PM-13 | Deleting a prompt returns 204 and the prompt is no longer retrievable |

### SUB-PM-0004 — Auto-Versioning

| ID | Criterion |
|----|-----------|
| AC-PM-14 | Updating a prompt's text creates a new version row in `prompt_versions` with an incremented version number |
| AC-PM-15 | The prompt's `current_text` and `updated_at` are updated to reflect the new version |
| AC-PM-16 | Concurrent updates to the same prompt produce sequential, non-duplicate version numbers |
| AC-PM-17 | Existing version rows are never modified or deleted |
| AC-PM-18 | The UI displays a "saving creates a new version" notice before submission |

### SUB-PM-0005 — Audit Logging

| ID | Criterion |
|----|-----------|
| AC-PM-19 | Every prompt operation (create, read, update, delete, version_create, version_compare) produces an audit log entry |
| AC-PM-20 | Audit log entries include user_id, action, resource_type (`prompt`), resource_id, timestamp, and IP address |

### SUB-PM-0006 — Version History

| ID | Criterion |
|----|-----------|
| AC-PM-21 | Version history endpoint returns versions ordered by version number descending |
| AC-PM-22 | Pagination works correctly with `page` and `size` parameters (default: page=1, size=20) |
| AC-PM-23 | Response includes `total` count for UI pagination controls |

### SUB-PM-0007 — LLM Version Comparison

| ID | Criterion |
|----|-----------|
| AC-PM-24 | Comparing two valid versions returns a natural-language diff summary |
| AC-PM-25 | Comparing versions that don't belong to the specified prompt returns 400 |
| AC-PM-26 | LLM calls that exceed 30 seconds return 504 |
| AC-PM-27 | Users exceeding 10 comparisons per minute receive 429 |
| AC-PM-28 | The comparison prompt template is stored as a managed prompt and can be versioned |

---

## 10. Known Limitations & Future Work

### Current Limitations (v1.0)

- **No Android UI** — Prompt management is admin-only and web-only. Android support can be added later via governance procedure 2.1.
- **No prompt template variables** — Prompts are stored as plain text. Template variable syntax (e.g., `{patient_name}`) is not validated or parsed.
- **No prompt categorization or tagging** — All prompts are in a flat list. No folders, tags, or categories.
- **No prompt usage tracking** — No visibility into which prompts are actively used by which subsystems.

### Future Work

- **Prompt A/B testing** — Compare prompt variants in production with measurable outcomes.
- **Usage analytics** — Track which prompts are called, by which services, and how often.
- **Template variables** — Define and validate template parameters with type constraints.
- **Prompt categorization** — Tags or folders for organizing prompts by subsystem or purpose.
- **Rollback** — One-click revert to a previous version.
- **Prompt playground** — Test a prompt with sample inputs directly from the management UI.
