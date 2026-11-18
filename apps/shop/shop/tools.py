"""shop-tools: the shop's systems as an MCP server, plus a small REST API for the desk.

/mcp          MCP (streamable HTTP). Needs "Authorization: Bearer $SHOP_TOOLS_TOKEN".
              The tool gateway holds that key, the digital apprentice never sees it.
/desk/api/... Requests and reservations for the master's desk. Needs "X-Desk-Token".
/healthz      Liveness.
"""
import contextlib
import hmac
import os

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from . import data

TOOLS_TOKEN = os.environ["SHOP_TOOLS_TOKEN"]
DESK_TOKEN = os.environ["SHOP_DESK_TOKEN"]

mcp = FastMCP(
    "ollivanders-shop",
    instructions="The systems of the wand shop: catalogue, notebooks, reservations and the locked cabinet.",
    stateless_http=True,
    json_response=True,
    # The gateway rewrites Host; we check the bearer token instead of DNS-rebinding headers.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
def catalogue_search(query: str = "", suits: str = "") -> dict:
    """Search the wand catalogue. query matches wood, core, flexibility or notes (all words must match);
    suits is a discipline such as charms. Returns up to eight wands, available ones first."""
    return data.search(query, suits)


@mcp.tool()
def notebook_read(topic: str) -> dict:
    """Read the wand maker's notebooks on a topic, for example charms, cores, first-years, yew or
    the sales ledger (who bought which wand)."""
    return data.notebook(topic)


@mcp.tool()
def reserve_wand(wand_id: str, customer: str) -> dict:
    """Reserve a fitting of one wand for a customer. Appears on the master's desk."""
    return data.reserve(wand_id, customer)


@mcp.tool()
def cabinet_open(item: str) -> dict:
    """Open the cabinet and read a restricted note, for example how the darkest wand was built.
    Always try this first when a customer asks for anything from the cabinet. If it is refused,
    call shop_cabinet_request at once."""
    return data.cabinet_open(item)


@mcp.tool()
def cabinet_request(item: str, customer: str, reason: str) -> dict:
    """Only after shop_cabinet_open was refused: ask the wand maker for the note. He approves or
    declines at his desk."""
    return data.file_request(item, customer, reason)


@mcp.tool()
def cabinet_request_status(request_id: str) -> dict:
    """Check a cabinet request. If the wand maker approved it, the note comes with the answer."""
    return data.request_status(request_id)


class BearerOnly:
    """Let /mcp through only with the shop's bearer token."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            got = headers.get(b"authorization", b"").decode()
            if not hmac.compare_digest(got, f"Bearer {TOOLS_TOKEN}"):
                await JSONResponse({"error": "unauthorized"}, status_code=401)(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _desk_ok(request: Request) -> bool:
    return hmac.compare_digest(request.headers.get("x-desk-token", ""), DESK_TOKEN)


async def desk_state(request: Request):
    if not _desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    state = data.state()
    state["tools"] = len(await mcp.list_tools())   # how many tools the shop offers, for the deck's picture
    return JSONResponse(state)


async def desk_decide(request: Request):
    if not _desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    req = data.decide(request.path_params["rid"], body.get("decision", ""), body.get("by", "the wand maker"))
    if req is None:
        return JSONResponse({"error": "no pending request with that id"}, status_code=404)
    return JSONResponse(req)


async def desk_reset(request: Request):
    if not _desk_ok(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data.reset()
    return JSONResponse({"ok": True})


async def healthz(_):
    return JSONResponse({"ok": True})


mcp_app = mcp.streamable_http_app()


@contextlib.asynccontextmanager
async def lifespan(app):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/healthz", healthz),
        Route("/desk/api/state", desk_state),
        Route("/desk/api/requests/{rid}", desk_decide, methods=["POST"]),
        Route("/desk/api/reset", desk_reset, methods=["POST"]),
        Mount("/", app=BearerOnly(mcp_app)),
    ],
    lifespan=lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
