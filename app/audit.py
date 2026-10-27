"""Append-only, hash-chained audit log. Each entry stores SHA-256(prev_hash + its own contents)."""
import hashlib
import json
from datetime import datetime, timezone

from . import db

GENESIS = "0" * 64


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _digest(prev: str, ts, actor, action, target, before, after, ai) -> str:
    body = json.dumps([ts, actor, action, target, before, after, int(ai)], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((prev + body).encode()).hexdigest()


def log(actor: str, action: str, target: str = "", before: str = "", after: str = "", ai: bool = False) -> int:
    ts = now()
    with db.LOCK:
        last = db.one("SELECT hash FROM audit ORDER BY seq DESC LIMIT 1")
        prev = last["hash"] if last else GENESIS
        h = _digest(prev, ts, actor, action, target, before, after, ai)
        return db.x(
            "INSERT INTO audit(ts,actor,action,target,before,after,ai,prev_hash,hash) VALUES (?,?,?,?,?,?,?,?,?)",
            (ts, actor, action, target, before, after, int(ai), prev, h),
        )


def verify() -> dict:
    """Recompute the whole chain and report the first broken link."""
    prev, checked = GENESIS, 0
    for r in db.q("SELECT * FROM audit ORDER BY seq"):
        expected = _digest(prev, r["ts"], r["actor"], r["action"], r["target"], r["before"], r["after"], r["ai"])
        if r["prev_hash"] != prev or r["hash"] != expected:
            return {"ok": False, "checked": checked, "broken_seq": r["seq"]}
        prev, checked = r["hash"], checked + 1
    return {"ok": True, "checked": checked, "broken_seq": None}


def search(term: str = "", limit: int = 200) -> list[dict]:
    if not term.strip():
        return db.q("SELECT * FROM audit ORDER BY seq DESC LIMIT ?", (limit,))
    like = f"%{term.strip()}%"
    return db.q(
        "SELECT * FROM audit WHERE actor LIKE ? OR action LIKE ? OR target LIKE ? OR before LIKE ? OR after LIKE ? "
        "ORDER BY seq DESC LIMIT ?",
        (like, like, like, like, like, limit),
    )
