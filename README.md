# Project Chimera Enterprise - Autonomous Business Operations Platform

A production-ready, multi-tenant, autonomous business operations platform powered by AI agents.

## 🎯 Overview

Project Chimera Enterprise is an advanced autonomous business operations platform that leverages specialized AI agents to handle the complete business pipeline from lead generation to deal closure and fulfillment. The system operates as a deployable, autonomous business engine with enterprise-grade security, monitoring, and multi-tenant architecture.

## 🤖 The Ten Agents

1. **MAESTRO (Orchestrator)** - Central nervous system and state machine
2. **ARCHITECT (Strategist)** - Processes client input into actionable mission briefings  
3. **SCOUT (Prospector)** - Autonomous lead generation and qualification
4. **LOREWEAVER (Bard)** - Content generation and brand authority building
5. **HERALD (Communicator)** - Personalized first-contact outreach
6. **DIPLOMAT (Closer)** - Reply management and deal closure
7. **QUARTERMASTER (Dispatcher)** - External fulfillment management
8. **ARTIFICER (Creator)** - Internal digital product creation
9. **WRENCH (Technician)** - Error detection and auto-repair
10. **AEGIS (Guardian)** - Ethical and safety checkpoint

## 🛠 Technology Stack

- **Backend**: FastAPI with Python 3.11+
- **Frontend**: Streamlit dashboard
- **Database**: SQLite (development) / PostgreSQL (production)
- **Vector Database**: ChromaDB for conversation memory
- **Browser Automation**: Playwright
- **LLM Integration**: OpenAI GPT-4, Anthropic Claude
- **Authentication**: JWT with bcrypt, enterprise security
- **Monitoring**: Prometheus metrics, health checks
- **Deployment**: Docker with docker-compose

## 🚀 Quick Start

### 1. Environment Setup
```bash
cd Project-Chimera-Dev
.\chimera_env\Scripts\activate  # Use existing virtual environment
```

### 2. Configuration
```bash
# Copy and edit environment configuration
copy .env.template .env
# Edit .env with your API keys and settings
```

### 3. Start Services
```bash
# Terminal 1: Main API Server
uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Dashboard  
streamlit run dashboard.py --server.port 8501
```

### 4. Access Points
- **Main Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8501
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

### 5. Admin Access
- **Username**: admin
- **Password**: ChimeraAdmin123!

## 📁 Project Structure

```
Project-Chimera-Dev/
├── 🔧 Backend/                    # Backend Services & API
│   ├── 🤖 agents/                 # The Ten Specialized Agents
│   ├── 🔐 auth/                   # Enterprise Authentication
│   ├── ⚙️ config/                 # Configuration Management
│   ├── 🗄️ database/               # Database Operations
│   ├── 📊 monitoring/             # Health & Metrics
│   ├── 🏢 tenants/                # Multi-Tenant Architecture
│   ├── 🛠️ tools/                  # Email & Memory Services
│   ├── 🔧 utils/                  # Error Handling & Utilities
│   ├── 🐳 docker/                 # Production Deployment
│   ├── 📁 data/                   # Data Storage
│   ├── 📝 logs/                   # Runtime Logs
│   ├── 🚀 main.py                 # FastAPI Application
│   ├── 🔧 setup_admin.py          # Admin Setup
│   ├── 📋 requirements.txt        # Dependencies
│   └── 📖 README.md               # Backend Documentation
├── 🎨 Frontend/                   # Modern UI Interface
│   ├── 📄 templates/              # HTML Templates
│   │   ├── dashboard.html         # Main Dashboard
│   │   ├── login.html             # Authentication Page
│   │   ├── agents.html            # Agent Management
│   │   ├── system-status.html     # System Monitoring
│   │   ├── analytics.html         # Business Analytics
│   │   ├── missions.html          # Mission Control
│   │   ├── llm-config.html        # LLM Configuration
│   │   └── error-handler.html     # Error Management
│   ├── 🎨 static/                 # CSS & JavaScript
│   │   ├── css/                   # Design System
│   │   └── js/                    # Interactive Features
│   ├── 📊 dashboard.py            # Streamlit Redirect
│   └── 📖 README.md               # Frontend Documentation
└── 📖 README.md                   # Main Documentation
```

## 🔧 Key Features

### Enterprise Features
- ✅ **Multi-Tenant Architecture** - Complete tenant isolation
- ✅ **Enterprise Security** - JWT, rate limiting, CORS, input validation
- ✅ **Production Deployment** - Docker, Nginx, PostgreSQL
- ✅ **Comprehensive Monitoring** - Health checks, Prometheus metrics
- ✅ **Error Handling** - Automated error detection and recovery
- ✅ **Audit Logging** - Complete operation tracking

### Core Capabilities
- ✅ **Autonomous Lead Generation** - Web scraping with Playwright
- ✅ **Email Automation** - Google OAuth2 integration
- ✅ **Content Generation** - AI-powered content creation
- ✅ **Deal Management** - Complete sales pipeline
- ✅ **Project Fulfillment** - Internal and external delivery
- ✅ **Real-time Dashboard** - Live system monitoring

## 🌐 API Endpoints

### Authentication
- `POST /auth/login` - User authentication
- `POST /auth/register` - User registration
- `GET /auth/me` - Current user info

### Mission Management
- `POST /mission/create` - Create mission briefing
- `GET /missions` - List missions

### Lead Operations
- `GET /leads` - List generated leads
- `POST /agent/prospector/search` - Trigger lead search

### Communication
- `GET /conversations` - List conversations
- `POST /outreach/trigger` - Trigger outreach

### Content & Fulfillment
- `GET /content/calendar` - Content calendar
- `POST /fulfillment/external` - External fulfillment
- `POST /fulfillment/internal` - Internal fulfillment

### System Monitoring
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed system status
- `GET /metrics` - Prometheus metrics

## 🐳 Production Deployment

### Docker Deployment
```bash
# Build and start all services
docker-compose up -d

# Or use the deployment script
./deploy.sh -e production
```

## 📊 Monitoring & Health

- **Health Endpoint**: `/health` - Basic system status
- **Detailed Health**: `/health/detailed` - Comprehensive checks
- **Metrics**: `/metrics` - Prometheus format metrics
- **Dashboard**: Real-time system monitoring via Streamlit

## 🔐 Security Features

- JWT-based authentication with refresh tokens
- Rate limiting and DDoS protection
- CORS configuration
- Input validation and sanitization
- Secure password hashing with bcrypt
- Multi-tenant data isolation

## 📈 Development Status

- ✅ **Phase 1**: Core infrastructure and agent framework
- ✅ **Phase 2**: Lead generation with browser automation
- ✅ **Phase 3**: Email communication and memory system
- ✅ **Phase 4**: Content generation and fulfillment
- ✅ **Phase 5**: Error handling and self-correction
- ✅ **Enterprise**: Production deployment and monitoring

---

**Project Chimera Enterprise** - Autonomous Business Operations Platform
*Ready for production deployment and enterprise use*
