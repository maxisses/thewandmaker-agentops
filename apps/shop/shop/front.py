"""shop-front: the shop chat (customer view) and the master's desk (operator view).

The chat talks to the apprentice through OpenShell: "openshell sandbox exec apprentice --
openclaw agent ...". shop-front never talks to the model or the shop tools itself.

/            shop chat
/desk        the master's desk (needs ?key=<desk token> once, then a cookie)
/api/chat    POST {"who": "...", "text": "..."}
/api/desk    GET state, POST /api/desk/requests/<id> {"decision": "approve"|"decline"}
/api/reset   POST, clears reservations, requests and conversations (desk key)
/scroll      the day's scroll: traces from MLflow, refusals from OpenShell's audit log (desk key)
/api/platform  versions and live counters for the deck's architecture picture (counts only, open)
"""
import asyncio
import contextlib
import hmac
import json
import os
import re
import subprocess
import time

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import backstage, campaign, facts, rush, scroll

HERE = os.path.dirname(__file__)
SANDBOX = os.environ.get("APPRENTICE_SANDBOX", "apprentice")
TOOLS_URL = os.environ.get("SHOP_TOOLS_URL", "http://shop-tools:8080")
DESK_TOKEN = os.environ["SHOP_DESK_TOKEN"]
GATEWAY = os.environ.get("OPENSHELL_ENDPOINT", "https://openshell.openshell.svc.cluster.local:8080")
MTLS_DIR = os.environ.get("OPENSHELL_MTLS_DIR", "/etc/openshell-mtls")
TURN_TIMEOUT = int(os.environ.get("TURN_TIMEOUT", "180"))

_epoch = str(int(time.time()))   # part of every session id; a reset starts fresh conversations
_log = []                        # last turns, for the deck and for debugging


def setup_openshell():
    """Register the OpenShell gateway for the CLI, using the client certificate mounted from the cluster."""
    home = os.path.expanduser("~/.config/openshell/gateways/olli/mtls")
    os.makedirs(home, mode=0o700, exist_ok=True)
    for name in ("ca.crt", "tls.crt", "tls.key"):
        with open(os.path.join(MTLS_DIR, name), "rb") as src, open(os.path.join(home, name), "wb") as dst:
            dst.write(src.read())
    os.chmod(os.path.join(home, "tls.key"), 0o600)
    subprocess.run(["openshell", "gateway", "add", GATEWAY, "--local", "--name", "olli"],
                   stdin=subprocess.DEVNULL, capture_output=True)
    subprocess.run(["openshell", "gateway", "select", "olli"], stdin=subprocess.DEVNULL, capture_output=True)


NAMES = {"first-year": "a first-year", "blond-boy": "a blond boy, name not given"}
TOOL_FAIL = re.compile(r"\[tools\] (?:\w+__)?(\S+) failed")
SLOTS = int(os.environ.get("TURNS_PER_APPRENTICE", "4"))
_slots = {}
_talking = {}                    # sandbox -> conversations it is holding right now (the deck's bars)


def parse_turn(stdout: str, stderr: str):
    reply, tools, failed, failures = "", [], [], 0
    start = stdout.find("{")
    if start >= 0:
        try:
            d = json.loads(stdout[start:])
            res = d.get("result", d)          # gateway mode wraps the result
            reply = " ".join(p.get("text") or "" for p in res.get("payloads", [])).strip()
            summary = (res.get("meta") or {}).get("toolSummary") or {}
            tools = [re.sub(r"^\w+__", "", t) for t in summary.get("tools", [])]
            failures = int(summary.get("failures") or 0)
        except ValueError:
            pass
    for line in stderr.splitlines():
        m = TOOL_FAIL.search(line)
        if m:
            failed.append(m.group(1))
    return {"reply": reply, "tools": tools, "failed": failed, "denied": [], "failures": failures}


async def run(cmd, timeout):
    proc = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.DEVNULL,
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise
    return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")


async def ensure_gateway(sandbox):
    """Start OpenClaw's gateway in the sandbox if it is not running (apprentice.sh put the script there)."""
    await run(["openshell", "sandbox", "exec", "-n", sandbox, "--no-tty", "--timeout", "120", "--",
               "sh", "/sandbox/.openclaw/start-gateway.sh"], 130)


async def turn(sandbox, session, message):
    cmd = ["openshell", "sandbox", "exec", "-n", sandbox, "--no-tty", "--timeout", str(TURN_TIMEOUT), "--",
           "openclaw", "agent", "--thinking", "off", "--json", "--session-id", session, "--message", message]
    rc, out, err = await run(cmd, TURN_TIMEOUT + 15)
    if rc != 0 and "{" not in out and re.search(r"gateway|ECONNREFUSED|connect", err, re.I):
        await ensure_gateway(sandbox)
        rc, out, err = await run(cmd, TURN_TIMEOUT + 15)
    return out, err


async def chat(request: Request):
    body = await request.json()
    who = re.sub(r"[^a-z0-9-]", "", str(body.get("who", "customer")).lower())[:32] or "customer"
    text = str(body.get("text", "")).strip()[:1000]
    if not text:
        return JSONResponse({"error": "empty message"}, status_code=400)
    try:
        result = await chat_turn(who, text, body.get("session"))
    except asyncio.TimeoutError:
        return JSONResponse({"error": "the digital apprentice took too long"}, status_code=504)
    return JSONResponse(result)


async def chat_turn(who, text, session=None, sandbox=None, customer=None):
    """One customer line to the apprentice and back: the chat, the red-team campaign and the phones."""
    customer = customer or NAMES.get(who, who.replace("-", " "))
    # The day is part of every conversation's name, also of one the page named itself: "New day" on
    # the desk starts everyone afresh. (Without it the deck's chat page kept one conversation for
    # hours, and the apprentice answered "already reserved" without calling a tool.)
    session = f"{session or who}-{_epoch}"
    session = re.sub(r"[^A-Za-z0-9_.-]", "", session)[:64]
    sandbox = sandbox or SANDBOX
    t0 = time.time()
    slot = _slots.setdefault(sandbox, asyncio.Semaphore(SLOTS))
    async with slot:
        _talking[sandbox] = _talking.get(sandbox, 0) + 1
        try:
            out, err = await turn(sandbox, session, f"[customer: {customer}] {text}")
        finally:
            _talking[sandbox] -= 1
    t1 = time.time()
    result = parse_turn(out, err)
    # What the lock refused comes from OpenShell's own audit log, not from the agent.
    # Several customers can be served at once in one sandbox, so a refusal counts for this turn only
    # if this turn called that tool.
    called = set(result["tools"])
    seen = set()
    for rec in await scroll.audit_recent(sandbox, t0, t1) if called and result["failures"] else []:
        tool = rec.get("tools", "")
        if tool in called and tool not in seen:
            seen.add(tool)
            result["denied"].append({"tool": tool, "reason": "deny rule" if "deny rule" in rec.get("reason", "") else "no rule"})
    result.update({"who": who, "seconds": round(t1 - t0, 1)})
    if not result["reply"]:
        result["reply"] = "(The digital apprentice is lost for words. Try again.)"
    _log.append({"at": time.strftime("%H:%M:%S"), "who": who, "text": text, **result})
    del _log[:-50]
    asyncio.create_task(scroll.tag_turn(sandbox, t0, customer, text, session))
    return result


def desk_ok(request: Request) -> bool:
    return hmac.compare_digest(request.headers.get("x-desk-token", ""), DESK_TOKEN)


async def desk_page(_):
    # The page itself is public. Its data calls need the key, which the page reads from the URL
    # fragment (/desk#key=...) and sends as a header. Fragments never reach the server or its logs,
    # and this works inside the deck's iframe where third-party cookies are blocked.
    return FileResponse(os.path.join(HERE, "static", "desk.html"))


async def desk_state(request: Request):
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{TOOLS_URL}/desk/api/state", headers={"x-desk-token": DESK_TOKEN})
    state = r.json()
    state["turns"] = _log[-20:]
    return JSONResponse(state)


async def desk_decide(request: Request):
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{TOOLS_URL}/desk/api/requests/{request.path_params['rid']}",
                         headers={"x-desk-token": DESK_TOKEN},
                         json={"decision": body.get("decision"), "by": "the wand maker"})
    return JSONResponse(r.json(), status_code=r.status_code)


async def reset(request: Request):
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    await new_day()
    return JSONResponse({"ok": True})


async def new_day():
    """"New day": requests and fittings emptied, and every customer starts a fresh conversation."""
    global _epoch
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(f"{TOOLS_URL}/desk/api/reset", headers={"x-desk-token": DESK_TOKEN})
    _epoch = str(int(time.time()))
    _log.clear()


async def reset_all():
    """Everything back to zero: the desk, the rush, the oracles' counters, the rails' counters.
    Returns what is left afterwards (0 when all is empty)."""
    await new_day()
    rush.reset()
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(MODEL_GW + "/rails/reset?oracle=1")
        rails = (await c.get(MODEL_GW + "/rails/state")).json()
    desk, r = await _desk_state(), await rush.snapshot()
    return (len(desk.get("requests", [])) + len(desk.get("reservations", [])) + r.get("served", 0) + r.get("name", 0)
            + sum(x.get("count", 0) for x in rails.get("rails", [])))


async def backstage_page(_):
    return FileResponse(os.path.join(HERE, "static", "backstage.html"))


async def backstage_api(request: Request):
    """The backstage page: GET the state of the last run; POST {"run": "reset" | "prepare" | "night"}."""
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    if request.method == "POST":
        kind = str((await request.json()).get("run", ""))
        if kind not in ("reset", "prepare", "night"):
            return JSONResponse({"error": "run is one of reset, prepare, night"}, status_code=400)
        if not backstage.start(kind):
            return JSONResponse({"error": "a run is already going"}, status_code=409)
    # The addresses the page links to. Nothing about a cluster is written into the shop's code:
    # install.sh reads them from the cluster it deploys to (config map shop-links).
    links = {"console": os.environ.get("CONSOLE_URL", ""), "deck": os.environ.get("DECK_URL", ""),
             "namespace": os.environ.get("SHOP_NAMESPACE", "ollivanders")}
    return JSONResponse(dict(backstage.snapshot(), links=links), headers={"Cache-Control": "no-store"})


# The hosted deck's door: one password, no user. A match hands out the desk key, which the deck
# then keeps in the browser exactly as it keeps the key from a "#key=" link. The password comes
# from the secret deck-login (gitops/20-shop/install.sh, from DECK_PASSWORD in .env); without it
# the door doesn't exist. The password is short and the key behind it runs Prepare and Reset, so
# wrong guesses are counted: per caller and for everyone together.
DECK_PASSWORD = os.environ.get("DECK_PASSWORD", "")
DECK_ORIGIN = os.environ.get("DECK_URL", "").rstrip("/")
LOGIN_PER_CALLER, LOGIN_FOR_ALL, LOGIN_WINDOW = 5, 30, 60.0
_login_misses: dict[str, list[float]] = {}


def _caller(request: Request) -> str:
    # Behind the router the socket's peer is the router; it appends the real caller last.
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[-1].strip() if fwd else (request.client.host if request.client else "?")


def _login_cors(request: Request) -> dict:
    h = {"Cache-Control": "no-store", "Vary": "Origin"}
    if DECK_ORIGIN and request.headers.get("origin", "") == DECK_ORIGIN:
        h.update({"Access-Control-Allow-Origin": DECK_ORIGIN, "Access-Control-Allow-Methods": "POST, OPTIONS",
                  "Access-Control-Allow-Headers": "content-type", "Access-Control-Max-Age": "600"})
    return h


async def deck_login(request: Request):
    """POST {"password": ...} -> {"key": <desk key>}; 401 on a miss, 429 after too many, 404 when off."""
    cors = _login_cors(request)
    if not DECK_PASSWORD:
        return JSONResponse({"error": "no password is set on this cluster"}, status_code=404, headers=cors)
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=cors)
    now, who = time.time(), _caller(request)
    for k in list(_login_misses):
        _login_misses[k] = [t for t in _login_misses[k] if now - t < LOGIN_WINDOW]
        if not _login_misses[k]:
            del _login_misses[k]
    if (len(_login_misses.get(who, [])) >= LOGIN_PER_CALLER
            or sum(len(v) for v in _login_misses.values()) >= LOGIN_FOR_ALL):
        return JSONResponse({"error": "too many tries, wait a minute"}, status_code=429,
                            headers=dict(cors, **{"Retry-After": str(int(LOGIN_WINDOW))}))
    try:
        given = str((await request.json()).get("password", ""))
    except Exception:
        given = ""
    if not hmac.compare_digest(given.encode(), DECK_PASSWORD.encode()):
        _login_misses.setdefault(who, []).append(now)
        return JSONResponse({"error": "wrong password"}, status_code=401, headers=cors)
    return JSONResponse({"key": DESK_TOKEN}, headers=cors)


async def scroll_page(_):
    # Public page, data needs the desk key (from the URL fragment), like the desk.
    return FileResponse(os.path.join(HERE, "static", "scroll.html"))


async def _desk_state():
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{TOOLS_URL}/desk/api/state", headers={"x-desk-token": DESK_TOKEN})
        return r.json()
    except (httpx.HTTPError, ValueError):
        return {}


async def _desk_requests():
    return (await _desk_state()).get("requests", [])


async def scroll_traces(request: Request):
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        # 1000, not 300: a campaign is 92 turns, and after three busy hours the night's visits had
        # slipped off the end of the list ("while the shop was shut" was empty on 16 November).
        traces = await scroll.list_traces(int(request.query_params.get("limit", "1000")))
    except httpx.HTTPError as e:
        return JSONResponse({"error": f"MLflow: {e}"}, status_code=502)
    desk = await _desk_state()
    return JSONResponse({"traces": traces, "requests": desk.get("requests", []),
                         "dayStarted": desk.get("day_started", 0)})


async def scroll_trace(request: Request):
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        d = await scroll.get_trace(request.path_params["tid"])
    except httpx.HTTPError as e:
        return JSONResponse({"error": f"MLflow: {e}"}, status_code=502)
    s = d.get("summary") or {}
    if s:
        t0, t1 = s["start"] / 1000 - 2, (s["start"] + s["ms"]) / 1000 + 2
        d["requests"] = [r for r in await _desk_requests() if t0 <= r.get("ts", 0) <= t1]
    return JSONResponse(d)


async def scroll_retag(request: Request):
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return JSONResponse({"retagged": await scroll.retag()})


MODEL_GW = os.environ.get("MODEL_GATEWAY_URL", "http://model-gateway:8080")


async def rails_page(_):
    return FileResponse(os.path.join(HERE, "static", "rails.html"))


async def rails_api(request: Request):
    """The rails' counters and last interventions, from the model gateway (desk key)."""
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    path = {"GET": "/rails/state"}.get(request.method, "/rails/" + request.path_params.get("op", "state"))
    async with httpx.AsyncClient(timeout=10) as c:
        if request.method == "GET":
            r = await c.get(MODEL_GW + "/rails/state")
        else:
            r = await c.post(MODEL_GW + path, content=await request.body(), headers={"content-type": "application/json"})
    return JSONResponse(r.json(), status_code=r.status_code)


async def campaign_page(_):
    return FileResponse(os.path.join(HERE, "static", "campaign.html"))


async def campaign_state(request: Request):
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return JSONResponse(await campaign.state(request.query_params.get("release")))


async def campaign_run(request: Request):
    """Start a campaign against one release of the rails; it runs in the background (desk key)."""
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    release = str(body.get("release", "1.5.1"))
    if release not in ("1.5", "1.5.1"):
        return JSONResponse({"error": "unknown release"}, status_code=400)
    if campaign._state["running"]:
        return JSONResponse({"error": "a campaign is already running"}, status_code=409)
    asyncio.create_task(campaign.run(release, chat_turn))
    return JSONResponse({"started": release})


async def phone_page(_):
    return FileResponse(os.path.join(HERE, "static", "phone.html"))


async def phone_hello(request: Request):
    """The phone says hello and learns its wizard's name."""
    body = await request.json()
    return JSONResponse(rush.hello(body.get("phone", "")))


async def phone_ask(request: Request):
    body = await request.json()
    text = str(body.get("text", "")).strip()[:500]
    if not text:
        return JSONResponse({"error": "empty message"}, status_code=400)
    t = rush.ask(str(body.get("phone", "")), text, chat_turn)
    return JSONResponse(rush.ticket(t["id"]))


async def phone_ticket(request: Request):
    t = rush.ticket(request.path_params["tid"])
    return JSONResponse(t) if t else JSONResponse({"error": "no such ticket"}, status_code=404)


CORS = {"Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"}


async def rush_stats(_):
    # Counts only, nothing anyone wrote: open to the deck on any origin.
    d = await rush.snapshot()
    d["pool"] = [{"name": s, "busy": _talking.get(s, 0), "max": SLOTS} for s in rush.POOL]
    return JSONResponse(d, headers=CORS)


async def platform(_):
    # Versions and counters for the architecture picture. Counts only: open to the deck on any origin.
    return JSONResponse(await facts.snapshot(rush.POOL, run), headers=CORS)


async def rush_reset(request: Request):
    if not desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    rush.reset()
    async with httpx.AsyncClient(timeout=10) as c:
        await c.post(MODEL_GW + "/rails/reset?oracle=1")
    return JSONResponse({"ok": True})


async def qr(request: Request):
    """The QR code for the newspaper ad: this shop's /phone page."""
    import io
    import segno
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
    buf = io.BytesIO()
    segno.make(f"https://{host}/phone", error="m").save(buf, kind="svg", scale=10, border=2, dark="#151515")
    return Response(buf.getvalue(), media_type="image/svg+xml", headers=CORS)


async def index(_):
    return FileResponse(os.path.join(HERE, "static", "chat.html"))


async def healthz(_):
    return JSONResponse({"ok": True})


@contextlib.asynccontextmanager
async def lifespan(_):
    task = asyncio.create_task(rush.sampler())
    yield
    task.cancel()


app = Starlette(lifespan=lifespan, routes=[
    Route("/", index),
    Route("/healthz", healthz),
    Route("/desk", desk_page),
    Route("/api/chat", chat, methods=["POST"]),
    Route("/api/desk", desk_state),
    Route("/api/desk/requests/{rid}", desk_decide, methods=["POST"]),
    Route("/api/reset", reset, methods=["POST"]),
    Route("/scroll", scroll_page),
    Route("/api/scroll/traces", scroll_traces),
    Route("/api/scroll/trace/{tid}", scroll_trace),
    Route("/api/scroll/retag", scroll_retag, methods=["POST"]),
    Route("/phone", phone_page),
    Route("/api/phone/hello", phone_hello, methods=["POST"]),
    Route("/api/phone/ask", phone_ask, methods=["POST"]),
    Route("/api/phone/ticket/{tid}", phone_ticket),
    Route("/api/rush", rush_stats),
    Route("/api/platform", platform),
    Route("/api/rush/reset", rush_reset, methods=["POST"]),
    Route("/qr.svg", qr),
    Route("/campaign", campaign_page),
    Route("/api/campaign", campaign_state),
    Route("/api/campaign/run", campaign_run, methods=["POST"]),
    Route("/rails", rails_page),
    Route("/api/rails", rails_api),
    Route("/api/rails/{op}", rails_api, methods=["POST"]),
    Route("/backstage", backstage_page),
    Route("/api/backstage", backstage_api, methods=["GET", "POST"]),
    Route("/api/deck-login", deck_login, methods=["POST", "OPTIONS"]),
    Mount("/static", app=StaticFiles(directory=os.path.join(HERE, "static"))),
])

backstage.deps.update(chat_turn=chat_turn, run=run, reset_all=reset_all, model_gw=MODEL_GW)

if __name__ == "__main__":
    setup_openshell()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), proxy_headers=True)
