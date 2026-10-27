"""FastAPI app. HTMX swaps server-rendered partials; there is no client-side framework."""
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from . import agent, audit, config, guard, llm, seed, service

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))


def cite(text: str) -> Markup:
    def link(i):
        href = "/memory" if i.startswith("NOTE") else f"/audit?q={i}"
        return f'<a class="cite" href="{href}">{i}</a>'

    def group(m):
        return " ".join(link(i) for i in re.findall(guard._ID, m.group(1)))
    return Markup(guard.CITE_GROUP.sub(group, str(escape(text))))


templates.env.filters["cite"] = cite


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed.ensure()
    yield


app = FastAPI(title="CareFlow Memory", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


def who(request: Request) -> tuple[str, str]:
    role = request.cookies.get("role", "Coordinator")
    role = role if role in config.ROLES else "Coordinator"
    return role, f"{config.ROLES[role]} ({role})"


def render(request: Request, name: str, **ctx):
    role, actor = who(request)
    base = {"role": role, "roles": list(config.ROLES), "mode": llm.mode(), "today": service.today(), "actor": actor}
    return templates.TemplateResponse(request, name, {**base, **ctx})


@app.get("/healthz")
def healthz():
    return {"ok": True, "mode": llm.mode()}


@app.post("/role")
def set_role(request: Request, role: str = Form(...)):
    r = RedirectResponse(request.headers.get("referer", "/"), status_code=303)
    r.set_cookie("role", role if role in config.ROLES else "Coordinator", samesite="lax")
    return r


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, f: str = "all"):
    items = service.all_items()
    flt = {"overdue": lambda i: i["overdue"], "stuck": lambda i: i["stuck"],
           "referrals": lambda i: i["kind"] == "referral", "reports": lambda i: i["kind"] == "report"}.get(f)
    open_ = [i for i in items if not i["closed"] and (flt is None or flt(i))]
    closed = [i for i in items if i["closed"]]
    return render(request, "dashboard.html", page="today", c=service.counts(items), open_=open_, closed=closed, f=f)


@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    return render(request, "chat.html", page="chat")


@app.post("/chat", response_class=HTMLResponse)
def chat_send(request: Request, message: str = Form("")):
    _, actor = who(request)
    return render(request, "_turn.html", user=message.strip()[:500], r=agent.handle(message, actor))


@app.post("/proposals/{pid}/confirm", response_class=HTMLResponse)
def proposal_confirm(request: Request, pid: str):
    _, actor = who(request)
    return render(request, "_proposal_done.html", done=service.confirm(pid, actor), cancelled=False)


@app.post("/proposals/{pid}/cancel", response_class=HTMLResponse)
def proposal_cancel(request: Request, pid: str):
    _, actor = who(request)
    service.cancel(pid, actor)
    return render(request, "_proposal_done.html", done=None, cancelled=True)


@app.get("/handover", response_class=HTMLResponse)
def handover_page(request: Request, id: int | None = None):
    hs = service.db.q("SELECT id, ts, author, signed FROM handovers ORDER BY id DESC LIMIT 8")
    return render(request, "handover.html", page="handover", h=service.get_handover(id), history=hs)


@app.post("/handover/generate")
def handover_generate(request: Request):
    _, actor = who(request)
    return RedirectResponse(f"/handover?id={service.build_handover(actor)}", status_code=303)


@app.post("/handover/{hid}/sign")
def handover_sign(request: Request, hid: int, narrative: str = Form("")):
    _, actor = who(request)
    service.sign_handover(hid, narrative, actor)
    return RedirectResponse(f"/handover?id={hid}", status_code=303)


@app.get("/handover/{hid}/export.md")
def handover_export(hid: int):
    h = service.get_handover(hid)
    return PlainTextResponse(service.handover_markdown(h) if h else "Not found", media_type="text/markdown")


@app.get("/memory", response_class=HTMLResponse)
def memory_page(request: Request):
    return render(request, "memory.html", page="memory", notes=service.notes())


@app.post("/memory/{nid}/edit")
def memory_edit(request: Request, nid: int, text: str = Form("")):
    service.update_note(nid, text, who(request)[1])
    return RedirectResponse("/memory", status_code=303)


@app.post("/memory/{nid}/delete")
def memory_delete(request: Request, nid: int):
    service.delete_note(nid, who(request)[1])
    return RedirectResponse("/memory", status_code=303)


@app.get("/audit", response_class=HTMLResponse)
def audit_page(request: Request, q: str = ""):
    return render(request, "audit.html", page="audit", rows=audit.search(q), q=q, v=None)


@app.post("/audit/verify", response_class=HTMLResponse)
def audit_verify(request: Request):
    return render(request, "_verify.html", v=audit.verify())


@app.post("/audit/tamper", response_class=HTMLResponse)
def audit_tamper(request: Request):
    """Demo only: edits a past entry directly in the database so the integrity check has something to catch."""
    role, _ = who(request)
    if role != "Admin":
        return HTMLResponse('<p class="msg err">Switch to the Admin role to run the tamper demo.</p>', status_code=403)
    row = service.db.one("SELECT seq FROM audit WHERE action='update_status' ORDER BY seq LIMIT 1")
    if row:
        service.db.x("UPDATE audit SET after='Cancelled' WHERE seq=?", (row["seq"],))
    return render(request, "_verify.html", v=audit.verify())


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    routes = [(t, tier, config.MODELS[tier]) for t, tier in llm.ROUTES.items()]
    return render(request, "settings.html", page="settings", routes=routes, calls=llm.recent(), stats=llm.stats(), base_url=config.BASE_URL, bench=None)


@app.post("/settings/benchmark", response_class=HTMLResponse)
def settings_bench(request: Request):
    return render(request, "_bench.html", bench=service.benchmark(), mode=llm.mode())


@app.post("/admin/reset")
def admin_reset(request: Request):
    role, _ = who(request)
    if role == "Admin":
        seed.reset()
    return RedirectResponse("/", status_code=303)
