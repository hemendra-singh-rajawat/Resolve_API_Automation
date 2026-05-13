from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import requests

from framework.config import EnvConfig, Secrets
from framework.logger import get_logger

log = get_logger(__name__)


@dataclass
class Token:
    access_token: str
    token_type: str = "Bearer"
    expires_at: float = 0.0  # epoch seconds
    refresh_token: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        # 30-second skew so we refresh just before the token actually dies.
        return time.time() >= (self.expires_at - 30)

    @property
    def header_value(self) -> str:
        return f"{self.token_type} {self.access_token}"


class TokenStore:
    """In-process token cache. Survives across tests within a single pytest session.

    Two modes selected by env var ``AUTH_MODE``:
      * ``oauth`` (default) — OAuth2 password grant against ``env.auth_url``.
      * ``jwt_static`` — mint a local HS256 JWT signed with ``JWT_SECRET``,
        matching the contract billing-rcm-service expects in development.
    """

    def __init__(self, env: EnvConfig, secrets: Secrets) -> None:
        self._env = env
        self._secrets = secrets
        self._token: Optional[Token] = None
        self._mode = os.getenv("AUTH_MODE", "oauth").lower()

    def get(self) -> Token:
        if self._token is None or self._token.is_expired:
            if self._mode == "jwt_static":
                log.info("Minting HS256 JWT (mode=jwt_static)")
                self._token = self._mint_local_jwt()
            else:
                log.info("Token missing/expired — fetching new one from {}", self._env.auth_url)
                self._token = self._fetch()
        return self._token

    def invalidate(self) -> None:
        self._token = None

    def _mint_local_jwt(self) -> Token:
        from jose import jwt  # local import keeps OAuth-only setups dependency-free

        secret = os.getenv("JWT_SECRET")
        if not secret:
            raise RuntimeError("AUTH_MODE=jwt_static requires JWT_SECRET in .env")
        ttl = int(os.getenv("JWT_TTL_SECONDS", "86400"))
        now = int(time.time())
        claims = {
            "sub": os.getenv("JWT_USER_ID", "00000000000000000000000000000000"),
            "user_id": os.getenv("JWT_USER_ID", "00000000000000000000000000000000"),
            "tenant_id": os.getenv("JWT_TENANT_ID", "00000000000000000000000000000000"),
            "email": os.getenv("JWT_EMAIL", "test@example.com"),
            "roles": ["billing_admin"],
            "permissions": [],
            "platform_role": "platform_admin",  # bypasses every require_permission check
            "iat": now,
            "exp": now + ttl,
        }
        return Token(
            access_token=jwt.encode(claims, secret, algorithm="HS256"),
            expires_at=now + ttl,
        )

    def _fetch(self) -> Token:
        if not (self._secrets.username and self._secrets.password):
            raise RuntimeError(
                "RCM_USERNAME / RCM_PASSWORD must be set in .env to obtain a token"
            )

        payload = {
            "grant_type": "password",
            "username": self._secrets.username,
            "password": self._secrets.password,
        }
        if self._secrets.client_id:
            payload["client_id"] = self._secrets.client_id
        if self._secrets.client_secret:
            payload["client_secret"] = self._secrets.client_secret

        resp = requests.post(
            self._env.auth_url,
            data=payload,
            timeout=self._env.timeout_s,
            verify=self._env.verify_ssl,
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Auth failed [{resp.status_code}]: {resp.text[:300]}"
            )
        data = resp.json()
        return Token(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=time.time() + int(data.get("expires_in", 3600)),
            refresh_token=data.get("refresh_token"),
        )
