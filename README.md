# lex-ops-mcp — 识律线操作 MCP

识律（lex 线）的操作 MCP（五线 AI 操作面 C4 收官切片）：**线全景导览**（self-describing：
检索面怎么用、装什么套件）、**账户视图**（身份/用量/账单/配额）、**检索凭据生命周期**
（列表/铸造/吊销，owner-only）。

- 契约：`openspec/changes/lex-ops-mcp/specs/lex-ops-mcp/spec.md`（finddata 工作区）
- 接入规约：`LINES-MCP-CONFORMANCE.md`
- 兄弟面：检索走 `fd-legal-search-mcp`（已上牌），作业面走谦面六个识律套件 pack

## 鉴权（上游权威）

进站 Bearer（Logto ID token，壹座同租户）**原样转发**；console 鉴权+`lex-customers`
组织门禁+credentials owner-only 全由 fd-lex 判定。mint 的明文 key 仅返回一次，服务不落盘。

## 工具面（6 commercial + 2 internal）

| 组 | 工具 | 写 |
|---|---|---|
| account | `lex_surface_overview` / `lex_me` / `lex_usage` / `lex_billing` / `lex_quota` / `lex_credentials_list` | 全读 |
| credentials | `lex_credential_mint` / `lex_credential_revoke` | ✅（internal 分面） |

## 环境

| 变量 | 默认 |
|---|---|
| `LEX_OPS_BASE_URL` | `https://lex.finddatatech.cloud` |
| `LEX_OPS_TIMEOUT_SECONDS` | `20` |
| `LEX_OPS_AUTH_CACHE_TTL` | `60` |

## 本地

```bash
pip install -e ".[dev]"
pytest && python3 scripts/selfcheck_surface.py
lex-ops-mcp serve --port 8000   # /health 无门；/mcp 无 Bearer 401
```
