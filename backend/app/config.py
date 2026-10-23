
import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Inside"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./inside.db"

    # Authentication
    JWT_SECRET_KEY: str = "CHANGE_ME_TO_A_RANDOM_SECRET_BEFORE_DEPLOYMENT"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Gemini AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Google Play Billing (optional)
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON: Optional[str] = None
    GOOGLE_PLAY_PACKAGE_NAME: str = "com.inside.inside"

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    PREMIUM_PRODUCT_ID: str = "inside_premium_lifetime"
    LIFETIME_PRODUCT_ID: str = "inside_premium_lifetime"
    PREMIUM_PRICE_PAISE: int = 19900
    PREMIUM_CURRENCY: str = "INR"

    # Free usage
    FREE_SCAN_LIMIT: int = 3

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH) if ENV_PATH.exists() else ".env",
        extra="ignore",
    )


settings = Settings()
