# Project Chimera - Secure Sandbox Environment
# Minimal Python environment for testing code fixes

FROM python:3.11-slim

# Create non-root user for security
RUN useradd -m -u 1000 sandbox && \
    mkdir -p /app && \
    chown sandbox:sandbox /app

# Install minimal required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages that might be needed for testing
RUN pip install --no-cache-dir \
    requests \
    beautifulsoup4 \
    lxml \
    aiohttp \
    asyncio \
    json5 \
    pydantic

# Set working directory
WORKDIR /app

# Switch to non-root user
USER sandbox

# Set environment variables for security
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-c", "print('Sandbox ready')"]
