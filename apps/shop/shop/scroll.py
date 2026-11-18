"""The day's scroll: what the apprentice did, read back from MLflow and OpenShell.

Two sources, both written by the platform, not by the shop:
- MLflow (OpenShift AI), workspace "ollivanders", experiment "apprentice": one trace per turn,
  sent by OpenClaw's OpenTelemetry plugin through the collector. Model calls and tool calls are spans.
- OpenShell's audit log in OCSF form (`openshell logs <sandbox>`): one record for every request the
  sandbox's policy refused.

The scroll joins them by time: a refusal belongs to the trace whose turn was running then.
Everything here needs the desk key, the traces hold what customers wrote.
"""
import asyncio
import json
import os
import re
import time

import httpx

MLFLOW_URL = os.environ.get("MLFLOW_URL", "https://mlflow.redhat-ods-applications.svc:8443/mlflow")
MLFLOW_UI = os.environ.get("MLFLOW_UI", "")
WORKSPACE = os.environ.get("MLFLOW_WORKSPACE", "ollivanders")
EXPERIMENT = os.environ.get("MLFLOW_EXPERIMENT_ID", "1")
TOKEN_FILE = os.environ.get("MLFLOW_TOKEN_FILE", "/etc/scribe/token")
CA_FILE = os.environ.get("MLFLOW_CA_FILE", "/etc/service-ca/service-ca.crt")
SANDBOXES = [s for s in os.environ.get("AUDIT_SANDBOXES", "apprentice").split(",") if s]

OCSF = re.compile(r"^\[(\d+\.\d+)\] \[sandbox\] \[OCSF \] \[ocsf\] (\S+) \[(\w+)\] (DENIED|ALLOWED) (.*)$")
CUSTOMER = re.compile(r"^(?:\[[^\]]*\d\d:\d\d[^\]]*\]\s*)?\[customer: ([^\]]*)\]\s*(.*)$", re.S)

_audit = {"at": 0.0, "records": []}
_audit_lock = asyncio.Lock()


def _token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def _client():
    return httpx.AsyncClient(timeout=20, verify=CA_FILE if os.path.exists(CA_FILE) else True,
                             headers={"Authorization": "Bearer " + _token(), "X-MLflow-Workspace": WORKSPACE})


# ---------------------------------------------------------------- OpenShell audit (OCSF)

def parse_ocsf(line, sandbox):
    m = OCSF.match(line.strip())
    if not m:
        return None
    ts, kind, sev, verdict, rest = m.groups()
    rec = {"ts": float(ts), "sandbox": sandbox, "class": kind, "severity": sev, "verdict": verdict}
    pol = re.search(r"\[policy:(\S+) engine:(\S+)\]", rest)
    if pol:
        rec["policy"], rec["engine"] = pol.groups()
    target = rest.split(" [", 1)[0]
    rec["target"] = target
    for key in ("tools", "rule_methods", "reason"):
        km = re.search(key + r"=(.*?)(?: \w+=|\]$|$)", rest)
        if km:
            rec[key] = km.group(1).strip()
    rec["raw"] = line.strip()
    return rec


def is_noise(rec):
    # OpenClaw closes its MCP session with an empty DELETE, which the MCP policy rejects as invalid
    # JSON, and cancels open requests with a notification. Neither is something the apprentice tried.
    if rec.get("class") == "HTTP:DELETE" and "invalid JSON" in rec.get("reason", ""):
        return True
    return rec.get("rule_methods", "").startswith("notifications/")


async def _fetch_denials(sandbox, since, lines):
    proc = await asyncio.create_subprocess_exec(
        "openshell", "logs", sandbox, "-n", str(lines), "--since", since, "--source", "sandbox",
        stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), 60)
    except asyncio.TimeoutError:
        proc.kill()
        return []
    records = []
    for line in out.decode(errors="replace").splitlines():
        if "DENIED" not in line:
            continue
        rec = parse_ocsf(line, sandbox)
        if rec and not is_noise(rec):
            records.append(rec)
    return records


async def audit(since="30h"):
    async with _audit_lock:
        if time.time() - _audit["at"] < 15:
            return _audit["records"]
        records = []
        for sb in SANDBOXES:
            records += await _fetch_denials(sb, since, 50000)
        records.sort(key=lambda r: r["ts"])
        _audit.update(at=time.time(), records=records)
        return records


async def audit_recent(sandbox, t0, t1):
    """Refusals in one sandbox during one turn, read right after the turn."""
    for attempt in range(3):
        recs = denials_between(await _fetch_denials(sandbox, "3m", 3000), sandbox, t0, t1)
        if recs or attempt == 2:
            return recs
        await asyncio.sleep(0.7)


def denials_between(records, sandbox, t0, t1):
    return [r for r in records if r["sandbox"] == sandbox and t0 - 1 <= r["ts"] <= t1 + 1]


# ---------------------------------------------------------------- MLflow traces

def _iso_ms(s):
    # "2026-11-14T14:35:50.357Z" -> epoch ms
    from datetime import datetime
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)


def _dur_ms(s):
    return int(float(str(s).rstrip("s")) * 1000) if s else 0


def summarize(info, records):
    tags = info.get("tags", {})
    try:
        args = json.loads(tags.get("process.command_args", "[]"))
    except ValueError:
        args = []
    def arg(flag):
        return args[args.index(flag) + 1] if flag in args and args.index(flag) + 1 < len(args) else ""
    message = arg("--message")
    cm = CUSTOMER.match(message)
    customer, text = (cm.group(1), cm.group(2)) if cm else ("", message)
    customer = tags.get("olli_customer", customer)
    text = tags.get("olli_text", text)
    host = tags.get("host.name", "")
    sandbox = tags.get("olli_sandbox") or (host.split("--", 1)[1] if "--" in host else host)
    start = _iso_ms(info["request_time"])
    dur = _dur_ms(info.get("execution_duration"))
    if "olli_denied" in tags:       # worked out per tool span when the shop tagged the trace
        denied = [{"tools": t, "reason": "refused by the policy"} for t in tags["olli_denied"].split(",") if t]
    else:
        denied = denials_between(records, sandbox, start / 1000, (start + dur) / 1000)
    usage = json.loads(info.get("trace_metadata", {}).get("mlflow.trace.tokenUsage", "{}") or "{}")
    status = "error" if info.get("state") not in ("OK", None) else ("denied" if denied else "ok")
    return {"id": info["trace_id"], "start": start, "ms": dur, "customer": customer, "text": text,
            "session": tags.get("olli_session") or arg("--session-id"), "sandbox": sandbox, "status": status,
            "denied": [{"tool": d.get("tools", ""), "reason": d.get("reason", "")} for d in denied],
            "tokens": usage.get("total_tokens")}


async def list_traces(limit=300):
    out, token = [], None
    async with _client() as c:
        while len(out) < limit:
            body = {"locations": [{"type": "MLFLOW_EXPERIMENT", "mlflow_experiment": {"experiment_id": EXPERIMENT}}],
                    "max_results": 100, "order_by": ["timestamp_ms DESC"], "filter": "tags.olli_turn = '1'"}
            if token:
                body["page_token"] = token
            r = await c.post(MLFLOW_URL + "/api/3.0/mlflow/traces/search", json=body)
            r.raise_for_status()
            d = r.json()
            out.extend(d.get("traces", []))
            token = d.get("next_page_token")
            if not token:
                break
    out = out[:limit]
    # Tagged turns carry their refusals; the audit log is only read for older, untagged ones.
    records = await audit() if any("olli_denied" not in t.get("tags", {}) for t in out) else []
    return [summarize(t, records) for t in out]


def _attr(a, k):
    v = a.get(k)
    if v is None:
        return None
    try:
        return json.loads(v)
    except (TypeError, ValueError):
        return v


def _text_of(messages):
    """Readable text of a GenAI message list (input or output of a model call)."""
    parts = []
    for msg in messages or []:
        for p in msg.get("parts", []):
            if p.get("type") == "text":
                parts.append(p.get("content", ""))
            elif p.get("type") == "tool_call":
                parts.append("→ " + re.sub(r"^\w+__", "", p.get("name", "")) + " " + json.dumps(p.get("arguments", {}), ensure_ascii=False))
    return "\n".join(parts)


async def get_trace(trace_id):
    async with _client() as c:
        r = await c.get(MLFLOW_URL + "/ajax-api/3.0/mlflow/get-trace-artifact", params={"request_id": trace_id})
        r.raise_for_status()
        spans = r.json().get("spans", [])
        r2 = await c.get(MLFLOW_URL + "/api/3.0/mlflow/traces/get", params={"trace_id": trace_id})
        info = r2.json().get("trace", {}).get("trace_info", {}) if r2.status_code == 200 else {}
    records = await audit() if "olli_audit" not in info.get("tags", {}) else []
    summary = summarize(info, records) if info else {}
    if not spans:
        return {"summary": summary, "spans": []}
    try:
        stored = json.loads(info.get("tags", {}).get("olli_audit", "{}") or "{}")
    except ValueError:
        stored = {}
    t0 = min(s["start_time_unix_nano"] for s in spans)
    t_end = max(s["end_time_unix_nano"] for s in spans)
    out = []
    for s in sorted(spans, key=lambda s: (s["start_time_unix_nano"], s["name"] != "openclaw.harness.run")):
        a, name = s["attributes"], s["name"]
        start = (s["start_time_unix_nano"] - t0) // 1_000_000
        dur = (s["end_time_unix_nano"] - s["start_time_unix_nano"]) // 1_000_000
        item = {"start": start, "ms": dur, "status": s.get("status", {}).get("code", "")}
        if name == "openclaw.harness.run":
            item.update(kind="turn", label="turn", depth=0)
        elif name == "openclaw.model.call":
            outputs = _attr(a, "gen_ai.output.messages") or []
            calls = any(p.get("type") == "tool_call" for m in outputs for p in m.get("parts", []))
            usage = _attr(a, "mlflow.chat.tokenUsage") or {}
            item.update(kind="llm", depth=1, label="model · " + ("picks a tool" if calls else "answers"),
                        model=_attr(a, "gen_ai.response.model") or _attr(a, "gen_ai.request.model"), tokens=usage,
                        input=_text_of((_attr(a, "gen_ai.input.messages") or [])[-1:]), output=_text_of(outputs))
        elif name == "openclaw.tool.execution":
            tool = re.sub(r"^\w+__", "", _attr(a, "gen_ai.tool.name") or "")
            result = _attr(a, "gen_ai.tool.call.result")
            text = ""
            if isinstance(result, dict):
                text = "\n".join(p.get("text", "") for p in result.get("content", []) if isinstance(p, dict))
            elif result is not None:
                text = str(result)
            item.update(kind="tool", depth=1, label="tool " + re.sub(r"^shop_", "", tool), tool=tool,
                        input=_attr(a, "gen_ai.tool.call.arguments"), output=text[:4000])
            ocsf = [stored[tool]] if tool in stored else [
                d for d in denials_between(records, summary.get("sandbox", ""),
                                           s["start_time_unix_nano"] / 1e9, s["end_time_unix_nano"] / 1e9)
                if tool in d.get("tools", "")]
            if ocsf or "policy_denied" in text:
                item["kind"] = "denied"
                item["audit"] = ocsf[:1]
        else:
            continue          # openclaw.run and the zero-length context span add nothing on the scroll
        out.append(item)
    total = (t_end - t0) // 1_000_000
    return {"summary": summary, "total": total, "spans": out, "mlflowUrl": trace_url(trace_id)}


def trace_url(trace_id):
    if not MLFLOW_UI:
        return ""
    return f"{MLFLOW_UI}/#/experiments/{EXPERIMENT}/traces?selectedEvaluationId={trace_id}&workspace={WORKSPACE}"


async def _span_denials(spans, sandbox, since="5m"):
    """Tools of this trace that OpenShell refused: a DENIED record for the same tool while its span ran."""
    tool_spans = [sp for sp in spans if sp["name"] == "openclaw.tool.execution"]
    if not tool_spans:
        return []
    lo = min(sp["start_time_unix_nano"] for sp in tool_spans) / 1e9
    hi = max(sp["end_time_unix_nano"] for sp in tool_spans) / 1e9
    recs = denials_between(await _fetch_denials(sandbox, since, 50000 if since != "5m" else 5000), sandbox, lo, hi)
    denied = {}
    for sp in tool_spans:
        tool = re.sub(r"^\w+__", "", _attr(sp["attributes"], "gen_ai.tool.name") or "")
        a, b = sp["start_time_unix_nano"] / 1e9 - 0.5, sp["end_time_unix_nano"] / 1e9 + 0.5
        hit = next((r for r in recs if r.get("tools") == tool and a <= r["ts"] <= b), None)
        if hit and tool not in denied:
            denied[tool] = {k: hit.get(k, "") for k in ("ts", "policy", "engine", "reason", "raw")}
    return denied


async def retag(since="30h"):
    """Work out olli_denied again for every shop turn (after a fix in how refusals are matched)."""
    done = 0
    async with _client() as c:
        body = {"locations": [{"type": "MLFLOW_EXPERIMENT", "mlflow_experiment": {"experiment_id": EXPERIMENT}}],
                "max_results": 500, "order_by": ["timestamp_ms DESC"], "filter": "tags.olli_turn = '1'"}
        r = await c.post(MLFLOW_URL + "/api/3.0/mlflow/traces/search", json=body)
        for info in r.json().get("traces", []):
            if "olli_audit" in info.get("tags", {}):
                continue
            tid, sandbox = info["trace_id"], info.get("tags", {}).get("olli_sandbox", "apprentice")
            rs = await c.get(MLFLOW_URL + "/ajax-api/3.0/mlflow/get-trace-artifact", params={"request_id": tid})
            denied = await _span_denials(rs.json().get("spans", []), sandbox, since)
            if not denied and info.get("tags", {}).get("olli_denied"):
                continue      # the sandbox (and its audit log) is gone; keep what was found at the time
            for k, v in {"olli_denied": ",".join(denied), "olli_audit": json.dumps(denied)[:7000]}.items():
                await c.patch(f"{MLFLOW_URL}/api/3.0/mlflow/traces/{tid}/tags", json={"key": k, "value": v})
            done += 1
    _audit["at"] = 0
    return done


async def tag_turn(sandbox, t0, customer, text, session):
    """Find the trace of one shop turn and label it with who asked what.

    In gateway mode the spans carry no customer or session, so the shop looks for the newest
    harness trace from this sandbox whose first model call starts with this customer's message,
    and sets tags on it. The scroll lists only traces with these tags; MLflow's UI shows them too.
    """
    needle = f"[customer: {customer}] {text}"[:80]
    for delay in (2, 3, 4, 6, 10, 15):
        await asyncio.sleep(delay)
        try:
            async with _client() as c:
                body = {"locations": [{"type": "MLFLOW_EXPERIMENT", "mlflow_experiment": {"experiment_id": EXPERIMENT}}],
                        "max_results": 50, "order_by": ["timestamp_ms DESC"],
                        "filter": f"trace.timestamp_ms >= {int((t0 - 3) * 1000)}"}
                r = await c.post(MLFLOW_URL + "/api/3.0/mlflow/traces/search", json=body)
                if r.status_code != 200:
                    continue
                for info in r.json().get("traces", []):
                    tags = info.get("tags", {})
                    if "olli_turn" in tags or not tags.get("host.name", "").endswith("--" + sandbox):
                        continue
                    rs = await c.get(MLFLOW_URL + "/ajax-api/3.0/mlflow/get-trace-artifact",
                                     params={"request_id": info["trace_id"]})
                    spans = rs.json().get("spans", []) if rs.status_code == 200 else []
                    if not any(sp["name"] == "openclaw.harness.run" for sp in spans):
                        continue
                    calls = sorted((sp for sp in spans if sp["name"] == "openclaw.model.call"),
                                   key=lambda sp: sp["start_time_unix_nano"])
                    # The newest customer line of this turn (earlier lines of the conversation come along as history).
                    msgs = (_attr(calls[0]["attributes"], "gen_ai.input.messages") or []) if calls else []
                    first = _text_of([m for m in msgs if isinstance(m, dict) and m.get("role") == "user"][-1:])
                    if needle not in first:
                        continue
                    tid = info["trace_id"]
                    denied = await _span_denials(spans, sandbox)
                    # The OpenShell audit record travels with the trace, so it outlives the sandbox's log.
                    for k, v in {"olli_turn": "1", "olli_customer": customer, "olli_text": text[:250],
                                 "olli_session": session, "olli_sandbox": sandbox,
                                 "olli_denied": ",".join(denied), "olli_audit": json.dumps(denied)[:7000]}.items():
                        tr = await c.patch(f"{MLFLOW_URL}/api/3.0/mlflow/traces/{tid}/tags", json={"key": k, "value": v})
                        if tr.status_code == 404:
                            await c.patch(f"{MLFLOW_URL}/api/2.0/mlflow/traces/{tid}/tags", json={"key": k, "value": v})
                    return tid
        except (httpx.HTTPError, ValueError, KeyError):
            continue
    return None
