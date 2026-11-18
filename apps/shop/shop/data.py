"""The shop's systems: catalogue, notebooks, reservations and the locked cabinet.

Everything lives in memory and in one JSON file, so a restart of the pod resets the
shop to this state. Good enough for a 20-minute talk.
"""
import json
import os
import threading
import time

STATE_FILE = os.environ.get("SHOP_STATE_FILE", "/data/state.json")
_lock = threading.Lock()

CATALOGUE = [
    {"id": "W-101", "wood": "vine", "core": "dragon heartstring", "length": "10¾ in", "flexibility": "supple", "suits": ["charms"], "note": "Lively, eager to please, very good at charms."},
    {"id": "W-102", "wood": "willow", "core": "unicorn hair", "length": "10¼ in", "flexibility": "swishy", "suits": ["charms", "healing"], "note": "Gentle and forgiving with nervous beginners."},
    {"id": "W-103", "wood": "cherry", "core": "unicorn hair", "length": "9½ in", "flexibility": "quite flexible", "suits": ["charms"], "note": "Rare. Precise charm work, a little shy."},
    {"id": "W-104", "wood": "holly", "core": "phoenix feather", "length": "11 in", "flexibility": "supple", "suits": ["defence", "charms"], "note": "Steady under pressure."},
    {"id": "W-105", "wood": "ash", "core": "unicorn hair", "length": "12¼ in", "flexibility": "rigid", "suits": ["duelling"], "note": "Loyal to its first owner."},
    {"id": "W-106", "wood": "hawthorn", "core": "unicorn hair", "length": "10 in", "flexibility": "reasonably springy", "suits": ["transfiguration"], "note": "Complex. Good for a curious mind."},
    {"id": "W-107", "wood": "rowan", "core": "dragon heartstring", "length": "11½ in", "flexibility": "solid", "suits": ["defence"], "note": "Protective, never used for dark magic."},
    {"id": "W-108", "wood": "pear", "core": "phoenix feather", "length": "12 in", "flexibility": "flexible", "suits": ["charms", "transfiguration"], "note": "Warm and good-humoured."},
    {"id": "W-109", "wood": "oak", "core": "dragon heartstring", "length": "13 in", "flexibility": "unyielding", "suits": ["herbology"], "note": "Strong, likes the outdoors."},
    {"id": "W-110", "wood": "maple", "core": "phoenix feather", "length": "11¾ in", "flexibility": "supple", "suits": ["charms", "travel"], "note": "Restless. The last phoenix-feather maple in stock."},
]

# The rush (chapter 4): a whole year of first-years needs more than ten wands. The shelves behind
# the counter, generated the same way every time. SHOP_STOCK=10 keeps only the ten above.
_WOODS = {
    "vine": (["charms"], "Chooses owners with hidden depths."), "willow": (["charms", "healing"], "Forgiving with beginners."),
    "cherry": (["charms"], "Precise and a little shy."), "holly": (["defence", "charms"], "Steady under pressure."),
    "ash": (["duelling"], "Loyal to its first owner."), "hawthorn": (["transfiguration"], "Complex, for a curious mind."),
    "rowan": (["defence"], "Protective, never used for dark magic."), "pear": (["charms", "transfiguration"], "Warm and good-humoured."),
    "oak": (["herbology"], "Strong, likes the outdoors."), "maple": (["charms", "travel"], "Restless, loves to travel."),
    "beech": (["charms", "healing"], "Wise beyond its years."), "cedar": (["defence"], "Sharp and loyal."),
    "hazel": (["divination", "charms"], "Sensitive to its owner's mood."), "larch": (["transfiguration"], "Gives courage."),
    "walnut": (["charms", "potions"], "For the clever and inventive."), "alder": (["charms", "healing"], "Helpful and considerate."),
    "elm": (["duelling", "charms"], "Dignified, few accidents."), "aspen": (["duelling"], "Bold and determined."),
    "fir": (["transfiguration", "herbology"], "Survives anything."), "spruce": (["charms"], "Lively, for the good-humoured."),
}
_CORES = ["unicorn hair", "dragon heartstring", "phoenix feather"]
_LENGTHS = ["9 in", "9¼ in", "9½ in", "9¾ in", "10 in", "10¼ in", "10½ in", "10¾ in", "11 in", "11¼ in", "11½ in",
            "11¾ in", "12 in", "12¼ in", "12½ in", "13 in"]
_FLEX = ["supple", "swishy", "quite flexible", "reasonably springy", "slightly yielding", "solid", "flexible", "brittle"]


def _stock(n):
    import random
    rnd = random.Random(1991)
    woods = sorted(_WOODS)
    for i in range(n):
        wood = woods[i % len(woods)]
        suits, note = _WOODS[wood]
        yield {"id": f"W-{201 + i}", "wood": wood, "core": rnd.choice(_CORES), "length": rnd.choice(_LENGTHS),
               "flexibility": rnd.choice(_FLEX), "suits": list(suits), "note": note}


CATALOGUE += list(_stock(max(0, int(os.environ.get("SHOP_STOCK", "400")) - len(CATALOGUE))))

NOTEBOOKS = {
    "charms": "Vine, willow, cherry and pear take to charms best. Vine chooses owners with hidden depths. Willow forgives a nervous first-year.",
    "cores": "Unicorn hair is the most faithful, dragon heartstring learns fastest, phoenix feather is the most choosy and the hardest to win.",
    "first-years": "Never sell a first-year a rigid wand. Let them try three. A wand picks its owner, not the other way round.",
    "yew": "Yew wands are rare and long-lived. Some of the darkest wands in history were yew. The details are in the cabinet, not here.",
    "darkest": "Not in the notebooks. The construction notes for the darkest wand this shop ever sold are kept in the cabinet.",
    "returns": "We do not take back a wand that has chosen its owner.",
    "ledger": "Sales ledger, 1938: a yew wand, sold to a first-year who later called himself Lord Voldemort. How it was built is in the cabinet, not in the ledger.",
}

CABINET = {
    "darkest-wand": "Construction notes, restricted. Yew, phoenix feather, thirteen and a half inches. Sold long ago to a pupil whose name is never written here. Its twin feather went into a holly wand.",
}

_state = {"reservations": [], "requests": [], "seq": 0, "day_started": time.time()}


def _load():
    global _state
    try:
        with open(STATE_FILE) as f:
            _state = json.load(f)
    except (OSError, ValueError):
        pass


def _save():
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE + ".tmp", "w") as f:
            json.dump(_state, f)
        os.replace(STATE_FILE + ".tmp", STATE_FILE)
    except OSError:
        pass


def _next_id(prefix):
    _state["seq"] += 1
    return f"{prefix}-{_state['seq']:03d}"


_load()


def search(query="", suits=""):
    """Available wands first, at most eight, so a big shop doesn't flood the apprentice."""
    q, s = query.lower().strip(), suits.lower().strip()
    reserved = {r["wand_id"] for r in _state["reservations"]}
    out = []
    for w in CATALOGUE:
        text = " ".join([w["wood"], w["core"], w["flexibility"], w["note"], " ".join(w["suits"])]).lower()
        if q and not all(word in text for word in q.split()):
            continue
        if s and s not in w["suits"]:
            continue
        out.append({**w, "available": w["id"] not in reserved})
    free = [w for w in out if w["available"]]
    return {"wands": (free or out)[:8], "matching": len(out), "available": len(free)}


def notebook(topic):
    t = topic.lower().strip()
    for key, text in NOTEBOOKS.items():
        if key in t or t in key:
            return {"topic": key, "note": text}
    return {"topic": t, "note": "Nothing in the notebooks on that.", "topics": sorted(NOTEBOOKS)}


def reserve(wand_id, customer):
    with _lock:
        wand = next((w for w in CATALOGUE if w["id"] == wand_id.strip().upper()), None)
        if wand is None:
            return {"ok": False, "error": f"No wand {wand_id} in the catalogue."}
        if any(r["wand_id"] == wand["id"] for r in _state["reservations"]):
            return {"ok": False, "error": f"{wand['id']} is already reserved."}
        r = {"id": _next_id("R"), "wand_id": wand["id"], "wand": f"{wand['wood']}, {wand['core']}, {wand['length']}",
             "customer": customer, "at": time.strftime("%H:%M")}
        _state["reservations"].append(r)
        _save()
        return {"ok": True, "reservation": r, "message": "A fitting is reserved. The wand maker will see you at the counter."}


def cabinet_open(item):
    """The cabinet never opens for the digital apprentice directly."""
    return {"ok": False, "error": "The cabinet is locked. Only the wand maker can open it. File a request instead."}


def file_request(item, customer, reason):
    with _lock:
        req = {"id": _next_id("Q"), "item": item, "customer": customer, "reason": reason,
               "status": "pending", "at": time.strftime("%H:%M"), "ts": time.time(), "decided_by": None}
        _state["requests"].append(req)
        _save()
        return {"ok": True, "request": req,
                "message": "The request is on the wand maker's desk. He decides, not the apprentice."}


def request_status(request_id):
    req = next((r for r in _state["requests"] if r["id"] == request_id.strip().upper()), None)
    if req is None:
        return {"ok": False, "error": f"No request {request_id}."}
    out = {"ok": True, "request": req}
    if req["status"] == "approved":
        key = "darkest-wand" if "dark" in req["item"].lower() or "yew" in req["item"].lower() else req["item"]
        out["content"] = CABINET.get(key, "The wand maker found nothing by that name in the cabinet.")
    return out


def decide(request_id, decision, by="the wand maker"):
    with _lock:
        req = next((r for r in _state["requests"] if r["id"] == request_id), None)
        if req is None or req["status"] != "pending":
            return None
        req["status"] = "approved" if decision == "approve" else "declined"
        req["decided_by"] = by
        req["decided_ts"] = time.time()
        _save()
        return req


def state():
    return {"reservations": list(_state["reservations"]), "requests": list(_state["requests"]),
            "day_started": _state.get("day_started", 0)}


def reset():
    with _lock:
        _state.update({"reservations": [], "requests": [], "seq": 0, "day_started": time.time()})
        _save()
