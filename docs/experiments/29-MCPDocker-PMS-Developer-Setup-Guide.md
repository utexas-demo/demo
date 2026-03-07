# MCP Docker Setup Guide for PMS Integration

**Document ID:** PMS-EXP-MCPDOCKER-001
**Version:** 1.0
**Date:** 2026-03-04
**Applies To:** PMS project (all platforms)
**Prerequisites Level:** Intermediate

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Part A: Install and Configure Docker MCP Toolkit](#3-part-a-install-and-configure-docker-mcp-toolkit)
4. [Part B: Integrate with PMS Backend](#4-part-b-integrate-with-pms-backend)
5. [Part C: Integrate with PMS Frontend](#5-part-c-integrate-with-pms-frontend)
6. [Part D: Testing and Verification](#6-part-d-testing-and-verification)
7. [Troubleshooting](#7-troubleshooting)
8. [Reference Commands](#8-reference-commands)

---

## 1. Overview

This guide walks you through deploying the PMS MCP Server and ecosystem MCP servers using Docker's MCP Gateway and Toolkit. By the end, you will have:

- Docker MCP CLI plugin installed and configured
- The PMS MCP Server (Experiment 09) containerized and running through the MCP Gateway
- PostgreSQL and GitHub catalog servers enabled for developer tooling
- Claude Desktop, Cursor, and VS Code connected to the MCP Gateway
- Security interceptors (secret-blocking, signature verification) active
- Centralized credential management via Docker Desktop Toolkit

### Architecture at a Glance

```mermaid
flowchart LR
    subgraph Clients["AI Clients"]
        CD["Claude Desktop"]
        CU["Cursor"]
        VS["VS Code"]
        CC["Claude Code"]
    end

    subgraph Docker["Docker Desktop"]
        GW["MCP Gateway<br/>:8811"]
        subgraph Servers["MCP Servers"]
            PMS["PMS MCP<br/>:9000"]
            PG["mcp/postgres"]
            GH["mcp/github"]
        end
    end

    subgraph Stack["PMS Stack"]
        BE["FastAPI :8000"]
        DB[("PostgreSQL<br/>:5432")]
    end

    Clients -->|stdio| GW
    GW --> PMS
    GW --> PG
    GW --> GH
    PMS --> BE
    PG --> DB
    BE --> DB

    style GW fill:#e8f4fd,stroke:#0078d4
    style PMS fill:#fff3cd,stroke:#ffc107
    style PG fill:#cce5ff,stroke:#0d6efd
    style GH fill:#e2d5f1,stroke:#6f42c1
```

---

## 2. Prerequisites

### 2.1 Required Software

| Software | Minimum Version | Check Command |
|---|---|---|
| Docker Desktop | 4.42.0 | `docker version` |
| Docker MCP CLI Plugin | 0.1.0 (bundled) | `docker mcp version` |
| Python | 3.11+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| Git | 2.40+ | `git --version` |
| PMS Backend (FastAPI) | Latest | `curl http://localhost:8000/health` |
| PMS Frontend (Next.js) | Latest | `curl http://localhost:3000` |
| PostgreSQL | 15+ | `psql --version` |

### 2.2 Installation of Prerequisites

**Docker Desktop (if not already installed):**

```bash
# macOS (Homebrew)
brew install --cask docker

# Verify Docker Desktop version >= 4.42.0
docker version --format '{{.Client.Version}}'
```

**Docker MCP CLI Plugin (if not bundled):**

```bash
# Clone and build from source
git clone https://github.com/docker/mcp-gateway.git
cd mcp-gateway

# Create plugin directory
mkdir -p ~/.docker/cli-plugins

# Build and install
make docker-mcp

# Verify installation
docker mcp version
```

### 2.3 Verify PMS Services

Before proceeding, confirm the PMS stack is running:

```bash
# Check PMS Backend
curl -s http://localhost:8000/health | jq .
# Expected: {"status": "healthy"}

# Check PMS Frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# Expected: 200

# Check PostgreSQL
pg_isready -h localhost -p 5432
# Expected: localhost:5432 - accepting connections

# Check PMS MCP Server (Experiment 09)
curl -s http://localhost:9000/health | jq .
# Expected: {"status": "ok"}
```

---

## 3. Part A: Install and Configure Docker MCP Toolkit

### Step 1: Enable MCP Toolkit in Docker Desktop

1. Open Docker Desktop
2. Navigate to **Settings** (gear icon) > **Features in Development** (or **Beta Features**)
3. Enable **"MCP Toolkit"** toggle
4. Click **Apply & Restart**

Verify from the CLI:

```bash
docker mcp version
# Expected output:
# Docker MCP CLI Plugin
# Version: x.x.x
# Gateway: running
```

### Step 2: Explore the MCP Catalog

```bash
# Search the catalog for available servers
docker mcp catalog search postgres
# Shows: mcp/postgres - PostgreSQL database operations

docker mcp catalog search github
# Shows: mcp/github - GitHub repository operations

# List all available catalog categories
docker mcp catalog list --limit 20
```

### Step 3: Enable Catalog Servers

```bash
# Enable PostgreSQL MCP server (for PMS database introspection)
docker mcp server enable mcp/postgres

# Enable GitHub MCP server (for PMS repo management)
docker mcp server enable mcp/github

# Verify enabled servers
docker mcp server ls
# Expected:
# NAME            IMAGE           STATUS
# postgres        mcp/postgres    running
# github          mcp/github      running
```

### Step 4: Configure Credentials via Toolkit

For the PostgreSQL MCP server, set the database connection:

```bash
# Set PostgreSQL connection string
docker mcp secret set postgres POSTGRESQL_URL "postgresql://pms_user:pms_password@host.docker.internal:5432/pms_db"
```

For the GitHub MCP server:

```bash
# Set GitHub personal access token
docker mcp secret set github GITHUB_TOKEN "ghp_your_token_here"
```

Alternatively, use Docker Desktop UI:
1. Open Docker Desktop > **MCP Toolkit** tab
2. Click on the server (e.g., "postgres")
3. Enter credentials in the **Secrets** section
4. Click **Save**

### Step 5: Containerize the PMS MCP Server

Create a Dockerfile for the PMS MCP Server:

```bash
# Navigate to the PMS MCP server directory
cd pms-mcp-server/
```

Create `Dockerfile.mcp`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Run the MCP server
EXPOSE 9000
CMD ["python", "-m", "pms_mcp_server", "--host", "0.0.0.0", "--port", "9000"]
```

Build and tag:

```bash
# Build the PMS MCP server image
docker build -f Dockerfile.mcp -t mps/pms-mcp-server:latest .

# Verify the image
docker images mps/pms-mcp-server
```

### Step 6: Register PMS MCP Server with Gateway

Create a Gateway configuration file `mcp-config.yaml`:

```yaml
servers:
  pms:
    name: "PMS MCP Server"
    image: "mps/pms-mcp-server:latest"
    transport: "sse"
    port: 9000
    env:
      PMS_BACKEND_URL: "http://host.docker.internal:8000"
      DATABASE_URL: "postgresql://pms_user:pms_password@host.docker.internal:5432/pms_db"
    resources:
      cpu: "1.0"
      memory: "2g"
    network:
      outbound: false  # No internet access - HIPAA isolation
```

Apply the configuration:

```bash
# Register the custom PMS MCP server
docker mcp config write < mcp-config.yaml

# Verify all servers
docker mcp server ls
# Expected:
# NAME            IMAGE                       STATUS
# pms             mps/pms-mcp-server:latest   running
# postgres        mcp/postgres                running
# github          mcp/github                  running
```

### Step 7: Connect AI Clients

```bash
# Connect Claude Desktop
docker mcp client connect claude-desktop

# Connect Cursor
docker mcp client connect cursor

# Connect VS Code
docker mcp client connect vscode

# Connect Claude Code (Gordon)
docker mcp client connect gordon

# Verify client connections
docker mcp client ls
# Expected:
# CLIENT           STATUS      SERVERS
# claude-desktop   connected   pms, postgres, github
# cursor           connected   pms, postgres, github
# vscode           connected   pms, postgres, github
# gordon           connected   pms, postgres, github
```

### Step 8: Enable Security Interceptors

```bash
# Enable signature verification (verify image provenance on pull)
docker mcp feature enable verify-signatures

# Enable secret blocking (scan payloads for leaked credentials)
docker mcp feature enable block-secrets

# Verify active features
docker mcp feature ls
# Expected:
# FEATURE              STATUS
# verify-signatures    enabled
# block-secrets        enabled
```

**Checkpoint:** You now have the Docker MCP Gateway running with 3 MCP servers (PMS, PostgreSQL, GitHub), all AI clients connected, and security interceptors active. Open Claude Desktop and verify you can see tools from all three servers.

---

## 4. Part B: Integrate with PMS Backend

### Step 1: Update Docker Compose

Add the MCP Gateway to the existing PMS `docker-compose.yml`:

```yaml
services:
  # ... existing PMS services ...

  pms-mcp-server:
    build:
      context: ./pms-mcp-server
      dockerfile: Dockerfile.mcp
    container_name: pms-mcp-server
    ports:
      - "9000:9000"
    environment:
      PMS_BACKEND_URL: http://pms-backend:8000
      DATABASE_URL: postgresql://pms_user:pms_password@postgres:5432/pms_db
      MCP_SERVER_NAME: "PMS MCP Server"
      LOG_LEVEL: INFO
    depends_on:
      pms-backend:
        condition: service_healthy
      postgres:
        condition: service_healthy
    networks:
      - pms-internal
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

networks:
  pms-internal:
    driver: bridge
    internal: true  # No outbound internet access
```

### Step 2: Configure PMS Backend for MCP Server Access

Add MCP-specific environment variables to the PMS backend service:

```yaml
  pms-backend:
    # ... existing config ...
    environment:
      # ... existing vars ...
      MCP_SERVER_ENABLED: "true"
      MCP_AUDIT_LOG_ENABLED: "true"
```

### Step 3: Set Up MCP Audit Logging

Create the audit log table in PostgreSQL:

```sql
-- migrations/add_mcp_audit_log.sql
CREATE TABLE IF NOT EXISTS mcp_audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    client_id VARCHAR(255) NOT NULL,
    client_type VARCHAR(50) NOT NULL,  -- 'claude-desktop', 'cursor', 'vscode', etc.
    server_name VARCHAR(255) NOT NULL,
    tool_name VARCHAR(255),
    resource_uri VARCHAR(512),
    prompt_name VARCHAR(255),
    parameters JSONB,
    response_status VARCHAR(20) NOT NULL,  -- 'success', 'error', 'denied'
    latency_ms INTEGER,
    user_identity VARCHAR(255),
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mcp_audit_timestamp ON mcp_audit_log(timestamp);
CREATE INDEX idx_mcp_audit_client ON mcp_audit_log(client_id);
CREATE INDEX idx_mcp_audit_tool ON mcp_audit_log(tool_name);
```

Run the migration:

```bash
# Apply via psql
psql -h localhost -U pms_user -d pms_db -f migrations/add_mcp_audit_log.sql
```

### Step 4: Gateway Audit Integration

Configure the MCP Gateway to forward call traces to the PMS audit log:

```yaml
# mcp-gateway-config.yaml (append to existing config)
logging:
  enabled: true
  format: json
  output: stdout
  call_tracing:
    enabled: true
    include_parameters: true
    redact_patterns:
      - "\\b\\d{3}-\\d{2}-\\d{4}\\b"  # SSN pattern
      - "\\b\\d{9}\\b"                  # MRN pattern
```

**Checkpoint:** The PMS MCP server is integrated into Docker Compose, audit logging is configured, and the Gateway forwards call traces with PHI redaction patterns.

---

## 5. Part C: Integrate with PMS Frontend

### Step 1: Frontend Environment Configuration

Add MCP Gateway awareness to the PMS Frontend `.env.local`:

```bash
# .env.local
NEXT_PUBLIC_MCP_GATEWAY_URL=http://localhost:8811
NEXT_PUBLIC_MCP_ENABLED=true
```

### Step 2: MCP Status Dashboard Component

Create a developer-facing MCP status component in the PMS Frontend:

```typescript
// components/dev/MCPStatus.tsx
"use client";

import { useEffect, useState } from "react";

interface MCPServer {
  name: string;
  image: string;
  status: "running" | "stopped" | "error";
  tools: number;
  uptime: string;
}

export function MCPStatus() {
  const [servers, setServers] = useState<MCPServer[]>([]);

  useEffect(() => {
    // Fetch MCP server status from PMS backend proxy
    fetch("/api/admin/mcp-servers")
      .then((res) => res.json())
      .then((data) => setServers(data.servers))
      .catch(console.error);
  }, []);

  if (process.env.NODE_ENV !== "development") return null;

  return (
    <div className="fixed bottom-4 right-4 bg-white shadow-lg rounded-lg p-4 max-w-sm border">
      <h3 className="font-semibold text-sm mb-2">MCP Servers</h3>
      {servers.map((s) => (
        <div key={s.name} className="flex items-center gap-2 text-xs py-1">
          <span
            className={`w-2 h-2 rounded-full ${
              s.status === "running" ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="font-medium">{s.name}</span>
          <span className="text-gray-500">{s.tools} tools</span>
        </div>
      ))}
    </div>
  );
}
```

### Step 3: Backend MCP Admin Endpoint

Add an admin endpoint to the PMS backend for MCP server status:

```python
# routers/admin.py (add to existing admin router)
import subprocess
import json

@router.get("/admin/mcp-servers")
async def get_mcp_servers(current_user: User = Depends(get_admin_user)):
    """Return status of all MCP servers managed by Docker MCP Gateway."""
    try:
        result = subprocess.run(
            ["docker", "mcp", "server", "ls", "--format", "json"],
            capture_output=True, text=True, timeout=5
        )
        servers = json.loads(result.stdout) if result.returncode == 0 else []
        return {"servers": servers}
    except Exception:
        return {"servers": [], "error": "MCP Gateway not available"}
```

### Step 4: MCP Audit Log Viewer

Add a route to view MCP audit logs in the admin dashboard:

```python
# routers/admin.py (add to existing admin router)
from sqlalchemy import select, desc
from models.mcp_audit import MCPAuditLog

@router.get("/admin/mcp-audit")
async def get_mcp_audit_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """Return recent MCP audit log entries."""
    stmt = select(MCPAuditLog).order_by(desc(MCPAuditLog.timestamp)).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return {"logs": [log.to_dict() for log in logs]}
```

**Checkpoint:** The PMS Frontend has a dev-mode MCP status widget, and the backend exposes admin endpoints for MCP server management and audit log viewing.

---

## 6. Part D: Testing and Verification

### Step 1: Verify MCP Gateway Health

```bash
# Check Gateway is running
docker mcp version
# Expected: Gateway: running

# List all enabled servers
docker mcp server ls
# Expected: pms, postgres, github all showing "running"
```

### Step 2: Test PMS MCP Server Through Gateway

```bash
# List available tools via the Gateway
docker mcp tools ls --server pms
# Expected: search_patients, get_patient, create_patient, list_encounters, etc.

# Test a tool call through the Gateway
docker mcp tools call --server pms --tool search_patients --input '{"query": "Smith"}'
# Expected: JSON response with matching patient records
```

### Step 3: Test PostgreSQL MCP Server

```bash
# List PostgreSQL tools
docker mcp tools ls --server postgres
# Expected: query, list_tables, describe_table, etc.

# Test schema introspection
docker mcp tools call --server postgres --tool list_tables
# Expected: List of PMS database tables
```

### Step 4: Test Security Interceptors

```bash
# Test secret blocking - try to send a payload with an API key pattern
docker mcp tools call --server pms --tool search_patients \
  --input '{"query": "ghp_fake_github_token_12345"}'
# Expected: Request blocked by secret-blocking interceptor

# Check Gateway logs for interceptor activity
docker mcp gateway logs --tail 20
```

### Step 5: Verify AI Client Integration

Open Claude Desktop and verify:
1. Tools from all three MCP servers appear in the tool list
2. Run: "List all tables in the PMS database" (uses PostgreSQL MCP)
3. Run: "Search for patients named Smith" (uses PMS MCP)
4. Run: "List open PRs in the PMS backend repo" (uses GitHub MCP)

### Step 6: Verify Audit Logging

```bash
# Check audit log entries
psql -h localhost -U pms_user -d pms_db -c \
  "SELECT timestamp, client_type, tool_name, response_status FROM mcp_audit_log ORDER BY timestamp DESC LIMIT 10;"
# Expected: Recent tool invocations logged with client identity
```

### Step 7: Run Integration Tests

```bash
# Run MCP integration test suite
cd pms-backend/
python -m pytest tests/integration/test_mcp_docker.py -v

# Example test
# test_gateway_proxies_pms_tools ... PASSED
# test_secret_blocking_interceptor ... PASSED
# test_audit_log_written ... PASSED
# test_resource_limits_enforced ... PASSED
```

**Checkpoint:** All MCP servers are running through the Gateway, security interceptors are active, AI clients can access tools, and audit logging is working.

---

## 7. Troubleshooting

### Docker MCP CLI Not Found

**Symptom:** `docker: 'mcp' is not a docker command`

**Solution:**
```bash
# Check Docker Desktop version (must be >= 4.42.0)
docker version --format '{{.Client.Version}}'

# If version is correct but CLI missing, reinstall plugin
git clone https://github.com/docker/mcp-gateway.git
cd mcp-gateway && make docker-mcp

# Verify plugin is in the correct directory
ls ~/.docker/cli-plugins/docker-mcp
```

### MCP Server Fails to Start

**Symptom:** `docker mcp server ls` shows server as "error"

**Solution:**
```bash
# Inspect the server for detailed error
docker mcp server inspect pms

# Check container logs
docker logs $(docker ps -qf "name=mcp-pms") --tail 50

# Common causes:
# - Port 9000 already in use: stop conflicting service
# - Missing environment variables: check mcp-config.yaml
# - Image not found: rebuild with docker build
```

### AI Client Not Seeing MCP Tools

**Symptom:** Claude Desktop or Cursor shows no MCP tools

**Solution:**
```bash
# Verify client connection
docker mcp client ls

# Reconnect the client
docker mcp client connect claude-desktop

# Restart Claude Desktop / Cursor after reconnecting

# Check Gateway is routing properly
docker mcp gateway logs --tail 20
```

### Gateway Connection Refused

**Symptom:** `Connection refused` when AI client connects to Gateway

**Solution:**
```bash
# Check if Gateway process is running
docker mcp gateway status

# Restart the Gateway
docker mcp gateway restart

# Check port availability
lsof -i :8811
```

### Secret Blocking False Positives

**Symptom:** Legitimate tool calls blocked by secret-blocking interceptor

**Solution:**
```bash
# Check Gateway logs for blocked requests
docker mcp gateway logs | grep "blocked"

# Adjust secret patterns in Gateway config
docker mcp config read > current-config.yaml
# Edit the block-secrets patterns
docker mcp config write < current-config.yaml
```

### Performance Issues

**Symptom:** Slow tool call responses (> 5 seconds)

**Solution:**
```bash
# Check resource usage per MCP server container
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" --no-stream | grep mcp

# Increase resource limits if needed
# Edit mcp-config.yaml:
#   resources:
#     cpu: "2.0"
#     memory: "4g"
docker mcp config write < mcp-config.yaml

# Check PMS backend response time (the bottleneck may be upstream)
curl -w "@curl-format.txt" -s http://localhost:8000/api/patients?q=Smith
```

### Credential Issues

**Symptom:** MCP server can't authenticate to external service

**Solution:**
```bash
# List stored secrets
docker mcp secret ls

# Update a secret
docker mcp secret set postgres POSTGRESQL_URL "postgresql://..."

# Or use Docker Desktop UI: MCP Toolkit > Server > Secrets
```

---

## 8. Reference Commands

### Daily Development Workflow

```bash
# Start of day: verify everything is running
docker mcp server ls
docker mcp client ls

# Check for catalog updates
docker mcp catalog search --updates

# View recent audit logs
docker mcp gateway logs --tail 50
```

### Server Management Commands

```bash
# Enable a new catalog server
docker mcp server enable mcp/<server-name>

# Disable a server
docker mcp server disable <server-name>

# Inspect server details (image, tools, resources)
docker mcp server inspect <server-name>

# Reset a server to default configuration
docker mcp server reset <server-name>

# List all tools across all servers
docker mcp tools ls
```

### Gateway Management Commands

```bash
# View Gateway status
docker mcp gateway status

# View Gateway logs
docker mcp gateway logs --tail 100

# Run Gateway in streaming mode (for remote access)
docker mcp gateway run --port 8811 --transport streaming

# Export Gateway configuration
docker mcp config read > mcp-config-backup.yaml

# Import Gateway configuration (team sharing)
docker mcp config write < team-mcp-config.yaml
```

### Monitoring Commands

```bash
# Container resource usage
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" --no-stream | grep mcp

# Check image provenance
docker scout verify mps/pms-mcp-server:latest

# View SBOM for a catalog image
docker scout sbom mcp/postgres
```

### Useful URLs

| Resource | URL |
|---|---|
| Docker Desktop MCP Toolkit | Open Docker Desktop > MCP Toolkit tab |
| MCP Gateway (streaming mode) | `http://localhost:8811` |
| PMS MCP Server (direct) | `http://localhost:9000` |
| PMS Backend | `http://localhost:8000` |
| PMS Frontend | `http://localhost:3000` |
| PMS Database | `postgresql://localhost:5432/pms_db` |
| Docker MCP Catalog | `https://hub.docker.com/u/mcp` |
| Docker MCP Gateway GitHub | `https://github.com/docker/mcp-gateway` |

---

## Next Steps

1. Complete the [MCP Docker Developer Tutorial](29-MCPDocker-Developer-Tutorial.md) for hands-on practice building custom integrations
2. Review the [PRD: MCP Docker PMS Integration](29-PRD-MCPDocker-PMS-Integration.md) for full architecture context
3. Review the [MCP PMS Integration (Experiment 09)](09-PRD-MCP-PMS-Integration.md) for the underlying PMS MCP Server design
4. Explore the [Docker MCP Catalog](https://hub.docker.com/u/mcp) for additional servers to enable

---

## Resources

### Official Documentation
- [Docker MCP Catalog and Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/)
- [Docker MCP Gateway Docs](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/)
- [Docker MCP CLI Reference](https://docs.docker.com/reference/cli/docker/mcp/)
- [Docker MCP Toolkit Docs](https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/)

### GitHub Repositories
- [Docker MCP Gateway](https://github.com/docker/mcp-gateway) — Open-source CLI plugin
- [Docker MCP Registry](https://github.com/docker/mcp-registry) — Official server registry

### Community Resources
- [Docker MCP CLI Commands Cheatsheet](https://www.ajeetraina.com/docker-mcp-cli-commands-and-cheatsheet/)
- [Add MCP Servers to Claude Code with MCP Toolkit](https://www.docker.com/blog/add-mcp-servers-to-claude-code-with-mcp-toolkit/)

### PMS-Specific References
- [PMS MCP Server PRD (Experiment 09)](09-PRD-MCP-PMS-Integration.md)
- [PMS MCP Server Setup Guide (Experiment 09)](09-MCP-PMS-Developer-Setup-Guide.md)
- [PMS Backend API Endpoints](../api/backend-endpoints.md)
