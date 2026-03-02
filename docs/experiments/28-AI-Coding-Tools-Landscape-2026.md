# AI Coding Tools Landscape -- Comprehensive Comparison (Early 2026)

**Experiment:** 28 -- AI Coding Tools Landscape Research
**Category:** Dev Tooling / Strategic Assessment
**Date:** March 2, 2026
**Purpose:** Vendor evaluation, lock-in risk analysis, and emergency transition planning for the PMS project

---

## Table of Contents

1. [Claude Code (Anthropic)](#1-claude-code-anthropic)
2. [OpenAI Codex / ChatGPT Coding Agents](#2-openai-codex--chatgpt-coding-agents)
3. [Qwen 3.5 (Alibaba)](#3-qwen-35-alibaba)
4. [GitHub Copilot](#4-github-copilot)
5. [Cursor](#5-cursor)
6. [Windsurf (Codeium)](#6-windsurf-codeium)
7. [Google Gemini Code Assist / Jules](#7-google-gemini-code-assist--jules)
8. [Amazon Q Developer](#8-amazon-q-developer)
9. [Other Notable Tools](#9-other-notable-tools)
10. [Healthcare / Enterprise Compliance Matrix](#10-healthcare--enterprise-compliance-matrix)
11. [Vendor Lock-in Risk Analysis](#11-vendor-lock-in-risk-analysis)
12. [Emergency Transition Playbook](#12-emergency-transition-playbook)
13. [Open-Source Fallback Stack](#13-open-source-fallback-stack)
14. [Recommendation for PMS Project](#14-recommendation-for-pms-project)
15. [Sources](#15-sources)

---

## 1. Claude Code (Anthropic)

### Overview

Claude Code is Anthropic's official CLI tool that transforms a terminal session into an AI-powered development environment. It reads files, writes code, runs commands, manages git workflows, and submits pull requests -- all through natural language conversation. Native extensions are available for VS Code, VS Code forks (Cursor, Windsurf), and JetBrains.

### Models

| Model | Context Window | Strengths |
|-------|---------------|-----------|
| **Claude Opus 4.6** | 200K standard / 1M extended | Flagship reasoning model. Released Feb 5, 2026. Best-in-class for complex multi-file edits, architecture decisions, security analysis |
| **Claude Sonnet 4.6** | 200K | Balanced performance/cost. Good for daily coding, code review, documentation |
| **Claude Haiku 4.5** | 200K | Fastest/cheapest. Suitable for autocomplete, simple extraction, structured data parsing |

### Key Features

- **Agentic coding**: Full autonomy -- reads issues, plans, codes, tests, commits, and submits PRs
- **Terminal access**: Runs arbitrary shell commands (with permission model: suggest/auto-approve/deny)
- **Multi-file editing**: Edits across the entire codebase with full repository context
- **MCP support**: Both as MCP client (connects to external tools) and MCP server (exposes its tools to other clients). Lazy-loading reduces context usage by up to 95%
- **Agent Teams** (experimental): Multiple Claude Code instances coordinate with a shared task list, direct messaging, and a team lead orchestrator. Teammates get project context (CLAUDE.md, MCP servers, skills) automatically
- **Sub-agents**: Spawn child sessions for parallel work within a single conversation
- **Git worktrees**: Isolated branches for concurrent work streams
- **Hooks**: Pre/post-command hooks for enforcement (linting, testing, HIPAA checks)
- **Skills**: Reusable instruction sets that teach Claude domain-specific capabilities
- **Headless mode**: Non-interactive execution for CI/CD pipelines and automation
- **CLAUDE.md**: Per-project instruction files that persist context across sessions

### Pricing

| Plan | Price | Claude Code Access | Details |
|------|-------|-------------------|---------|
| **Free** | $0/month | No access | Chat only |
| **Pro** | $20/month ($17/yr) | Yes, limited | Basic Claude Code with usage caps |
| **Max 5x** | $100/month | Yes | 5x Pro usage, Opus 4.6 access, Agent Teams (preview), 1M context |
| **Max 20x** | $200/month | Yes | 20x Pro usage, highest throughput, priority access |
| **API** | Pay-per-token | Yes | Opus: $5/$25 per 1M input/output tokens (standard); $10/$37.50 (extended context). Sonnet: ~$3/$15. Haiku: ~$0.80/$4 |

### Open-Source / Self-Hosted

- Claude Code CLI itself is **not open-source**
- No self-hosted model option -- all inference runs on Anthropic's servers
- Can be used via AWS Bedrock or Google Vertex AI for managed deployment with data residency controls
- MCP protocol is open standard; CLAUDE.md files and skills are portable

### Healthcare / Enterprise Compliance

- **SOC 2 Type II**: Yes
- **ISO 27001:2022**: Yes
- **ISO 42001:2023**: Yes (AI management system)
- **HIPAA**: Available via Enterprise plan with signed BAA. Claude for Healthcare launched at JPM26 (January 2026)
- **Data residency**: AWS Bedrock and Vertex AI deployments provide zero-data-egress options. BYOK (Bring Your Own Key) encryption coming H1 2026
- **Data training opt-out**: API and Enterprise customers' data is not used for training

### Strengths for PMS Project

- Best-in-class code reasoning and multi-file refactoring (SWE-bench Verified: 80%+)
- Deep agentic capabilities (Agent Teams, sub-agents, hooks, skills) match the project's multi-experiment workflow
- CLAUDE.md system perfectly aligns with the docs-as-source-of-truth approach
- HIPAA-ready Enterprise plan with BAA available
- MCP ecosystem enables integration with PMS-specific tools (FHIR, HL7 servers)

### Weaknesses for PMS Project

- **Vendor lock-in risk**: January 2026 OAuth crackdown blocked all third-party tools from using subscription tokens without warning
- **No self-hosted inference**: All code goes to Anthropic's servers -- requires explicit data classification and vendor risk assessment
- **Cost at scale**: Heavy autonomous usage (Agent Teams, long sessions) can be expensive on API billing
- **Single vendor dependency**: If Anthropic has an outage, no local fallback exists natively
- **Walled garden trend**: Increasing restrictions on how subscriptions can be used outside official tools

---

## 2. OpenAI Codex / ChatGPT Coding Agents

### Overview

OpenAI's coding tool ecosystem has two components: (1) **Codex** -- a cloud-based asynchronous coding agent accessible via ChatGPT, and (2) **Codex CLI** -- an open-source terminal-based coding agent built in Rust. Codex is powered by codex-1, a model based on o3 optimized for software engineering.

### Models

| Model | Use Case | Notes |
|-------|----------|-------|
| **GPT-5.1-Codex (Max)** | Default for Codex app | Flagship for complex tasks |
| **GPT-5.1-Codex (Mini)** | Lighter tasks in Codex CLI | Optimized for low-latency Q&A and editing |
| **codex-mini-latest** | API access | $1.50/$6.00 per 1M tokens |
| **GPT-5** | API access | $1.25/$10.00 per 1M tokens |
| **o3** | Foundation model | Used internally by codex-1 |
| **o4-mini** | CLI optimization | Smaller version for local CLI use |

### Key Features

- **Codex App** (cloud): Asynchronous coding agent that works in a sandboxed environment, reads repos, implements features, runs tests, creates PRs
- **Codex CLI** (terminal): Open-source (Rust), inspects repos, edits files, runs commands
- **MCP support**: Yes -- configure MCP servers in `~/.codex/config.toml`; Codex CLI can also run as an MCP server
- **Multi-agent support**: Multiple agents work on the same repo using isolated worktrees
- **Skills**: Folders of instructions/scripts that teach Codex specific capabilities (shared standard with Claude Code and GitHub Copilot)
- **Multi-file editing**: Yes, through agentic workflow
- **Terminal access**: Yes, with configurable approval modes

### Pricing

| Plan | Price | Access |
|------|-------|--------|
| **ChatGPT Plus** | $20/month | Codex Web + Codex CLI with usage limits |
| **ChatGPT Pro** | $200/month | Higher usage limits |
| **API (codex-mini-latest)** | $1.50/$6.00 per 1M tokens | Direct API access |
| **API (GPT-5)** | $1.25/$10.00 per 1M tokens | Direct API access |

### Open-Source / Self-Hosted

- **Codex CLI is open-source** (GitHub: openai/codex)
- Models are not self-hostable -- inference runs on OpenAI's servers
- CLI can be configured to use alternative OpenAI-compatible endpoints

### Healthcare / Enterprise Compliance

- **SOC 2 Type II**: Yes (OpenAI)
- **HIPAA**: Enterprise agreements available with BAA for ChatGPT Enterprise / API
- **Data training opt-out**: API data not used for training by default; Enterprise plans provide additional guarantees
- **Data residency**: Limited -- primarily US-based infrastructure

### Strengths for PMS Project

- Open-source CLI allows inspection and customization
- Competitive API pricing (codex-mini at $1.50/$6 is cheaper than Claude for many tasks)
- Multi-agent support with worktree isolation
- Skills interoperability with Claude Code

### Weaknesses for PMS Project

- Newer ecosystem -- less mature than Claude Code for agentic coding workflows
- Codex App runs in a sandboxed cloud environment (less control than local CLI)
- Less healthcare-specific tooling compared to Anthropic's Claude for Healthcare
- Model naming/versioning has been historically confusing

---

## 3. Qwen 3.5 (Alibaba)

### Overview

Alibaba released Qwen 3.5 on February 16, 2026. The flagship model -- Qwen3.5-397B-A17B -- uses a sparse Mixture-of-Experts (MoE) architecture with 397 billion total parameters but only 17 billion active per forward pass. Released under Apache 2.0 license, supporting 201 languages, with a 1M token context window.

### Models

| Model | Parameters (Total/Active) | Context | License |
|-------|--------------------------|---------|---------|
| **Qwen3.5-397B-A17B** | 397B / 17B active | 1M tokens | Apache 2.0 |
| **Qwen3.5-Medium** series | Various smaller sizes | Various | Apache 2.0 |
| **Qwen3.5-Plus** (hosted) | Proprietary hosted version | 1M tokens | API access |

### Key Features

- **Self-hostable**: Open-weight model runs on your own infrastructure with zero per-token costs
- **Efficient inference**: Only 17B active parameters means it can run on a single H100 GPU (unlike dense 400B models)
- **Coding performance**: SWE-bench Verified 76.8%, LiveCodeBench v6 85.0, AIME 2026 93.3%
- **8.6x to 19.0x increase** in decoding throughput compared to previous Qwen generations
- **Agent compatibility**: Works with OpenClaw, Claude Code (as backend model via proxy), Cline, and Alibaba's Qwen Code
- **Visual agents**: Multimodal capabilities for image/document understanding
- **Tool calling**: Built-in support for web search and code interpreter

### Pricing

| Option | Cost |
|--------|------|
| **Self-hosted** | $0 per-token (infrastructure costs only) |
| **Qwen3.5-Plus API** (Alibaba Cloud) | ~$0.11 per 1M input tokens (up to 128K context) |
| **Tool calling: Web Search** | $10 per 1,000 calls |
| **Tool calling: Code Interpreter** | Free (limited time) |

### Open-Source / Self-Hosted

- **Fully open-weight** under Apache 2.0
- Available on GitHub, Hugging Face, and ModelScope
- Self-hosted via vLLM, Ollama, or any compatible inference framework
- Zero data egress when self-hosted -- ideal for HIPAA environments

### Healthcare / Enterprise Compliance

- **Self-hosted compliance**: When run on-premise, inherits the compliance posture of your own infrastructure
- **No BAA from Alibaba**: The hosted API (Qwen3.5-Plus) does not have healthcare-specific compliance certifications for US markets
- **Data sovereignty**: Self-hosted deployment means PHI never leaves your network
- **Regulatory note**: Chinese origin may raise concerns in some US healthcare procurement processes (worth documenting in vendor risk assessment)

### Strengths for PMS Project

- **Zero PHI egress** when self-hosted -- strongest HIPAA data protection posture possible
- Apache 2.0 license means no vendor lock-in whatsoever
- SWE-bench score of 76.8% is competitive with frontier closed models
- Extremely cost-effective for high-volume tasks (medication parsing, clinical extraction)
- Already integrated in Experiment 20 (Qwen 3.5 PMS Integration)

### Weaknesses for PMS Project

- Self-hosting requires GPU infrastructure (H100 or equivalent) -- significant capital expenditure
- Not as strong as Opus 4.6 on the most complex reasoning tasks (76.8% vs 80%+ SWE-bench)
- No commercial support or BAA for the open-weight model
- Community support only -- no enterprise SLA
- Chinese origin model may face procurement scrutiny in some healthcare contexts

---

## 4. GitHub Copilot

### Overview

GitHub Copilot has evolved from inline code completion to a full agentic coding platform. The **Copilot Coding Agent** (GA since September 2025) takes GitHub issues and autonomously implements features, creates branches, runs tests, and submits PRs. **Agent Mode** in VS Code handles multi-file edits with MCP support.

### Models

GitHub Copilot is now multi-model, with model selection varying by tier:
- GPT-5 (default for premium requests)
- Claude models (available in some tiers)
- Gemini models (available in some tiers)
- Multiple models accessible depending on subscription level

### Key Features

- **Copilot Coding Agent**: Autonomous issue-to-PR workflow, runs asynchronously in GitHub's cloud
- **Agent Mode** (VS Code): Multi-file editing with tool use and MCP support
- **Code Review**: AI-powered pull request review
- **Inline completions**: Real-time code suggestions (unlimited on Pro)
- **Copilot Chat**: Context-aware Q&A in IDE and github.com
- **Copilot CLI**: Terminal command generation and explanation
- **MCP support**: Yes, in Agent Mode
- **Multi-model access**: GPT-5, Claude, Gemini depending on tier
- **Spark**: Rapid prototyping tool

### Pricing

| Plan | Price | Key Limits |
|------|-------|------------|
| **Free** | $0 | Limited completions, limited chat |
| **Pro** | $10/month | Unlimited completions, 300 premium requests/month |
| **Pro+** | Higher tier | All Pro features + larger premium request allowance + all models |
| **Business** | Per-user/month | Coding agent, centralized management, IP indemnity |
| **Enterprise** | Per-user/month | Advanced features, admin controls, compliance features |

**Premium requests**: Chat, agent mode, code review, coding agent, and CLI all consume premium requests. Overage: $0.04/request after monthly allocation.

### Open-Source / Self-Hosted

- **Not open-source**, not self-hostable
- Runs on GitHub's infrastructure (Microsoft Azure)
- GitHub Enterprise Cloud offers data residency options

### Healthcare / Enterprise Compliance

- **SOC 2 Type I**: Yes (Copilot Business/Enterprise)
- **ISO 27001**: Yes (GitHub Trust Center)
- **HIPAA**: No explicit HIPAA BAA for Copilot specifically. PHI must never enter AI prompt context unless legal team has confirmed coverage
- **Data residency**: GitHub Enterprise Cloud with data residency now in public preview (as of January 2026)
- **Data training opt-out**: Business and Enterprise plans -- code suggestions not retained and not used for training

### Strengths for PMS Project

- Deep GitHub integration -- the PMS project lives on GitHub, so issue-to-PR automation is native
- Multi-model access provides some hedge against single-vendor risk
- Free tier available for evaluation
- Copilot Coding Agent can automate routine tasks (dependency updates, test generation)
- Widely adopted -- easy to onboard new team members

### Weaknesses for PMS Project

- Premium request system adds unpredictable cost at scale
- No HIPAA BAA specifically covering Copilot -- risky for healthcare project
- Less powerful agentic capabilities compared to Claude Code or Codex for complex multi-step tasks
- Cannot self-host models -- all code goes to Microsoft/OpenAI servers
- Agent Mode quality varies significantly by model selection

---

## 5. Cursor

### Overview

Cursor is an AI-first IDE (built on VS Code) with deep codebase context, multi-file editing via Composer, and background agents that run tasks autonomously. As of early 2026, Cursor has a $29.3B valuation and over $1B ARR, making it one of the most commercially successful AI coding tools.

### Models Supported

Cursor provides access to multiple frontier models:
- GPT-5 (OpenAI)
- Claude Opus 4.6 / Sonnet 4.6 (Anthropic)
- Gemini (Google)
- Auto mode: Model selection is automatic and does not consume user credits

### Key Features

- **Composer**: Multi-file editing with natural language instructions
- **Agent Mode**: Autonomous task execution across files
- **Background Agents**: Cloud-hosted agents that work on tasks in the background
- **Tab completion**: AI-powered autocomplete (unlimited on Pro+)
- **Auto mode**: Automatic model selection at no credit cost
- **Codebase indexing**: Embeddings-based deep codebase understanding
- **MCP support**: Yes
- **Chat**: Context-aware Q&A with @-references to files, docs, web
- **Terminal integration**: AI assistance in the integrated terminal

### Pricing

| Plan | Price | Details |
|------|-------|---------|
| **Hobby (Free)** | $0 | Limited agent requests and tab completions |
| **Pro** | $20/month | Extended agent requests, unlimited tab completions, background agents, max context windows |
| **Pro+** | $60/month | 3x usage of all models |
| **Ultra** | $200/month | 20x usage credits, priority access to new features |
| **Teams** | $40/user/month | Pro-equivalent AI + organizational features |

### Open-Source / Self-Hosted

- **Not open-source**, not self-hostable
- Proprietary IDE based on VS Code
- No on-premise deployment option

### Healthcare / Enterprise Compliance

- **SOC 2 Type II**: Yes
- **GDPR / CCPA**: Compliant
- **HIPAA**: **No** -- no HIPAA BAA available, no self-hosted option
- **Encryption**: AES-256 at rest, TLS 1.2+ in transit
- **SSO**: SAML-based SSO available
- **Data residency**: No self-hosted server deployment option -- significant limitation for regulated environments
- **Recommendation**: Healthcare organizations should avoid Cursor for PHI-adjacent work until HIPAA/VPC support is available

### Strengths for PMS Project

- Best-in-class IDE experience for day-to-day coding
- Multi-model access reduces single-vendor dependency
- Auto mode is cost-efficient for routine tasks
- Strong community and ecosystem (large extension library)
- Background agents good for long-running tasks

### Weaknesses for PMS Project

- **No HIPAA compliance** -- cannot be used for PHI-related code review or generation
- Not self-hostable -- all code processed on Cursor's servers
- High cost at Ultra tier ($200/month per developer)
- Cursor's data path runs through multiple model vendors without unbroken BAA chain
- Less powerful for pure terminal/CLI workflows compared to Claude Code

---

## 6. Windsurf (Codeium)

### Overview

Windsurf (formerly Codeium) is an AI-powered IDE featuring **Cascade** -- an agentic AI that understands your codebase, suggests multi-file edits, runs terminal commands, and remembers context across sessions. Key differentiator: **three deployment modes** (Cloud, Hybrid, Self-Hosted) with enterprise-grade compliance.

### Key Features

- **Cascade**: Multi-step agentic coding with memory (remembers codebase details and workflow patterns)
- **Tab/Supercomplete**: Fast inline code completions
- **Multi-file editing**: Cascade handles cross-file refactoring
- **Terminal command execution**: Yes
- **Image-to-code**: Drop an image into Cascade to generate UI code
- **Lint auto-fix**: Automatically detects and fixes lint errors it generates
- **MCP support**: Yes (Cascade can connect to MCP servers)
- **IDE + Plugin**: Available as standalone editor and VS Code/JetBrains plugin

### Pricing

| Plan | Price | Details |
|------|-------|---------|
| **Free** | $0 | 25 credits/month, basic AI features |
| **Pro** | $15/month | 500 credits, full Cascade access, priority |
| **Teams** | $30/user/month | Collaboration, admin controls |
| **Enterprise** | $60/user/month | ZDR defaults, full compliance suite |

### Open-Source / Self-Hosted

- **Not open-source** (proprietary)
- **Self-hosted deployment available** -- can run the entire inference chain on-premise
- Three deployment modes: Cloud, Hybrid, Self-Hosted
- Self-hosted mode means zero data leaves your network

### Healthcare / Enterprise Compliance

- **SOC 2 Type II**: Yes
- **FedRAMP High**: Yes -- one of few AI coding tools with this certification
- **HIPAA**: Yes -- will sign a BAA for significant implementations
- **Zero Data Retention (ZDR)**: Default for all paid seats
- **RBAC + SAML SSO**: Yes, with full audit logs
- **Self-hosted**: Complete data residency control

### Strengths for PMS Project

- **Best compliance posture** among AI IDEs: SOC 2 + FedRAMP High + HIPAA BAA + self-hosted option
- Zero data retention default eliminates a major risk category
- Self-hosted mode provides strongest data sovereignty
- Cascade memory feature reduces repetitive context-setting
- Competitive pricing ($15/month Pro is cheapest paid AI IDE)

### Weaknesses for PMS Project

- Smaller community than Cursor or Copilot -- fewer tutorials, extensions
- Cascade agent capabilities are less mature than Claude Code for complex autonomous workflows
- Credit-based system can be limiting for heavy agentic use
- Self-hosted deployment requires infrastructure investment
- IDE-only -- no standalone CLI tool comparable to Claude Code

---

## 7. Google Gemini Code Assist / Jules

### Overview

Google offers two coding tools: **Gemini Code Assist** -- an IDE-based coding assistant powered by Gemini 2.5 with agent mode and 1M token context, and **Jules** -- an asynchronous coding agent built on Gemini 3 Pro that handles multi-task workflows independently.

### Models

| Model | Used By |
|-------|---------|
| **Gemini 2.5** | Gemini Code Assist |
| **Gemini 3 Pro** | Jules |

### Key Features

**Gemini Code Assist:**
- Code completions, full function generation from comments
- Agent Mode (since July 2025): Autonomous multi-step coding in IDE
- 1M token context window for entire codebase understanding
- MCP support for connecting to external tools/data
- Unit test generation, debugging assistance, documentation
- Source citation for generated code

**Jules:**
- Asynchronous coding agent -- assign features, bugs, or test tasks
- Reads code, understands intent, executes multiple tasks concurrently
- Built on Gemini 3 Pro
- Integrates with Google AI Pro/Ultra subscription tiers

### Pricing

| Plan | Price | Jules Limits |
|------|-------|-------------|
| **Free (Individual)** | $0 | Basic access, limited daily requests |
| **AI Pro** | ~$19.99/month | 5x higher limits, daily coding use |
| **AI Ultra** | Higher tier | 20x limits, multi-agent workflows |
| **Enterprise (GCP)** | $19/user/month | Standard/Enterprise tiers via Google Cloud |
| **Gemini API** | Pay-per-token | Standard Google AI Developer pricing |

### Open-Source / Self-Hosted

- **Not open-source**, not self-hostable
- Available through Google Cloud for enterprise deployment
- Google Cloud provides regional data processing controls

### Healthcare / Enterprise Compliance

- **SOC 2**: Yes (Google Cloud)
- **ISO 27001**: Yes
- **HIPAA**: Google Cloud services can be covered under BAA -- Gemini Code Assist Enterprise through Google Cloud likely eligible
- **FedRAMP**: Google Cloud has FedRAMP authorization
- **Data residency**: Google Cloud regional controls available

### Strengths for PMS Project

- 1M token context window matches Claude Code for large codebase understanding
- Google Cloud compliance infrastructure is mature
- Jules for asynchronous task automation (similar to GitHub's Coding Agent)
- Competitive pricing for enterprise teams already on Google Cloud
- Agent Mode + MCP support increasingly capable

### Weaknesses for PMS Project

- Newer entrant in agentic coding -- less battle-tested than Claude Code
- Jules is still maturing as a product
- Less community content and tutorials for healthcare use cases
- Google's rapid product iteration means features may change or be deprecated
- Not as integrated with GitHub workflows as Copilot

---

## 8. Amazon Q Developer

### Overview

Amazon Q Developer (successor to CodeWhisperer) is AWS's AI coding assistant with agentic capabilities for feature implementation, documentation, testing, code review, refactoring, and software upgrades. Deeply integrated with AWS services and IDEs.

### Key Features

- **Agentic coding**: Autonomously implements features, writes tests, reviews code, refactors
- **Code suggestions**: Real-time inline suggestions in 25+ languages
- **Code transformation**: Automated language/framework upgrades (e.g., Java 8 to 17)
- **Vulnerability scanning**: Real-time security scanning with remediation suggestions
- **IDE support**: VS Code, JetBrains, Visual Studio, Eclipse (preview)
- **CLI integration**: Terminal-based assistance
- **Private repository context**: Connect to private repos for personalized recommendations
- **AWS integration**: Deep integration with AWS services for infrastructure-as-code, CloudFormation, etc.

### Pricing

| Plan | Price | Key Limits |
|------|-------|------------|
| **Free Tier** (perpetual) | $0 | 50 agentic chat interactions/month, 1,000 LOC transformation/month |
| **Pro Tier** | $19/user/month | Higher limits, 4,000 LOC transformation/month (pooled), IP indemnity |

### Open-Source / Self-Hosted

- **Not open-source**, not self-hostable
- Runs on AWS infrastructure
- Available through AWS Marketplace

### Healthcare / Enterprise Compliance

- **SOC 2**: Yes (AWS)
- **ISO 27001**: Yes (AWS)
- **HIPAA**: Yes -- AWS's compliance certifications extend to Q Developer. **Most compliance-ready cloud AI coding tool for regulated industries**
- **PCI DSS**: Yes
- **IP Indemnity**: Pro tier includes IP indemnity (Amazon defends against license infringement claims)
- **Data training opt-out**: Pro tier -- proprietary content not used for service improvement, automatic opt-out from data retention

### Strengths for PMS Project

- **Strongest HIPAA compliance posture** among cloud-based AI coding tools -- AWS compliance certifications extend directly
- IP indemnity eliminates a significant legal risk
- Free perpetual tier for evaluation and light use
- Code transformation feature valuable for dependency upgrades
- Vulnerability scanning with automated remediation aligns with security requirements (Experiment 12)

### Weaknesses for PMS Project

- Less capable at complex agentic coding compared to Claude Code or Codex
- Heavily AWS-centric -- less useful if not deploying on AWS
- Smaller community than Copilot or Cursor
- Limited model choice -- tied to AWS's model offerings
- Agent capabilities are newer and less proven for multi-step workflows
- 50 free agentic chats/month is restrictive

---

## 9. Other Notable Tools

### Aider

- **Type**: Open-source CLI tool (Apache 2.0)
- **GitHub Stars**: 25K+
- **Model Support**: Any LLM -- Claude, GPT-4o, o3, DeepSeek, local models via Ollama
- **Key Features**: Maps entire codebase, auto-commits with git, lints/tests automatically, architect mode (two-model pipeline), IDE integration, voice/image input
- **Pricing**: Free (BYOK -- pay only for API calls, typically $5-30/month)
- **Self-Hosted**: Yes -- runs locally, models via Ollama for zero-API-cost operation
- **Healthcare**: Fully self-hostable; compliance depends on model choice and infrastructure
- **Strengths**: No vendor lock-in, model-agnostic, excellent git integration, low cost
- **Weaknesses**: CLI-only (no GUI), smaller feature set than Claude Code's agent teams/skills, requires more manual configuration

### Continue

- **Type**: Open-source IDE extension (Apache 2.0)
- **GitHub Stars**: 20K+
- **Supported IDEs**: VS Code, JetBrains
- **Model Support**: Any LLM -- cloud (OpenAI, Anthropic, Google) or local (Ollama, LM Studio)
- **Key Features**: Chat, autocomplete, edit, agent mode; model-agnostic; source-controlled AI checks enforceable in CI
- **Pricing**: Free (BYOK)
- **Self-Hosted**: Yes -- runs locally with local models
- **Healthcare**: Self-hostable option provides data sovereignty
- **Strengths**: Model flexibility, IDE integration, CI enforcement, active community
- **Weaknesses**: Less autonomous than Claude Code, requires configuration effort, agent mode less mature

### Cline

- **Type**: Open-source VS Code extension (Apache 2.0)
- **GitHub Stars**: 58.2K (as of Feb 2026)
- **Model Support**: 10+ providers -- OpenRouter, Anthropic, OpenAI, Google, AWS Bedrock, Azure, GCP Vertex, local via Ollama/LM Studio
- **Key Features**: Autonomous multi-step agent, file editing, terminal commands, browser automation, MCP tool integration, Plan/Act dual modes
- **Pricing**: Free (BYOK)
- **Self-Hosted**: Yes -- runs locally
- **Healthcare**: Can use local models for zero data egress; MCP integration for FHIR/HL7 tools
- **Strengths**: Most popular open-source coding agent, massive model provider support, browser automation, MCP native
- **Weaknesses**: VS Code only, can be expensive with frontier models, requires careful approval management for autonomous actions

### Roo Code

- **Type**: Open-source VS Code extension (Apache 2.0) -- fork of Cline
- **Version**: 3.50.4 (Feb 21, 2026) -- one of the fastest-evolving extensions
- **Key Features**: Five distinct modes (Code, Architect, Test, etc.), custom modes to reduce hallucination, multi-file edits, model-agnostic
- **Pricing**: Free (BYOK)
- **Self-Hosted**: Yes
- **Healthcare**: Same as Cline -- self-hostable with local models
- **Strengths**: Role-driven execution reduces errors, faster iteration than Cline, custom modes for specialized tasks
- **Weaknesses**: Smaller community than Cline, fork divergence risk, VS Code only

### Devin (Cognition)

- **Type**: Fully autonomous cloud-based AI software engineer
- **Key Features**: Interactive planning, parallel Devins, cloud IDE, automatic repo indexing/wiki generation, Devin Search for codebase Q&A
- **Pricing**: Core $20/month, Team $500/month (250 ACUs, ~62.5 hours), Enterprise custom. ACU overage: $2/unit (~15 min of work)
- **Self-Hosted**: No -- cloud only
- **Healthcare**: No HIPAA compliance advertised
- **Strengths**: Most autonomous agent -- can complete entire features independently, good for junior-level tasks
- **Weaknesses**: Expensive at Team tier ($500/month), cloud-only with no data residency controls, unreliable for complex healthcare logic, not suitable for PHI-adjacent work

### Replit Agent

- **Type**: Cloud IDE with AI agent
- **Agent 3 Features**: Autonomous builds, self-testing, 50+ languages, can build other agents/automations
- **Pricing**: Starter (free with daily credits), Core ($20/month, $25 credits), Pro ($100/month for up to 15 builders), Teams ($35-40/user/month)
- **Self-Hosted**: No -- cloud IDE only
- **Healthcare**: Not suitable for HIPAA workloads
- **Strengths**: Full cloud dev environment, rapid prototyping, non-coder friendly
- **Weaknesses**: Cloud-only, not designed for enterprise/healthcare, credit-based pricing unpredictable

---

## 10. Healthcare / Enterprise Compliance Matrix

| Tool | SOC 2 | HIPAA BAA | Self-Hosted | FedRAMP | Data Training Opt-Out | IP Indemnity |
|------|-------|-----------|-------------|---------|----------------------|--------------|
| **Claude Code** (Enterprise) | Type II | Yes | No (Bedrock/Vertex) | No | Yes | No |
| **OpenAI Codex** (Enterprise) | Type II | Yes | No | No | Yes (API) | No |
| **Qwen 3.5** (self-hosted) | N/A (your infra) | N/A (your infra) | **Yes** | N/A | N/A | N/A |
| **GitHub Copilot** (Enterprise) | Type I | **Unclear** | No | No | Yes (Business+) | Yes |
| **Cursor** | Type II | **No** | **No** | No | Unclear | No |
| **Windsurf** (Enterprise) | Type II | **Yes** | **Yes** | **High** | Yes (ZDR default) | No |
| **Gemini Code Assist** (GCP) | Yes (GCP) | Yes (GCP) | No | Yes (GCP) | Yes | No |
| **Amazon Q Developer** (Pro) | Yes (AWS) | **Yes** | No | Yes (AWS) | **Yes** | **Yes** |
| **Aider** (self-hosted) | N/A (your infra) | N/A (your infra) | **Yes** | N/A | N/A | N/A |
| **Cline/Roo Code** (local) | N/A (your infra) | N/A (your infra) | **Yes** | N/A | N/A | N/A |
| **Devin** | Unclear | **No** | No | No | Unclear | No |
| **Replit** | Unclear | **No** | No | No | Unclear | No |

**Best for healthcare PMS project (ranked)**:
1. **Amazon Q Developer** -- HIPAA + IP indemnity + data opt-out + SOC 2
2. **Windsurf Enterprise** -- HIPAA BAA + self-hosted + FedRAMP High + ZDR
3. **Claude Code Enterprise** -- HIPAA BAA + SOC 2 Type II + healthcare-specific launch
4. **Self-hosted stack** (Qwen 3.5 + Aider/Cline) -- zero data egress, full control
5. **Gemini Code Assist Enterprise** (via GCP) -- inherits GCP compliance

---

## 11. Vendor Lock-in Risk Analysis

### The January 2026 Incident

On **January 9, 2026 at 02:20 UTC**, Anthropic deployed technical safeguards that blocked all third-party tools from using Claude Pro/Max subscription OAuth tokens. Tools like OpenCode (56K GitHub stars) stopped working instantly. There was **no warning, no migration path, and no grace period**.

**What happened:**
- Third-party tools (OpenCode, Cursor users via xAI, custom integrations) had been using Claude subscription tokens by spoofing the Claude Code client identity
- Anthropic blocked these requests server-side
- Developer backlash was significant -- DHH called it "very customer hostile"
- Developers canceled subscriptions en masse
- OpenCode shipped ChatGPT Plus support within hours
- By February 19, 2026, Anthropic formally removed all Claude OAuth code from third-party access

**Economic motivation:** The Max $200/month subscription provided unlimited tokens for Claude Code, while equivalent API usage would cost $1,000+. The "Ralph Wiggum" technique (autonomous loops running for hours) had gone viral in late December.

### Lock-in Risk Categories

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **Pricing change** (subscription or API) | High | Medium | Multi-vendor strategy; budget alerts; Qwen 3.5 self-hosted fallback |
| **Feature removal or restriction** | High | **Demonstrated** | Portable CLAUDE.md files; MCP-based integrations are protocol-standard |
| **Service outage** | Medium | Low-Medium | See Emergency Transition Playbook below |
| **Product discontinuation** | Medium | Low | Claude Code is Anthropic's flagship dev tool; unlikely but possible |
| **Terms of service change** | High | **Demonstrated** | January 2026 incident proves this is real; maintain alternative tooling |
| **Data access/export limitation** | Low | Low | All code stays local; only prompts/responses transit Anthropic servers |
| **Model quality regression** | Medium | Low | Pin model versions via API; benchmark new versions before adopting |

### What Is Portable vs. Locked-In

**Portable (safe to invest in):**
- CLAUDE.md instruction files (plain markdown, usable by any tool)
- MCP server configurations (open protocol standard, works with Cursor, Windsurf, Codex)
- Skills folders (open standard shared with Codex and Copilot)
- Git hooks and CI/CD integrations (tool-agnostic)
- Project documentation in docs/ (markdown, not tool-specific)

**Locked-in (Anthropic-specific):**
- Agent Teams orchestration (proprietary feature, no equivalent elsewhere)
- Claude Code-specific hooks (pre-tool-use, post-tool-use hooks)
- Subscription-based pricing (not transferable)
- Claude-specific prompt engineering patterns (thinking tokens, adaptive thinking)

---

## 12. Emergency Transition Playbook

### Scenario 1: Anthropic Service Outage (Hours to Days)

**Immediate actions (< 1 hour):**
1. Switch to **Cursor** or **Windsurf** with a different model backend (GPT-5, Gemini)
2. If CLI-preferred: Use **Aider** with OpenAI API (`aider --model gpt-4o`)
3. If using MCP servers: They work with any MCP-compatible client (Cursor, Windsurf, Cline)
4. CLAUDE.md files continue to provide context to any tool that reads markdown

**Short-term (1-3 days):**
1. Switch API calls to OpenAI Codex CLI or GPT-5 API
2. Use Cline (VS Code) with Claude-alternative model backend
3. Agent Teams workflows must be paused -- no equivalent multi-agent orchestration in other tools

### Scenario 2: Anthropic Blocks Feature or Changes Pricing (Days to Weeks)

**Assessment (Day 1):**
1. Evaluate impact on current workflows
2. Check if API access is still viable (even if subscription changes)
3. Assess alternative tools against current usage patterns

**Migration (Week 1-2):**
1. **For CLI workflows**: Migrate to **Codex CLI** (open-source, similar UX) or **Aider**
2. **For IDE workflows**: Migrate to **Cursor** (multi-model) or **Windsurf** (self-hosted option)
3. **For agent workflows**: Evaluate **Cline** + custom automation or **Devin** for autonomous tasks
4. **For HIPAA workflows**: Migrate to **Amazon Q Developer** or **Windsurf Enterprise**

### Scenario 3: Full Vendor Abandonment (Weeks to Months)

**Phase 1 -- Immediate (Week 1):**
1. Deploy **Qwen 3.5** on local GPU infrastructure via vLLM
2. Configure **Aider** or **Cline** to use local Qwen endpoint
3. Maintain all CLAUDE.md files as documentation (they are tool-agnostic)

**Phase 2 -- Stabilization (Week 2-4):**
1. Set up **LiteLLM** proxy for unified model access (route to multiple providers with automatic fallback)
2. Configure fallback chain: Primary (OpenAI) -> Secondary (Google) -> Tertiary (Qwen self-hosted)
3. Migrate Agent Teams workflows to **LangGraph** (already integrated in Experiment 26)
4. Evaluate **Codex CLI** as primary terminal tool replacement

**Phase 3 -- Optimization (Month 2-3):**
1. Fine-tune Qwen 3.5 on PMS-specific patterns for improved performance
2. Build custom MCP servers that work with any client
3. Establish multi-vendor procurement to prevent future single-vendor dependency

---

## 13. Open-Source Fallback Stack

The following stack provides a fully open-source, self-hosted alternative to Claude Code:

### Recommended Open-Source Stack

```
Layer 1 -- Model Inference:
  - Qwen 3.5-397B-A17B (Apache 2.0) via vLLM or Ollama
  - Alternative: DeepSeek R1/V3, Llama 3.3, Devstral 2

Layer 2 -- Model Proxy/Router:
  - LiteLLM (MIT license) -- unified API, fallback routing, budget controls
  - Routes: Claude -> OpenAI -> Google -> Local Qwen

Layer 3 -- Coding Agent (choose one or more):
  - Aider (Apache 2.0) -- terminal-first, git-native, model-agnostic
  - Cline (Apache 2.0) -- VS Code, autonomous agent, MCP support
  - Roo Code (Apache 2.0) -- VS Code, role-driven modes, fast iteration
  - Continue (Apache 2.0) -- VS Code/JetBrains, chat/autocomplete/agent

Layer 4 -- Agent Orchestration:
  - LangGraph (MIT) -- stateful multi-agent flows with checkpointing
  - Already integrated in PMS Experiment 26

Layer 5 -- MCP Ecosystem:
  - MCP protocol is open standard
  - PMS MCP servers (Experiment 09) work with any MCP client
```

### Cost Comparison

| Stack | Monthly Cost (single developer) | Data Sovereignty |
|-------|-------------------------------|------------------|
| Claude Code Max 20x | $200/month | No (Anthropic servers) |
| Claude Code API (moderate use) | ~$50-150/month | No (Anthropic servers, or Bedrock/Vertex) |
| Cursor Pro + API keys | $20 + ~$30-80 API | No (Cursor + model vendor servers) |
| Aider + OpenAI API | $0 + ~$20-50 API | No (OpenAI servers) |
| Aider + Qwen 3.5 self-hosted | $0 + GPU infra | **Yes (100%)** |
| Cline + Qwen 3.5 self-hosted | $0 + GPU infra | **Yes (100%)** |

---

## 14. Recommendation for PMS Project

### Current Strategy Validation

The PMS project's current use of Claude Code as the primary development tool is **well-justified** based on:
- Best-in-class code reasoning for complex healthcare logic
- CLAUDE.md/docs-as-source-of-truth alignment
- MCP ecosystem matches the project's integration architecture
- Agent Teams support multi-experiment parallel development
- HIPAA-ready Enterprise plan available

### Risk Mitigation Actions

1. **Maintain portable abstractions**: Keep CLAUDE.md files, MCP servers, and skills as primary configuration -- these work across tools
2. **Establish Qwen 3.5 as on-premise backbone**: Already underway (Experiment 20) -- this provides zero-PHI-egress AI for clinical inference
3. **Keep LiteLLM proxy in the architecture**: Enables instant failover between model providers (Experiment 26 LangGraph already supports this)
4. **Evaluate Windsurf Enterprise**: For developers working directly with PHI-adjacent code, Windsurf's self-hosted + HIPAA BAA + FedRAMP High is the strongest compliance option
5. **Maintain Amazon Q Developer awareness**: If the project moves to AWS, Q Developer's HIPAA compliance + IP indemnity is unmatched
6. **Test Codex CLI quarterly**: As an open-source tool with growing capabilities, it's the most likely long-term Claude Code alternative for CLI workflows
7. **Document all Anthropic-specific patterns**: Any workflow that only works with Claude Code should be documented with its migration path

### Tool Allocation Strategy

| Use Case | Primary Tool | Fallback |
|----------|-------------|----------|
| Day-to-day coding (terminal) | Claude Code | Codex CLI or Aider |
| Day-to-day coding (IDE) | Cursor | Windsurf or Cline |
| Complex multi-file refactoring | Claude Code (Opus 4.6) | Codex CLI (GPT-5) |
| HIPAA-sensitive code generation | Claude Code Enterprise or Windsurf Enterprise | Self-hosted Qwen 3.5 + Aider |
| CI/CD automation | Claude Code (headless) | GitHub Actions + Codex CLI |
| Clinical AI inference (runtime) | Qwen 3.5 (self-hosted) | Gemma 3 (self-hosted) |
| Code review | GitHub Copilot or Claude Code | Amazon Q Developer |
| Security scanning | Claude Code (Experiment 12) | Amazon Q Developer vulnerability scanning |

---

## 15. Sources

- [Claude Code Product Page](https://claude.com/product/claude-code)
- [Claude Code Pricing Guide](https://www.thecaio.ai/blog/claude-code-pricing-guide)
- [Anthropic Pricing (API)](https://platform.claude.com/docs/en/about-claude/pricing)
- [Claude Opus 4.6 Capabilities](https://www.anthropic.com/claude/opus)
- [What's New in Claude 4.6](https://platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-6)
- [Anthropic Privacy & Certifications](https://privacy.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained)
- [Claude for Healthcare Launch](https://www.anthropic.com/news/healthcare-life-sciences)
- [Claude Code SOC 2 Compliance Guide](https://amitkoth.com/claude-code-soc2-compliance-auditor-guide/)
- [Anthropic's Walled Garden Crackdown](https://paddo.dev/blog/anthropic-walled-garden-crackdown/)
- [Anthropic Blocks Third-Party Tools (VentureBeat)](https://venturebeat.com/technology/anthropic-cracks-down-on-unauthorized-claude-usage-by-third-party-harnesses)
- [Anthropic Clarifies Ban (The Register)](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/)
- [OpenAI Codex Introduction](https://openai.com/index/introducing-codex/)
- [OpenAI Codex CLI Docs](https://developers.openai.com/codex/cli/)
- [OpenAI Codex MCP Support](https://developers.openai.com/codex/mcp/)
- [OpenAI Codex CLI Features](https://developers.openai.com/codex/cli/features/)
- [OpenAI Codex Pricing](https://developers.openai.com/codex/pricing/)
- [OpenAI API Pricing](https://developers.openai.com/api/docs/pricing)
- [Codex CLI GitHub Repo](https://github.com/openai/codex)
- [Qwen 3.5 Release (MarkTechPost)](https://www.marktechpost.com/2026/02/16/alibaba-qwen-team-releases-qwen3-5-397b-moe-model-with-17b-active-parameters-and-1m-token-context-for-ai-agents/)
- [Qwen 3.5 Developer Guide](https://www.nxcode.io/resources/news/qwen-3-5-developer-guide-api-visual-agents-2026)
- [Qwen 3.5 397B Open Weight (Sci-Tech Today)](https://www.sci-tech-today.com/news/alibaba-qwen3-5-397b-open-weight-ai/)
- [Qwen 3.5 Agentic Benchmarks](https://www.buildmvpfast.com/blog/alibaba-qwen-3-5-agentic-ai-benchmark-2026)
- [Qwen 3.5-Plus Pricing Analysis](https://hellochinatech.com/p/qwen-3-5-price-shock-alibaba-cloud)
- [Qwen Official Site](https://qwen.ai/)
- [GitHub Copilot Plans & Pricing](https://github.com/features/copilot/plans)
- [GitHub Copilot Plans (Docs)](https://docs.github.com/en/copilot/get-started/plans)
- [Copilot Coding Agent GA](https://github.com/orgs/community/discussions/159068)
- [GitHub Copilot Data Residency](https://github.blog/changelog/2026-01-29-copilot-metrics-in-github-enterprise-cloud-with-data-residency-in-public-preview/)
- [GitHub Trust Center](https://github.com/trust-center)
- [Cursor Pricing](https://cursor.com/pricing)
- [Cursor Enterprise](https://cursor.com/enterprise)
- [Cursor Security](https://cursor.com/security)
- [Cursor Models](https://cursor.com/docs/models)
- [Cursor HIPAA Analysis](https://www.specode.ai/blog/build-health-app-with-cursor)
- [Windsurf Official Site](https://windsurf.com/)
- [Windsurf Enterprise](https://windsurf.com/enterprise)
- [Windsurf Security](https://windsurf.com/security)
- [Windsurf SOC 2 Type II](https://windsurf.com/blog/codeium-is-soc2-type2-compliant)
- [Windsurf Enterprise Healthcare Readiness](https://harini.blog/2025/07/02/windsurf-detailed-enterprise-security-readiness-report/)
- [Gemini Code Assist Overview](https://developers.google.com/gemini-code-assist/docs/overview)
- [Gemini Code Assist Product Page](https://codeassist.google/)
- [Jules Coding Agent](https://jules.google.com/)
- [Google AI Plans](https://one.google.com/about/google-ai-plans/)
- [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Amazon Q Developer](https://aws.amazon.com/q/developer/)
- [Amazon Q Developer Pricing](https://aws.amazon.com/q/developer/pricing/)
- [Amazon Q Developer Features](https://aws.amazon.com/q/developer/features/)
- [Aider Official Site](https://aider.chat/)
- [Aider GitHub Repo](https://github.com/Aider-AI/aider)
- [Continue Official Site](https://www.continue.dev/)
- [Continue GitHub Repo](https://github.com/continuedev/continue)
- [Cline Official Site](https://cline.bot)
- [Roo Code Official Site](https://roocode.com)
- [Roo Code vs Cline Comparison](https://www.qodo.ai/blog/roo-code-vs-cline/)
- [Devin AI](https://devin.ai/pricing)
- [Devin 2.0 Launch (VentureBeat)](https://venturebeat.com/programming-development/devin-2-0-is-here-cognition-slashes-price-of-ai-software-engineer-to-20-per-month-from-500)
- [Replit Pricing](https://replit.com/pricing)
- [Replit Agent Docs](https://docs.replit.com/replitai/agent)
- [Claude Code Agent Teams Docs](https://code.claude.com/docs/en/agent-teams)
- [Best Open Source AI Coding Agents 2026](https://cssauthor.com/best-open-source-ai-coding-agents/)
- [Open Source Claude Code Alternatives](https://openalternative.co/alternatives/claude-code)
- [Healthcare AI Coding Compliance](https://www.codeparticle.com/blog/why-healthcare-companies-shouldn-t-use-saas-ai-tools-for-coding)
- [AI Coding Tools in Practice (AlterSquare)](https://altersquare.io/ai-coding-tools-2026-used-across-20-client-projects/)

---

**Note:** This landscape is rapidly evolving. Pricing, features, and compliance certifications should be re-verified before making procurement decisions. Last verified: March 2, 2026.
