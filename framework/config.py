from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"

load_dotenv(ROOT / ".env", override=False)


class RetryConfig(BaseModel):
    max_attempts: int = 3
    backoff_seconds: float = 1.5


class FeatureFlags(BaseModel):
    schema_validation: bool = True
    db_validation: bool = False


class EnvConfig(BaseModel):
    name: str
    base_url: str
    auth_url: str
    timeout_ms: int = 30000
    verify_ssl: bool = True
    default_headers: dict[str, str] = Field(default_factory=dict)
    rate_limit_per_sec: int = 10
    retry: RetryConfig = Field(default_factory=RetryConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    @property
    def timeout_s(self) -> float:
        return self.timeout_ms / 1000.0


class Secrets(BaseModel):
    username: str | None = None
    password: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    db_host: str | None = None
    db_port: int | None = None
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_dialect: str = "postgresql+psycopg2"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache(maxsize=1)
def get_env() -> EnvConfig:
    env_name = os.getenv("ENV", "qa").lower()
    data = _read_yaml(CONFIG_DIR / f"env.{env_name}.yaml")
    cfg = EnvConfig(**data)
    # CLI / env-var override of base_url is handy for ad-hoc runs.
    if os.getenv("RCM_BASE_URL"):
        cfg = cfg.model_copy(update={"base_url": os.environ["RCM_BASE_URL"]})
    return cfg


@lru_cache(maxsize=1)
def get_secrets() -> Secrets:
    return Secrets(
        username=os.getenv("RCM_USERNAME"),
        password=os.getenv("RCM_PASSWORD"),
        client_id=os.getenv("RCM_CLIENT_ID"),
        client_secret=os.getenv("RCM_CLIENT_SECRET"),
        db_host=os.getenv("DB_HOST"),
        db_port=int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else None,
        db_name=os.getenv("DB_NAME"),
        db_user=os.getenv("DB_USER"),
        db_password=os.getenv("DB_PASSWORD"),
        db_dialect=os.getenv("DB_DIALECT", "postgresql+psycopg2"),
    )
