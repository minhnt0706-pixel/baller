"""
Application configuration loaded from environment variables.

All required settings are validated at startup; missing vars raise RuntimeError
listing every missing variable before the server binds to any port.
"""

import os
from functools import lru_cache
from typing import List


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require(name: str) -> str:
    """Return the value of *name* from the environment (never empty)."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise _MissingVarError(name)
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class _MissingVarError(Exception):
    """Sentinel used only inside _collect_config."""


# ---------------------------------------------------------------------------
# Settings dataclass (plain, no Pydantic to keep the import surface minimal)
# ---------------------------------------------------------------------------

class Settings:
    """Application settings resolved from environment variables."""

    # Database
    database_url: str

    # Redis (for rate limiting via slowapi)
    redis_url: str

    # VietQR / payment
    vietqr_bank_id: str
    vietqr_account_no: str
    vietqr_account_name: str
    vietqr_template: str

    # CORS
    cors_origins: List[str]

    # Application mode
    app_env: str  # 'development' | 'staging' | 'production'

    # Rate-limiting window & max calls
    rate_limit_booking_per_minute: int

    # Pending-payment expiry in minutes
    pending_payment_expiry_minutes: int

    def __init__(self) -> None:
        missing: List[str] = []

        def require(name: str) -> str:
            try:
                return _require(name)
            except _MissingVarError:
                missing.append(name)
                return ""  # placeholder; we raise below if any are missing

        # --- Required ---
        self.database_url = require("DATABASE_URL")
        self.redis_url = require("REDIS_URL")
        self.vietqr_bank_id = require("VIETQR_BANK_ID")
        self.vietqr_account_no = require("VIETQR_ACCOUNT_NO")
        self.vietqr_account_name = require("VIETQR_ACCOUNT_NAME")

        if missing:
            raise RuntimeError(
                "Application startup aborted — the following required environment "
                "variables are not set or are empty: "
                + ", ".join(missing)
            )

        # --- Optional with defaults ---
        self.vietqr_template = _optional("VIETQR_TEMPLATE", "compact2")
        self.app_env = _optional("APP_ENV", "production")
        self.rate_limit_booking_per_minute = int(
            _optional("RATE_LIMIT_BOOKING_PER_MINUTE", "10")
        )
        self.pending_payment_expiry_minutes = int(
            _optional("PENDING_PAYMENT_EXPIRY_MINUTES", "10")
        )

        # Parse CORS origins
        raw_cors = _optional("CORS_ORIGINS", "")
        parsed: List[str] = [
            origin.strip()
            for origin in raw_cors.split(",")
            if origin.strip()
        ]

        # Security: disallow wildcard in non-development environments
        if self.app_env != "development" and "*" in parsed:
            raise RuntimeError(
                "CORS_ORIGINS must not contain '*' when APP_ENV != 'development'."
            )

        self.cors_origins = parsed


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached after first call)."""
    return Settings()
