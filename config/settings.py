"""
Project Chimera Enterprise Configuration Management System
Handles all environment variables and application settings with enterprise security
"""
import os
from typing import Optional, List
import os
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Enterprise application settings with environment variable support"""

    def __init__(self):
        # Load from environment variables with defaults
        self.app_name = os.getenv("APP_NAME", "Project Chimera Enterprise")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")

        # Server Configuration
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))

        # Security Configuration
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-immediately")

        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        # CORS Configuration
        self.allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501")
        self.allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1")

        # Database Configuration
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./data/chimera_enterprise.db")

        # AI API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

        # Google Services
        self.google_credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

        # Redis Configuration
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        # Browser Automation
        self.headless_browser = os.getenv("HEADLESS_BROWSER", "true").lower() == "true"
        self.browser_timeout = int(os.getenv("BROWSER_TIMEOUT", "30000"))

        # Vector Database
        self.chromadb_path = os.getenv("CHROMADB_PATH", "./data/memory_bank")

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "./logs/chimera_enterprise.log")

        # Multi-tenant Configuration
        self.max_clients = int(os.getenv("MAX_CLIENTS", "50"))
        self.commission_rate = float(os.getenv("COMMISSION_RATE", "0.40"))

        # Email Configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_username = os.getenv("EMAIL_USERNAME", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")

        # Agent Configuration
        self.max_concurrent_agents = int(os.getenv("MAX_CONCURRENT_AGENTS", "10"))
        self.agent_timeout = int(os.getenv("AGENT_TIMEOUT", "300"))

        # LLM Configuration
        self.default_llm_model = os.getenv("DEFAULT_LLM_MODEL", "gpt-4-turbo-preview")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "4000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))

        # Rate Limiting
        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))



    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def allowed_hosts_list(self) -> List[str]:
        """Get allowed hosts as a list"""
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
