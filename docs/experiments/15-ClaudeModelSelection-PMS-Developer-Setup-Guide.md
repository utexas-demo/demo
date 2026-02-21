# Claude Model Selection Setup Guide for PMS Integration

**Document ID:** PMS-EXP-CLAUDEMODEL-001
**Version:** 1.0
**Date:** 2026-02-20
**Applies To:** PMS project (all platforms)
**Prerequisites Level:** Intermediate

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Part A: Anthropic SDK Installation and API Configuration](#3-part-a-anthropic-sdk-installation-and-api-configuration)
4. [Part B: Model Router Service Setup](#4-part-b-model-router-service-setup)
5. [Part C: Integrate with PMS Backend](#5-part-c-integrate-with-pms-backend)
6. [Part D: Integrate with PMS Frontend](#6-part-d-integrate-with-pms-frontend)
7. [Part E: Testing and Verification](#7-part-e-testing-and-verification)
8. [Troubleshooting](#8-troubleshooting)
9. [Reference Commands](#9-reference-commands)

---

## 1. Overview

This guide walks you through setting up the **Claude Model Router** — a FastAPI microservice that intelligently routes AI requests to the optimal Claude model (Opus 4.6, Sonnet 4.6, or Haiku 4.5) based on task complexity, latency needs, and cost constraints.

By the end of this guide you will have:
- The Anthropic Python SDK configured with API key management
- A Model Router service running on port 8001
- Task-based routing to Opus 4.6, Sonnet 4.6, and Haiku 4.5
- PHI sanitization middleware
- Redis response caching
- Cost tracking in PostgreSQL
- Integration with the PMS backend and frontend

### Architecture at a Glance

```mermaid
flowchart LR
    subgraph PMS["PMS Stack"]
        FE["Next.js :3000"]
        BE["FastAPI :8000"]
        DB[(PostgreSQL :5432)]
    end

    subgraph Router["Model Router :8001"]
        CLS["Task Classifier"]
        SAN["PHI Sanitizer"]
        SDK["Anthropic SDK"]
    end

    subgraph Cache["Cache Layer"]
        RED["Redis :6379"]
    end

    subgraph Claude["Anthropic API"]
        O["Opus 4.6"]
        S["Sonnet 4.6"]
        H["Haiku 4.5"]
    end

    FE --> BE
    BE -->|"/ai/route"| CLS
    CLS --> SAN
    SAN --> SDK
    SDK --> O
    SDK --> S
    SDK --> H
    CLS --> RED

    style FE fill:#4FC3F7,stroke:#0288D1,color:#000
    style BE fill:#81C784,stroke:#388E3C,color:#000
    style CLS fill:#FFB74D,stroke:#F57C00,color:#000
    style O fill:#CE93D8,stroke:#7B1FA2,color:#000
    style S fill:#CE93D8,stroke:#7B1FA2,color:#000
    style H fill:#CE93D8,stroke:#7B1FA2,color:#000
```

---

## 2. Prerequisites

### 2.1 Required Software

| Software | Minimum Version | Check Command |
|----------|----------------|---------------|
| Python | 3.11+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| Docker & Docker Compose | 24+ / 2.20+ | `docker --version && docker compose version` |
| Redis | 7.0+ | `redis-cli --version` |
| PostgreSQL | 16+ | `psql --version` |
| Git | 2.40+ | `git --version` |

### 2.2 Anthropic API Key

1. Sign up or log in at [console.anthropic.com](https://console.anthropic.com)
2. Navigate to **API Keys** → **Create Key**
3. Copy the key (starts with `sk-ant-`)
4. Store it securely — you will configure it in Step 3

**For HIPAA-compliant deployments**, contact Anthropic Sales for an Enterprise plan with BAA. Alternatively, use AWS Bedrock or Google Vertex AI with healthcare-tier BAAs.

### 2.3 Verify PMS Services

Confirm the PMS backend, frontend, and database are running:

```bash
# Check PMS backend
curl -s http://localhost:8000/docs | head -5
# Expected: HTML content of FastAPI Swagger UI

# Check PMS frontend
curl -s http://localhost:3000 | head -5
# Expected: HTML content of Next.js app

# Check PostgreSQL
psql -h localhost -U pms -d pms_db -c "SELECT 1;"
# Expected: 1 row returned
```

**Checkpoint:** All three PMS services respond. You have an Anthropic API key ready.

---

## 3. Part A: Anthropic SDK Installation and API Configuration

### Step 1: Create the Model Router project directory

```bash
mkdir -p pms-model-router/app
cd pms-model-router
```

### Step 2: Set up Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install \
  anthropic>=1.0.0 \
  fastapi>=0.115.0 \
  uvicorn>=0.30.0 \
  redis>=5.0.0 \
  pydantic>=2.0.0 \
  pydantic-settings>=2.0.0 \
  python-dotenv>=1.0.0 \
  httpx>=0.27.0 \
  sqlalchemy>=2.0.0 \
  asyncpg>=0.30.0
```

### Step 4: Configure environment variables

Create `.env` (never commit this file):

```bash
cat > .env << 'EOF'
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Model IDs (pin to specific versions for stability)
CLAUDE_OPUS_MODEL=claude-opus-4-6
CLAUDE_SONNET_MODEL=claude-sonnet-4-6
CLAUDE_HAIKU_MODEL=claude-haiku-4-5-20251001

# Service config
MODEL_ROUTER_HOST=0.0.0.0
MODEL_ROUTER_PORT=8001

# Redis
REDIS_URL=redis://localhost:6379/0

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://pms:pms_password@localhost:5432/pms_db

# Cost limits
DAILY_BUDGET_USD=50.00
MONTHLY_BUDGET_USD=1000.00

# PHI Sanitization
PHI_SANITIZATION_ENABLED=true
EOF
```

### Step 5: Verify SDK connectivity

```python
# test_connection.py
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

# Test each model tier
for model in ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-6"]:
    response = client.messages.create(
        model=model,
        max_tokens=50,
        messages=[{"role": "user", "content": "Say 'Hello from ' followed by your model name."}]
    )
    print(f"{model}: {response.content[0].text}")
    print(f"  Input tokens: {response.usage.input_tokens}")
    print(f"  Output tokens: {response.usage.output_tokens}")
```

Run it:

```bash
source .env && python test_connection.py
```

Expected output (model names will vary):

```
claude-haiku-4-5-20251001: Hello from Claude Haiku 4.5!
  Input tokens: 18
  Output tokens: 12
claude-sonnet-4-6: Hello from Claude Sonnet 4.6!
  Input tokens: 18
  Output tokens: 13
claude-opus-4-6: Hello from Claude Opus 4.6!
  Input tokens: 18
  Output tokens: 13
```

**Checkpoint:** All three Claude models respond via the Anthropic SDK. API key is valid.

---

## 4. Part B: Model Router Service Setup

### Step 1: Create the configuration module

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    claude_opus_model: str = "claude-opus-4-6"
    claude_sonnet_model: str = "claude-sonnet-4-6"
    claude_haiku_model: str = "claude-haiku-4-5-20251001"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+asyncpg://pms:pms_password@localhost:5432/pms_db"
    daily_budget_usd: float = 50.0
    monthly_budget_usd: float = 1000.0
    phi_sanitization_enabled: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
```

### Step 2: Create the task classifier

```python
# app/classifier.py
from enum import Enum


class ModelTier(str, Enum):
    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


class TaskType(str, Enum):
    # Haiku-tier tasks
    TEXT_EXTRACTION = "text_extraction"
    CLASSIFICATION = "classification"
    FORMATTING = "formatting"
    REAL_TIME_ALERT = "real_time_alert"
    SIMPLE_SUMMARY = "simple_summary"

    # Sonnet-tier tasks
    ENCOUNTER_SUMMARY = "encounter_summary"
    CODE_GENERATION = "code_generation"
    MEDICATION_CHECK = "medication_check"
    REPORT_GENERATION = "report_generation"
    DATA_ANALYSIS = "data_analysis"

    # Opus-tier tasks
    CLINICAL_DECISION_SUPPORT = "clinical_decision_support"
    DRUG_INTERACTION_COMPLEX = "drug_interaction_complex"
    DIAGNOSTIC_DIFFERENTIAL = "diagnostic_differential"
    SECURITY_AUDIT = "security_audit"
    AGENT_ORCHESTRATION = "agent_orchestration"
    MULTI_STEP_REASONING = "multi_step_reasoning"


# Task → Model mapping
TASK_ROUTING: dict[TaskType, ModelTier] = {
    # Haiku tasks — speed and cost priority
    TaskType.TEXT_EXTRACTION: ModelTier.HAIKU,
    TaskType.CLASSIFICATION: ModelTier.HAIKU,
    TaskType.FORMATTING: ModelTier.HAIKU,
    TaskType.REAL_TIME_ALERT: ModelTier.HAIKU,
    TaskType.SIMPLE_SUMMARY: ModelTier.HAIKU,

    # Sonnet tasks — balanced performance
    TaskType.ENCOUNTER_SUMMARY: ModelTier.SONNET,
    TaskType.CODE_GENERATION: ModelTier.SONNET,
    TaskType.MEDICATION_CHECK: ModelTier.SONNET,
    TaskType.REPORT_GENERATION: ModelTier.SONNET,
    TaskType.DATA_ANALYSIS: ModelTier.SONNET,

    # Opus tasks — maximum reasoning
    TaskType.CLINICAL_DECISION_SUPPORT: ModelTier.OPUS,
    TaskType.DRUG_INTERACTION_COMPLEX: ModelTier.OPUS,
    TaskType.DIAGNOSTIC_DIFFERENTIAL: ModelTier.OPUS,
    TaskType.SECURITY_AUDIT: ModelTier.OPUS,
    TaskType.AGENT_ORCHESTRATION: ModelTier.OPUS,
    TaskType.MULTI_STEP_REASONING: ModelTier.OPUS,
}


def classify_task(task_type: TaskType, override: ModelTier | None = None) -> ModelTier:
    """Determine which model tier to use for a given task."""
    if override:
        return override
    return TASK_ROUTING.get(task_type, ModelTier.SONNET)
```

### Step 3: Create the PHI sanitizer

```python
# app/phi_sanitizer.py
import re
import uuid


class PHISanitizer:
    """Replace PHI with tokens before sending to Anthropic API."""

    PHI_PATTERNS = {
        "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
        "MRN": r"\bMRN[:\s]*\d{6,10}\b",
        "PHONE": r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "DOB": r"\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/\d{4}\b",
    }

    def __init__(self):
        self.token_map: dict[str, str] = {}

    def sanitize(self, text: str) -> str:
        """Replace PHI patterns with UUID tokens."""
        self.token_map = {}
        for phi_type, pattern in self.PHI_PATTERNS.items():
            for match in re.finditer(pattern, text):
                original = match.group()
                if original not in self.token_map:
                    token = f"[{phi_type}_{uuid.uuid4().hex[:8]}]"
                    self.token_map[original] = token
                text = text.replace(original, self.token_map[original])
        return text

    def rehydrate(self, text: str) -> str:
        """Restore original PHI values from tokens."""
        reverse_map = {v: k for k, v in self.token_map.items()}
        for token, original in reverse_map.items():
            text = text.replace(token, original)
        return text
```

### Step 4: Create the main router service

```python
# app/main.py
import time
import hashlib
import json
from contextlib import asynccontextmanager

import anthropic
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .classifier import TaskType, ModelTier, classify_task
from .phi_sanitizer import PHISanitizer


# Pricing per million tokens (USD)
PRICING = {
    ModelTier.OPUS: {"input": 5.0, "output": 25.0},
    ModelTier.SONNET: {"input": 3.0, "output": 15.0},
    ModelTier.HAIKU: {"input": 1.0, "output": 5.0},
}

MODEL_IDS = {
    ModelTier.OPUS: settings.claude_opus_model,
    ModelTier.SONNET: settings.claude_sonnet_model,
    ModelTier.HAIKU: settings.claude_haiku_model,
}

redis_client: redis.Redis | None = None
anthropic_client: anthropic.AsyncAnthropic | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, anthropic_client
    redis_client = redis.from_url(settings.redis_url)
    anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    yield
    await redis_client.aclose()


app = FastAPI(
    title="PMS Claude Model Router",
    version="1.0.0",
    lifespan=lifespan,
)


class AIRequest(BaseModel):
    task_type: TaskType
    prompt: str
    system_prompt: str | None = None
    max_tokens: int = 4096
    model_override: ModelTier | None = None
    use_cache: bool = True
    use_extended_thinking: bool = False
    thinking_budget_tokens: int = 10000


class AIResponse(BaseModel):
    content: str
    model_used: str
    model_tier: ModelTier
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    cached: bool


@app.post("/ai/route", response_model=AIResponse)
async def route_ai_request(request: AIRequest):
    start_time = time.time()

    # 1. Classify task → select model tier
    tier = classify_task(request.task_type, request.model_override)
    model_id = MODEL_IDS[tier]

    # 2. Check cache
    if request.use_cache:
        cache_key = hashlib.sha256(
            f"{model_id}:{request.prompt}:{request.system_prompt}".encode()
        ).hexdigest()
        cached = await redis_client.get(cache_key)
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            data["latency_ms"] = (time.time() - start_time) * 1000
            return AIResponse(**data)

    # 3. Sanitize PHI
    sanitizer = PHISanitizer()
    if settings.phi_sanitization_enabled:
        sanitized_prompt = sanitizer.sanitize(request.prompt)
    else:
        sanitized_prompt = request.prompt

    # 4. Build messages
    messages = [{"role": "user", "content": sanitized_prompt}]

    # 5. Call Anthropic API
    try:
        kwargs = {
            "model": model_id,
            "max_tokens": request.max_tokens,
            "messages": messages,
        }
        if request.system_prompt:
            kwargs["system"] = request.system_prompt
        if request.use_extended_thinking and tier in (ModelTier.OPUS, ModelTier.SONNET):
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": request.thinking_budget_tokens,
            }

        response = await anthropic_client.messages.create(**kwargs)
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Anthropic API error: {e}")

    # 6. Extract content and rehydrate PHI
    content = response.content[0].text
    if settings.phi_sanitization_enabled:
        content = sanitizer.rehydrate(content)

    # 7. Calculate cost
    input_cost = (response.usage.input_tokens / 1_000_000) * PRICING[tier]["input"]
    output_cost = (response.usage.output_tokens / 1_000_000) * PRICING[tier]["output"]
    total_cost = input_cost + output_cost

    latency_ms = (time.time() - start_time) * 1000

    result = AIResponse(
        content=content,
        model_used=model_id,
        model_tier=tier,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cost_usd=round(total_cost, 6),
        latency_ms=round(latency_ms, 1),
        cached=False,
    )

    # 8. Store in cache
    if request.use_cache:
        cache_data = result.model_dump()
        cache_data["cached"] = False  # original was not cached
        ttl = 300 if tier == ModelTier.HAIKU else 3600
        await redis_client.setex(cache_key, ttl, json.dumps(cache_data))

    return result


@app.get("/ai/models")
async def list_models():
    """Return available models and their routing configuration."""
    return {
        "models": {
            tier.value: {
                "model_id": MODEL_IDS[tier],
                "pricing": PRICING[tier],
            }
            for tier in ModelTier
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pms-model-router"}
```

### Step 5: Run the Model Router

```bash
cd pms-model-router
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Step 6: Docker deployment (production)

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

Create `docker-compose.yml`:

```yaml
services:
  model-router:
    build: .
    ports:
      - "8001:8001"
    env_file: .env
    depends_on:
      - redis
    networks:
      - pms-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    networks:
      - pms-network

volumes:
  redis-data:

networks:
  pms-network:
    external: true
```

```bash
docker compose up -d
```

**Checkpoint:** Model Router is running on port 8001. Health endpoint responds. All three Claude models are accessible.

---

## 5. Part C: Integrate with PMS Backend

### Step 1: Add the Model Router client to the PMS backend

Add to `pms-backend/requirements.txt`:

```
httpx>=0.27.0
```

### Step 2: Create the AI client module

```python
# pms-backend/app/services/ai_client.py
import httpx
from enum import Enum


MODEL_ROUTER_URL = "http://localhost:8001"


class TaskType(str, Enum):
    TEXT_EXTRACTION = "text_extraction"
    ENCOUNTER_SUMMARY = "encounter_summary"
    MEDICATION_CHECK = "medication_check"
    CLINICAL_DECISION_SUPPORT = "clinical_decision_support"
    # ... (mirror the full TaskType enum from the router)


async def ai_request(
    task_type: TaskType,
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int = 4096,
    model_override: str | None = None,
) -> dict:
    """Send an AI request through the Model Router."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{MODEL_ROUTER_URL}/ai/route",
            json={
                "task_type": task_type.value,
                "prompt": prompt,
                "system_prompt": system_prompt,
                "max_tokens": max_tokens,
                "model_override": model_override,
            },
        )
        response.raise_for_status()
        return response.json()
```

### Step 3: Use in PMS API endpoints

```python
# pms-backend/app/api/encounters.py (example integration)
from app.services.ai_client import ai_request, TaskType


@router.post("/{encounter_id}/summarize")
async def summarize_encounter(encounter_id: int, db: AsyncSession = Depends(get_db)):
    encounter = await get_encounter(db, encounter_id)

    result = await ai_request(
        task_type=TaskType.ENCOUNTER_SUMMARY,
        prompt=f"Summarize this clinical encounter:\n\n{encounter.notes}",
        system_prompt="You are a medical documentation specialist. Produce a concise SOAP-format summary.",
    )

    return {
        "summary": result["content"],
        "model_used": result["model_used"],
        "cost_usd": result["cost_usd"],
    }
```

**Checkpoint:** PMS backend can send AI requests through the Model Router. Encounter summarization returns results from Sonnet 4.6.

---

## 6. Part D: Integrate with PMS Frontend

### Step 1: Add AI components to the Next.js frontend

```bash
cd pms-frontend
```

### Step 2: Create the AI service hook

```typescript
// src/hooks/useAI.ts
import { useState } from "react";

interface AIResponse {
  content: string;
  model_used: string;
  model_tier: "opus" | "sonnet" | "haiku";
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  cached: boolean;
}

export function useAI() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendAIRequest(
    taskType: string,
    prompt: string,
    systemPrompt?: string
  ): Promise<AIResponse | null> {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/ai/route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_type: taskType,
          prompt,
          system_prompt: systemPrompt,
        }),
      });

      if (!response.ok) throw new Error(`AI request failed: ${response.status}`);
      return await response.json();
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI request failed");
      return null;
    } finally {
      setLoading(false);
    }
  }

  return { sendAIRequest, loading, error };
}
```

### Step 3: Create the AI Model Badge component

```typescript
// src/components/AIModelBadge.tsx
interface Props {
  modelTier: "opus" | "sonnet" | "haiku";
  latencyMs: number;
  costUsd: number;
  cached: boolean;
}

const TIER_COLORS = {
  opus: "bg-purple-100 text-purple-800",
  sonnet: "bg-blue-100 text-blue-800",
  haiku: "bg-green-100 text-green-800",
};

export function AIModelBadge({ modelTier, latencyMs, costUsd, cached }: Props) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`px-2 py-0.5 rounded-full font-medium ${TIER_COLORS[modelTier]}`}>
        {modelTier.toUpperCase()}
      </span>
      <span className="text-gray-500">{latencyMs.toFixed(0)}ms</span>
      <span className="text-gray-500">${costUsd.toFixed(4)}</span>
      {cached && <span className="text-amber-600 font-medium">cached</span>}
    </div>
  );
}
```

### Step 4: Add API proxy route

```typescript
// src/app/api/ai/route/route.ts
import { NextRequest, NextResponse } from "next/server";

const MODEL_ROUTER_URL = process.env.MODEL_ROUTER_URL || "http://localhost:8001";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const response = await fetch(`${MODEL_ROUTER_URL}/ai/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
```

### Step 5: Add environment variable

Add to `pms-frontend/.env.local`:

```
MODEL_ROUTER_URL=http://localhost:8001
```

**Checkpoint:** Frontend can send AI requests via the Next.js API route, which proxies to the Model Router. The AI Model Badge shows which Claude model served each response.

---

## 7. Part E: Testing and Verification

### Test 1: Health check

```bash
curl -s http://localhost:8001/health | python3 -m json.tool
```

Expected:

```json
{
    "status": "ok",
    "service": "pms-model-router"
}
```

### Test 2: List available models

```bash
curl -s http://localhost:8001/ai/models | python3 -m json.tool
```

### Test 3: Route a Haiku task (fast, cheap)

```bash
curl -s -X POST http://localhost:8001/ai/route \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "text_extraction",
    "prompt": "Extract the patient name and date of birth from: John Smith, DOB 03/15/1985, MRN 12345678",
    "max_tokens": 200
  }' | python3 -m json.tool
```

Expected: `model_tier: "haiku"`, latency < 500ms.

### Test 4: Route a Sonnet task (balanced)

```bash
curl -s -X POST http://localhost:8001/ai/route \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "encounter_summary",
    "prompt": "Summarize: Patient presents with 3-day history of productive cough, fever 101.2F, and bilateral rales on auscultation. CXR shows right lower lobe infiltrate. Started on amoxicillin-clavulanate.",
    "system_prompt": "You are a clinical documentation specialist.",
    "max_tokens": 500
  }' | python3 -m json.tool
```

Expected: `model_tier: "sonnet"`, clinical SOAP summary returned.

### Test 5: Route an Opus task (deep reasoning)

```bash
curl -s -X POST http://localhost:8001/ai/route \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "clinical_decision_support",
    "prompt": "Patient is on warfarin 5mg daily for atrial fibrillation. New diagnosis of H. pylori. Evaluate the safety of adding clarithromycin + amoxicillin + omeprazole triple therapy. Consider CYP interactions, INR monitoring, and alternative regimens.",
    "system_prompt": "You are a clinical pharmacology expert.",
    "max_tokens": 2000,
    "use_extended_thinking": true
  }' | python3 -m json.tool
```

Expected: `model_tier: "opus"`, detailed drug interaction analysis with alternatives.

### Test 6: Verify PHI sanitization

```bash
curl -s -X POST http://localhost:8001/ai/route \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "simple_summary",
    "prompt": "Summarize for patient John Smith, SSN 123-45-6789, DOB 03/15/1985, phone (555) 123-4567"
  }' | python3 -m json.tool
```

Verify that the response content contains the original identifiers (rehydrated) but check audit logs to confirm the outbound API call had them replaced with tokens.

### Test 7: Cache hit verification

Run the same Haiku request from Test 3 twice. The second response should have `"cached": true` and significantly lower latency.

**Checkpoint:** All three model tiers respond correctly. PHI sanitization works. Caching works. Cost tracking returns values.

---

## 8. Troubleshooting

### API Key Invalid or Expired

**Symptoms:** `401 Unauthorized` from Anthropic API.
**Fix:** Verify key in `.env` starts with `sk-ant-`. Check [console.anthropic.com](https://console.anthropic.com) that the key is active. Regenerate if needed.

### Rate Limiting (429 Errors)

**Symptoms:** `429 Too Many Requests` responses.
**Fix:** Implement exponential backoff. Check your tier's rate limits at [Anthropic rate limits](https://platform.claude.com/docs/en/about-claude/pricing). Consider upgrading to a higher usage tier or distributing across Bedrock + direct API.

### Redis Connection Refused

**Symptoms:** `ConnectionRefusedError` on startup.
**Fix:**

```bash
# Check if Redis is running
redis-cli ping
# Expected: PONG

# If not running:
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### Model Not Found

**Symptoms:** `404` or `invalid_model` error from Anthropic.
**Fix:** Verify model IDs in `.env` match the exact values from [Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview). Note that Haiku uses a dated ID: `claude-haiku-4-5-20251001`.

### Extended Thinking Errors

**Symptoms:** Error when `use_extended_thinking: true`.
**Fix:** Extended thinking requires `max_tokens` to be at least `budget_tokens + 1000`. Ensure `budget_tokens` is set. Only Opus 4.6 and Sonnet 4.6 support adaptive thinking.

### High Latency on Opus Requests

**Symptoms:** Opus requests taking > 30 seconds.
**Fix:** Opus is inherently slower than Sonnet/Haiku. For time-sensitive tasks, consider: (1) reducing `max_tokens`, (2) using Sonnet with `model_override`, or (3) enabling fast mode via the API (premium pricing).

### Port Conflicts

**Symptoms:** `Address already in use` on port 8001.
**Fix:**

```bash
lsof -i :8001
kill -9 <PID>
```

---

## 9. Reference Commands

### Daily Development Workflow

```bash
# Start all services
docker compose up -d

# View router logs
docker compose logs -f model-router

# Run locally for development
cd pms-model-router && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Management Commands

```bash
# Check model availability
curl -s http://localhost:8001/ai/models | python3 -m json.tool

# Health check
curl -s http://localhost:8001/health

# Flush Redis cache
redis-cli FLUSHDB

# View Redis cache keys
redis-cli KEYS "*"
```

### Useful URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Model Router API | http://localhost:8001 | AI routing service |
| Model Router Docs | http://localhost:8001/docs | Swagger UI |
| PMS Backend | http://localhost:8000 | Main PMS API |
| PMS Frontend | http://localhost:3000 | Web application |
| Anthropic Console | https://console.anthropic.com | API key management |
| Anthropic Docs | https://platform.claude.com/docs | Official documentation |

---

## Next Steps

After completing setup, proceed to the [Claude Model Selection Developer Tutorial](15-ClaudeModelSelection-Developer-Tutorial.md) to build your first model-routed clinical AI pipeline end-to-end.

## Resources

- [Anthropic API Documentation](https://platform.claude.com/docs)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Claude Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- [Claude API Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [PMS Adaptive Thinking Setup Guide](08-AdaptiveThinking-PMS-Developer-Setup-Guide.md)
- [PMS MCP Setup Guide](09-MCP-PMS-Developer-Setup-Guide.md)
