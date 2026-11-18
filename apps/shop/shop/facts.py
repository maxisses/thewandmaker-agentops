"""What the running platform says about itself, for the architecture picture in the deck.

GET /api/platform returns two things:

  facts  fixed at install time: versions and names. "make up-facts" reads them from the cluster
         and writes them into the config map platform-facts, which shop-front gets as the
         environment variable PLATFORM_FACTS.
  live   counters this shop has anyway: turns and refusals since the day started (MLflow), model
         calls and 429s (model gateway), what the rails caught, requests on the desk, the newest
         red-team campaign, and how many apprentices OpenShell reports as ready.

Counts and versions only, nothing anybody wrote, so the deck may read it from any origin. A part
that can't be read is left out; the deck then keeps the label it has in the scripted version.
"""
import asyncio
import json
import os
import time

import httpx

from . import campaign, scroll

MODEL_GW = os.environ.get("MODEL_GATEWAY_URL", "http://model-gateway:8080")
TOOLS_URL = os.environ.get("SHOP_TOOLS_URL", "http://shop-tools:8080")
DESK_TOKEN = os.environ.get("SHOP_DESK_TOKEN", "")

try:
    FACTS = json.loads(os.environ.get("PLATFORM_FACTS") or "{}")
except ValueError:
    FACTS = {}

_cache = {"at": 0.0, "data": None}
_asked = {"mlflow": False}
_boxes = {"at": 0.0, "n": None}


async def _desk():
    async with httpx.AsyncClient(timeout=8) as c:
        return (await c.get(f"{TOOLS_URL}/desk/api/state", headers={"x-desk-token": DESK_TOKEN})).json()


async def _turns(day_started):
    """Turns and refused turns since the master pressed "New day"."""
    traces = [t for t in await scroll.list_traces(200) if t["start"] / 1000 >= day_started]
    return {"turnsToday": len(traces), "tracesToday": len(traces),
            "refusedToday": sum(1 for t in traces if t["status"] == "denied")}


async def _gateway():
    async with httpx.AsyncClient(timeout=5) as c:
        d = (await c.get(MODEL_GW + "/rails/state")).json()
    o = d.get("oracle", {})
    b = (d.get("oracles") or {}).get("backup") or {}
    s = (d.get("oracles") or {}).get("spare") or {}
    out = {"modelCalls": o.get("calls", 0) + o.get("backup_calls", 0), "throttled": o.get("throttled", 0),
           # the backup oracle (OpenRouter): calls since the last reset, and who answered last
           "backupCalls": o.get("backup_calls", 0), "lastOracle": o.get("last", ""), "oracleMode": o.get("mode", ""),
           "backupModel": str(b.get("model", "")).split("/")[-1],
           # the second backup (another Red Hat endpoint): the calls of backupCalls that went there
           "spareCalls": o.get("spare_calls", 0), "spareName": s.get("name", ""),
           "spareModel": str(s.get("model", "")).split("/")[-1]}
    if d.get("enabled"):
        out["rails"] = {"release": str(d.get("config", "")).replace("release-", "").replace("-", "."),
                        "steppedIn": sum(r.get("count", 0) for r in d.get("rails", []))}
    return out


async def _campaign(release):
    runs = (await campaign.state()).get("runs", {})
    r = runs.get(release) or runs.get("1.5.1") or runs.get("1.5")
    if not r or not r.get("rules"):
        return {}
    return {"campaign": {"release": r.get("release", ""),
                         "attacks": sum(v["total"] for v in r["rules"].values()),
                         "held": sum(v["held"] for v in r["rules"].values())}}


async def _sandboxes(pool, run):
    """How many of our apprentices OpenShell lists as ready. Asked every 20 seconds at most."""
    now = time.time()
    if now - _boxes["at"] > 20:
        _boxes["at"] = now
        try:
            rc, out, _ = await run(["openshell", "sandbox", "list"], 15)
            lines = [l for l in out.splitlines() if l.strip()] if rc == 0 else []
            ready = 0
            for name in pool:
                row = next((l for l in lines if name in l.split()), "")
                if row and not any(w in row.lower() for w in ("error", "failed", "pending", "provisioning", "deleting")):
                    ready += 1
            _boxes["n"] = ready if lines else None
        except Exception:
            _boxes["n"] = None
    return {"sandboxes": _boxes["n"]} if _boxes["n"] is not None else {}


async def _mlflow_version():
    """MLflow says its own version; asked once."""
    if _asked["mlflow"] or FACTS.get("mlflow"):
        return
    try:
        async with scroll._client() as c:
            r = await c.get(scroll.MLFLOW_URL + "/version")
        if r.status_code == 200 and len(r.text) < 20:
            FACTS["mlflow"] = ".".join(r.text.strip().split(".")[:2])
            _asked["mlflow"] = True
    except httpx.HTTPError:
        pass


async def snapshot(pool, run):
    now = time.time()
    if _cache["data"] is not None and now - _cache["at"] < 4:
        return _cache["data"]
    await _mlflow_version()
    live = {}
    try:
        desk = await _desk()
    except (httpx.HTTPError, ValueError):
        desk = {}
    day = desk.get("day_started", 0)
    reqs = [r for r in desk.get("requests", []) if r.get("ts", 0) >= day]
    if desk:
        live["requests"] = {"filed": len(reqs), "declined": sum(1 for r in reqs if r.get("status") == "declined")}
    if desk.get("tools"):
        live["tools"] = desk["tools"]
    parts = await asyncio.gather(_turns(day), _gateway(), _sandboxes(pool, run), return_exceptions=True)
    for p in parts:
        if isinstance(p, dict):
            live.update(p)
    try:
        live.update(await _campaign((live.get("rails") or {}).get("release", "")))
    except Exception:
        pass
    _cache.update(at=now, data={"facts": FACTS, "live": live, "at": int(now)})
    return _cache["data"]
