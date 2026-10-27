"""LLM client for Nebius Token Factory. Routes by task to Nemotron Nano / Super / Ultra, falls back on failure,
and records model, tokens and latency for every call. With no API key it runs in offline mode."""
import time
from dataclasses import dataclass

from . import audit, config, db, guard

ROUTES = {"scope": "nano", "extract": "nano", "chat": "super", "handover": "ultra", "audit_explain": "ultra"}
FALLBACK = {"ultra": "super", "super": "nano", "nano": None}


@dataclass
class Result:
    text: str | None
    model: str
    tier: str
    tok_in: int = 0
    tok_out: int = 0
    latency_ms: int = 0
    offline: bool = False
    fell_back: bool = False

    @property
    def label(self) -> str:
        if self.offline:
            return "Offline rules, no model call"
        if self.text is None:
            return "Model unavailable, grounded fallback"
        s = f"{self.tier.title()} · {self.model} · {self.tok_in + self.tok_out} tokens · {self.latency_ms / 1000:.1f}s"
        return s + (" · fell back" if self.fell_back else "")


def mode() -> str:
    return "live" if config.API_KEY else "offline"


def _client():
    from openai import OpenAI

    return OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)


def _record(task, tier, model, tin, tout, ms, ok):
    db.x(
        "INSERT INTO llm_calls(ts,task,tier,model,tok_in,tok_out,latency_ms,ok) VALUES (?,?,?,?,?,?,?,?)",
        (audit.now(), task, tier, model, tin, tout, ms, int(ok)),
    )


def complete(task: str, system: str, user: str, *, tier: str | None = None, json_mode=False, max_tokens=700) -> Result:
    tier = tier or ROUTES[task]
    if mode() == "offline":
        return Result(None, "offline-rules", tier, offline=True)
    guard.assert_no_names(system + "\n" + user)  # last line of defence before data leaves the process
    t, fell = tier, False
    while t:
        model, t0 = config.MODELS[t], time.perf_counter()
        try:
            kw = {"response_format": {"type": "json_object"}} if json_mode else {}
            r = _client().chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=0.2,
                timeout=config.TIMEOUT[t],
                **kw,
            )
            ms = int((time.perf_counter() - t0) * 1000)
            u = getattr(r, "usage", None)
            tin, tout = getattr(u, "prompt_tokens", 0) or 0, getattr(u, "completion_tokens", 0) or 0
            _record(task, t, model, tin, tout, ms, True)
            return Result(r.choices[0].message.content or "", model, t, tin, tout, ms, fell_back=fell)
        except Exception:
            _record(task, t, model, 0, 0, int((time.perf_counter() - t0) * 1000), False)
            t, fell = FALLBACK[t], True
    return Result(None, "unavailable", tier, fell_back=True)


def recent(n: int = 12) -> list[dict]:
    return db.q("SELECT * FROM llm_calls ORDER BY id DESC LIMIT ?", (n,))


def stats() -> list[dict]:
    return db.q(
        "SELECT tier, model, COUNT(*) calls, CAST(AVG(latency_ms) AS INT) avg_ms, SUM(tok_in+tok_out) tokens "
        "FROM llm_calls WHERE ok=1 GROUP BY tier, model ORDER BY tier"
    )
