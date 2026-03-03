# Claude Context Mode Developer Tutorial

**Document ID:** PMS-EXP-CONTEXTMODE-TUT-001
**Version:** 1.0
**Date:** March 3, 2026
**Applies To:** PMS project (all platforms)
**Prerequisites:** [Claude Context Mode Setup Guide](36-ClaudeContextMode-PMS-Developer-Setup-Guide.md) completed

---

## What You Will Build

In this tutorial, you will build a **PMS Development Session Optimizer** — a complete Context Mode workflow that demonstrates how to use sandbox execution, FTS5 knowledge indexing, batch processing, and subagent routing to run an efficient, long-running Claude Code development session on the PMS codebase.

By the end, you will have:

1. **Indexed** the full PMS documentation into a searchable FTS5 knowledge base
2. **Sandboxed** patient record API analysis with PHI-safe summarization
3. **Batch-processed** a full-stack health check across all PMS services
4. **Built** a medication reconciliation debugging workflow using Context Mode tools
5. **Measured** context savings and session efficiency using `/context-mode:stats`

**Estimated time:** 45-60 minutes

---

## Step 1: Index PMS Documentation into the Knowledge Base

The first step in any Context Mode session is to build a searchable knowledge base from the PMS documentation. This indexes content into SQLite FTS5 with Porter stemming and BM25 ranking, so you can retrieve relevant snippets on demand without loading full documents into the context window.

### 1.1 Index Architecture Decision Records

Inside Claude Code, instruct Claude to run:

```
Use context-mode to index the PMS architecture decisions.
```

Claude will use the `index` tool with content from `docs/architecture/`:

```python
# Context Mode indexes this into SQLite FTS5
# Only the index confirmation (~50 bytes) enters the conversation context
# The full content of all ADRs (~200KB) stays in the FTS5 database

batch_execute([
    {
        "code": "for f in docs/architecture/*.md; do echo \"=== $f ===\"; cat \"$f\"; echo; done",
        "language": "shell"
    }
])
```

### 1.2 Index System Requirements

```python
# Index the three-tier requirements hierarchy
batch_execute([
    {
        "code": "cat docs/specs/requirements/SYS-REQ.md",
        "language": "shell"
    },
    {
        "code": "for f in docs/specs/requirements/domain/*.md; do echo \"=== $f ===\"; cat \"$f\"; echo; done",
        "language": "shell"
    },
    {
        "code": "for f in docs/specs/requirements/platform/*.md; do echo \"=== $f ===\"; cat \"$f\"; echo; done",
        "language": "shell"
    }
])
```

### 1.3 Index API Specifications

```python
# Index the FastAPI OpenAPI schema
fetch_and_index("http://localhost:8000/docs")

# Index the backend API endpoint documentation
index(open("docs/api/backend-endpoints.md").read())
```

### 1.4 Verify the Knowledge Base

Search the indexed content to confirm it is retrievable:

```python
# Test multi-query search with BM25 ranking
search(queries=[
    "patient records CRUD operations",
    "HIPAA audit logging requirements",
    "medication management prescriptions"
])
```

**Expected output:** Ranked snippets from the indexed documents, with relevance scores. Each result is a compact snippet (~100-300 bytes) rather than full documents.

**Context impact:** Indexing processes ~500 KB of documentation, but only ~2 KB of index confirmations and search results enter the conversation context — a 99.6% savings.

**Checkpoint:** PMS documentation is indexed. Search returns relevant snippets from architecture decisions, requirements, and API specs.

---

## Step 2: PHI-Safe Patient Data Analysis

One of Context Mode's most important features for healthcare development is sandbox processing of patient data. Raw patient records containing PHI are processed in an isolated subprocess — only aggregated summaries enter the conversation context.

### 2.1 Analyze Patient Records Without Loading PHI

```python
# WRONG: This loads raw patient JSON (50KB+) into context
# curl http://localhost:8000/api/patients

# RIGHT: Sandbox processes the data; only summary enters context
execute("""
import requests
import json

resp = requests.get('http://localhost:8000/api/patients')
patients = resp.json()

# Aggregate statistics only — no individual patient data
total = len(patients)
active = sum(1 for p in patients if p.get('status') == 'active')
inactive = total - active

# Age distribution (if birth_date available)
ages = []
from datetime import date
for p in patients:
    bd = p.get('birth_date')
    if bd:
        try:
            born = date.fromisoformat(bd)
            ages.append((date.today() - born).days // 365)
        except (ValueError, TypeError):
            pass

# Field inventory
fields = set()
for p in patients:
    fields.update(p.keys())

print(f"Patient Summary")
print(f"  Total: {total} ({active} active, {inactive} inactive)")
if ages:
    print(f"  Age range: {min(ages)}-{max(ages)} (mean: {sum(ages)/len(ages):.0f})")
print(f"  Fields: {', '.join(sorted(fields))}")
print(f"  Sample IDs: {[p.get('id') for p in patients[:3]]}")
""", language="python")
```

**What enters context (~200 bytes):**
```
Patient Summary
  Total: 847 (792 active, 55 inactive)
  Age range: 18-94 (mean: 52)
  Fields: allergies, birth_date, encounters, first_name, id, last_name, medications, status
  Sample IDs: [1, 2, 3]
```

**What stays in sandbox (~50 KB):** Full patient records with names, dates, diagnoses, medications — all discarded after processing.

### 2.2 Analyze Encounter Patterns

```python
execute("""
import requests
from collections import Counter

resp = requests.get('http://localhost:8000/api/encounters')
encounters = resp.json()

# Type distribution
types = Counter(e.get('encounter_type', 'unknown') for e in encounters)

# Status distribution
statuses = Counter(e.get('status', 'unknown') for e in encounters)

# Monthly volume (last 6 months)
from datetime import datetime, timedelta
six_months_ago = (datetime.now() - timedelta(days=180)).isoformat()
recent = [e for e in encounters if e.get('date', '') >= six_months_ago]

print(f"Encounter Summary")
print(f"  Total: {len(encounters)} ({len(recent)} in last 6 months)")
print(f"  Types: {dict(types.most_common(5))}")
print(f"  Statuses: {dict(statuses)}")
print(f"  Avg encounters per month (6mo): {len(recent)/6:.0f}")
""", language="python")
```

### 2.3 Search for Related Documentation

After analyzing the data, search the knowledge base for relevant context:

```python
# Find documentation related to what you observed
search(queries=[
    "encounter types classification",
    "patient status active inactive",
    "encounter API pagination"
])
```

**Checkpoint:** You have analyzed patient and encounter data without loading any PHI into the conversation context. Only aggregated statistics are visible in the session.

---

## Step 3: Full-Stack Health Check with Batch Processing

Batch execution runs multiple commands in parallel, consolidating results into a single compact response. This is essential for multi-service development environments like PMS.

### 3.1 Build a PMS Service Health Check

```python
# Check all PMS services in a single batch call
batch_execute([
    {
        "code": "curl -s http://localhost:8000/health | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'Backend: {d.get(\\\"status\\\", \\\"unknown\\\")}, version: {d.get(\\\"version\\\", \\\"N/A\\\")}')\"",
        "language": "shell"
    },
    {
        "code": "curl -s -o /dev/null -w 'Frontend: HTTP %{http_code}' http://localhost:3000",
        "language": "shell"
    },
    {
        "code": "pg_isready -h localhost -p 5432 && echo 'PostgreSQL: accepting connections' || echo 'PostgreSQL: unavailable'",
        "language": "shell"
    },
    {
        "code": "curl -s -o /dev/null -w 'FastAPI Docs: HTTP %{http_code}' http://localhost:8000/docs",
        "language": "shell"
    }
])
```

**What enters context (~150 bytes):**
```
Backend: healthy, version: 0.5.2
Frontend: HTTP 200
PostgreSQL: accepting connections
FastAPI Docs: HTTP 200
```

### 3.2 Run Cross-Platform Test Summary

```python
# Parallel test suite execution with summary-only output
batch_execute([
    {
        "code": "cd /path/to/pms-backend && python -m pytest tests/ -q --tb=no 2>&1 | tail -3",
        "language": "shell"
    },
    {
        "code": "cd /path/to/pms-frontend && npx jest --watchAll=false --silent 2>&1 | tail -5",
        "language": "shell"
    }
])
```

**Context impact:** Full test output is typically 6-85 KB. With Context Mode, only the summary lines (pass/fail counts) enter the context — approximately 337 bytes.

**Checkpoint:** All PMS services health-checked in a single batch call. Test summaries extracted without loading full output.

---

## Step 4: Medication Reconciliation Debugging Workflow

This step demonstrates a realistic PMS development scenario: debugging the medication reconciliation feature using Context Mode tools throughout the workflow.

### 4.1 Understand the Feature (Search Knowledge Base)

Start by searching the indexed documentation for context about medication reconciliation:

```python
search(queries=[
    "medication reconciliation workflow",
    "drug interaction checking",
    "prescription CRUD API endpoints"
])
```

This returns compact snippets from the indexed PRDs, setup guides, and API docs — typically 500-800 bytes total instead of reading multiple full documents (50+ KB).

### 4.2 Inspect the Database Schema

```python
# Understand the medication-related tables without loading full schema
execute("""
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, dbname='pms', user='pms_user', password='pms_pass')
cur = conn.cursor()

# List medication-related tables
cur.execute(\"\"\"
    SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name)))
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name LIKE '%medic%' OR table_name LIKE '%presc%' OR table_name LIKE '%drug%'
    ORDER BY table_name
\"\"\")
tables = cur.fetchall()

print("Medication-related tables:")
for t, size in tables:
    # Get column info
    cur.execute(f\"\"\"
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = '{t}'
        ORDER BY ordinal_position
    \"\"\")
    cols = cur.fetchall()
    print(f"  {t} ({size}):")
    for col, dtype, nullable in cols:
        print(f"    - {col}: {dtype} {'(nullable)' if nullable == 'YES' else ''}")

    # Row count
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    count = cur.fetchone()[0]
    print(f"    Rows: {count}")

conn.close()
""", language="python")
```

### 4.3 Trace a Specific Bug

Suppose the medication reconciliation endpoint returns incorrect interaction data. Debug in the sandbox:

```python
# Trace the medication interaction logic without PHI in context
execute("""
import requests

# Fetch a test patient's medications (IDs only, no names)
resp = requests.get('http://localhost:8000/api/patients/1/prescriptions')
meds = resp.json()

print(f"Patient 1 has {len(meds)} prescriptions")
print(f"Medication IDs: {[m.get('medication_id') for m in meds]}")
print(f"Statuses: {[m.get('status') for m in meds]}")

# Test the interaction endpoint
if len(meds) >= 2:
    med_ids = [m.get('medication_id') for m in meds[:5]]
    interaction_resp = requests.post(
        'http://localhost:8000/api/medications/interactions',
        json={'medication_ids': med_ids}
    )
    result = interaction_resp.json()
    print(f"\\nInteraction check for {len(med_ids)} medications:")
    print(f"  Status: {interaction_resp.status_code}")
    print(f"  Interactions found: {len(result.get('interactions', []))}")
    for ix in result.get('interactions', []):
        print(f"  - {ix.get('severity', 'unknown')}: {ix.get('description', 'N/A')[:80]}")
else:
    print("Not enough prescriptions for interaction check")
""", language="python")
```

### 4.4 Inspect the Source Code

```python
# Find and analyze the interaction checking logic
execute("""
# Find the relevant source files
echo "=== Files containing 'interaction' ==="
grep -rl 'interaction' --include='*.py' pms-backend/app/ 2>/dev/null | head -10

echo ""
echo "=== Interaction endpoint handler ==="
grep -n 'def.*interaction' pms-backend/app/routers/*.py 2>/dev/null | head -10

echo ""
echo "=== Interaction model/schema ==="
grep -n 'class.*Interaction' pms-backend/app/models/*.py pms-backend/app/schemas/*.py 2>/dev/null | head -10
""", language="shell")
```

### 4.5 Compare Context Usage

At this point in the tutorial, check your context savings:

```
/context-mode:stats
```

**Expected output:**
```
Session Statistics
-----------------
Duration: ~25 minutes
Total data processed: ~180 KB
Data kept in sandbox: ~175 KB
Context entered: ~5 KB
Savings: 97.2%

Per-Tool Breakdown:
  execute: 6 calls, 160 KB processed, 1.8 KB in context
  search: 3 calls, 15 KB indexed, 1.2 KB returned
  batch_execute: 2 calls, 5 KB processed, 0.5 KB in context
  fetch_and_index: 1 call, 45 KB indexed, 0.1 KB confirmation
```

Compare this to a session without Context Mode: the same workflow would have consumed approximately 180 KB of the 200 KB context window in 25 minutes. With Context Mode, only 5 KB has been used — leaving 195 KB available for continued development.

**Checkpoint:** You have debugged a medication reconciliation feature across database, API, and source code layers while consuming only ~5 KB of context.

---

## Step 5: Build a Reusable PMS Session Startup Script

Now that you understand the Context Mode tools, create a reusable session startup workflow that any PMS developer can run at the start of their Claude Code session.

### 5.1 Create the CLAUDE.md Context Mode Section

Add this to your project's `CLAUDE.md`:

```markdown
## Context Mode Session Startup

At the start of each Claude Code session working on PMS, run these Context Mode commands:

### 1. Health Check (batch_execute)
Verify all PMS services are running:
- Backend: http://localhost:8000/health
- Frontend: http://localhost:3000
- PostgreSQL: pg_isready localhost:5432

### 2. Index Fresh Documentation (batch_execute)
Re-index documentation that may have changed since last session:
- docs/architecture/*.md (ADRs)
- docs/specs/requirements/**/*.md (requirements)
- docs/api/backend-endpoints.md (API reference)

### 3. PHI-Safe Convention Reminder
- Patient data operations: ALWAYS use `execute` (sandbox-and-discard)
- Documentation and code: safe to use `index` (persist in FTS5)
- Never `index` or `fetch_and_index` URLs containing patient data
```

### 5.2 Create a Startup Batch Template

Save this as a reference for quick session initialization:

```python
# PMS Session Startup — run at the beginning of each Claude Code session
# Total context cost: ~1.5 KB (vs ~200 KB manual setup)

# Step 1: Health check all services
batch_execute([
    {"code": "curl -sf http://localhost:8000/health | python3 -c \"import sys,json; print('Backend:', json.load(sys.stdin).get('status'))\"", "language": "shell"},
    {"code": "curl -sf -o /dev/null -w 'Frontend: HTTP %{http_code}' http://localhost:3000", "language": "shell"},
    {"code": "pg_isready -h localhost -p 5432 2>&1 | tail -1", "language": "shell"},
])

# Step 2: Index documentation (only new/changed files)
batch_execute([
    {"code": "find docs/ -name '*.md' -newer .context-mode-last-index -print0 2>/dev/null | xargs -0 cat 2>/dev/null || echo 'No changes since last index'", "language": "shell"},
])

# Step 3: Quick project status
batch_execute([
    {"code": "git log --oneline -5", "language": "shell"},
    {"code": "git diff --stat HEAD~1", "language": "shell"},
    {"code": "git branch --show-current", "language": "shell"},
])
```

**Context cost of entire startup:** Approximately 1.5 KB — leaving 198.5 KB of the 200 KB context window for actual development work.

**Checkpoint:** You have a reusable session startup workflow that initializes Context Mode for PMS development in under 30 seconds.

---

## Step 6: Advanced Patterns

### 6.1 Subagent-Powered Code Exploration

Context Mode's PreToolUse hook automatically routes subagent tool calls through the sandbox. Launch a research subagent that benefits from context compression:

```
Ask Claude Code to: "Use a subagent to analyze the PMS backend router structure.
List all API endpoints, their HTTP methods, and which service modules they call."
```

The subagent will automatically use Context Mode's `batch_execute` instead of raw `Read` or `Bash` tools. The subagent's analysis (which might process 100+ KB of source files) returns as a compact summary (~2-3 KB) to the main conversation.

### 6.2 Progressive Search for Debugging

When investigating a complex bug, use the progressive search pattern:

```python
# First pass: broad search (returns 2 results each, uses 3 of the 8 free queries)
search(queries=[
    "medication reconciliation error",
    "drug interaction validation",
    "prescription status update"
])

# Second pass: targeted search based on first results
search(queries=[
    "MedicationService.check_interactions",
    "InteractionSeverity enum",
])

# Third pass: if you need more, switch to batch (avoids throttle)
batch_execute([
    {"code": "grep -rn 'check_interactions' pms-backend/app/ --include='*.py'", "language": "shell"},
    {"code": "grep -rn 'InteractionSeverity' pms-backend/app/ --include='*.py'", "language": "shell"},
    {"code": "grep -rn 'reconciliation' pms-backend/app/ --include='*.py'", "language": "shell"},
])
```

### 6.3 Multi-File Refactoring with Context Mode

When refactoring across multiple files, use Context Mode to understand the codebase scope without consuming context:

```python
# Step 1: Map the refactoring scope
execute("""
echo "=== Files to refactor ==="
grep -rl 'old_function_name' --include='*.py' pms-backend/app/ 2>/dev/null

echo ""
echo "=== Occurrences per file ==="
grep -rc 'old_function_name' --include='*.py' pms-backend/app/ 2>/dev/null | grep -v ':0$'

echo ""
echo "=== Import chains ==="
grep -rn 'from.*import.*old_function_name' --include='*.py' pms-backend/app/ 2>/dev/null

echo ""
echo "=== Test coverage ==="
grep -rl 'old_function_name' --include='*.py' pms-backend/tests/ 2>/dev/null
""", language="shell")
```

Then proceed with the actual refactoring using Claude Code's standard Edit tool — you now have full context of the refactoring scope without having consumed context window reading all the files.

### 6.4 Session Duration Monitoring

Set up periodic context monitoring during long sessions:

```
# Check every 30 minutes during long development sessions
/context-mode:stats

# If savings drop below 80%, look for:
# 1. Unbatched sequential tool calls
# 2. Large file reads that should use execute
# 3. API responses that bypassed the sandbox
```

**Target benchmarks by session type:**

| Session Type | Expected Duration | Context Savings | Typical Context Used |
|-------------|-------------------|-----------------|---------------------|
| Bug fix (single file) | 1-2 hours | 85-90% | 10-20 KB |
| Feature development | 2-3 hours | 90-95% | 15-30 KB |
| Cross-platform refactor | 2-4 hours | 95-98% | 5-15 KB |
| Documentation update | 3-5 hours | 98%+ | 3-8 KB |

---

## Summary

In this tutorial you built a complete PMS development session optimization workflow:

| Step | What You Did | Context Impact |
|------|-------------|----------------|
| 1. Index Docs | Loaded ~500 KB of PMS docs into FTS5 | ~2 KB (index confirmations) |
| 2. PHI-Safe Analysis | Analyzed patient and encounter data | ~400 bytes (aggregated stats) |
| 3. Health Check | Batch-checked 4 PMS services | ~150 bytes |
| 4. Debug Workflow | Traced medication reconciliation bug | ~3 KB (code summaries) |
| 5. Startup Script | Built reusable session initialization | ~1.5 KB |
| 6. Advanced Patterns | Subagent routing, progressive search | ~2-3 KB |
| **Total** | **Full development workflow** | **~9 KB (vs ~200+ KB without Context Mode)** |

### Key Takeaways

1. **Sandbox everything with PHI:** Use `execute` for any operation touching patient data — raw PHI never enters the conversation context
2. **Batch for parallelism:** Use `batch_execute` for multi-service operations and multi-file analysis to reduce tool call overhead
3. **Index documentation, not data:** Use `index` and `fetch_and_index` for non-PHI content (docs, schemas, code); use `execute` for sensitive data
4. **Monitor context usage:** Run `/context-mode:stats` periodically to verify savings and identify inefficient patterns
5. **Progressive search:** Start broad (3 queries), narrow based on results, then switch to `batch_execute` for deep exploration

---

## Next Steps

1. **[MCP PMS Integration (Exp 09)](09-PRD-MCP-PMS-Integration.md)** — Combine Context Mode with PMS MCP tools: Context Mode compresses MCP tool outputs for maximum session efficiency
2. **[Multi-Agent Modes (Exp 14)](14-AgentTeams-Developer-Tutorial.md)** — Use Context Mode's subagent routing with agent teams for parallel PMS development
3. **[Knowledge Work Plugins (Exp 24)](24-PRD-KnowledgeWorkPlugins-PMS-Integration.md)** — Package Context Mode workflows as reusable PMS plugin commands
4. **[Claude Code Mastery (Exp 27)](27-ClaudeCode-Developer-Tutorial.md)** — Deep-dive into Claude Code features that complement Context Mode

---

## Resources

- [Context Mode GitHub Repository](https://github.com/mksglu/claude-context-mode)
- [Context Mode Benchmark Results](https://github.com/mksglu/claude-context-mode/blob/main/BENCHMARK.md)
- [Context Mode Demo Script](https://github.com/mksglu/claude-context-mode/blob/main/demo.md)
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)
- [MCP Specification](https://modelcontextprotocol.io)
