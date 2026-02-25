# Authentication Bypass Guide

**Applies to:** PMS Backend
**Requirement:** [SYS-REQ-0016](../specs/requirements/SYS-REQ.md#sys-req-0016-authentication-bypass-for-development) | [ADR-0023](../architecture/0023-auth-bypass-flag-for-development.md)
**Last Updated:** 2026-02-25

---

## Overview

The PMS backend supports disabling authentication for local development and CI testing via the `AUTH_ENABLED` environment variable. When disabled, **all requests authenticate as the real seeded admin user** — the system queries the database for the admin account and uses their actual UUID and roles. This means `/users/me`, admin-only endpoints, and audit logs all work correctly with a real identity.

---

## Seeded Admin Credentials

The admin user is created by migration `003_seed_admin_user`. The credentials come from environment variables with these defaults:

| Field | Environment Variable | Default Value |
|-------|---------------------|---------------|
| Email | `ADMIN_EMAIL` (or `ADMIN_SEED_EMAIL`) | `admin@pms.dev` |
| Password | `ADMIN_PASSWORD` (or `ADMIN_SEED_PASSWORD`) | `CHANGE-ME-in-production` |
| First Name | — | `System` |
| Last Name | — | `Admin` |
| Display Name | `ADMIN_SEED_NAME` | `System Admin` |
| Role | — | `admin` |

> **Note:** The admin password in the `.env` file and the migration default are both `CHANGE-ME-in-production`. You should change this to a strong password for any shared or deployed environment. The password is bcrypt-hashed before storage — the plaintext is never stored in the database.

---

## Disabling Authentication (Development Mode)

### Step 1: Ensure the database is running and migrations are applied

The bypass requires the seeded admin user to exist in the database.

```bash
# Start PostgreSQL (if not already running)
# Then run migrations:
alembic upgrade head
```

This creates the admin user with the email from `ADMIN_EMAIL` (default: `admin@pms.dev`).

### Step 2: Set `AUTH_ENABLED=false` in your `.env` file

```bash
# In your .env file, add or update:
AUTH_ENABLED=false
```

Or set it inline when starting the server:

```bash
AUTH_ENABLED=false python -m uvicorn pms.main:app --reload
```

### Step 3: Start the server

```bash
python -m uvicorn pms.main:app --reload
```

You should see a warning in the logs:

```
WARNING  AUTH_ENABLED=false — authentication is DISABLED. All requests will
         authenticate as seeded admin (admin@pms.dev). Do NOT use this setting
         in production.
```

### Step 4: Make requests without a token

All endpoints now work without an `Authorization` header:

```bash
# Get current user profile — returns the real admin
curl http://localhost:8000/users/me

# List patients — works without a token
curl http://localhost:8000/patients/

# Admin-only endpoints work too
curl http://localhost:8000/users/
```

On the first request, you'll see a second log line:

```
WARNING  Auth bypass active — all requests authenticate as admin user
         admin@pms.dev (550e8400-e29b-41d4-a716-...)
```

The UUID shown is the real admin user's ID from the database. All audit log entries will reference this ID.

---

## Enabling Authentication (Production Mode)

### Step 1: Remove or update `AUTH_ENABLED` in your `.env` file

```bash
# Either remove the line entirely (defaults to true),
# or explicitly set:
AUTH_ENABLED=true
```

### Step 2: Restart the server

```bash
python -m uvicorn pms.main:app --reload
```

No bypass warning will appear. All endpoints now require a valid JWT token.

### Step 3: Obtain a token

Log in with the seeded admin credentials:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@pms.dev", "password": "CHANGE-ME-in-production"}'
```

Use the returned `access_token` in subsequent requests:

```bash
curl http://localhost:8000/users/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## How It Works

| Aspect | Detail |
|--------|--------|
| **Config variable** | `AUTH_ENABLED` in `config.py` (read from `.env` or environment) |
| **Default** | `true` (authentication enforced) |
| **Bypass behavior** | `require_auth` dependency skips JWT validation and returns the real admin's `sub` (UUID) and `roles` |
| **Admin lookup** | Queries `users` table by `ADMIN_EMAIL` with eager-loaded roles (`selectinload`) |
| **Caching** | Result cached in `_bypass_payload_cache` after first lookup — no repeated DB queries |
| **Cache reset** | Call `clear_bypass_cache()` (exposed for tests) or restart the server |
| **Missing admin** | Raises `RuntimeError`: "AUTH_ENABLED=false but no admin user found with email '...'. Run migrations to seed the admin user." |
| **Logging** | Two WARN-level logs: (1) at startup via `main.py` lifespan, (2) on first bypass request via `middleware/auth.py` |
| **Audit trail** | All actions are attributed to the real admin user ID — audit logs show a valid, traceable identity |

---

## Using a Custom Admin Email

If you changed the admin email during migration, set `ADMIN_EMAIL` to match:

```bash
# .env
ADMIN_EMAIL=custom-admin@myorg.com
AUTH_ENABLED=false
```

The bypass will look up this email in the database instead of the default `admin@pms.dev`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: AUTH_ENABLED=false but no admin user found` | Migrations not run, or `ADMIN_EMAIL` doesn't match the seeded user | Run `alembic upgrade head`, or set `ADMIN_EMAIL` to match the email used during seeding |
| Endpoints return 401 even with `AUTH_ENABLED=false` | Server was not restarted after changing `.env` | Restart the server |
| `/users/me` returns 404 | Stale cache pointing to a deleted user | Restart the server to clear the bypass cache |
| Bypass uses wrong user | `ADMIN_EMAIL` doesn't match the seeded admin | Check `ADMIN_EMAIL` in `.env` matches the email in the `users` table |

---

## Security Warnings

- **Never** set `AUTH_ENABLED=false` in production, staging, or QA environments.
- The `.env.production` template should **not** include `AUTH_ENABLED`.
- CI pipelines should reject deployments where `AUTH_ENABLED=false`.
- When bypass is active, **anyone** with network access to the server has full admin access.
