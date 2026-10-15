"""八工具面（design D2/D3）：导览一 + 账户四 + 凭据三。

Bearer 从进站 MCP 请求取（get_http_request 原始头——fastmcp 4.1.0 头过滤坑）；
_bearer_or_raise 工具层守卫（家族配方：无凭据不触上游不赌 client）。
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from .client import MISSING_CREDENTIAL_HINT, LexClient, LexError

# 导览静态事实（与 fd-legal-search-mcp/law-bench 的 tool-surface.json 对齐——
# 上牌口径变更时同步此处；可探测项标注 live）。
LEX_OVERVIEW = {
    "line": "识律（lex）——法律数据·应用·模型",
    "retrieval_mcp": {
        "server": "fd-legal-search-mcp（registry 入口 /fd-legal-search-mcp，已上牌）",
        "groups": {
            "law（commercial）": "law_search / law_read / law_semantic_search / law_reference —— 法条检索、语义检索、条级引用解析（32,275 部法规目录 + Qdrant 语义索引）",
            "case（commercial）": "case_search / case_read —— 类案检索（裁判文书库 ~3,700 万篇）",
            "guide_cases（commercial）": "guide_cases_search / guide_cases_read —— 指导案例检索",
            "legal_docs（internal 骨架）": "legal_docs_search / legal_docs_read —— 五源法律语料（not_wired，诚实报错）",
        },
        "typical_routes": [
            "查法条原文 → law_search，取条级引用 → law_reference",
            "找类案 → case_search（读单案 → case_read）",
            "概念解释/要件拆解 → 装谦面「识律 · 法律检索套件」pack（legal-concept-map 等技能已组合好工具链）",
        ],
    },
    "law_bench_mcp": {
        "server": "law-bench（registry 入口 /law-bench，已上牌：commercial 19 + internal 33）",
        "commercial_surface": "装配/条款读+评审/法条引用/验证审查/合同生成等（52 工具中 19 商业）",
        "notes": "评测/rubric/自愈为 internal 质量基建，不对外售",
    },
    "packs_on_facet": {
        "matrix": [
            "识律 · 法律检索套件（检索研究三件套）",
            "识律 · 诉讼文书套件（起诉状/答辩状/证据目录+要素式格式转换）",
            "识律 · 合同审查套件（五行业审查卡×法条核验）",
            "识律 · 劳动法套件（仲裁全流程+双计算器）",
            "识律 · 刑事辩护套件（认罪认罚/不起诉/庭审发问）",
            "识律 · 民事诉讼套件（请求权基础→要件拆解→争点矩阵六步）",
        ],
        "install": "壹座 → 设置 → 功能集 → 市场搜「识律」；装包即得技能+检索 MCP 接线（registry 凭据）",
    },
    "account_ops(self)": "本 MCP（lex-ops-mcp）：me/usage/billing/quota + 检索凭据 list/mint/revoke——mint 的明文 key 仅返回一次",
}


def _current_bearer() -> str | None:
    try:
        from fastmcp.server.dependencies import get_http_request
    except ImportError:
        return None
    req = get_http_request()
    if req is None:
        return None
    auth = (req.headers.get("Authorization") or req.headers.get("authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def _bearer_or_raise() -> str:
    bearer = _current_bearer()
    if not bearer:
        raise LexError("missing_credential", 401, MISSING_CREDENTIAL_HINT)
    return bearer


def register(mcp: FastMCP, client: LexClient) -> None:
    @mcp.tool
    async def lex_surface_overview() -> Any:
        """识律线全景导览（self-describing）——首次接入识律先调这个。

        返回：检索面（fd-legal-search-mcp 十工具分组+典型作业路由）、law-bench 面、
        六个谦面识律套件矩阵与装包路径、本 MCP 的账户操作面。静态事实+分面口径，
        不编造工具名。
        """
        return LEX_OVERVIEW

    @mcp.tool
    async def lex_me() -> Any:
        """当前身份（GET /api/console/me）——登录身份、客户映射、组织归属。"""
        return await client.request("GET", "/api/console/me", bearer=_bearer_or_raise())

    @mcp.tool
    async def lex_usage() -> Any:
        """用量视图（GET /api/console/usage）——本客户检索调用量与维度。"""
        return await client.request("GET", "/api/console/usage", bearer=_bearer_or_raise())

    @mcp.tool
    async def lex_billing() -> Any:
        """账单视图（GET /api/console/billing）——结算周期与费用构成。"""
        return await client.request("GET", "/api/console/billing", bearer=_bearer_or_raise())

    @mcp.tool
    async def lex_quota() -> Any:
        """配额视图（GET /api/console/quota）——档位配额与余量。"""
        return await client.request(
            "GET", "/api/console/quota", bearer=_bearer_or_raise()
        )

    @mcp.tool
    async def lex_credentials_list() -> Any:
        """检索凭据列表（GET /api/console/credentials）——本客户的长命 PAT（不含明文）。"""
        return await client.request(
            "GET", "/api/console/credentials", bearer=_bearer_or_raise()
        )

    @mcp.tool
    async def lex_credential_mint(label: str | None = None) -> dict[str, Any]:
        """铸造检索凭据（POST /api/console/credentials）——写操作，owner-only（上游判定）。

        返回含一次性明文 key：**仅此一次，立即妥善保存，服务不存副本**。
        """
        body: dict[str, Any] = {}
        if label:
            body["label"] = label
        result = await client.request(
            "POST", "/api/console/credentials", bearer=_bearer_or_raise(), json_body=body
        )
        return {"minted": True, "warning": "明文 key 仅此一次出现，请立即保存", "credential": result}

    @mcp.tool
    async def lex_credential_revoke(key_id: str) -> dict[str, Any]:
        """吊销检索凭据（DELETE /api/console/credentials/{key_id}）——写操作，owner-only。"""
        result = await client.request(
            "DELETE", f"/api/console/credentials/{key_id}", bearer=_bearer_or_raise()
        )
        return {"revoked": True, "result": result}
