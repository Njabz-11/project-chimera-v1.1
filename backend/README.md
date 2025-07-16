# Project Chimera - Backend

This directory contains the backend components of Project Chimera Enterprise.

## 🏗 Architecture

### Core Components

- **`main.py`** - FastAPI application entry point
- **`agents/`** - The Ten Specialized AI Agents
- **`auth/`** - Authentication and authorization system
- **`database/`** - Database management and operations
- **`tools/`** - Core tools (Email service, Memory bank)
- **`utils/`** - Utilities and error handling

### Configuration & Infrastructure

- **`config/`** - Application configuration management
- **`monitoring/`** - Health checks and metrics
- **`tenants/`** - Multi-tenant architecture
- **`docker/`** - Docker deployment configurations
- **`data/`** - Database files and storage
- **`logs/`** - Application runtime logs

## 🚀 Quick Start

### 1. Environment Setup
```bash
cd Backend
python -m venv chimera_env
chimera_env\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configuration
```bash
copy .env.template .env
# Edit .env with your API keys and settings
```

### 3. Initialize Database
```bash
python setup_admin.py
```

### 4. Start Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

- **Health Check:** `GET /health`
- **Authentication:** `POST /auth/login`
- **Agents:** `GET /admin/system/detailed`
- **Missions:** `POST /mission/create`
- **System Status:** `GET /system/status/detailed`

## 🤖 The Ten Agents

1. **MAESTRO** - Central orchestrator
2. **ARCHITECT** - Mission planning
3. **SCOUT** - Lead generation
4. **LOREWEAVER** - Content creation
5. **HERALD** - First contact
6. **DIPLOMAT** - Deal closure
7. **QUARTERMASTER** - External fulfillment
8. **ARTIFICER** - Internal creation
9. **WRENCH** - Error handling
10. **AEGIS** - Safety checkpoint

## 🔧 Development

### Running Tests
```bash
python -m pytest tests/
```

### Docker Deployment
```bash
docker-compose up -d
```

### Environment Variables
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `DATABASE_URL` - Database connection string
- `JWT_SECRET_KEY` - JWT signing key

## 📊 Monitoring

- **Health Checks:** `/health`, `/health/detailed`
- **Metrics:** `/metrics` (Prometheus format)
- **Logs:** `logs/` directory

---

**Project Chimera Backend** - Autonomous Business Operations Platform
*Enterprise-grade AI agent system*
