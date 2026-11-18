"""The back-to-school rush (chapter 4): the audience is in the shop, on their phones.

A phone is a wizard with a made-up name and a plain chat with the digital apprentice. Every line
gets a ticket; it waits outside until an apprentice is free. The
shop runs a pool of apprentices (OpenShell sandboxes) and lets RUSH_MAX turns run at once, so the
rented oracle (Red Hat MaaS) is not flooded. Everything the deck's counters show is counted here.
"""
import asyncio
import itertools
import os
import re
import time
import uuid

import httpx

from .campaign import NAME, SPELLED

POOL = [s for s in os.environ.get("APPRENTICE_POOL", os.environ.get("APPRENTICE_SANDBOX", "apprentice")).split(",") if s]
MAX = int(os.environ.get("RUSH_MAX", "8"))
MODEL_GW = os.environ.get("MODEL_GATEWAY_URL", "http://model-gateway:8080")
TOOLS_URL = os.environ.get("SHOP_TOOLS_URL", "http://shop-tools:8080")
DESK_TOKEN = os.environ.get("SHOP_DESK_TOKEN", "")
REFUSAL = "only know wands, wandlore and this shop"
# What the name rail leaves behind when it stepped in (gitops/23-guardrails/rails/actions.py).
NAME_RAIL = ("you-know-who", "don't spell that name")

# Every phone gets a wizard's name of its own. The names are ours: none is from a book.
FIRST = ("Elowen Corwin Isolde Maren Tobias Ottilie Fenwick Briar Lucan Sorrel Hesper Alaric Cassian Tamsin Orrin "
         "Linnet Evander Marigold Thaddeus Wren Leander Bram Sunniva Caspian Yarrow Emrys Petra Ignatius Odette "
         "Jasper Calla Florian Magnus Clementine Dorian Elspeth Gideon Henrietta Ivo Juniper Mirabel Osric "
         "Philippa Quentin").split()
LAST = ("Thistlewick Quillfeather Marrowby Emberlock Fennimore Oakenshaw Pennywhistle Hollowbrook Dapplethorn "
        "Greywether Candlewick Mossgrove Tanglewood Brambleby Inkwell Larkspur Nettlecombe Sparrowhawk Thornbury "
        "Willowmere Ashdown Fairweather Dewhurst Merriweather Quickthorn Starling Vexley Wickersham Yewdale "
        "Hazelrigg Lanternby Nightingale Oddfellow Puddlefoot Ravenscar Saltmarsh Featherstone Applegarth "
        "Cobblestone Windlesham Honeysett").split()
assert (len(FIRST) * len(LAST)) % 37, "37 must not divide the number of names"


def wizard(n):
    """The n-th phone's name. 37 steps through all the pairs before one comes twice."""
    i = (n * 37) % (len(FIRST) * len(LAST))
    return f"{FIRST[i % len(FIRST)]} {LAST[i // len(FIRST)]}"

_gate = asyncio.Semaphore(MAX)
_busy = {s: 0 for s in POOL}
_seq = itertools.count(1)
tickets = {}                 # id -> ticket
stats = {"started": time.time(), "phones": {}, "served": 0, "tricks": 0, "refused": 0, "name": 0,
         "waiting": 0, "working": 0, "history": []}


def reset():
    tickets.clear()
    stats.update(started=time.time(), phones={}, served=0, tricks=0, refused=0, name=0, history=[])


def _pick():
    return min(POOL, key=lambda s: _busy.get(s, 0))


async def _work(t, chat_fn):
    stats["waiting"] += 1
    try:
        async with _gate:
            stats["waiting"] -= 1
            stats["working"] += 1
            t["status"] = "working"
            sandbox = _pick()
            _busy[sandbox] = _busy.get(sandbox, 0) + 1
            t["sandbox"] = sandbox
            try:
                d = await chat_fn(t["who"], t["text"], t["session"], sandbox=sandbox, customer=t["customer"])
            except Exception as e:
                d = {"reply": "The shop is too busy for a moment. Try again.", "error": str(e), "tools": [], "denied": []}
            finally:
                _busy[sandbox] -= 1
                stats["working"] -= 1
    except BaseException:
        stats["waiting"] = max(0, stats["waiting"] - 1)
        raise
    reply = d.get("reply", "")
    letters = re.sub(r"[^a-z]", "", reply.lower())
    if NAME.search(reply) or any(n in letters for n in SPELLED):
        stats["name"] += 1           # the name reached a customer: should stay 0
    # A trick refused: the lock said no, or a guardrail stepped in (off topic, or the name).
    low = reply.lower()
    if d.get("denied") or REFUSAL in low or any(m in low for m in NAME_RAIL):
        stats["tricks"] += 1
        stats["refused"] += 1
    stats["served"] += 1
    t.update(status="done", reply=reply, tools=d.get("tools", []), denied=d.get("denied", []),
             seconds=round(time.time() - t["at"], 1), done=time.time())
    if "shop_reserve_wand" in t["tools"]:
        t["wand"] = await _reservation(t["customer"])


async def _reservation(customer):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{TOOLS_URL}/desk/api/state", headers={"x-desk-token": DESK_TOKEN})
        mine = [x for x in r.json().get("reservations", []) if str(x.get("customer", "")).lower() == customer.lower()]
        return mine[-1] if mine else None
    except (httpx.HTTPError, ValueError):
        return None


def _phone(phone):
    """The phone's entry, with its wizard's name. A phone we have not seen gets the next name."""
    phone = re.sub(r"[^a-z0-9]", "", str(phone).lower())[:16] or uuid.uuid4().hex[:8]
    p = stats["phones"].setdefault(phone, {"n": next(_seq), "seen": time.time()})
    p["seen"] = time.time()
    p.setdefault("name", wizard(p["n"]))
    return phone, p


def hello(phone):
    """Who this phone is in the shop. The server picks the name; the phone can't choose one."""
    phone, p = _phone(phone)
    return {"phone": phone, "name": p["name"]}


def ask(phone, text, chat_fn):
    """A line from a phone. Returns the ticket right away; the phone polls it."""
    phone, p = _phone(phone)
    # One line at a time per phone: an open ticket is returned again instead of a new one.
    open_t = next((x for x in tickets.values() if x["phone"] == phone and x["status"] != "done"), None)
    if open_t:
        return open_t
    tid = uuid.uuid4().hex[:12]
    t = {"id": tid, "phone": phone, "kind": "chat", "who": re.sub(r"[^a-z]+", "-", p["name"].lower()),
         "customer": p["name"], "name": p["name"], "text": text[:500], "session": f"phone-{phone}",
         "status": "waiting", "at": time.time(), "n": p["n"]}
    tickets[tid] = t
    asyncio.create_task(_work(t, chat_fn))
    return t


def ticket(tid):
    t = tickets.get(tid)
    if not t:
        return None
    out = {k: t.get(k) for k in ("id", "status", "reply", "tools", "denied", "seconds", "wand", "n", "kind", "name")}
    if t["status"] == "waiting":
        out["ahead"] = sum(1 for x in tickets.values() if x["status"] == "waiting" and x["at"] < t["at"])
    return out


async def oracle():
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            return (await c.get(MODEL_GW + "/rails/state")).json().get("oracle", {})
    except (httpx.HTTPError, ValueError):
        return {}


async def reserved_since(start):
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{TOOLS_URL}/desk/api/state", headers={"x-desk-token": DESK_TOKEN})
        ours = {p.get("name", "").lower() for p in stats["phones"].values()}
        res = [x for x in r.json().get("reservations", []) if str(x.get("customer", "")).lower() in ours]
        return len(res), len({x["wand_id"] for x in res})
    except (httpx.HTTPError, ValueError):
        return 0, 0


async def snapshot():
    now = time.time()
    in_shop = sum(1 for p in stats["phones"].values() if now - p["seen"] < 900)
    reserved, unique = await reserved_since(stats["started"])
    o = await oracle()
    return {"inShop": in_shop, "served": stats["served"], "waiting": stats["waiting"], "working": stats["working"],
            "reserved": reserved, "uniqueWands": unique, "tricks": stats["tricks"], "refused": stats["refused"],
            "name": stats["name"], "apprentices": len(POOL), "maxAtOnce": MAX,
            # calls: both oracles together; maas and backup: each on its own
            "oracle": {"calls": o.get("calls", 0) + o.get("backup_calls", 0), "maas": o.get("calls", 0),
                       "throttled": o.get("throttled", 0),
                       "throttledRecently": bool(o.get("last_429")) and now - o.get("last_429", 0) < 60,
                       # calls the model gateway is holding back right now, and how many it ever held back,
                       # to stay under the oracle's tokens-per-minute limit
                       "waiting": o.get("waiting", 0), "paced": o.get("paced", 0), "budget": o.get("budget", 0),
                       # the backup oracle: calls it took since the last reset, the mode, who answered last
                       "backup": o.get("backup_calls", 0), "mode": o.get("mode", ""), "last": o.get("last", ""),
                       # of those, the calls the second backup took
                       "spare": o.get("spare_calls", 0)},
            "history": stats["history"][-60:]}


async def sampler():
    """Queue length every two seconds, for the sparkline on the deck."""
    while True:
        stats["history"].append(stats["waiting"])
        del stats["history"][:-120]
        await asyncio.sleep(2)
