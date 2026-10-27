"""Thin SQLite helpers. One short-lived connection per call keeps the demo simple and thread-safe."""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from . import config

LOCK = threading.RLock()
path = config.DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients(id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS items(
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, patient_id TEXT NOT NULL, dept TEXT NOT NULL,
  title TEXT NOT NULL, status TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 2,
  due TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id TEXT NOT NULL, text TEXT NOT NULL,
  author TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  target TEXT NOT NULL, before TEXT NOT NULL, after TEXT NOT NULL, ai INTEGER NOT NULL,
  prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS handovers(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, author TEXT NOT NULL, body TEXT NOT NULL,
  snapshot TEXT NOT NULL, signed INTEGER NOT NULL DEFAULT 0, model TEXT NOT NULL DEFAULT '',
  latency_ms INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS proposals(
  id TEXT PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL, payload TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS llm_calls(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, task TEXT NOT NULL, tier TEXT NOT NULL,
  model TEXT NOT NULL, tok_in INTEGER, tok_out INTEGER, latency_ms INTEGER, ok INTEGER NOT NULL);
"""


def conn() -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path, timeout=10)
    c.row_factory = sqlite3.Row
    return c


@contextmanager
def tx():
    c = conn()
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with LOCK, tx() as c:
        c.executescript(SCHEMA)


def q(sql: str, args=()) -> list[dict]:
    with tx() as c:
        return [dict(r) for r in c.execute(sql, args)]


def one(sql: str, args=()) -> dict | None:
    rows = q(sql, args)
    return rows[0] if rows else None


def x(sql: str, args=()) -> int:
    with LOCK, tx() as c:
        return c.execute(sql, args).lastrowid
