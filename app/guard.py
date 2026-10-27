"""Guardrails: scope check, PII masking, output validation. Every model call passes through these."""
import re

from . import db

REFUSAL = (
    "I can help with tasks, referrals, follow-ups, reports and handovers. I can't give clinical advice, "
    "diagnoses or treatment guidance. Please ask the treating clinician."
)

CLINICAL = re.compile(
    r"\b(diagnos(e|is|ing)|prognosis|prescri(be|ption)|dosage|dose|doses|overdose)\b"
    r"|\b\d+\s?(mg|mcg|ml|iu)\b"
    r"|\b(what|which) (drug|medicine|medication|treatment|therapy|antibiotic)s?\b"
    r"|\bshould (he|she|they|i|we|the patient) (take|stop|start|skip|be given|get|use)\b"
    r"|\bcan (he|she|they|i) (take|stop|skip|mix)\b"
    r"|\b(symptoms?|side effects?|chest pain|fever|rash|infection|cancer|tumou?r|blood pressure)\b.*\b(mean|cause|indicate|serious|safe|treat|cure)\b"
    r"|what('?s| is) wrong with|\btriage\b|\bis (it|this|that)\b.*\b(safe|serious|dangerous|cancer|tumou?r)\b|\bhow (do|can|should|would) (i|we) (treat|cure)\b",
    re.I,
)
BANNED_OUT = re.compile(
    r"\b(you should (take|stop|start)|i (recommend|advise|suggest) (taking|stopping|starting)|"
    r"(recommended|safe|suggested) dos(e|age)|the diagnosis is|likely (has|suffers from)|\d+\s?(mg|mcg)\b)",
    re.I,
)
ID_RE = re.compile(r"\b(?:TSK|REF|FUP|RPT)-\d{3}\b")
_ID = r"(?:TSK|REF|FUP|RPT|NOTE|AUD)-\d+"
CITE_RE = re.compile(rf"\[({_ID})\]")  # single-ID form, used for link rendering
CITE_GROUP = re.compile(rf"\[({_ID}(?:\s*[,;]\s*{_ID})*)\]")  # also matches [REF-001, REF-003]


class PIILeak(Exception):
    """Raised if a raw patient name is about to leave the process."""


def _pairs() -> list[tuple[str, str]]:
    pairs = []
    for p in db.q("SELECT id,name FROM patients"):
        pairs.append((p["name"], p["id"]))
        pairs += [(part, p["id"]) for part in p["name"].split() if len(part) >= 3]
    return sorted(pairs, key=lambda x: -len(x[0]))


def mask(text: str) -> str:
    """Replace patient names (full or partial) with tokens such as PATIENT_007."""
    for name, pid in _pairs():
        text = re.sub(rf"\b{re.escape(name)}\b", pid, text, flags=re.I)
    return text


def unmask(text: str) -> str:
    names = {p["id"]: p["name"] for p in db.q("SELECT id,name FROM patients")}
    return re.sub(r"PATIENT_\d{3}", lambda m: names.get(m.group(0), m.group(0)), text)


def assert_no_names(text: str) -> None:
    for name, _ in _pairs():
        if re.search(rf"\b{re.escape(name)}\b", text, flags=re.I):
            raise PIILeak("raw patient name found in outbound model payload")


def scope_guard(text: str) -> tuple[bool, str]:
    """Rules first (free, deterministic). When a live model is available, Nemotron Nano double-checks."""
    if CLINICAL.search(text):
        return False, "rule"
    from . import llm  # local import avoids a cycle

    if llm.mode() == "live":
        res = llm.complete(
            "scope",
            'Classify the request as "admin" (tasks, referrals, follow-ups, reports, appointments, handovers, notes, '
            'audit) or "clinical" (diagnosis, treatment, medication, dosage, symptoms, triage). '
            'Reply with JSON only: {"label":"admin"} or {"label":"clinical"}.',
            mask(text),
            json_mode=True,
            max_tokens=20,
        )
        if res.text and "clinical" in res.text.lower():
            return False, "nano"
    return True, "ok"


def validate_output(text: str, valid_ids: set[str], require_cite: bool) -> tuple[bool, str]:
    """Reject clinical-sounding output and any citation that does not exist in the retrieved records."""
    if BANNED_OUT.search(text):
        return False, "clinical phrasing"
    cited = {i for g in CITE_GROUP.findall(text) for i in re.findall(_ID, g)}
    unknown = cited - valid_ids
    if unknown:
        return False, f"unknown record IDs: {', '.join(sorted(unknown))}"
    if require_cite and not cited:
        return False, "no citations"
    return True, "ok"
