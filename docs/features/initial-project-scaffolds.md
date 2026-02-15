# Feature: Initial Project Scaffolds

**Date:** 2026-02-15
**Status:** Complete

## What Was Built

Three project repositories were scaffolded for the Patient Management System, all sharing a `docs/` submodule from `ammar-utexas/demo`.

### pms-backend (Python/FastAPI)

Full async FastAPI project with layered architecture:

- **42 files**, Python 3.12+
- Routers, services, models, schemas, and middleware for all four subsystems
- SQLAlchemy 2.0 async with asyncpg (PostgreSQL)
- Alembic database migrations
- JWT authentication with RBAC middleware
- AES encryption service for PHI fields
- Drug interaction checker (placeholder)
- Audit logging middleware
- 5 passing tests (pytest)
- Dockerfile (multi-stage)

### pms-frontend (Next.js/TypeScript)

Full Next.js 15 App Router project:

- **39 files**, TypeScript strict mode
- Pages for Dashboard, Login, Patients (list + detail), Encounters (list + detail), Medications, Reports
- Reusable UI components: Button, Card, Input, Badge
- Sidebar + Header layout pattern
- API client with automatic JWT token attachment
- TypeScript types matching backend Pydantic schemas
- Tailwind CSS 3 for styling
- 9 passing tests (Vitest)
- Dockerfile (multi-stage)

### pms-android (Kotlin/Compose)

Full Android project with clean architecture:

- **46 files**, Kotlin 2.1, min SDK 26, target SDK 35
- Jetpack Compose screens with Material 3 for all subsystems
- Hilt dependency injection
- Retrofit + kotlinx.serialization for API calls
- Room database for offline patient caching
- DataStore for auth token persistence
- Bottom navigation bar
- Dynamic color theme support
- 2 unit test files (entity mapping + model serialization)
- ProGuard rules for release builds

## Key Files

| Repo | Entry Point | Config | Tests |
|---|---|---|---|
| pms-backend | `src/pms/main.py` | `pyproject.toml` | `tests/` |
| pms-frontend | `src/app/layout.tsx` | `package.json` | `__tests__/` |
| pms-android | `app/src/main/.../MainActivity.kt` | `app/build.gradle.kts` | `app/src/test/` |

## Design Choices

- **Placeholder implementations**: All routers/screens return stub data so apps run immediately without a database.
- **Type parity**: TypeScript types and Kotlin data classes exactly mirror backend Pydantic schemas.
- **Shared docs submodule**: All three repos include `docs/` pointing to `ammar-utexas/demo`.
- **CLAUDE.md in each repo**: Backend-specific agent instructions for autonomous development.

## Known Limitations

- Backend routers are stubs — no actual database queries yet.
- No real authentication — login endpoint returns a hardcoded token.
- No pagination on list endpoints.
- Android unit tests require Gradle build to run (no CI configured yet).
- Reports are placeholder cards with no real data.

## Follow-Up Work

- Implement actual CRUD operations with database queries.
- Add real JWT authentication with user table and password hashing.
- Configure CI/CD pipelines for each repo.
- Add pagination to all list endpoints.
- Implement real drug interaction checking via external API.
