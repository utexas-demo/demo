# Feature: Authentication & User Management

**Date:** 2026-02-18
**Status:** Draft
**Branch:** `feature/authentication`
**Related Requirements:** SYS-REQ-0001, SYS-REQ-0005

---

## 1. Overview

The PMS requires a closed-registration authentication system where an administrator controls who can access the platform. Users cannot self-register. An admin user is seeded into the database on first deployment and is responsible for creating all subsequent user accounts. Users authenticate via one of four methods: Google OAuth, Microsoft OAuth, GitHub OAuth, or email/password. Each user can hold one or more roles within the organization.

---

## 2. Authentication Methods

### 2.1 OAuth 2.0 Providers

All OAuth providers use the Authorization Code flow with PKCE. The system supports three providers:

| Provider | Use Case | Identity Claim |
|---|---|---|
| Google | Organizations using Google Workspace | `email` from Google ID token |
| Microsoft | Organizations using Microsoft 365 / Azure AD | `preferred_username` or `email` from MS ID token |
| GitHub | Development and lab staff with GitHub accounts | `email` from GitHub user API |

**OAuth flow (all providers):**

1. User visits the login page and selects a provider.
2. Frontend redirects to the provider's authorization endpoint.
3. User authenticates with the provider (including any MFA the provider enforces).
4. Provider redirects back with an authorization code.
5. Backend exchanges the code for an ID token / access token.
6. Backend extracts the email from the token.
7. Backend looks up the email in the `users` table.
   - **Match found** and user is active → issue a PMS JWT session token.
   - **Match found** but user is inactive → reject with 403 ("Account disabled").
   - **No match** → reject with 403 ("Account not registered. Contact your administrator.").
8. If this is the user's first login via this provider, create a record in `user_oauth_accounts` linking the provider identity to the user.

**Key constraint:** OAuth is an authentication mechanism only — it does not create new users. The user must already exist in the system (created by an admin) with a matching email address.

### 2.2 Email/Password Authentication

For organizations that do not use OAuth or for users who prefer direct credentials.

**Flow:**

1. Admin creates a user account with an email address.
2. System generates a one-time invite token and sends an invite email to the user.
3. User clicks the invite link, sets their password, and activates their account.
4. On subsequent logins, user enters email + password.
5. Backend validates credentials and issues a PMS JWT session token.

**Password requirements:**
- Minimum 12 characters
- At least one uppercase, one lowercase, one digit, one special character
- Passwords stored as bcrypt hashes (cost factor 12)
- Account locks after 5 consecutive failed attempts (30-minute lockout)

---

## 3. User Management

### 3.1 Admin Seeding

On first deployment (database migration), the system seeds a default administrator account:

| Field | Value | Source |
|---|---|---|
| Email | Configurable | `ADMIN_SEED_EMAIL` environment variable |
| Name | Configurable | `ADMIN_SEED_NAME` environment variable |
| Password | Configurable | `ADMIN_SEED_PASSWORD` environment variable |
| Role | `admin` | Hardcoded |
| Status | `active` | Hardcoded |

The seed operation is **idempotent**: if a user with the seed email already exists, the migration skips the insert. The admin should change the seed password on first login.

### 3.2 User Creation (Admin-Only)

Only users with the `admin` role can create new accounts. The creation flow:

1. Admin navigates to User Management in the web interface.
2. Admin provides: email, full name, and one or more roles.
3. Backend validates:
   - Email is not already registered (unique constraint).
   - Each role exists in the system.
4. Backend creates the user with status `invited`.
5. Backend generates a one-time invite token (expires in 72 hours).
6. System sends an invite email with a link to set a password.
7. User clicks the link, sets a password, and their status becomes `active`.

Admins can also:
- **Deactivate** a user → status becomes `inactive`, all active sessions are revoked.
- **Reactivate** a user → status returns to `active`.
- **Update roles** → add or remove roles from a user at any time.
- **Resend invite** → generates a new invite token if the original expired.

### 3.3 User Statuses

| Status | Description |
|---|---|
| `invited` | Account created by admin, user has not yet set a password |
| `active` | User has set credentials and can authenticate |
| `inactive` | Account disabled by admin, cannot authenticate |

---

## 4. Role Model

### 4.1 Roles

The system defines four roles. These replace the existing role definitions in [SYS-REQ-0005](../specs/requirements/SYS-REQ.md) and [System Spec Section 5](../specs/system-spec.md).

| Role | Code | Description |
|---|---|---|
| Admin | `admin` | Full system management: user CRUD, configuration, compliance reports, all data access |
| Clinician | `clinician` | Clinical operations: patient records, encounters, prescriptions, clinical notes, lab results |
| Sales | `sales` | Commercial operations: patient intake, insurance verification, billing, financial reports |
| Lab Staff | `lab-staff` | Laboratory operations: lab orders, specimen tracking, result entry, lab reports |

### 4.2 Multi-Role Assignment

A user can hold **one or more roles** simultaneously. This supports scenarios such as:

- A physician who is also an admin (clinician + admin).
- A lab technician who handles patient intake (lab-staff + sales).
- A practice owner with full access (admin + clinician + sales + lab-staff).

Role assignment rules:
- Every user must have at least one role.
- Roles are assigned at user creation and can be modified by any admin.
- An admin cannot remove the `admin` role from themselves if they are the last admin (prevents lockout).
- Permission checks use the **union** of all the user's roles — if any of the user's roles grants access, access is allowed.

### 4.3 Role-Permission Matrix

Permissions are evaluated per endpoint. The matrix below defines access at the feature level:

| Feature Area | admin | clinician | sales | lab-staff |
|---|---|---|---|---|
| User management (CRUD) | Full | -- | -- | -- |
| Role assignment | Full | -- | -- | -- |
| Patient records | Full | Read/Write | Read | Read |
| Clinical encounters | Full | Read/Write | -- | Read |
| Prescriptions | Full | Read/Write | -- | Read |
| Lab orders & results | Full | Read/Write | -- | Read/Write |
| Billing & insurance | Full | Read | Read/Write | -- |
| Clinical reports | Full | Read | Read | Read |
| Compliance / audit logs | Full | -- | -- | -- |
| System configuration | Full | -- | -- | -- |
| Prompt management | Full | -- | -- | -- |

> **Note:** "Full" means create, read, update, and delete. "--" means no access (403).

---

## 5. Conceptual Data Model

### 5.1 Tables

**`users`**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | Primary key |
| `email` | VARCHAR(255) | Unique, not null |
| `name` | VARCHAR(255) | Not null |
| `password_hash` | VARCHAR(255) | Nullable (OAuth-only users may not have a password) |
| `status` | ENUM(`invited`, `active`, `inactive`) | Not null, default `invited` |
| `invite_token` | VARCHAR(255) | Nullable, unique |
| `invite_expires_at` | TIMESTAMP | Nullable |
| `failed_login_attempts` | INTEGER | Default 0 |
| `locked_until` | TIMESTAMP | Nullable |
| `created_at` | TIMESTAMP | Not null |
| `updated_at` | TIMESTAMP | Not null |

**`roles`**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | VARCHAR(50) | Unique, not null |
| `description` | TEXT | Nullable |

Seeded with: `admin`, `clinician`, `sales`, `lab-staff`.

**`user_roles`** (many-to-many join)

| Column | Type | Constraints |
|---|---|---|
| `user_id` | UUID | FK → `users.id`, not null |
| `role_id` | UUID | FK → `roles.id`, not null |
| `assigned_at` | TIMESTAMP | Not null |
| `assigned_by` | UUID | FK → `users.id`, not null |

Primary key: (`user_id`, `role_id`).

**`user_oauth_accounts`**

| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | Primary key |
| `user_id` | UUID | FK → `users.id`, not null |
| `provider` | ENUM(`google`, `microsoft`, `github`) | Not null |
| `provider_user_id` | VARCHAR(255) | Not null |
| `provider_email` | VARCHAR(255) | Not null |
| `created_at` | TIMESTAMP | Not null |

Unique constraint: (`provider`, `provider_user_id`).

### 5.2 Entity Relationships

```
users 1──────M user_roles M──────1 roles
  │
  1
  │
  M
user_oauth_accounts
```

---

## 6. API Endpoints

### 6.1 Authentication

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/auth/login` | Email/password login → returns JWT | No |
| GET | `/auth/oauth/{provider}/authorize` | Initiate OAuth flow (redirect to provider) | No |
| GET | `/auth/oauth/{provider}/callback` | OAuth callback → returns JWT | No |
| POST | `/auth/invite/accept` | Accept invite, set password → activates account | No (uses invite token) |
| POST | `/auth/logout` | Revoke current session | Yes |
| POST | `/auth/password/reset-request` | Request password reset email | No |
| POST | `/auth/password/reset` | Reset password with token | No (uses reset token) |

### 6.2 User Management (Admin-Only)

| Method | Endpoint | Description | Roles |
|---|---|---|---|
| GET | `/users` | List all users (paginated) | admin |
| POST | `/users` | Create a new user (sends invite) | admin |
| GET | `/users/{id}` | Get user details | admin |
| PUT | `/users/{id}` | Update user (name, email) | admin |
| PATCH | `/users/{id}/status` | Activate / deactivate user | admin |
| PUT | `/users/{id}/roles` | Replace user's roles | admin |
| POST | `/users/{id}/resend-invite` | Resend invite email | admin |
| GET | `/users/me` | Get current user's own profile | Any authenticated |

---

## 7. JWT Token Structure

Tokens issued by the PMS carry the user's roles for stateless authorization:

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "jane.doe@example.com",
  "name": "Jane Doe",
  "roles": ["clinician", "admin"],
  "iat": 1740000000,
  "exp": 1740001800
}
```

| Field | Description |
|---|---|
| `sub` | User UUID |
| `roles` | Array of all role codes assigned to the user |
| `exp` | Expiration (default: 30 minutes, configurable via `JWT_EXPIRY_MINUTES`) |

Refresh tokens (opaque, stored server-side) allow silent session renewal without re-authentication. Refresh token lifetime: 7 days.

---

## 8. Acceptance Criteria

### Authentication
1. A user can log in via Google, Microsoft, or GitHub OAuth and receive a valid JWT.
2. A user can log in via email/password and receive a valid JWT.
3. An OAuth login for an email not in the system returns 403.
4. An OAuth login for an inactive user returns 403.
5. Five consecutive failed email/password attempts lock the account for 30 minutes.
6. A locked account cannot authenticate via any method during the lockout period.

### User Management
7. On first deployment, a seeded admin account exists and can log in.
8. An admin can create a user by providing email, name, and roles.
9. A newly created user receives an invite email with a link to set their password.
10. An invite token expires after 72 hours; an admin can resend the invite.
11. An admin can deactivate a user, immediately revoking all active sessions.
12. An admin can reactivate a previously deactivated user.
13. A non-admin user receives 403 when attempting any user management operation.

### Roles
14. A user can be assigned multiple roles simultaneously.
15. The JWT `roles` claim contains all assigned role codes.
16. Endpoint access is granted if any of the user's roles is in the endpoint's allowed list.
17. An admin cannot remove the `admin` role from the last remaining admin user.
18. Role changes take effect on the next token issuance (existing tokens retain old roles until expiry).

---

## 9. Design Decisions

1. **Closed registration** — Users cannot self-register. This aligns with HIPAA's minimum necessary access principle: only authorized personnel, explicitly added by an administrator, gain access to the system.
2. **OAuth as authentication only** — OAuth providers verify identity but do not grant authorization. The user must pre-exist in the PMS database. This ensures the admin retains full control over who accesses the system.
3. **Multi-role via join table** — Roles are modeled as a many-to-many relationship rather than a single role column. This avoids the need for composite roles ("clinician-admin") and allows flexible permission combinations.
4. **Union-based permission evaluation** — When a user has multiple roles, permissions are the union (logical OR) across all roles. This is simpler than intersection-based models and matches the expected behavior (more roles = more access).
5. **Four roles replacing five** — The existing system defines physician, nurse, administrator, billing, and pharmacist. This feature consolidates to four broader roles (admin, clinician, sales, lab-staff) that better reflect the organization's operational structure. The `clinician` role covers physicians, nurses, and pharmacists. The `sales` role covers billing and patient intake.
6. **Bcrypt for password hashing** — Industry standard for password storage. Cost factor 12 provides a good balance between security and login latency.
7. **Provider-agnostic OAuth** — All three providers follow the same Authorization Code + PKCE flow, abstracted behind a common interface. Adding a new provider requires only configuration (client ID, secret, endpoints), not code changes.

---

## 10. Relationship to Existing Requirements

This feature impacts two system-level requirements:

| Requirement | Current State | Impact |
|---|---|---|
| **SYS-REQ-0001** (MFA) | Specifies TOTP-based MFA | OAuth providers enforce their own MFA policies (Google, Microsoft, GitHub all support MFA). For email/password auth, TOTP support is deferred to a follow-up feature. The OAuth flow satisfies the MFA intent for OAuth users. |
| **SYS-REQ-0005** (RBAC) | Defines 5 roles: physician, nurse, administrator, billing, pharmacist | This feature redefines the role model to 4 roles: admin, clinician, sales, lab-staff. SYS-REQ-0005, the system spec (Section 5), and all SUB-* role references will need to be updated to reflect the new role model. |

**Artifacts requiring updates after implementation:**
- `SYS-REQ.md` — Update SYS-REQ-0001 and SYS-REQ-0005 descriptions and acceptance criteria
- `system-spec.md` — Update Section 5 (User Roles) with the new 4-role model
- `SUB-PR.md`, `SUB-CW.md`, `SUB-MM.md`, `SUB-RA.md`, `SUB-PM.md` — Update role references in auth requirements
- `requirements-governance.md` — Verify conflict resolutions referencing old roles remain valid
- `traceability-matrix.md` — Add test cases for authentication and user management

---

## 11. Open Questions

1. **TOTP for email/password users** — Should TOTP-based MFA be required for email/password users in v1, or deferred? OAuth users already benefit from provider-side MFA.
2. **Session concurrency** — Should users be limited to one active session, or allowed multiple simultaneous sessions (e.g., web + mobile)?
3. **Password rotation policy** — Should passwords expire after a configurable period (e.g., 90 days)?
4. **OAuth provider configurability** — Should the enabled OAuth providers be configurable per deployment (e.g., some deployments only use Microsoft)?
