# Multi-stage Dockerfile for Project Chimera Enterprise
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r chimera && useradd -r -g chimera chimera

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Development stage
FROM base as development

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data logs static && \
    chown -R chimera:chimera /app

USER chimera

EXPOSE 8000

CMD ["python", "main.py"]

# Production stage
FROM base as production

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p data logs static && \
    chown -R chimera:chimera /app

# Remove development files
RUN rm -rf tests/ *.md install_enterprise_deps.py setup_admin.py test_enterprise_security.py

# Switch to non-root user
USER chimera

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Use gunicorn for production
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
