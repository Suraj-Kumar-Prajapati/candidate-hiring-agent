import os

from pydantic import PostgresDsn, ConfigDict, field_validator
from typing import Any, Dict, Optional


class Settings(ConfigDict):
    PROJECT_NAME: str = "AI Hiring Agent Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1/"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Database configuration
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "hiring_agent")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "hiring_agent_db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    DATABASE_URL: Optional[PostgresDsn] = None

    # AWS SES Configuration
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "ses")
    AWS_SES_ACCESS_KEY_ID: str = os.getenv("AWS_SES_ACCESS_KEY_ID", "")
    AWS_SES_SECRET_ACCESS_KEY: str = os.getenv("AWS_SES_SECRET_ACCESS_KEY", "")
    AWS_SES_REGION: str = os.getenv("AWS_SES_REGION", "us-east-1")
    
    # Company Email Configuration
    COMPANY_EMAIL: str = os.getenv("COMPANY_EMAIL", "HR Hiring <hiring@hr.com>")
    DEVELOPERS_EMAIL: str = os.getenv("DEVELOPERS_EMAIL", "Suraj Prajapati<suraj@quskdjs.com>")
    HR_EMAIL: str = os.getenv("HR_EMAIL", "hiring@hr.com")

    @field_validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v

        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            port=values.get("POSTGRES_PORT"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )

    # Redis Configuration (for caching and queues)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # LLM Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.6"))

    # Email Configuration
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

    # Agent Configuration
    MAX_CONCURRENT_WORKFLOWS: int = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "10"))
    WORKFLOW_TIMEOUT_MINUTES: int = int(os.getenv("WORKFLOW_TIMEOUT_MINUTES", "60"))

    # File Upload
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    UPLOAD_DIRECTORY: str = os.getenv("UPLOAD_DIRECTORY", "./uploads")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
