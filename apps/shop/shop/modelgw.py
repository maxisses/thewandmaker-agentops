"""model-gateway: the model path between OpenShell's inference route and Red Hat MaaS.

Every chat request from the apprentice comes through here. Three things happen:

1. Qwen's thinking phase is switched off (chat_template_kwargs.enable_thinking = false): one model
   call takes ~2 s instead of ~14 s on our MaaS model.
2. Input rails: a new customer line is checked by NeMo Guardrails before the model sees it. If the
   rails block it, the apprentice gets the rails' answer instead and the model is never called.
3. Output rails: an answer to the customer (text, no tool call) is checked before it leaves. The
   rails may change it (the name becomes You-Know-Who, German becomes English).

Tool calls pass through untouched. The gateway holds no key: the OpenShell gateway sends the MaaS
key in the Authorization header and we pass it on. /raw/v1 is the same path without rails, for
the rails' own model calls.

4. The oracle's limit. Red Hat MaaS allows 400,000 tokens a minute. The gateway keeps count and
   lets calls wait their turn instead of running into the limit; see "the rented oracle's limit"
   below.
5. The backup oracle. When MaaS is locked or the minute's budget is used up, a call does not wait:
   it goes to a second, paid oracle (OpenRouter, one model pinned to one provider), with its own
   key and a hard cap in US dollars; see "the backup oracle" below.
6. The second backup. When the backup can't take a call either (it failed, rests or reached its
   cap), a third oracle takes it: a second model endpoint from Red Hat, with its own key and no
   cap; see "the second backup" below.

/rails/state   counters and the last interventions      /rails/reset   counters to zero
/rails/config  GET or POST {"config": "release-1-5"}    which release of the rails is live
/oracle        GET the three oracles' calls, tokens and dollars;
               POST {"mode": "overflow" | "lock" | "backup-first" | "maas" | "backup" | "spare"}
"""
import asyncio
import contextlib
import json
import os
import re
import time
from collections import deque

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

# The model's name at the upstream (MaaS), and what every call to it carries on top. Callers use
# their own names for the model (the apprentice says "oracle", the rails still say the old model's
# name), so a call that goes to MaaS always gets the upstream's name. MODEL_EXTRA is JSON: the
# model of 17 November, gpt-oss-120b, always reasons, and {"reasoning_effort": "low"} keeps that
# short (measured: an answer in 1.5 s and 32 tokens instead of 300 tokens of thought and no answer).
MAAS_MODEL = os.environ.get("MODEL_NAME") or os.environ.get("RAILS_MODEL", "qwen38-27b")
try:
    MODEL_EXTRA = json.loads(os.environ.get("MODEL_EXTRA", "") or "{}")
except ValueError:
    MODEL_EXTRA = {}
UPSTREAM = os.environ["MODEL_UPSTREAM"].rstrip("/")          # e.g. https://maas.example/v1
THINKING = os.environ.get("MODEL_THINKING", "false").lower() == "true"
RAILS_URL = os.environ.get("RAILS_URL", "").rstrip("/")      # e.g. http://rails.ollivanders.svc
STATE = {"config": os.environ.get("RAILS_CONFIG", "release-1-5-1"), "enabled": bool(RAILS_URL)}
client = httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10))
PASS = ("authorization", "content-type", "accept")

RAILS = {"en": "Answers in English", "topic": "Wands, wandlore and the shop only", "name": "The name is never written"}
counters = {k: 0 for k in RAILS}
# The rented oracle (MaaS): calls sent, 429s received, calls waiting for their turn right now,
# calls that had to wait at all, and until when the oracle is locked after a 429.
# backup_calls: calls the two backups took since the last reset (the deck's counter); spare_calls:
# those of them that went to the second backup.
oracle = {"calls": 0, "throttled": 0, "last_429": 0.0, "limit_headers": {}, "waiting": 0, "paced": 0,
          "blocked_until": 0.0, "backup_calls": 0, "spare_calls": 0}
events = deque(maxlen=40)
ACTION_RAIL = {"ensure_english": "en", "hide_name": "name", "hide_name_spelled": "name", "self_check_input": "topic"}


def _headers(request: Request):
    return {k: v for k, v in request.headers.items() if k.lower() in PASS}


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def _note(rail, before, after, where):
    counters[rail] += 1
    events.appendleft({"at": time.time(), "rail": rail, "where": where,
                       "before": before[-300:], "after": after[:300], "config": STATE["config"]})


async def rails(kind, messages, auth=""):
    """Run only the input or only the output rails of the live release. Returns (text, log).

    The rails server passes the caller's Authorization header on to the model for its own checks
    (the topic check asks the model), so we forward the key OpenShell gave us.
    """
    body = {"model": os.environ.get("RAILS_MODEL", "qwen38-27b"), "messages": messages,
            "guardrails": {"config_id": STATE["config"], "options": {
                "rails": {"input": kind == "input", "output": kind == "output", "dialog": False, "retrieval": False},
                "log": {"activated_rails": True}}}}
    r = await client.post(f"{RAILS_URL}/v1/chat/completions", json=body, timeout=90,
                          headers={"Authorization": auth} if auth else None)
    r.raise_for_status()
    d = r.json()
    text = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return text, ((d.get("guardrails") or {}).get("log") or {}).get("activated_rails") or []


def _sse(model, content=None, tool_calls=None, finish="stop", usage=None):
    """An OpenAI-style stream with the whole answer in one chunk."""
    cid, now = f"chatcmpl-rails-{int(time.time() * 1000)}", int(time.time())
    delta = {"role": "assistant", "content": content}
    if tool_calls:
        delta["tool_calls"] = [{"index": i, "id": tc.get("id"), "type": "function",
                                "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments", "")}}
                               for i, tc in enumerate(tool_calls)]
    chunks = [{"id": cid, "object": "chat.completion.chunk", "created": now, "model": model,
               "choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
              {"id": cid, "object": "chat.completion.chunk", "created": now, "model": model,
               "choices": [{"index": 0, "delta": {}, "finish_reason": finish}]}]
    if usage:
        chunks.append({"id": cid, "object": "chat.completion.chunk", "created": now, "model": model,
                       "choices": [], "usage": usage})
    body = "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"
    return Response(body, media_type="text/event-stream")


def _json(model, content, usage=None):
    return JSONResponse({"id": f"chatcmpl-rails-{int(time.time() * 1000)}", "object": "chat.completion",
                         "created": int(time.time()), "model": model,
                         "choices": [{"index": 0, "finish_reason": "stop",
                                      "message": {"role": "assistant", "content": content}}],
                         "usage": usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})


KEEP = ("content-type", "cache-control", "retry-after")   # retry-after: the caller should know how long to wait

# ---------- the rented oracle's limit ----------
# Red Hat MaaS allows 400,000 tokens a minute for our key. Go over it and it answers 429 with
# "retry-after: 60", and every further request inside those 60 seconds starts the minute again
# (measured on 15 November: the "resets at" time in the answer moves with every request). A few
# impatient callers keep the lock shut for good; a campaign sat behind it for twenty minutes.
# So the gateway keeps count itself. A call waits here until the last minute's tokens leave room
# for it, and when a 429 does come back, everything waits until the lock has opened, and then
# the call is sent again. Callers see a slow answer, not an error.
BUDGET = int(os.environ.get("ORACLE_TOKENS_PER_MINUTE", "340000"))   # below MaaS's 400,000 on purpose
TRIES = 3
_spent = deque()            # [time, tokens] of every call in the last minute


def _estimate(body: bytes) -> int:
    """Tokens a request will cost, guessed from its size; replaced by the real number afterwards."""
    return int(len(body) / 3.6) + 300


async def _turn(estimate: int, backup: bool = True):
    """Wait until the oracle will take another call of this size. Returns the call's ledger entry,
    or None: MaaS is locked or full, and the backup oracle takes this call instead of waiting."""
    if backup and MODE["oracle"] in ("backup", "spare"):
        return None
    if backup and MODE["oracle"] == "backup-first" and _any_backup(estimate):
        return None
    waited = False
    oracle["waiting"] += 1
    try:
        while True:
            now = time.time()
            if now < oracle["blocked_until"]:
                if backup and _any_backup(estimate):
                    return None
                waited = True
                await asyncio.sleep(min(1.0, oracle["blocked_until"] - now))
                continue
            while _spent and now - _spent[0][0] > 60:
                _spent.popleft()
            if _spent and sum(t for _, t in _spent) + estimate > BUDGET:
                if backup and MODE["oracle"] in ("overflow", "backup-first") and _any_backup(estimate):
                    return None
                waited = True
                await asyncio.sleep(min(1.0, 60.2 - (now - _spent[0][0])))
                continue
            entry = [now, estimate]
            _spent.append(entry)
            return entry
    finally:
        oracle["waiting"] -= 1
        if waited:
            oracle["paced"] += 1


def _lock(r):
    """The oracle said 429: nobody calls it until its lock has opened."""
    try:
        wait = float(r.headers.get("retry-after", "60"))
    except ValueError:
        wait = 60.0
    oracle["blocked_until"] = max(oracle["blocked_until"], time.time() + min(wait, 120) + 1.5)


def _count(r):
    """Count one call to the oracle. Reads headers only: r may be a stream whose body nobody has read yet."""
    oracle["calls"] += 1
    if r.status_code == 429:
        oracle["throttled"] += 1
        oracle["last_429"] = time.time()
        oracle["limit_headers"] = {k: v for k, v in r.headers.items() if "limit" in k.lower() or "retry" in k.lower()}
        print("429 from MaaS:", oracle["limit_headers"], flush=True)


def _answered_by_maas(tokens: int):
    m = oracles["maas"]
    m["calls"] += 1
    m["tokens"] += tokens
    last.update(oracle="maas", at=time.time())


# ---------- the backup oracle ----------
# Red Hat MaaS stays the first choice. When it is locked after a 429, or the minute's budget above
# is used up, a call goes to the backup instead of waiting: OpenRouter, one model pinned to one
# provider (BACKUP_REQUEST carries the "provider" pin and switches reasoning off). It has its own
# key, from the secret oracle-backup (gitops/20-shop/backup-oracle.sh), and a hard cap in US
# dollars. At start the gateway asks OpenRouter what the key has spent so far, so the cap holds
# across restarts. If the backup fails, it rests for a minute and calls wait for MaaS as before.
BACKUP_URL = os.environ.get("BACKUP_UPSTREAM", "").rstrip("/")
BACKUP_MODEL = os.environ.get("BACKUP_MODEL", "")
BACKUP_KEY = os.environ.get("BACKUP_API_KEY", "")
BACKUP_REQUEST = json.loads(os.environ.get("BACKUP_REQUEST") or "{}")
BACKUP_CAP = float(os.environ.get("BACKUP_CAP_USD", "3"))
# US dollars per million tokens
PRICE = {"input": float(os.environ.get("BACKUP_PRICE_INPUT", "0.0507")),
         "output": float(os.environ.get("BACKUP_PRICE_OUTPUT", "0.2028")),
         "cache_read": float(os.environ.get("BACKUP_PRICE_CACHE_READ", "0.001014"))}
# ---------- the second backup ----------
# A second model endpoint from Red Hat (another model, another key), behind the backup: it takes a
# call when the backup can't (failed, resting, at its cap, or not configured). Its key comes from
# the same secret, oracle-backup. No cap: nobody bills us for it. Measured on 16 November: one call
# in 0.5 to 3 seconds, tool calls in the shape we need; its reasoning can't be switched off (five
# request fields tried), so SPARE_REQUEST is empty and the reasoning is dropped on the way back.
SPARE_URL = os.environ.get("SPARE_UPSTREAM", "").rstrip("/")
SPARE_MODEL = os.environ.get("SPARE_MODEL", "")
SPARE_KEY = os.environ.get("SPARE_API_KEY", "")
SPARE_NAME = os.environ.get("SPARE_NAME", "second backup")
SPARE_REQUEST = json.loads(os.environ.get("SPARE_REQUEST") or "{}")
# Which of the two backups is asked first: BACKUP_FIRST is "backup" (OpenRouter) or "spare".
# Max's choice on 16 November: the Red Hat endpoint first, it costs us nothing.
FIRST = ("spare", "backup") if os.environ.get("BACKUP_FIRST", "backup") == "spare" else ("backup", "spare")
# Every mode below means "the backups" where it says "the backup": first the backup, then the second.
# overflow: MaaS first, the backup takes what MaaS can't take right now (locked, or the minute full).
# lock: the backup only while MaaS is locked after a 429; a full minute still waits (demo 4's story).
# backup-first: the backup (OpenRouter) first; MaaS when the backup is resting, failed or at its cap.
# maas: never the backup. backup: every call to the backups, no MaaS at all (for testing the backup).
# spare: every call to the second backup, nothing else (for testing it).
MODES = ("overflow", "lock", "backup-first", "maas", "backup", "spare")
MODE = {"oracle": os.environ.get("ORACLE_MODE", "overflow")}
# Since this gateway started; never reset (the dollars hold the cap).
oracles = {
    "maas": {"name": "Red Hat MaaS", "calls": 0, "tokens": 0, "dollars": 0.0},
    "backup": {"name": "OpenRouter", "model": BACKUP_MODEL, "calls": 0, "failed": 0,
               "tokens": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0,
               "dollars": 0.0,            # counted here, at the prices above
               "dollars_reported": 0.0,   # what OpenRouter says each call cost
               "spent_before": None,      # what the key had spent when this gateway started
               "spent_known": False,      # OpenRouter has told us spent_before
               "cap": BACKUP_CAP, "resting_until": 0.0, "last_error": ""},
    "spare": {"name": SPARE_NAME, "model": SPARE_MODEL, "calls": 0, "failed": 0, "tokens": 0,
              "input_tokens": 0, "output_tokens": 0, "resting_until": 0.0, "last_error": ""},
}
last = {"oracle": "", "at": 0.0}           # which oracle answered last


def _backup_spent() -> float:
    b = oracles["backup"]
    return (b["spent_before"] or 0.0) + max(b["dollars"], b["dollars_reported"])


def _price(fresh_in: int, cached: int, out: int) -> float:
    return (fresh_in * PRICE["input"] + cached * PRICE["cache_read"] + out * PRICE["output"]) / 1e6


def _backup_ready(estimate: int) -> bool:
    """Is the backup there, awake and far enough from its cap for a call of this size?"""
    if MODE["oracle"] in ("maas", "spare") or not (BACKUP_URL and BACKUP_KEY and BACKUP_MODEL):
        return False
    if time.time() < oracles["backup"]["resting_until"]:
        return False
    # BACKUP_CAP_USD 0 means no cap of ours (Max, 17 November); the key's own limit at OpenRouter still holds.
    return BACKUP_CAP <= 0 or _backup_spent() + _price(estimate, 0, 2000) <= BACKUP_CAP


def _spare_ready() -> bool:
    return (MODE["oracle"] != "maas" and bool(SPARE_URL and SPARE_KEY and SPARE_MODEL)
            and time.time() >= oracles["spare"]["resting_until"])


def _any_backup(estimate: int) -> bool:
    return _backup_ready(estimate) or _spare_ready()


async def _backup_seed():
    """Ask OpenRouter what this key has spent so far; until it answers, count as if a third of the
    cap were gone. Tries again every half minute."""
    if not (BACKUP_URL and BACKUP_KEY):
        return
    oracles["backup"]["spent_before"] = BACKUP_CAP / 3
    for _ in range(120):
        try:
            r = await client.get(f"{BACKUP_URL}/key", headers={"Authorization": f"Bearer {BACKUP_KEY}"}, timeout=20)
            r.raise_for_status()
            oracles["backup"]["spent_before"] = float(r.json()["data"]["usage"])
            oracles["backup"]["spent_known"] = True
            print(f"backup oracle: the key has spent {oracles['backup']['spent_before']:.4f} US dollars so far", flush=True)
            return
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
            print("backup oracle: spend so far unknown,", type(e).__name__, flush=True)
        await asyncio.sleep(30)


async def _ask(which: str, path: str, payload: dict):
    """One chat call to the backup or the second backup, in one piece. Returns the answer, or None
    after a failure; the oracle that failed then rests for a minute."""
    b = oracles[which]
    url, key, model, extra = ((BACKUP_URL, BACKUP_KEY, BACKUP_MODEL, BACKUP_REQUEST) if which == "backup"
                              else (SPARE_URL, SPARE_KEY, SPARE_MODEL, SPARE_REQUEST))
    body = {k: v for k, v in payload.items() if k not in ("chat_template_kwargs", "stream_options") and k not in MODEL_EXTRA}
    body.update(extra, model=model, stream=False)
    b["calls"] += 1
    oracle["backup_calls"] += 1
    if which == "spare":
        oracle["spare_calls"] += 1
    err = ""
    try:
        r = await client.post(f"{url}/{path}", json=body, timeout=180,
                              headers={"Authorization": f"Bearer {key}", "content-type": "application/json"})
        d = r.json() if r.status_code == 200 else None
        if r.status_code != 200 or not (d or {}).get("choices"):
            err = f"{r.status_code} {r.text[:200]}"
    except (httpx.HTTPError, ValueError) as e:
        err = type(e).__name__
    if err:
        b["failed"] += 1
        b["last_error"] = err
        b["resting_until"] = time.time() + 60
        print(f"{b['name']} failed, resting a minute:", err, flush=True)
        return None
    u = d.get("usage") or {}
    p, c = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
    b["input_tokens"] += p
    b["output_tokens"] += c
    b["tokens"] += p + c
    if which == "backup":
        cached = int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
        b["cached_tokens"] += cached
        b["dollars"] += _price(p - cached, cached, c)
        if isinstance(u.get("cost"), (int, float)):
            b["dollars_reported"] += u["cost"]
    else:
        # The second backup always reasons and sends the reasoning along; the caller has no use for it.
        for ch in d.get("choices") or []:
            (ch.get("message") or {}).pop("reasoning", None)
    last.update(oracle=which, at=time.time())
    return d


async def _backup(path: str, payload: dict):
    """One chat call to the backups: the backup first, the second backup if the first can't or fails.
    Returns (answer, None) or (None, error response)."""
    estimate = _estimate(json.dumps(payload).encode())
    for which in FIRST:
        if _spare_ready() if which == "spare" else _backup_ready(estimate):
            d = await _ask(which, path, payload)
            if d is not None:
                return d, None
    return None, JSONResponse({"error": {"message": "the backup oracles are unavailable (failed, resting, "
                                                    "at the cap or not configured)"}}, status_code=503)


def _answered(d: dict, asked: str) -> str:
    """The model that answered, as the caller's trace should name it. The apprentice asks for one
    model by name; behind this gateway another may answer (a backup), and the trace should say so."""
    return str(d.get("model") or asked).split("/")[-1]


def _reply(payload: dict, d: dict):
    """The backup's answer in the shape the caller asked for: JSON, or a stream in one chunk."""
    if not payload.get("stream"):
        return JSONResponse(d)
    choice = (d.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    return _sse(_answered(d, payload.get("model", "")), msg.get("content"), msg.get("tool_calls"),
                choice.get("finish_reason") or ("tool_calls" if msg.get("tool_calls") else "stop"), d.get("usage"))


async def passthrough(request: Request, path: str, body: bytes, payload: dict | None = None):
    is_chat = request.method == "POST" and path.endswith("chat/completions")
    for attempt in range(TRIES):
        entry = await _turn(_estimate(body), backup=payload is not None) if is_chat else None
        if is_chat and entry is None:
            d, error = await _backup(path, payload)
            if d is not None:
                return _reply(payload, d)
            if MODE["oracle"] in ("backup", "spare"):
                return error
            entry = await _turn(_estimate(body), backup=False)
        req = client.build_request(request.method, f"{UPSTREAM}/{path}", headers=_headers(request),
                                   content=body, params=request.query_params)
        upstream = await client.send(req, stream=True)
        if is_chat:
            _count(upstream)
        keep = {k: v for k, v in upstream.headers.items() if k.lower() in KEEP}
        if upstream.status_code == 200:
            if is_chat:
                _answered_by_maas(entry[1])     # a stream: the estimate stands in for the real count
            return StreamingResponse(upstream.aiter_raw(), status_code=200, headers=keep,
                                     background=BackgroundTask(upstream.aclose))
        # An error is short: read it, give the connection back to the pool. (Leaving it unread
        # used to leak one connection per 429 until the pool was empty.)
        try:
            content = await upstream.aread()
        finally:
            await upstream.aclose()
        if entry:
            entry[1] = 0            # a refused call cost nothing
        if upstream.status_code == 429 and is_chat and attempt < TRIES - 1:
            _lock(upstream)
            continue                # _turn() now waits until the lock has opened
        return Response(content, status_code=upstream.status_code, headers=keep)


async def proxy(request: Request, guarded=True):
    path = request.path_params["path"]
    body = await request.body()
    is_chat = request.method == "POST" and path.endswith("chat/completions") and body
    if not is_chat:
        return await passthrough(request, path, body)
    try:
        payload = json.loads(body)
    except ValueError:
        return await passthrough(request, path, body)
    payload.setdefault("chat_template_kwargs", {})["enable_thinking"] = THINKING
    asked = payload.get("model", "")
    payload["model"] = MAAS_MODEL
    for k, v in MODEL_EXTRA.items():
        payload.setdefault(k, v)
    if not (guarded and STATE["enabled"]):
        return await passthrough(request, path, json.dumps(payload).encode(), payload)

    model, stream = payload.get("model", ""), bool(payload.get("stream"))
    messages = payload.get("messages") or []
    auth = request.headers.get("authorization", "")
    users = [m for m in messages if m.get("role") == "user"]
    last_user = _text(users[-1].get("content")) if users else ""

    # Input rails, once per customer line: only when the newest message is the customer's.
    if messages and messages[-1].get("role") == "user" and last_user:
        try:
            answer, log = await rails("input", [{"role": "user", "content": last_user}], auth)
            if any(a.get("stop") for a in log):
                _note("topic", last_user, answer, "in")
                return _sse(model, answer) if stream else _json(model, answer)
        except (httpx.HTTPError, ValueError) as e:
            print("input rails unavailable:", e, flush=True)

    # The model, in one piece, so the output rails can see the whole answer before it leaves.
    payload["stream"] = False
    payload.pop("stream_options", None)
    out = json.dumps(payload).encode()
    send = dict(_headers(request), **{"content-type": "application/json"})
    d = None
    for attempt in range(TRIES):
        entry = await _turn(_estimate(out))
        if entry is None:
            d, error = await _backup(path, payload)
            if d is not None:
                break
            if MODE["oracle"] in ("backup", "spare"):
                return error
            entry = await _turn(_estimate(out), backup=False)
        r = await client.post(f"{UPSTREAM}/{path}", headers=send, content=out)
        _count(r)
        if r.status_code != 429 or attempt == TRIES - 1:
            break
        entry[1] = 0
        _lock(r)
    if d is None:
        if r.status_code != 200:
            entry[1] = 0
            return Response(r.content, status_code=r.status_code,
                            headers={k: v for k, v in r.headers.items() if k.lower() in KEEP})
        d = r.json()
        entry[1] = int((d.get("usage") or {}).get("total_tokens") or entry[1])   # what it really cost
        _answered_by_maas(entry[1])
    choice = (d.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    content, tool_calls, usage = msg.get("content"), msg.get("tool_calls"), d.get("usage")

    if content and not tool_calls:
        try:
            new, log = await rails("output", [{"role": "user", "content": last_user},
                                              {"role": "assistant", "content": content}], auth)
            # The output rails run one after the other on the answer; a rail stepped in if it changed it.
            prev = content
            for a in log:
                for act in a.get("executed_actions") or []:
                    rail, ret = ACTION_RAIL.get(act.get("action_name")), act.get("return_value")
                    if rail and isinstance(ret, str):
                        if ret.strip() != prev.strip():
                            _note(rail, prev, ret, "out")
                        prev = ret
            if new:
                content = new
        except (httpx.HTTPError, ValueError) as e:
            print("output rails unavailable:", e, flush=True)

    if stream:
        return _sse(_answered(d, model), content, tool_calls, choice.get("finish_reason") or ("tool_calls" if tool_calls else "stop"), usage)
    msg["content"] = content
    return JSONResponse(d)


async def chat(request: Request):
    return await proxy(request, guarded=True)


async def raw(request: Request):
    return await proxy(request, guarded=False)


async def rails_state(_):
    return JSONResponse({"config": STATE["config"], "enabled": STATE["enabled"],
                         "rails": [{"id": k, "name": v, "count": counters[k]} for k, v in RAILS.items()],
                         "events": list(events),
                         "oracle": dict(oracle, budget=BUDGET, mode=MODE["oracle"], last=last["oracle"],
                                        spent_last_minute=sum(t for at, t in _spent if time.time() - at <= 60)),
                         "oracles": _oracles()})


def _oracles():
    b = oracles["backup"]
    return {"maas": dict(oracles["maas"]),
            "backup": dict(b, dollars=round(b["dollars"], 9), dollars_reported=round(b["dollars_reported"], 9),
                           spent_total=round(_backup_spent(), 9), configured=bool(BACKUP_URL and BACKUP_KEY and BACKUP_MODEL),
                           resting=time.time() < b["resting_until"]),
            "spare": dict(oracles["spare"], configured=bool(SPARE_URL and SPARE_KEY and SPARE_MODEL),
                          resting=time.time() < oracles["spare"]["resting_until"]),
            "mode": MODE["oracle"], "first": FIRST[0], "last": dict(last)}


async def oracle_state(request: Request):
    if request.method == "POST":
        mode = str((await request.json()).get("mode", ""))
        if mode not in MODES:
            return JSONResponse({"error": "mode is one of " + ", ".join(MODES)}, status_code=400)
        MODE["oracle"] = mode
        print("oracle mode:", mode, flush=True)
    return JSONResponse(_oracles())


async def rails_reset(request: Request):
    for k in counters:
        counters[k] = 0
    events.clear()
    if request.query_params.get("oracle"):
        oracle.update(calls=0, throttled=0, last_429=0.0, paced=0, backup_calls=0, spare_calls=0)
    return JSONResponse({"ok": True})


async def rails_config(request: Request):
    if request.method == "POST":
        body = await request.json()
        if body.get("config"):
            STATE["config"] = str(body["config"])
        if "enabled" in body:
            STATE["enabled"] = bool(body["enabled"]) and bool(RAILS_URL)
    return JSONResponse({"config": STATE["config"], "enabled": STATE["enabled"]})


async def healthz(_):
    return JSONResponse({"ok": True, "upstream": UPSTREAM, "thinking": THINKING, **STATE,
                         "backup": BACKUP_MODEL if (BACKUP_URL and BACKUP_KEY) else "",
                         "spare": SPARE_MODEL if (SPARE_URL and SPARE_KEY) else "", "oracle_mode": MODE["oracle"]})


@contextlib.asynccontextmanager
async def lifespan(_app):
    seed = asyncio.create_task(_backup_seed())
    yield
    seed.cancel()


app = Starlette(lifespan=lifespan, routes=[
    Route("/healthz", healthz),
    Route("/rails/state", rails_state),
    Route("/rails/reset", rails_reset, methods=["POST"]),
    Route("/rails/config", rails_config, methods=["GET", "POST"]),
    Route("/oracle", oracle_state, methods=["GET", "POST"]),
    Route("/raw/v1/{path:path}", raw, methods=["GET", "POST"]),
    Route("/v1/{path:path}", chat, methods=["GET", "POST"]),
])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
