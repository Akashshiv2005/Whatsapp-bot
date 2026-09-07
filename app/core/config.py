import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    APP_NAME: str = "iZone Technologies WhatsApp Automation"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Meta WhatsApp Cloud API Credentials
    META_ACCESS_TOKEN: str = "placeholder_meta_access_token"
    META_PHONE_NUMBER_ID: str = "placeholder_phone_id"
    META_BUSINESS_ACCOUNT_ID: str = "placeholder_business_id"
    META_VERIFY_TOKEN: str = "izone_meta_verify_token_secure_123"
    META_API_VERSION: str = "v19.0"

    # Database (strictly loaded from .env in production)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/izone_bot"

    # CORS Settings
    CORS_ORIGINS: str = "*"

    # Security
    ADMIN_API_KEY: str = "izone_admin_secret_api_key_2026"

    # Company Defaults
    COMPANY_NAME: str = "iZone Technologies"
    COMPANY_WEBSITE: str = "https://izonetech.in/"
    COMPANY_PHONE: str = "+919940048776"
    COMPANY_EMAIL: str = "info@izonetech.in"
    COMPANY_LOCATION_LATITUDE: float = 10.8271
    COMPANY_LOCATION_LONGITUDE: float = 78.6890
    COMPANY_ADDRESS: str = "3rd Floor, Aruvi Arcade Complex, 5th Cross Thillainagar, North Extension Road, Tiruchirappalli, Tamil Nadu – 620018"
    COMPANY_WORKING_HOURS: str = "Monday – Saturday, 10:00 AM – 6:30 PM"

    # SMTP / Email Forwarding
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    NOTIFICATION_EMAIL: Optional[str] = "info@izonetech.in"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def meta_api_base_url(self) -> str:
        return f"https://graph.facebook.com/{self.META_API_VERSION}/{self.META_PHONE_NUMBER_ID}/messages"


@lru_cache
def get_settings() -> Settings:
    return Settings()
