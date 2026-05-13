from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from framework.config import Secrets, get_secrets
from framework.logger import get_logger

log = get_logger(__name__)

_engine: Optional[Engine] = None


def _build_url(s: Secrets) -> str:
    missing = [k for k in ("db_host", "db_name", "db_user", "db_password") if not getattr(s, k)]
    if missing:
        raise RuntimeError(
            f"DB connection requires {missing} in .env (or skip db-marked tests)"
        )
    port = f":{s.db_port}" if s.db_port else ""
    return f"{s.db_dialect}://{s.db_user}:{s.db_password}@{s.db_host}{port}/{s.db_name}"


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        s = get_secrets()
        url = _build_url(s)
        log.info("Creating DB engine for {}", url.split("@")[-1])
        _engine = create_engine(url, pool_pre_ping=True, future=True)
    return _engine


@contextmanager
def db_session() -> Iterator[Any]:
    eng = get_engine()
    with eng.connect() as conn:
        yield conn


def query_one(sql: str, **params: Any) -> Optional[dict[str, Any]]:
    """Run a parameterised SELECT, return first row as dict or None."""
    with db_session() as conn:
        row = conn.execute(text(sql), params).mappings().first()
        return dict(row) if row else None


def query_all(sql: str, **params: Any) -> list[dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]


def count(table: str, **where: Any) -> int:
    clauses = " AND ".join(f"{k} = :{k}" for k in where) or "1=1"
    sql = f"SELECT COUNT(*) AS c FROM {table} WHERE {clauses}"
    row = query_one(sql, **where)
    return int(row["c"]) if row else 0
