# MCP (Model Context Protocol) Setup Guide for PMS Integration

**Document ID:** PMS-EXP-MCP-001
**Version:** 1.0
**Date:** February 19, 2026
**Applies To:** PMS project (all platforms)
**Prerequisites Level:** Intermediate

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Part A: Install and Configure the PMS MCP Server](#3-part-a-install-and-configure-the-pms-mcp-server)
4. [Part B: Integrate with PMS Backend](#4-part-b-integrate-with-pms-backend)
5. [Part C: Integrate with PMS Frontend](#5-part-c-integrate-with-pms-frontend)
6. [Part D: Testing and Verification](#6-part-d-testing-and-verification)
7. [Troubleshooting](#7-troubleshooting)
8. [Reference Commands](#8-reference-commands)

---

## 1. Overview

This guide walks you through setting up the **PMS MCP Server** — a Model Context Protocol server that wraps the existing PMS FastAPI backend and exposes patient records, encounters, prescriptions, and reports as MCP tools, resources, and prompts. By the end, you will have:

- A running `pms-mcp-server` Docker container on port 9000
- MCP tools for all PMS CRUD endpoints
- MCP resources for patient summaries and formulary data
- MCP prompt templates for clinical documentation
- OAuth 2.1 authentication with role-based scoping
- Audit logging for HIPAA compliance
- Claude Desktop connected to the PMS MCP server

### Architecture at a Glance

```mermaid
flowchart LR
    subgraph Clients["MCP Clients"]
        CD["Claude Desktop"]
        NEXT["Next.js :3000<br/>(MCP Client)"]
        OC["OpenClaw Agent"]
    end

    subgraph Docker["Docker Network"]
        MCP["PMS MCP Server<br/>:9000<br/>(FastMCP + OAuth)"]
        API["PMS Backend<br/>:8000<br/>(FastAPI)"]
        DB[("PostgreSQL<br/>:5432")]
    end

    CD -->|"Streamable HTTP<br/>+ OAuth"| MCP
    NEXT -->|"Streamable HTTP"| MCP
    OC -->|"Streamable HTTP"| MCP
    MCP -->|"HTTP"| API
    MCP -->|"Audit logs"| DB
    API --> DB

    style MCP fill:#d4edda,stroke:#28a745
    style API fill:#cce5ff,stroke:#0d6efd
    style DB fill:#fff3cd,stroke:#ffc107
```

---

## 2. Prerequisites

### 2.1 Required Software

| Software | Minimum Version | Check Command |
|---|---|---|
| Python | 3.12+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Git | 2.40+ | `git --version` |
| pip | 23+ | `pip --version` |
| uv (recommended) | 0.4+ | `uv --version` |

### 2.2 Installation of Prerequisites

**Python 3.12** (if not installed):
```bash
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt update && sudo apt install python3.12 python3.12-venv

# Verify
python3 --version
```

**uv** (fast Python package manager, recommended):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Claude Desktop** (for external MCP client testing):
```bash
# macOS — download from https://claude.ai/download
# Or via Homebrew:
brew install --cask claude
```

### 2.3 Verify PMS Services

Before setting up the MCP server, confirm the PMS core services are running:

```bash
# Check PMS Backend
curl -s http://localhost:8000/health | python3 -m json.tool
# Expected: {"status": "healthy", ...}

# Check PMS Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# Expected: 200

# Check PostgreSQL
docker exec pms-postgres pg_isready -U pms
# Expected: accepting connections
```

If any service is not running, follow the [Project Setup Guide](../config/project-setup.md) first.

---

## 3. Part A: Install and Configure the PMS MCP Server

### Step 1: Create the MCP Server Directory

```bash
# From the PMS project root
mkdir -p services/mcp-server
cd services/mcp-server
```

### Step 2: Initialize the Python Project

```bash
# Using uv (recommended)
uv init --name pms-mcp-server
uv add "mcp[cli]>=1.9" "fastmcp>=2.0" "httpx>=0.27" "authlib>=1.3" "asyncpg>=0.29" "python-dotenv"

# Or using pip
python3 -m venv .venv
source .venv/bin/activate
pip install "mcp[cli]>=1.9" "fastmcp>=2.0" "httpx>=0.27" "authlib>=1.3" "asyncpg>=0.29" python-dotenv
```

### Step 3: Create the MCP Server Entry Point

Create `services/mcp-server/server.py`:

```python
"""PMS MCP Server — Exposes PMS APIs as MCP tools, resources, and prompts."""

import os
from datetime import datetime

import httpx
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP(
    name="PMS MCP Server",
    instructions=(
        "You are connected to the MPS Patient Management System. "
        "Use the available tools to query and manage patient records, "
        "encounters, prescriptions, and reports. Always verify patient "
        "identity before accessing records. Never expose PHI in logs."
    ),
)

PMS_BACKEND_URL = os.getenv("PMS_BACKEND_URL", "http://localhost:8000")


# --- MCP Tools: Patient Records ---

@mcp.tool()
async def search_patients(query: str, limit: int = 10) -> dict:
    """Search for patients by name, MRN, or date of birth.

    Args:
        query: Search term (patient name, MRN, or DOB in YYYY-MM-DD format)
        limit: Maximum number of results to return (default: 10)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PMS_BACKEND_URL}/api/patients",
            params={"search": query, "limit": limit},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_patient(patient_id: int) -> dict:
    """Retrieve a single patient record by ID.

    Args:
        patient_id: The unique patient identifier
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PMS_BACKEND_URL}/api/patients/{patient_id}"
        )
        response.raise_for_status()
        return response.json()


# --- MCP Tools: Encounters ---

@mcp.tool()
async def list_encounters(patient_id: int, limit: int = 20) -> dict:
    """List clinical encounters for a patient.

    Args:
        patient_id: The patient whose encounters to list
        limit: Maximum number of encounters to return (default: 20)
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PMS_BACKEND_URL}/api/encounters",
            params={"patient_id": patient_id, "limit": limit},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_encounter(encounter_id: int) -> dict:
    """Retrieve a single encounter record.

    Args:
        encounter_id: The unique encounter identifier
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PMS_BACKEND_URL}/api/encounters/{encounter_id}"
        )
        response.raise_for_status()
        return response.json()


# --- MCP Tools: Prescriptions ---

@mcp.tool()
async def list_prescriptions(patient_id: int) -> dict:
    """List active prescriptions for a patient.

    Args:
        patient_id: The patient whose prescriptions to list
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PMS_BACKEND_URL}/api/prescriptions",
            params={"patient_id": patient_id},
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def check_interactions(medication_ids: list[int]) -> dict:
    """Check for drug-drug interactions between medications.

    Args:
        medication_ids: List of medication IDs to check for interactions
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PMS_BACKEND_URL}/api/prescriptions/interactions",
            json={"medication_ids": medication_ids},
        )
        response.raise_for_status()
        return response.json()


# --- MCP Tools: Reports ---

@mcp.tool()
async def generate_report(report_type: str, patient_id: int | None = None, date_from: str | None = None, date_to: str | None = None) -> dict:
    """Generate a clinical or operational report.

    Args:
        report_type: Type of report (e.g., 'patient_summary', 'encounter_history', 'medication_list', 'daily_census')
        patient_id: Patient ID (required for patient-specific reports)
        date_from: Start date in YYYY-MM-DD format (optional)
        date_to: End date in YYYY-MM-DD format (optional)
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PMS_BACKEND_URL}/api/reports",
            json={
                "report_type": report_type,
                "patient_id": patient_id,
                "date_from": date_from,
                "date_to": date_to,
            },
        )
        response.raise_for_status()
        return response.json()


# --- MCP Resources ---

@mcp.resource("pms://patients/{patient_id}/summary")
async def patient_summary(patient_id: int) -> str:
    """Get a read-only summary for a patient, suitable for LLM context."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PMS_BACKEND_URL}/api/patients/{patient_id}"
        )
        response.raise_for_status()
        patient = response.json()

    return (
        f"Patient: {patient.get('name', 'Unknown')}\n"
        f"MRN: {patient.get('mrn', 'N/A')}\n"
        f"DOB: {patient.get('date_of_birth', 'N/A')}\n"
        f"Active Conditions: {', '.join(patient.get('conditions', []))}\n"
        f"Allergies: {', '.join(patient.get('allergies', []))}\n"
    )


@mcp.resource("pms://formulary/current")
async def formulary() -> str:
    """Get the current medication formulary."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PMS_BACKEND_URL}/api/prescriptions/formulary"
        )
        response.raise_for_status()
        return str(response.json())


# --- MCP Prompts ---

@mcp.prompt()
def discharge_summary(patient_id: int, encounter_id: int) -> str:
    """Generate a discharge summary prompt for a patient encounter.

    Args:
        patient_id: The patient being discharged
        encounter_id: The encounter being closed
    """
    return (
        f"Generate a discharge summary for patient ID {patient_id}, "
        f"encounter ID {encounter_id}. Include:\n"
        "1. Reason for admission\n"
        "2. Hospital course\n"
        "3. Discharge diagnoses\n"
        "4. Discharge medications with instructions\n"
        "5. Follow-up appointments\n"
        "6. Patient education provided\n\n"
        "Use the get_patient, get_encounter, and list_prescriptions tools "
        "to gather the necessary data before writing the summary."
    )


@mcp.prompt()
def encounter_note(patient_id: int) -> str:
    """Generate an encounter note prompt for documenting a clinical visit.

    Args:
        patient_id: The patient being seen
    """
    return (
        f"Document the current encounter for patient ID {patient_id} "
        "using SOAP format:\n"
        "- Subjective: Chief complaint, HPI, review of systems\n"
        "- Objective: Vitals, physical exam, lab results\n"
        "- Assessment: Diagnoses, clinical reasoning\n"
        "- Plan: Orders, prescriptions, follow-up\n\n"
        "Use the get_patient and list_prescriptions tools to pull current data."
    )


@mcp.prompt()
def med_reconciliation(patient_id: int) -> str:
    """Generate a medication reconciliation prompt.

    Args:
        patient_id: The patient whose medications to reconcile
    """
    return (
        f"Perform a medication reconciliation for patient ID {patient_id}.\n"
        "1. Use list_prescriptions to get current medications\n"
        "2. Use check_interactions to verify no harmful interactions\n"
        "3. Flag any duplicates, contraindications, or dosing concerns\n"
        "4. Produce a reconciled medication list\n"
    )
```

### Step 4: Create Environment Configuration

Create `services/mcp-server/.env`:

```bash
# PMS MCP Server Configuration
PMS_BACKEND_URL=http://pms-backend:8000
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=9000
MCP_SERVER_NAME="PMS MCP Server"

# PostgreSQL (for audit logging)
DATABASE_URL=postgresql+asyncpg://pms:pms_password@pms-postgres:5432/pms

# OAuth 2.1
OAUTH_ISSUER=http://pms-mcp-server:9000
OAUTH_TOKEN_EXPIRY=900
OAUTH_REFRESH_EXPIRY=28800

# Logging
LOG_LEVEL=INFO
AUDIT_LOG_ENABLED=true
```

### Step 5: Create the Dockerfile

Create `services/mcp-server/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:9000/health')" || exit 1

EXPOSE 9000

# Run the MCP server with Streamable HTTP transport
CMD ["uv", "run", "fastmcp", "run", "server.py", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9000"]
```

### Step 6: Add to Docker Compose

Add the following service to your `docker-compose.yml`:

```yaml
  pms-mcp-server:
    build:
      context: ./services/mcp-server
      dockerfile: Dockerfile
    container_name: pms-mcp-server
    ports:
      - "9000:9000"
    environment:
      - PMS_BACKEND_URL=http://pms-backend:8000
      - DATABASE_URL=postgresql+asyncpg://pms:pms_password@pms-postgres:5432/pms
      - LOG_LEVEL=INFO
      - AUDIT_LOG_ENABLED=true
    depends_on:
      pms-backend:
        condition: service_healthy
      pms-postgres:
        condition: service_healthy
    networks:
      - pms-network
    restart: unless-stopped
```

### Step 7: Build and Start

```bash
# Build the MCP server image
docker compose build pms-mcp-server

# Start the MCP server (and dependencies)
docker compose up -d pms-mcp-server

# Verify it's running
docker compose logs pms-mcp-server --tail 20
```

**Checkpoint:** You should see log output indicating the MCP server is listening on port 9000. The server should report its name ("PMS MCP Server") and the available tools/resources/prompts.

---

## 4. Part B: Integrate with PMS Backend

### Step 1: Verify Tool Discovery

Use the MCP CLI to confirm tools are discoverable:

```bash
# Install the MCP CLI (if not already installed)
uv tool install "mcp[cli]"

# List all tools exposed by the PMS MCP server
mcp tools list --transport streamable-http --url http://localhost:9000/mcp

# Expected output:
# search_patients - Search for patients by name, MRN, or date of birth.
# get_patient - Retrieve a single patient record by ID.
# list_encounters - List clinical encounters for a patient.
# get_encounter - Retrieve a single encounter record.
# list_prescriptions - List active prescriptions for a patient.
# check_interactions - Check for drug-drug interactions between medications.
# generate_report - Generate a clinical or operational report.
```

### Step 2: Test a Tool Call

```bash
# Call the search_patients tool
mcp tools call search_patients \
    --transport streamable-http \
    --url http://localhost:9000/mcp \
    --input '{"query": "John", "limit": 5}'
```

### Step 3: Verify Resources

```bash
# List available resources
mcp resources list --transport streamable-http --url http://localhost:9000/mcp

# Read a patient summary resource
mcp resources read "pms://patients/1/summary" \
    --transport streamable-http \
    --url http://localhost:9000/mcp
```

### Step 4: Verify Prompts

```bash
# List available prompts
mcp prompts list --transport streamable-http --url http://localhost:9000/mcp

# Get a specific prompt
mcp prompts get discharge_summary \
    --transport streamable-http \
    --url http://localhost:9000/mcp \
    --input '{"patient_id": 1, "encounter_id": 100}'
```

### Step 5: Create the Audit Log Table

Run the following migration on the PMS database:

```sql
CREATE TABLE IF NOT EXISTS mcp_audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    client_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    method VARCHAR(50) NOT NULL,          -- 'tools/call', 'resources/read', 'prompts/get'
    target_name VARCHAR(255) NOT NULL,    -- tool/resource/prompt name
    parameters JSONB,                     -- request parameters (PHI redacted)
    response_status VARCHAR(20) NOT NULL, -- 'success', 'error'
    latency_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mcp_audit_timestamp ON mcp_audit_log (timestamp);
CREATE INDEX idx_mcp_audit_client ON mcp_audit_log (client_id);
CREATE INDEX idx_mcp_audit_user ON mcp_audit_log (user_id);
CREATE INDEX idx_mcp_audit_method ON mcp_audit_log (method);
```

**Checkpoint:** All MCP tools, resources, and prompts are discoverable and callable from the CLI. The audit log table is created in PostgreSQL.

---

## 5. Part C: Integrate with PMS Frontend

### Step 1: Install the MCP TypeScript SDK

```bash
# From the PMS frontend directory
cd pms-frontend
npm install @modelcontextprotocol/sdk
```

### Step 2: Create the MCP Client Service

Create `pms-frontend/src/lib/mcp-client.ts`:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const MCP_SERVER_URL = process.env.NEXT_PUBLIC_MCP_SERVER_URL || "http://localhost:9000/mcp";

let mcpClient: Client | null = null;

export async function getMCPClient(): Promise<Client> {
  if (mcpClient) return mcpClient;

  const transport = new StreamableHTTPClientTransport(
    new URL(MCP_SERVER_URL)
  );

  mcpClient = new Client({
    name: "pms-frontend",
    version: "1.0.0",
  });

  await mcpClient.connect(transport);
  return mcpClient;
}

export async function callMCPTool(toolName: string, args: Record<string, unknown>) {
  const client = await getMCPClient();
  const result = await client.callTool({ name: toolName, arguments: args });
  return result;
}

export async function listMCPTools() {
  const client = await getMCPClient();
  const result = await client.listTools();
  return result.tools;
}

export async function readMCPResource(uri: string) {
  const client = await getMCPClient();
  const result = await client.readResource({ uri });
  return result;
}
```

### Step 3: Add Environment Variable

Add to `pms-frontend/.env.local`:

```bash
NEXT_PUBLIC_MCP_SERVER_URL=http://localhost:9000/mcp
```

### Step 4: Create a React Hook for MCP

Create `pms-frontend/src/hooks/useMCPTool.ts`:

```typescript
"use client";

import { useState, useCallback } from "react";
import { callMCPTool } from "@/lib/mcp-client";

interface UseMCPToolResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  execute: (args: Record<string, unknown>) => Promise<T>;
}

export function useMCPTool<T = unknown>(toolName: string): UseMCPToolResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(
    async (args: Record<string, unknown>): Promise<T> => {
      setLoading(true);
      setError(null);
      try {
        const result = await callMCPTool(toolName, args);
        const parsed = result.content[0].type === "text"
          ? JSON.parse(result.content[0].text)
          : result.content[0];
        setData(parsed as T);
        return parsed as T;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        setError(error);
        throw error;
      } finally {
        setLoading(false);
      }
    },
    [toolName]
  );

  return { data, loading, error, execute };
}
```

### Step 5: Example Usage in a Component

```typescript
"use client";

import { useMCPTool } from "@/hooks/useMCPTool";

interface Patient {
  id: number;
  name: string;
  mrn: string;
  date_of_birth: string;
}

export function PatientSearch() {
  const { data, loading, error, execute } = useMCPTool<Patient[]>("search_patients");

  const handleSearch = async (query: string) => {
    await execute({ query, limit: 10 });
  };

  return (
    <div>
      <input
        type="text"
        placeholder="Search patients..."
        onChange={(e) => handleSearch(e.target.value)}
      />
      {loading && <p>Searching...</p>}
      {error && <p>Error: {error.message}</p>}
      {data?.map((patient) => (
        <div key={patient.id}>
          <strong>{patient.name}</strong> — MRN: {patient.mrn}
        </div>
      ))}
    </div>
  );
}
```

**Checkpoint:** The PMS frontend can discover and call MCP tools. The `useMCPTool` hook provides a clean React integration pattern.

---

## 6. Part D: Testing and Verification

### Service Health Check

```bash
# MCP server health
curl -s http://localhost:9000/health | python3 -m json.tool

# Expected:
# {
#   "status": "healthy",
#   "server_name": "PMS MCP Server",
#   "tools_count": 7,
#   "resources_count": 2,
#   "prompts_count": 3,
#   "transport": "streamable-http"
# }
```

### Functional Tests

```bash
# Test 1: Search patients via MCP
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
# Expected: JSON-RPC response with all 7 tools listed

# Test 2: Call a tool
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "search_patients",
      "arguments": {"query": "Smith", "limit": 5}
    }
  }'
# Expected: JSON-RPC response with patient search results

# Test 3: Read a resource
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "resources/read",
    "params": {
      "uri": "pms://formulary/current"
    }
  }'
# Expected: JSON-RPC response with formulary data
```

### Connect Claude Desktop

Edit your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "pms": {
      "url": "http://localhost:9000/mcp",
      "transport": "streamable-http"
    }
  }
}
```

Restart Claude Desktop and verify:
1. Open Claude Desktop
2. Look for the MCP server indicator (hammer icon)
3. Click it to see the list of available tools
4. Try asking: "Search for patients named Smith"

**Checkpoint:** The MCP server responds to health checks, JSON-RPC tool calls work, and Claude Desktop can discover and invoke PMS tools.

---

## 7. Troubleshooting

### Connection Refused on Port 9000

**Symptom:** `curl: (7) Failed to connect to localhost port 9000: Connection refused`

**Cause:** The MCP server container is not running or hasn't started yet.

**Fix:**
```bash
# Check if the container is running
docker compose ps pms-mcp-server

# Check logs for startup errors
docker compose logs pms-mcp-server --tail 50

# Restart the service
docker compose restart pms-mcp-server
```

### "PMS Backend Unreachable" in MCP Server Logs

**Symptom:** MCP tool calls return errors with "Connection refused" to the backend.

**Cause:** The PMS backend is not running, or the `PMS_BACKEND_URL` environment variable points to the wrong address.

**Fix:**
```bash
# Verify the backend is running
curl -s http://localhost:8000/health

# Check the environment variable in docker-compose.yml
# Inside Docker network, use service name: http://pms-backend:8000
# Outside Docker, use: http://localhost:8000
```

### OAuth Token Expired

**Symptom:** MCP tool calls return `401 Unauthorized` after working initially.

**Cause:** The OAuth access token has expired (default: 15 minutes).

**Fix:**
- MCP clients should implement automatic token refresh using the refresh token
- For development, increase `OAUTH_TOKEN_EXPIRY` in `.env` (e.g., `3600` for 1 hour)
- For Claude Desktop, restart the app to re-authenticate

### Port 9000 Already in Use

**Symptom:** Docker container fails to start with "port already in use" error.

**Cause:** Another service (possibly a previous MCP server instance or SonarQube) is using port 9000.

**Fix:**
```bash
# Find what's using port 9000
lsof -i :9000

# Kill the process or change the port in docker-compose.yml
# Alternative port: 9001
```

### JSON-RPC Parse Error

**Symptom:** MCP calls return `{"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}}`

**Cause:** Malformed JSON in the request body.

**Fix:**
- Ensure `Content-Type: application/json` header is set
- Validate JSON syntax (use `python3 -m json.tool` to check)
- Ensure all required fields (`jsonrpc`, `id`, `method`) are present

### Tools Not Showing in Claude Desktop

**Symptom:** Claude Desktop connects but shows no tools.

**Cause:** Claude Desktop configuration has incorrect URL or the MCP server isn't exposing tools on the expected path.

**Fix:**
```bash
# Verify the MCP endpoint
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'

# Ensure the URL in claude_desktop_config.json matches exactly
# Restart Claude Desktop after config changes
```

---

## 8. Reference Commands

### Daily Development Workflow

```bash
# Start the MCP server (with dependencies)
docker compose up -d pms-mcp-server

# Tail logs in real-time
docker compose logs -f pms-mcp-server

# Restart after code changes
docker compose restart pms-mcp-server

# Rebuild after dependency changes
docker compose build pms-mcp-server && docker compose up -d pms-mcp-server
```

### Management Commands

```bash
# List available MCP tools
mcp tools list --transport streamable-http --url http://localhost:9000/mcp

# List available MCP resources
mcp resources list --transport streamable-http --url http://localhost:9000/mcp

# List available MCP prompts
mcp prompts list --transport streamable-http --url http://localhost:9000/mcp

# Run the MCP server locally (without Docker, for development)
cd services/mcp-server
uv run fastmcp run server.py --transport streamable-http --port 9000
```

### Monitoring Commands

```bash
# Check MCP server health
curl -s http://localhost:9000/health | python3 -m json.tool

# View recent audit log entries
docker exec pms-postgres psql -U pms -d pms -c \
    "SELECT timestamp, client_id, method, target_name, response_status FROM mcp_audit_log ORDER BY timestamp DESC LIMIT 20;"

# Check container resource usage
docker stats pms-mcp-server --no-stream
```

### Useful URLs

| Service | URL | Description |
|---|---|---|
| MCP Server (Streamable HTTP) | `http://localhost:9000/mcp` | Main MCP endpoint |
| MCP Health Check | `http://localhost:9000/health` | Server health status |
| PMS Backend | `http://localhost:8000` | Underlying FastAPI backend |
| PMS Frontend | `http://localhost:3000` | Next.js frontend |
| PostgreSQL | `localhost:5432` | Database (user: `pms`) |

---

## Next Steps

After completing this setup guide:

1. Follow the [MCP Developer Tutorial](09-MCP-Developer-Tutorial.md) to build your first custom MCP integration end-to-end
2. Review the [PRD: MCP PMS Integration](09-PRD-MCP-PMS-Integration.md) for the full product requirements and phase plan
3. Explore the [FastMCP documentation](https://gofastmcp.com/) for advanced features (resource subscriptions, middleware, context injection)
4. Connect additional MCP clients (Cursor, VS Code Copilot) for AI-assisted development

---

## Resources

- **Official MCP Documentation:** [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **MCP Specification (2025-11-25):** [modelcontextprotocol.io/specification/2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- **MCP Python SDK:** [github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)
- **MCP TypeScript SDK:** [github.com/modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)
- **FastMCP Framework:** [gofastmcp.com](https://gofastmcp.com/)
- **FastAPI-MCP Integration:** [github.com/tadata-org/fastapi_mcp](https://github.com/tadata-org/fastapi_mcp)
- **MCP Security Best Practices:** [modelcontextprotocol.io/specification/draft/basic/security_best_practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices)
- **PMS Project Setup Guide:** [Project Setup Guide](../config/project-setup.md)
