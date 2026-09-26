"""Application configuration via pydantic-settings, with .env support.

Every value can be overridden with an environment variable (or an .env file),
e.g.:

    DATABASE_URL=postgresql+psycopg://user:pass@host/dbname
    SECRET_KEY=change-me
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Pulmora"
    DEBUG: bool = False

    # --- Database (SQLite for dev; override via env for other engines) ---
    DATABASE_URL: str = "sqlite:///./db.sqlite3"

    # --- Security / JWT ---
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    AUTH_COOKIE_NAME: str = "lcps_access_token"

    # --- Machine learning ---
    # Dataset used to train the logistic regression model at startup.
    DATASET_PATH: str = "static/dataset/lungcancer.csv"
    TRAIN_TEST_SPLIT_SIZE: float = 0.25
    TRAIN_RANDOM_STATE: int = 1

    # --- Rate limiting (slowapi) on POST /predict ---
    PREDICT_RATE_LIMIT: str = "10/minute"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- PDF ---
    INR_CONVERSION_RATE: float = 75.0  # 1 USD ~= 75 INR (as in original views.py)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
