"""
SentinelIQ Configuration Settings
Centralized environment-variable configuration using Pydantic Settings.
"""
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    # App info
    APP_NAME: str = "SentinelIQ"
    APP_FULL_NAME: str = "SentinelIQ — Intelligent Transaction Risk & Investigation Platform"
    APP_TAGLINE: str = "Explainable Risk. Traceable Decisions."
    APP_ENV: str = "development"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security & Tokens
    SECRET_KEY: str = Field(default="sentineliq-default-dev-secret-key-32-bytes-change-in-prod-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Demo credentials for review / testing (only active if ENABLE_DEMO_USERS is True)
    ENABLE_DEMO_USERS: bool = True
    DEMO_ADMIN_PASSWORD: str = "SentinelIQ@Admin2026!"
    DEMO_ANALYST_PASSWORD: str = "SentinelIQ@Analyst2026!"
    DEMO_COMPLIANCE_PASSWORD: str = "SentinelIQ@Compliance2026!"
    DEMO_READONLY_PASSWORD: str = "SentinelIQ@ReadOnly2026!"

    # Database & Storage
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "sentineliq_risk_intelligence"
    APP_STORAGE: str = "mongodb"  # 'mongodb' or 'memory' (in-memory mock for isolated tests)

    # URLs & CORS
    FRONTEND_BASE_URL: str = "http://localhost:8000"
    API_BASE_URL: str = "http://localhost:8000/api/v1"
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    # Generator and Evaluation Paths
    DEFAULT_SEED: int = 20261022
    DEFAULT_PROFILE: str = "demo"
    DATASET_EXPORT_DIR: str = "./exports"
    GROUND_TRUTH_DIR: str = "./ground_truth"
    REPORTS_DIR: str = "./reports"
    LOG_LEVEL: str = "INFO"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
