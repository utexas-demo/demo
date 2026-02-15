# Environment Configuration

**Related ADR:** [ADR-0006: Release Management Strategy](../architecture/0006-release-management-strategy.md)

---

## Environment Overview

| Environment | Purpose | Deploy Trigger | Data | Feature Flag Control |
|---|---|---|---|---|
| Dev | Development and integration testing | Auto on merge to `main` | Synthetic | Developers toggle freely |
| QA | Regression and acceptance testing | Manual trigger from CI | Synthetic | QA team approval for changes |
| Staging | Pre-production validation | RC tag deploy | Sanitized production copy | Product owner approval |
| Production | Live system | Manual promotion | Real PHI | Change control board approval |

## Dev Environment

- **URL pattern:** `*.dev.pms.internal`
- **Deploy trigger:** Automatic on every merge to `main` (CI must pass)
- **Database:** Synthetic test data, seeded on deploy
- **Feature flags:** All flags freely toggled by developers for testing
- **Access:** Development team only
- **HIPAA controls:** Relaxed (synthetic data, no PHI)
- **Logging:** Verbose, debug-level

## QA Environment

- **URL pattern:** `*.qa.pms.internal`
- **Deploy trigger:** Manual trigger from CI pipeline (select branch/tag)
- **Database:** Synthetic test data matching production schema
- **Feature flags:** Changes require QA team lead approval
- **Access:** QA team + development team (read-only for devs)
- **HIPAA controls:** Standard (synthetic data, but production-like configuration)
- **Logging:** Info-level, structured JSON

## Staging Environment

- **URL pattern:** `*.staging.pms.internal`
- **Deploy trigger:** RC tag deployment (e.g., `v0.2.0-rc.1`)
- **Database:** Sanitized copy of production data (PHI removed/anonymized)
- **Feature flags:** Changes require product owner approval
- **Access:** Product owner + QA lead + tech lead
- **HIPAA controls:** Full (production-equivalent configuration)
- **Logging:** Info-level, structured JSON, audit trail enabled

## Production Environment

- **URL pattern:** `*.pms.utexas.edu`
- **Deploy trigger:** Manual promotion after change control board approval
- **Database:** Real PHI, encrypted at rest (AES-256), TLS 1.3 in transit
- **Feature flags:** Changes require change control board approval
- **Access:** All authorized users per RBAC policy
- **HIPAA controls:** Full — encryption, audit logging, access controls, breach notification
- **Logging:** Info-level, structured JSON, immutable audit trail, 6-year retention

## Environment Variables by Environment

| Variable | Dev | QA | Staging | Prod |
|---|---|---|---|---|
| `DEBUG` | `true` | `false` | `false` | `false` |
| `DATABASE_URL` | Local PostgreSQL | QA PostgreSQL | Staging RDS | Prod RDS |
| `SECRET_KEY` | Dev key | Rotated monthly | Rotated monthly | Rotated monthly |
| `ENCRYPTION_KEY` | Dev key | Per-env key | Per-env key | HSM-managed |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `INFO` | `INFO` |
| `FEATURE_*` | Per developer | QA-controlled | PO-controlled | CCB-controlled |

## Promotion Flow

```
Dev ──[CI pass]──→ QA ──[QA sign-off]──→ Staging ──[CCB approval]──→ Prod
```

Each promotion copies the exact same container image/build artifact — no rebuilds between environments. Only environment variables and feature flag states differ.
