"""lex console HTTP 客户端：Bearer 原样转发 + 诚实错误映射（上游权威）。"""

from __future__ import annotations

from typing import Any

import httpx


class LexError(Exception):
    def __init__(self, kind: str, status: int | None, detail: str):
        super().__init__(f"[{kind}] {detail}" + (f" (HTTP {status})" if status else ""))
        self.kind = kind
        self.status = status
        self.detail = detail


MISSING_CREDENTIAL_HINT = (
    "缺少凭据：识律 console 需要 Bearer Logto ID token（壹座同租户登录后获取；"
    "须已开通识律客户身份）"
)


class LexClient:
    def __init__(self, base_url: str, timeout_seconds: float = 20.0, transport=None):
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout_seconds, transport=transport
        )

    async def aclose(self):
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        bearer: str | None,
        params: dict | None = None,
        json_body: Any | None = None,
    ) -> Any:
        if not bearer:
            raise LexError("missing_credential", 401, MISSING_CREDENTIAL_HINT)
        try:
            res = await self._client.request(
                method,
                path,
                headers={"Authorization": f"Bearer {bearer}"},
                params=params,
                json=json_body,
            )
        except httpx.HTTPError as e:
            raise LexError(
                "unreachable", None, f"识律服务不可达：{type(e).__name__}: {e}"
            ) from e
        if res.status_code == 401:
            raise LexError("unauthorized", 401, _detail(res))
        if res.status_code == 402:
            raise LexError("billing", 402, _detail(res))
        if res.status_code == 403:
            raise LexError("forbidden", 403, _detail(res))
        if res.status_code == 404:
            raise LexError("not_found", 404, _detail(res))
        if res.status_code == 409:
            raise LexError("conflict", 409, _detail(res))
        if res.status_code == 422:
            raise LexError("invalid", 422, _detail(res))
        if res.status_code == 429:
            raise LexError("rate_limited", 429, _detail(res))
        if res.status_code >= 500:
            raise LexError("unreachable", res.status_code, f"识律服务错误：{_detail(res)}")
        if res.status_code >= 400:
            raise LexError("invalid", res.status_code, _detail(res))
        if not res.content:
            return None
        try:
            return res.json()
        except ValueError:
            return {"_raw": res.text}


def _detail(res: httpx.Response) -> str:
    try:
        body = res.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])[:800]
        if isinstance(body, dict) and "error" in body:
            return str(body["error"])[:800]
        return str(body)[:800]
    except Exception:
        return (res.text or "")[:800] or f"HTTP {res.status_code}（无 body）"
