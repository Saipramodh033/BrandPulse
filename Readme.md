# BrandPulse

> **Autonomous content strategy engine powered by a ReAct AI agent.**

BrandPulse continuously monitors market signals, generates platform-ready social media content ideas, and learns from human feedback — fully automated, end-to-end. Built for B2B marketing teams who want AI-generated content that is specific, grounded in real events, and actually sounds human.

**🚀 Business Impact: 95% Faster than Manual AI Prompting**  
Even with tools like ChatGPT, marketers spend 20–30 minutes manually searching for industry news, feeding context into the prompt, and requesting rewrites. BrandPulse replaces this entire manual research workflow with an autonomous agent, cutting a 30-minute task down to a 45-second background job.

---

## Table of Contents

- [Key Engineering Highlights](#key-engineering-highlights)
- [Screenshots](#screenshots)
- [Agent Architecture](#agent-architecture)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [What It Does](#what-it-does)
- [Setup & Installation](#setup--installation)
- [Environment Variables](#environment-variables)
- [Usage Guide](#usage-guide)
- [Live Run Tracing](#live-run-tracing)
- [Project Structure](#project-structure)
- [Database Models](#database-models)
- [API Reference](#api-reference)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [API Limits (Free Tiers)](#api-limits-free-tiers)

---

## Key Engineering Highlights

- **Custom ReAct Agent Pattern**: Built a fully autonomous AI agent from scratch that reasons, uses 5 distinct tools, evaluates its own signal quality, and implements retry/fallback logic.
- **Event-Driven Microservices**: Decoupled the API (FastAPI) from the heavy LLM background processing (Celery/Redis), ensuring non-blocking frontend performance.
- **Real-Time Distributed Tracing**: Implemented a Redis Pub/Sub to WebSocket pipeline to stream live agent thought processes (trace events) directly to the Next.js frontend in real-time.
- **Production-Ready Data Layer**: Utilised PostgreSQL with pgvector for semantic memory, SQLAlchemy ORM for robust data modeling, and strict Pydantic schemas for LLM outputs to prevent hallucination errors.

---

## Screenshots

<table>
  <tr>
    <td width="50%" valign="top">
      <b>1. Idea Inbox</b><br/>
      Review ideas in real time.<br/><br/>
      <img src="docs/screenshots/01_inbox_review.png" width="100%">
    </td>
    <td width="50%" valign="top">
      <b>2. Content Library</b><br/>
      All approved ideas centrally.<br/><br/>
      <img src="docs/screenshots/03_content_library.png" width="100%">
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <b>3. Live Agent Trace</b><br/>
      Watch tool calls stream live.<br/><br/>
      <img src="docs/screenshots/04_worker_logs.png" width="100%">
    </td>
    <td width="50%" valign="top">
      <b>4. HITL Refinement</b><br/>
      Rewrite with specific feedback.<br/><br/>
      <img src="docs/screenshots/02_inbox_refine.png" width="100%">
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <b>5. Settings</b><br/>
      Configure automated schedule.<br/><br/>
      <img src="docs/screenshots/05_settings.png" width="100%">
    </td>
    <td width="50%"></td>
  </tr>
</table>

---

## Agent Architecture

The core of BrandPulse is a **ReAct (Reason + Act) agent** — a pattern where the LLM autonomously decides which tools to call, in what order, and when the output is good enough to submit.

This is not a hardcoded pipeline. The LLM reasons about signal quality, angle freshness, and idea quality at each step and makes its own decisions.

### Agent Tools

| Tool | What the LLM does with it |
|---|---|
| `recall_company_memory` | Reads past angles, rejected angles, recent hooks from DB. Always called first. |
| `profile_company` | Extracts structured profile: industry space, target audience, brand voice. |
| `search_web` | Searches for recent market news. Can be called multiple times with different queries. |
| `extract_signal` | Evaluates search results: is this signal specific + recent + verifiable? |
| `generate_ideas` | Generates 4 ideas grounded in the market signal and chosen angle. |
| `validate_and_critique_ideas` | Quality-checks ideas against 4 editorial criteria before surfacing them. |
| `finish` | Submits the final validated ideas and ends the agent loop. |

### Decision Loop

```mermaid
%%{init: {"flowchart": {"nodeSpacing": 100, "rankSpacing": 80}}}%%
flowchart LR
    Trigger([Trigger]) --> T1
    T1["① recall_company_memory\nprofile_company"] --> T2
    T2["② search_web · extract_signal"] --> D1{Signal\nstrong?}
    D1 -->|yes| T3["③ generate_ideas"]
    D1 -->|no · retry| T2
    T3 --> T4

    subgraph tail[" "]
        direction TB
        T4["④ validate_and_critique_ideas"] --> D2{3+ ideas\npass?}
        D2 -->|yes| T5(["⑤ finish"])
    end

    D2 -->|no · regenerate| T3
    T1 <-->|read / write| DB[(PostgreSQL)]
    T2 -->|search| Web[/Tavily · DuckDuckGo/]
    T5 -->|save + surface| Inbox([Idea Inbox])
```



> Gemini Flash LLM reasons between every step — choosing which tool to call next based on the observation returned.


**What makes this genuinely agentic:**
- The LLM decides *when* to search again and *what different query to use*
- The LLM decides *whether* signal is strong enough to proceed
- The LLM decides *which angle* to pick based on memory
- The LLM decides *when* the output meets the quality bar

### Content Angle Taxonomy

The agent picks from 10 structured content angles, tracked per company to ensure freshness:

```
build-in-public        | user-perception      | hiring-and-culture
contrarian-take        | industry-trend       | competitive-positioning
data-driven-insight    | founder-story        | product-update
customer-success
```

Rejected angles are never reused. Overused angles are deprioritised.

### Evergreen Mode

If the agent cannot find a strong, specific market signal after 3 search attempts, it automatically switches to **evergreen mode**: generates timeless, foundational content not dependent on current events. This ensures every scheduled run produces output.

### HITL (Human-in-the-Loop) Refinement

Reviewers can request a rewrite of any individual idea with written feedback. This triggers a dedicated Celery task that calls the LLM directly and returns the refined idea back to `pending` status for re-review.

---

## System Architecture

```mermaid
graph LR
    Browser([Browser]) --> FE[Next.js 14\n:3000]
    FE -->|REST| API[FastAPI\n:8000]
    FE -->|WebSocket| API
    API -->|read / write| DB[(PostgreSQL\n:5432)]
    API -->|subscribe| Redis[(Redis\n:6379)]

    subgraph Worker["Celery Worker + Beat Scheduler"]
        Agent["ReAct Agent\nGemini Flash LLM"]
    end

    Agent -->|publish trace| Redis
    Agent -->|read / write| DB
    Agent -->|LLM calls| Gemini[Google Gemini]
    Agent -->|web search| Search[Tavily\nDuckDuckGo]
```

### Services

| Service | Technology | Role |
|---|---|---|
| `frontend` | Next.js 14, TypeScript, Framer Motion | Idea inbox, company dashboard, live run trace panel |
| `api` | FastAPI, Uvicorn | REST API + WebSocket pub/sub gateway |
| `worker` | Celery 5 + Celery Beat | ReAct agent runner, scheduled task dispatcher |
| `postgres` | PostgreSQL 15 + pgvector | Primary data store for companies, ideas, run logs |
| `redis` | Redis 7 | Celery message broker + Redis pub/sub for live WebSocket traces |

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **LLM** | Google Gemini (via `langchain-google-genai`) | 2.0.8 |
| **Agent Pattern** | LangChain tool-calling (ReAct) | 0.3.13 |
| **Web Search** | Tavily (DuckDuckGo fallback) | 0.3.3 |
| **Task Queue** | Celery + Celery Beat | 5.4.0 |
| **Message Broker** | Redis | 5.1.1 client |
| **API** | FastAPI + WebSockets | 0.115.0 |
| **Frontend** | Next.js 14, TypeScript | 14.x |
| **Database** | PostgreSQL 15 + pgvector | — |
| **ORM** | SQLAlchemy 2 + Alembic | 2.0.36 |
| **PDF Parsing** | PyPDF2 / pypdf | — |
| **Email** | Resend | 0.8.0 |
| **Container** | Docker Compose | — |

---

## What It Does

1. **Recalls memory** — checks what angles have already been used or rejected for this company
2. **Profiles the company** — extracts industry space, audience, and brand voice from their document
3. **Researches market news** — searches for specific, recent, verifiable signals using Tavily or DuckDuckGo
4. **Evaluates signal quality** — retries with different queries if the signal is too generic (up to 3 attempts)
5. **Chooses a fresh angle** — picks a content direction that hasn't been overused or rejected
6. **Generates 4 ideas** — hook, body, CTA, platform, implication type — grounded in the signal
7. **Self-validates** — critiques its own output against editorial quality criteria
8. **Surfaces to inbox** — human reviewer sees ideas in real time as each step completes
9. **Refines on demand** — admin feedback triggers an LLM rewrite of a specific idea

Runs are scheduled automatically per company (configurable frequency in hours) via Celery Beat. Runs can also be triggered manually from the dashboard.

---

## Setup & Installation

### Prerequisites

- Docker Desktop
- A Google Gemini API key ([get one free](https://aistudio.google.com/app/apikey))
- Optionally: a Tavily API key ([free tier](https://tavily.com) — 1,000 searches/month)

### 1. Clone

```bash
git clone <repo-url>
cd brandpulse-engine
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` — minimum required:

```env
GOOGLE_API_KEY=AIzaSy...
DATABASE_URL=postgresql://brandpulse:brandpulse@postgres:5432/brandpulse
REDIS_URL=redis://redis:6379/0
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### 3. Start

```bash
docker compose up --build
```

This starts all 5 services. Database tables are created automatically on first startup.

### 4. Access

| Interface | URL |
|---|---|
| **Idea Inbox / Dashboard** | http://localhost:3000 |
| **API Swagger Docs** | http://localhost:8000/docs |
| **API Health** | http://localhost:8000/health |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | ✅ | — | Gemini API key for all LLM calls |
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `REDIS_URL` | ✅ | — | Redis connection string |
| `NEXT_PUBLIC_API_URL` | ✅ | — | API base URL visible to the browser |
| `TAVILY_API_KEY` | ⬜ | — | Web search key. DuckDuckGo used automatically if absent |
| `ENABLE_WEB_SEARCH` | ⬜ | `true` | Set `false` to disable web search entirely (uses evergreen mode always) |
| `API_KEY` | ⬜ | — | API key for auth middleware. Leave empty to disable in dev |
| `SEND_EMAILS` | ⬜ | `false` | Enable Resend email delivery |
| `RESEND_API_KEY` | ⬜ | — | Resend.com key |
| `RESEND_FROM_EMAIL` | ⬜ | — | Sender email address |
| `LOG_LEVEL` | ⬜ | `INFO` | Logging verbosity: `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `MAX_PDF_SIZE_MB` | ⬜ | `10` | Maximum PDF upload size |

---

## Usage Guide

### Adding a Company

1. Open **http://localhost:3000**
2. Click **+ Add Company**
3. Fill in:
   - **Name** — the company name
   - **Description** — what they do (used as LLM context if no PDF)
   - **Run Frequency** — hours between automated runs (e.g. `24` = daily)
   - **PDF Upload** (optional) — company brochure, website content, pitch deck
4. Submit — the first run is scheduled immediately

### Reviewing Ideas

Navigate to a company's **Inbox**. Ideas arrive in real time as the agent produces them.

| Action | What happens |
|---|---|
| ✅ **Approve** | Marks idea as ready. Angle is logged as approved for memory. |
| ❌ **Reject** | Discards idea. Angle is logged as rejected — agent avoids it in future runs. |
| 🔄 **Refine** | Write specific feedback. A Celery task calls the LLM to rewrite the idea and returns it to `pending` for re-review. |

### Triggering a Run Manually

From the dashboard, click **▶ Trigger Run** on any company. The inbox immediately shows a live trace panel with each agent tool call as it fires.

### Monitoring

The dashboard shows:
- Total ideas generated across all companies
- Approval rate (win rate %)
- Recent run activity feed with per-company run status

---

## Live Run Tracing

Every agent tool call is published to a Redis pub/sub channel (`trace:{company_id}`). The API subscribes and forwards events over WebSocket to the frontend.

The **inbox live panel** shows step-by-step progress in real time:

```
● Recalling past angles          ✓
● Profiling company              ✓
● Searching market news          ✓
● Extracting signal              ✓ (strength: strong)
● Generating ideas               ✓ (↻ currently running)
● Validating ideas               ...
```

The panel appears immediately on run trigger — starting from "Waiting in queue…" before the worker even picks it up, then updating as each tool call completes.

---

## Project Structure

```
brandpulse-engine/
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.worker
├── requirements.txt
├── .env.example
│
└── services/
    │
    ├── shared/                         # Shared code across all services
    │   ├── models.py                   # SQLAlchemy ORM: Company, GeneratedIdea, RunLog, CompanyProfile
    │   ├── database.py                 # Session factory, connection pooling, health check
    │   └── init_db.py                  # Schema bootstrap on startup
    │
    ├── worker/                         # Celery worker + ReAct agent
    │   ├── celery_app.py               # Celery config, broker, Beat schedule
    │   ├── scheduler.py                # Worker process entry point
    │   │
    │   ├── agent/                      # ReAct agent (core intelligence)
    │   │   ├── core.py                 # run_ideation_v4() — agent loop
    │   │   │                           # refine_generated_idea() — HITL rewrite
    │   │   ├── tools.py                # @tool definitions (7 tools)
    │   │   │                           # make_db_tools() — DB-aware tool factory
    │   │   ├── prompts.py              # ReAct system prompt + legacy prompts
    │   │   ├── schemas.py              # Pydantic structured output schemas
    │   │   └── llm.py                  # Gemini LLM factory (get_llm, get_llm_structured)
    │   │
    │   ├── tasks/
    │   │   ├── ideation_task.py        # Celery tasks: queue_generation_tasks,
    │   │   │                           #   process_company_ideation, process_idea_refinement
    │   │   └── generation_task.py      # Direct session generation helper
    │   │
    │   ├── email_service/              # Email delivery (Resend)
    │   │   ├── sender.py
    │   │   └── logger.py
    │   │
    │   └── utils/
    │       ├── pdf.py                  # PDF text extraction
    │       ├── time.py                 # next_run_time calculation
    │       └── validation.py           # Input sanitisation
    │
    ├── api/                            # FastAPI backend
    │   ├── main.py                     # App factory, CORS, Redis listener, startup
    │   ├── dependencies.py             # DB session injection
    │   └── routers/
    │       ├── companies.py            # Company CRUD, run triggering, angle analytics
    │       ├── ideas.py                # Idea approve, reject, refine
    │       ├── websockets.py           # WebSocket manager + trace endpoint
    │       └── dashboard.py            # Aggregate stats API
    │
    └── frontend/                       # Next.js 14 app
        └── src/app/
            ├── page.tsx                # Company dashboard (stats, activity feed)
            └── companies/[id]/inbox/   # Idea inbox + live agent trace panel
```

---

## Database Models

| Model | Key Fields | Purpose |
|---|---|---|
| `Company` | `name`, `description`, `pdf_text`, `frequency_hours`, `next_run_time`, `status` | Company registry. Controls scheduling. |
| `CompanyProfile` | `space`, `audience`, `brand_voice`, `key_differentiators`, `region` | Cached LLM-extracted profile. Invalidated when company is updated. |
| `GeneratedIdea` | `hook`, `body`, `cta`, `platform`, `implication_type`, `angle_category`, `angle_detail`, `signal_used`, `status` | Individual content idea. Status: `pending → approved / rejected / refine_requested`. |
| `RunLog` | `company_id`, `trace_events`, `signal_strength`, `chosen_angle`, `evergreen`, `error` | Full trace of each agent run for debugging and analytics. |

---

## API Reference

### Companies

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/companies/` | List all companies with stats |
| `POST` | `/api/companies/` | Create a new company |
| `GET` | `/api/companies/{id}` | Get company details |
| `PATCH` | `/api/companies/{id}` | Update company settings |
| `DELETE` | `/api/companies/{id}` | Delete company and all its data |
| `POST` | `/api/companies/{id}/run` | **Manually trigger an ideation run** |
| `GET` | `/api/companies/{id}/runs` | List run history with trace events |
| `GET` | `/api/companies/{id}/ideas` | List ideas (filterable by status) |
| `GET` | `/api/companies/{id}/angles` | Angle usage analytics |

### Ideas

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/ideas/{id}` | Get a single idea |
| `PATCH` | `/api/ideas/{id}/approve` | Approve an idea |
| `PATCH` | `/api/ideas/{id}/reject` | Reject with optional feedback |
| `POST` | `/api/ideas/{id}/refine` | Request LLM rewrite with feedback |

### System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard/stats` | Aggregate metrics (total ideas, win rate) |
| `GET` | `/api/dashboard/activity` | Recent run activity feed |
| `GET` | `/health` | API health check |
| `WS` | `/api/ws/trace/{company_id}` | **Live agent trace WebSocket stream** |

---

## Development

### Rebuilding after code changes

```bash
# Restart a single service
docker compose restart worker

# Rebuild and restart
docker compose up --build worker
```

### Checking logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f worker
docker compose logs -f api
```

### Database shell

```bash
docker exec -it brandpulse_postgres psql -U brandpulse -d brandpulse
```

### Useful queries

```sql
-- Check company run schedule
SELECT name, next_run_time, status FROM companies;

-- See recent ideas for a company
SELECT hook, status, angle_category, created_at 
FROM generated_ideas 
WHERE company_id = 1 
ORDER BY created_at DESC 
LIMIT 10;

-- See run trace for last run
SELECT trace_events, signal_strength, evergreen, error 
FROM run_logs 
ORDER BY started_at DESC 
LIMIT 1;
```

### Customising the Agent

**Change the system prompt** (how the agent reasons):
- Edit `services/worker/agent/prompts.py` → `get_react_system_prompt()`

**Add or modify a tool**:
- Edit `services/worker/agent/tools.py`
- Add the new tool to `all_tools` list in `services/worker/agent/core.py`
- Rebuild the worker: `docker compose up --build worker`

**Change the content angle taxonomy**:
- Edit `ANGLE_CATEGORIES` list in `services/worker/agent/tools.py`

**Adjust max agent iterations** (default: 20 tool calls per run):
- Edit `MAX_ITERATIONS` in `services/worker/agent/core.py`

---

## Troubleshooting

### Worker not generating ideas?

```bash
# Check worker logs
docker compose logs -f worker

# Verify the company is due for a run
docker exec brandpulse_postgres psql -U brandpulse -d brandpulse \
  -c "SELECT name, next_run_time, status FROM companies;"

# Reset next_run_time to trigger immediately
docker exec brandpulse_postgres psql -U brandpulse -d brandpulse \
  -c "UPDATE companies SET next_run_time = NOW() WHERE name = 'YourCompany';"
```

### API not starting?

```bash
docker compose logs api
# Most common cause: DATABASE_URL or GOOGLE_API_KEY not set in .env
```

### Frontend can't reach API?

Check that `NEXT_PUBLIC_API_URL` in `.env` matches where the API is actually running (`http://localhost:8000/api` for local dev).

### Agent produces no ideas after a run?

Check the RunLog in the database:

```sql
SELECT error, signal_strength, evergreen, trace_events 
FROM run_logs 
ORDER BY started_at DESC 
LIMIT 1;
```

Common causes:
- LLM quota exceeded (`GOOGLE_API_KEY` rate limit)
- Web search returning empty results (check Tavily key or DuckDuckGo rate limits)
- `validate_and_critique_ideas` rejecting all ideas — lower quality bar or check prompts

### Live trace panel not updating?

Check Redis is running and the WebSocket connection is established:

```bash
docker compose ps redis
docker compose logs api | grep -i websocket
```

---

## API Limits (Free Tiers)

| Service | Free Tier | Notes |
|---|---|---|
| **Google Gemini** | 1,500 requests/day, 15 RPM | Each agent run makes ~5–10 LLM calls |
| **Tavily** | 1,000 searches/month | Falls back to DuckDuckGo if key absent or quota hit |
| **Resend** | 3,000 emails/month | Email delivery is off by default (`SEND_EMAILS=false`) |

---

*Last updated: June 2026*
