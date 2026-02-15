# Project Setup Guide

## Prerequisites

| Tool | Version | Used By |
|---|---|---|
| Python | 3.12+ | pms-backend |
| PostgreSQL | 16+ | pms-backend |
| Node.js | 22+ | pms-frontend |
| Android Studio | Ladybug 2024.2+ | pms-android |
| JDK | 17+ | pms-android |
| Git | 2.x | All |

## Clone All Repos

```bash
git clone --recurse-submodules git@github.com:ammar-utexas/pms-backend.git
git clone --recurse-submodules git@github.com:ammar-utexas/pms-frontend.git
git clone --recurse-submodules git@github.com:ammar-utexas/pms-android.git
```

## Backend Setup

```bash
cd pms-backend

# Virtual environment
python -m venv .venv
source .venv/bin/activate

# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY, ENCRYPTION_KEY

# Run migrations (requires PostgreSQL)
alembic upgrade head

# Start server
python -m uvicorn pms.main:app --reload
# → http://localhost:8000/docs
```

## Frontend Setup

```bash
cd pms-frontend

# Install
npm install

# Configure
cp .env.example .env.local
# Edit .env.local: set NEXT_PUBLIC_API_URL if not localhost:8000

# Start dev server
npm run dev
# → http://localhost:3000
```

## Android Setup

```bash
cd pms-android

# Open in Android Studio
# File → Open → select pms-android/

# Sync Gradle
# Run on emulator (connects to backend at 10.0.2.2:8000)
```

## Running Tests

```bash
# Backend
cd pms-backend && pytest

# Frontend
cd pms-frontend && npm run test:run

# Android
cd pms-android && ./gradlew test
```

## Updating Shared Docs

When docs change in the `demo` repo, update the submodule in each project:

```bash
cd pms-backend/docs && git pull origin main && cd .. && git add docs && git commit -m "Update docs submodule"
cd pms-frontend/docs && git pull origin main && cd .. && git add docs && git commit -m "Update docs submodule"
cd pms-android/docs && git pull origin main && cd .. && git add docs && git commit -m "Update docs submodule"
```
