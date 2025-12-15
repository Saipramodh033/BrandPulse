# 🚀 BrandPulse

**Autonomous AI Agent for Strategic Intelligence**

BrandPulse is a fully autonomous AI agent built with LangGraph that generates market intelligence insights without human intervention. The agent independently researches market trends, analyzes company contexts, generates strategic insights, and delivers them via email—all on a scheduled basis. Simply upload company profiles and let the agent do the work.

---

## ✨ Features

### 🎯 **Core Capabilities**
- **Autonomous Insight Generation**: AI agent automatically generates strategic intelligence on schedule
- **RAG-Powered Analysis**: Vector embeddings (pgvector) enable semantic understanding of company profiles
- **Market Research**: Optional web search integration (Tavily) for real-time market trends
- **Email Delivery**: Automated email delivery via Resend (100 emails/day free tier)
- **Approval Workflow**: Admin review and approval before insights are sent to clients

### 📊 **Professional Dashboard**
- **Authentication**: Secure login with bcrypt password hashing
- **Company Management**: CRUD operations with PDF profile upload
- **Insights Review**: Approve, reject, or request refinements
- **Analytics**: System metrics, KPIs, and performance tracking
- **Settings**: Configurable LLM prompts for customization

### 🤖 **AI Architecture**
- **LangGraph Agent**: Multi-step reasoning with search, analysis, and generation nodes
- **Google Gemini**: LLM for insight generation and embeddings
- **Adaptive Scheduling**: Configurable frequency per company (minutes to days)
- **Auto-Rejection**: Expired pending insights trigger apology emails

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     BrandPulse System                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │  Dashboard   │      │    Worker    │      │ PostgreSQL│ │
│  │  (Streamlit) │◄────►│  (Scheduler) │◄────►│ +pgvector │ │
│  │   Port 8501  │      │   Python     │      │  Port 5432│ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│         │                      │                             │
│         │                      ├─► Google Gemini API         │
│         │                      ├─► Tavily Search API         │
│         │                      └─► Resend Email API          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### **Components**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Dashboard** | Streamlit 1.x | Admin UI for company/insight management |
| **Worker** | Python 3.11 + APScheduler | Autonomous agent with scheduled jobs |
| **Database** | PostgreSQL 15 + pgvector | Structured data + vector embeddings |
| **LLM** | Google Gemini (gemini-1.5-flash) | Text generation + embeddings |
| **Search** | Tavily API (optional) | Real-time market intelligence |
| **Email** | Resend | Transactional email delivery |

---

## 🚀 Quick Start

### **Prerequisites**
- Docker & Docker Compose
- Google AI API key (free tier: 1500 requests/day)
- Resend API key (free tier: 100 emails/day)
- Tavily API key (optional, free tier: 1000 searches/month)

### **1. Clone Repository**
```bash
git clone <your-repo-url>
cd brandpulse-engine
```

### **2. Configure Environment**
```bash
# Copy template
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

**Required Variables:**
```env
# Database
POSTGRES_DB=brandpulse
POSTGRES_USER=brandpulse_user
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://brandpulse_user:your_secure_password_here@postgres:5432/brandpulse

# Google AI (Get from: https://makersuite.google.com/app/apikey)
GOOGLE_API_KEY=AIzaSy...

# Resend Email (Get from: https://resend.com/api-keys)
RESEND_API_KEY=re_...
RESEND_FROM_EMAIL=noreply@yourdomain.com
SEND_EMAILS=false  # Set to 'true' when ready to send emails

# Admin Login
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me_in_production

# Optional: Web Search (Get from: https://tavily.com)
TAVILY_API_KEY=tvly-...
ENABLE_WEB_SEARCH=true
```

### **3. Start Services**
```bash
# Build and start all containers
docker-compose up --build -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### **4. Initialize Database**
```bash
# Create tables and seed data
docker exec brandpulse_dashboard python -c "from services.shared.models import create_tables; from services.shared.database import engine; create_tables(engine)"
```

### **5. Access Dashboard**
Open browser to: **http://localhost:8501**

**Default Login:**
- Username: `admin`
- Password: `admin123` (or your configured password)

---

## 📖 Usage Guide

### **Adding a Company**
1. Navigate to **Companies** page
2. Click **Add New Company**
3. Fill in details:
   - Company Name
   - Description
   - Email (for insight delivery)
   - Frequency (hours between insights)
4. Upload PDF profile (company background, services, etc.)
5. Submit → System generates embeddings and schedules first run

### **Reviewing Insights**
1. Navigate to **Insights** page
2. View pending insights in tabs (Pending/Approved/Rejected)
3. Expand insight to read full content
4. Actions:
   - ✅ **Approve** → Sends email to company
   - ❌ **Reject** → Provide feedback for refinement
   - 🔄 **Refining** → Agent regenerates based on feedback

### **Monitoring System**
1. Navigate to **Analytics** page
2. View metrics:
   - Total insights generated
   - Approval rate
   - Average processing time
   - Email delivery stats

### **Customizing Prompts**
1. Navigate to **Settings** page
2. Edit **System Prompt** (agent behavior)
3. Edit **User Template** (company analysis template)
4. Save changes → Affects future insight generation

---

## 🛠️ Development

### **Project Structure**
```
brandpulse-engine/
├── docker-compose.yml          # Service orchestration
├── Dockerfile.worker           # Worker container
├── Dockerfile.dashboard        # Dashboard container
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in Git)
├── .env.example                # Environment template
├── README.md                   # This file
├── services/
│   ├── __init__.py
│   ├── shared/                 # Shared code
│   │   ├── __init__.py
│   │   ├── database.py         # SQLAlchemy setup
│   │   ├── models.py           # Database models
│   │   ├── models_config.py    # Configuration models (PromptConfig)
│   │   └── init_db.py          # Database initialization
│   ├── worker/                 # Autonomous agent
│   │   ├── __init__.py
│   │   ├── scheduler.py        # APScheduler entry point
│   │   ├── tasks/              # Scheduled job definitions
│   │   │   ├── __init__.py
│   │   │   ├── generation_task.py    # Insight generation job
│   │   │   ├── metrics_task.py       # System metrics update
│   │   │   ├── refinement_task.py    # Rejected insight refinement
│   │   │   └── rejection_task.py     # Auto-reject expired insights
│   │   ├── agent/              # LangGraph agent
│   │   │   ├── __init__.py
│   │   │   ├── core.py         # Agent workflow & state management
│   │   │   ├── nodes.py        # Agent nodes (search, analyze, generate)
│   │   │   ├── llm.py          # LLM interface (Gemini)
│   │   │   └── prompts.py      # System prompts
│   │   ├── email_service/      # Email delivery
│   │   │   ├── __init__.py
│   │   │   ├── sender.py       # Resend integration
│   │   │   └── logger.py       # Email tracking (EmailLog)
│   │   └── utils/              # Worker utilities
│   │       ├── __init__.py
│   │       ├── pdf.py          # PDF text extraction (PyPDF2)
│   │       ├── time.py         # Scheduling helpers
│   │       └── validation.py   # Input validation
│   └── dashboard/              # Streamlit UI
│       ├── __init__.py
│       ├── app.py              # Main entry point & router
│       ├── pages/              # Dashboard pages
│       │   ├── login.py        # Authentication page
│       │   ├── companies.py    # Company CRUD
│       │   ├── insights.py     # Insight review workflow
│       │   ├── metrics.py      # Analytics dashboard
│       │   └── settings.py     # LLM prompt configuration
│       └── utils/              # Dashboard utilities
│           ├── auth.py         # Login/logout logic
│           └── session.py      # Session state management
├── templates/                  # Jinja2 email templates
│   ├── insight_email.html      # Approved insight email
│   └── apology_email.html      # Auto-rejection apology
└── logs/                       # Log files (mounted volume)
    └── .gitkeep
```

### **Database Models**

| Model | Description |
|-------|-------------|
| **Admin** | Dashboard user accounts (bcrypt hashed passwords) |
| **Company** | Client registry with RAG embeddings (768-dim vectors) |
| **Insight** | Generated strategic intelligence content |
| **EmailLog** | Email delivery tracking (insights + apologies) |
| **Metric** | Aggregated system performance metrics |
| **PromptConfig** | LLM prompt configuration (system/user templates) |

### **Agent Workflow (LangGraph)**
```
START → Search Node → Analyze Node → Generate Node → END
  │         │              │              │
  │    [Tavily/DDG]   [Company PDF]   [Gemini LLM]
  │         │              │              │
  └─────────┴──────────────┴──────────────┘
              ↓
         Insight Created
              ↓
         Admin Review
              ↓
    [Approve] → Email Sent
    [Reject]  → Agent Refines
```

### **Scheduler Jobs**

| Job | Frequency | Purpose |
|-----|-----------|---------|
| **Auto-Rejection** | Every run | Reject insights pending >24 hours, send apology |
| **Refinement** | Every run | Re-process rejected insights with admin feedback |
| **Generation** | Every run | Generate insights for companies due for processing |
| **Metrics Update** | Every run | Aggregate system performance statistics |

---

## ⚙️ Configuration

### **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `SCHEDULER_CHECK_INTERVAL` | 50 | Seconds between scheduler runs |
| `MAX_PDF_SIZE_MB` | 10 | Maximum PDF upload size |
| `SEND_EMAILS` | false | Enable/disable actual email sending |
| `ENABLE_WEB_SEARCH` | true | Enable/disable Tavily search |
| `LOG_LEVEL` | INFO | Logging verbosity (DEBUG/INFO/WARNING/ERROR) |

### **Customization**

**Agent Behavior:**
- Edit `services/shared/models_config.py` → `PromptConfig` defaults
- Or use Dashboard → Settings page

**Email Templates:**
- Edit `templates/insight_email.html` for approved insights
- Edit `templates/apology_email.html` for auto-rejections

**Scheduler Timing:**
- Edit `SCHEDULER_CHECK_INTERVAL` in `.env`
- Per-company frequency: Dashboard → Companies → Edit

---

## 🔒 Security

- ✅ **Password Hashing**: bcrypt for admin accounts
- ✅ **Session Management**: Streamlit session state with authentication checks
- ✅ **Input Validation**: File size limits, email validation
- ✅ **API Key Protection**: Environment variables (not in code)
- ✅ **Database Isolation**: PostgreSQL with user permissions
- ⚠️ **Production Hardening**: Change default passwords, enable HTTPS, restrict ports

---

## 📊 API Limits (Free Tiers)

| Service | Free Tier | Rate Limit |
|---------|-----------|------------|
| **Google Gemini** | 1,500 requests/day | 15 RPM |
| **Resend** | 3,000 emails/month | 100/day |
| **Tavily** | 1,000 searches/month | 50/day |

---

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Rebuild after code changes
docker-compose up --build -d

# Database console
docker exec -it brandpulse_postgres psql -U brandpulse_user -d brandpulse

# Worker shell
docker exec -it brandpulse_worker bash

# Dashboard shell
docker exec -it brandpulse_dashboard bash
```

---

## 🧪 Testing

```bash
# Run worker scheduler manually
docker exec brandpulse_worker python services/worker/scheduler.py

# Test email sending (dev mode)
docker exec brandpulse_worker python -c "
from services.worker.email_service.sender import send_insight_email
# ... test code
"

# Check database
docker exec brandpulse_postgres psql -U brandpulse_user -d brandpulse -c "SELECT * FROM companies;"
```

---

## 🔧 Troubleshooting

### **Dashboard not loading?**
```bash
# Check logs
docker logs brandpulse_dashboard --tail 50

# Restart dashboard
docker-compose restart dashboard
```

### **Worker not generating insights?**
```bash
# Check logs
docker logs brandpulse_worker --tail 50

# Verify company next_run_time
docker exec brandpulse_postgres psql -U brandpulse_user -d brandpulse -c \
  "SELECT name, next_run_time, status FROM companies;"
```

### **Database connection errors?**
```bash
# Check PostgreSQL health
docker-compose ps postgres

# Verify DATABASE_URL in .env matches PostgreSQL credentials
```

### **Emails not sending?**
1. Check `SEND_EMAILS=true` in `.env`
2. Verify `RESEND_API_KEY` is valid
3. Check logs: `docker logs brandpulse_worker | grep -i email`


---

## 🎉 Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) - Dashboard framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Agent orchestration
- [Google Gemini](https://ai.google.dev/) - LLM and embeddings
- [Resend](https://resend.com/) - Email delivery
- [Tavily](https://tavily.com/) - Web search API
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search

---

**Last Updated**: December 2025
**Version**: 1.0.0
