"""FastMCP 组装 + ASGI 布线（鉴权门 + /health）。"""

from __future__ import annotations

from . import SERVER_NAME, tools_lex
from .auth_gate import AuthGate, AuthGateMiddleware
from .client import LexClient
from .config import Settings

INSTRUCTIONS = (
    "识律线操作助手：先读 lex_surface_overview 拿全景（检索面怎么用、装什么套件），"
    "再操作账户面（身份/用量/账单/配额）与检索凭据生命周期（列表/铸造/吊销）。"
    "每个调用以你的识律凭据（Logto ID token）执行，组织门禁与 owner-only 上游判定。"
    "铸造的 key 明文仅此一次——提醒用户立即保存。错误如实透传（401=未登录/未开通、"
    "403=门禁或非 owner、404=无此凭据）；空结果如实为空，绝不编造。"
)

_HEALTH_OK = b'{"status":"ok"}'


def create_server(settings: Settings | None = None) -> "FastMCP":
    from fastmcp import FastMCP

    settings = settings or Settings.from_env()
    mcp = FastMCP(SERVER_NAME, instructions=INSTRUCTIONS)
    client = LexClient(settings.base_url, timeout_seconds=settings.timeout_seconds)
    tools_lex.register(mcp, client)
    mcp._lex_ops_client = client
    mcp._lex_ops_settings = settings
    return mcp


def build_app(settings: Settings | None = None):
    mcp = create_server(settings)
    settings_: Settings = mcp._lex_ops_settings
    mcp_app = mcp.http_app(path="/mcp")
    gate = AuthGateMiddleware(mcp_app, AuthGate(settings_.auth_cache_ttl_seconds))

    async def app(scope, receive, send):
        if scope.get("type") == "http":
            path = (scope.get("path") or "").rstrip("/")
            if path == "/health":
                await send({"type": "http.response.start", "status": 200,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": _HEALTH_OK})
                return
        await gate(scope, receive, send)

    return app
