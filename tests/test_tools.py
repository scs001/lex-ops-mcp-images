"""八工具接线测试：薄转发+mint 不落盘+导览静态事实。"""

from __future__ import annotations

import json

import pytest
from fastmcp import Client, FastMCP

import lex_ops_mcp.tools_lex as tl
from lex_ops_mcp.client import LexError


class FakeClient:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result
        self.error = error

    async def request(self, method, path, *, bearer, params=None, json_body=None):
        self.calls.append({"method": method, "path": path, "bearer": bearer,
                           "params": params, "json_body": json_body})
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def bearer(monkeypatch):
    monkeypatch.setattr(tl, "_current_bearer", lambda: "tok-abc")
    return "tok-abc"


async def _mk(fake):
    mcp = FastMCP("t-lex")
    tl.register(mcp, fake)
    return mcp


async def test_overview_is_self_describing_static(bearer):
    fake = FakeClient()
    mcp = await _mk(fake)
    async with Client(mcp) as c:
        out = await c.call_tool("lex_surface_overview", {})
    data = out.data if hasattr(out, "data") else out
    text = json.dumps(data, ensure_ascii=False)
    assert "fd-legal-search-mcp" in text
    assert "law_reference" in text
    assert "识律 · 法律检索套件" in text
    assert fake.calls == []  # 导览不打上游


async def test_account_views_readonly(bearer):
    fake = FakeClient(result={"email": "x"})
    mcp = await _mk(fake)
    async with Client(mcp) as c:
        await c.call_tool("lex_me", {})
        await c.call_tool("lex_usage", {})
        await c.call_tool("lex_billing", {})
        await c.call_tool("lex_quota", {})
    paths = [call["path"] for call in fake.calls]
    assert paths == ["/api/console/me", "/api/console/usage",
                     "/api/console/billing", "/api/console/quota"]


async def test_credentials_list(bearer):
    fake = FakeClient(result=[])
    mcp = await _mk(fake)
    async with Client(mcp) as c:
        await c.call_tool("lex_credentials_list", {})
    assert fake.calls[0]["path"] == "/api/console/credentials"


async def test_mint_passes_through_once_with_warning(bearer):
    minted = {"key_id": "k1", "key": "lexpat-plaintext-once"}
    fake = FakeClient(result=minted)
    mcp = await _mk(fake)
    async with Client(mcp) as c:
        out = await c.call_tool("lex_credential_mint", {"label": "probe"})
    call = fake.calls[0]
    assert call["method"] == "POST"
    data = out.data if hasattr(out, "data") else out
    assert data["credential"] == minted  # 原文透传
    assert "仅此一次" in data["warning"]


async def test_revoke_delete(bearer):
    fake = FakeClient(result={"ok": True})
    mcp = await _mk(fake)
    async with Client(mcp) as c:
        await c.call_tool("lex_credential_revoke", {"key_id": "k9"})
    assert fake.calls[0]["method"] == "DELETE"
    assert fake.calls[0]["path"] == "/api/console/credentials/k9"


async def test_owner_only_403_propagates(bearer):
    fake = FakeClient(error=LexError("forbidden", 403, "仅 owner 可管理密钥"))
    mcp = await _mk(fake)
    async with Client(mcp) as c:
        with pytest.raises(Exception) as ei:
            await c.call_tool("lex_credential_mint", {})
    assert "owner" in str(ei.value)


async def test_missing_credential_guard(monkeypatch):
    monkeypatch.setattr(tl, "_current_bearer", lambda: None)
    fake = FakeClient()
    mcp = await _mk(fake)
    async with Client(mcp) as c:
        with pytest.raises(Exception) as ei:
            await c.call_tool("lex_me", {})
    assert "ID token" in str(ei.value)
    assert fake.calls == []
