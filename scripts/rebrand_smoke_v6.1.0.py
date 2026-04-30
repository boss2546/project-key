"""
PDB Rebrand v6.1.0 — Comprehensive Backend Self-Test (in-process TestClient)

Run: python scripts/rebrand_smoke_v6.1.0.py

Why this exists:
- User delegated full backend testing to เขียว (normally ฟ้า would do tests)
- Sandbox blocks port binding → use FastAPI TestClient instead of HTTP smoke
- Covers: auth, profile/personality, MCP protocol, files, billing, error format,
  branding in API responses, KEEP invariants
- Skips LLM/Stripe-dependent flows (require external API keys)

Categories: 9 — see SECTION headers below.
"""
import sys
import json
import secrets
from urllib.parse import urlparse

sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from backend.main import app

c = TestClient(app)
PASS = 0
FAIL = 0
ERRORS: list[tuple[str, str]] = []


def run(name: str, fn):
    """Run a single test function and tally."""
    global PASS, FAIL
    try:
        ok = fn()
        if ok:
            print(f"  PASS  {name}")
            PASS += 1
        else:
            print(f"  FAIL  {name}")
            FAIL += 1
            ERRORS.append((name, "returned False"))
    except AssertionError as e:
        print(f"  FAIL  {name} -> {e}")
        FAIL += 1
        ERRORS.append((name, str(e)))
    except Exception as e:
        print(f"  FAIL  {name} -> {type(e).__name__}: {e}")
        FAIL += 1
        ERRORS.append((name, f"{type(e).__name__}: {e}"))


def section(title: str):
    print(f"\n=== {title} ===")


# ─────────────────────────────────────────────────────────────────
section("1. Health + landing + static (no auth)")
# ─────────────────────────────────────────────────────────────────
def t_root():
    r = c.get("/")
    return (
        r.status_code == 200
        and "Personal Data Bank" in r.text
        and "Project KEY" not in r.text
    )
run("GET / -> 200 + 'Personal Data Bank' + 0 'Project KEY'", t_root)

run("GET /legacy/index.html -> 200 + rebranded",
    lambda: (lambda r: r.status_code == 200 and "Personal Data Bank" in r.text and "Project KEY" not in r.text)(c.get("/legacy/index.html")))

run("GET /legacy/app.js -> 200 + rebranded (smoke-test fix)",
    lambda: (lambda r: r.status_code == 200 and "Personal Data Bank" in r.text and "Project KEY" not in r.text)(c.get("/legacy/app.js")))

run("GET /legacy/pricing.html -> 200 + rebranded",
    lambda: (lambda r: r.status_code == 200 and "Personal Data Bank" in r.text and "Project KEY" not in r.text)(c.get("/legacy/pricing.html")))

run("GET /legacy/styles.css -> 200 (CSS unchanged)",
    lambda: c.get("/legacy/styles.css").status_code == 200)


# ─────────────────────────────────────────────────────────────────
section("2. Auth flows (positive + edge cases)")
# ─────────────────────────────────────────────────────────────────
email_a = f"smoke_a_{secrets.token_hex(4)}@test.local"
email_b = f"smoke_b_{secrets.token_hex(4)}@test.local"
PWD = "Smoke1234!"
ctx = {"token_a": None, "token_b": None}


def t_register_a():
    r = c.post("/api/auth/register", json={"email": email_a, "password": PWD, "display_name": "A"})
    if r.status_code != 200:
        return False
    j = r.json()
    ctx["token_a"] = j.get("token")
    return bool(ctx["token_a"]) and j["user"]["email"] == email_a
run("POST /api/auth/register (user A) -> token + user", t_register_a)


def t_register_b():
    r = c.post("/api/auth/register", json={"email": email_b, "password": PWD, "display_name": "B"})
    if r.status_code != 200:
        return False
    ctx["token_b"] = r.json().get("token")
    return bool(ctx["token_b"])
run("POST /api/auth/register (user B) -> token", t_register_b)


def t_register_dup():
    r = c.post("/api/auth/register", json={"email": email_a, "password": PWD, "display_name": "Dup"})
    return r.status_code in (400, 409, 422)
run("POST /api/auth/register (duplicate email) -> 4xx", t_register_dup)


def t_register_short_pwd():
    r = c.post("/api/auth/register", json={"email": f"short_{secrets.token_hex(2)}@t.local", "password": "x", "display_name": "S"})
    return r.status_code in (400, 422)
run("POST /api/auth/register (password too short) -> 4xx", t_register_short_pwd)


def t_register_invalid_email():
    r = c.post("/api/auth/register", json={"email": "not-an-email", "password": PWD, "display_name": "I"})
    return r.status_code in (400, 422)
run("POST /api/auth/register (invalid email) -> 4xx", t_register_invalid_email)


def t_login_ok():
    r = c.post("/api/auth/login", json={"email": email_a, "password": PWD})
    return r.status_code == 200 and r.json().get("token")
run("POST /api/auth/login (correct) -> 200 + token", t_login_ok)


def t_login_wrong_pwd():
    r = c.post("/api/auth/login", json={"email": email_a, "password": "wrong-password-xyz"})
    return r.status_code in (400, 401, 403)
run("POST /api/auth/login (wrong password) -> 4xx", t_login_wrong_pwd)


def t_login_unknown_user():
    r = c.post("/api/auth/login", json={"email": "nobody@nowhere.local", "password": PWD})
    return r.status_code in (400, 401, 403, 404)
run("POST /api/auth/login (unknown user) -> 4xx", t_login_unknown_user)


def t_me_ok():
    r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {ctx['token_a']}"})
    return r.status_code == 200 and r.json().get("email") == email_a
run("GET /api/auth/me with valid token -> 200 + own user", t_me_ok)


def t_me_no_token():
    r = c.get("/api/auth/me")
    return r.status_code in (401, 403)
run("GET /api/auth/me without token -> 401/403", t_me_no_token)


def t_me_bad_token():
    r = c.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    return r.status_code in (401, 403)
run("GET /api/auth/me with bad token -> 401/403", t_me_bad_token)


# ─────────────────────────────────────────────────────────────────
section("3. Profile + Personality (v6.0.0 feature must still work post-rebrand)")
# ─────────────────────────────────────────────────────────────────
H_A = {"Authorization": f"Bearer {ctx['token_a']}"}


def t_profile_get():
    r = c.get("/api/profile", headers=H_A)
    return r.status_code == 200 and "exists" in r.json()
run("GET /api/profile -> 200 + has 'exists' field", t_profile_get)


def t_personality_reference():
    """Schema (per probe):
      mbti.types -> list[16], enneagram.types -> dict{1..9},
      clifton.all -> list[34], via.all -> list[24]
    """
    r = c.get("/api/personality/reference")
    if r.status_code != 200:
        return False
    j = r.json()
    return (
        len(j["mbti"]["types"]) == 16
        and len(j["enneagram"]["types"]) == 9
        and len(j["clifton"]["all"]) == 34
        and len(j["via"]["all"]) == 24
    )
run("GET /api/personality/reference -> 16/9/34/24 (mbti.types, enneagram.types, clifton.all, via.all)",
    t_personality_reference)


def t_profile_put_personality():
    # Schema is NESTED: mbti.{type,source}, enneagram.{core,wing}
    r = c.put(
        "/api/profile",
        headers=H_A,
        json={
            "identity_summary": "Smoke test user",
            "mbti": {"type": "INTJ", "source": "official"},
            "enneagram": {"core": 5, "wing": 4},
            "clifton_top5": ["Achiever", "Learner", "Strategic"],
            "via_top5": ["Curiosity", "Love of Learning", "Judgment", "Perspective", "Honesty"],
        },
    )
    return r.status_code == 200
run("PUT /api/profile (4 personality systems, nested schema) -> 200", t_profile_put_personality)


def t_profile_get_after_put():
    r = c.get("/api/profile", headers=H_A)
    if r.status_code != 200:
        return False
    j = r.json()
    mbti = j.get("mbti") or {}
    enn = j.get("enneagram") or {}
    return (
        mbti.get("type") == "INTJ"
        and enn.get("core") == 5
        and "Achiever" in (j.get("clifton_top5") or [])
        and "Curiosity" in (j.get("via_top5") or [])
    )
run("GET /api/profile after PUT -> personality fields persisted (nested)", t_profile_get_after_put)


def t_history_after_put():
    r = c.get("/api/profile/personality/history?limit=10", headers=H_A)
    if r.status_code != 200:
        return False
    j = r.json()
    history = j.get("history", []) if isinstance(j, dict) else j
    return isinstance(history, list) and len(history) >= 4  # one entry per system
run("GET /api/profile/personality/history -> >=4 entries after PUT", t_history_after_put)


def t_profile_put_invalid_mbti():
    r = c.put("/api/profile", headers=H_A, json={"mbti": {"type": "ZZZZ", "source": "official"}})
    return r.status_code == 422
run("PUT /api/profile (invalid MBTI nested) -> 422", t_profile_put_invalid_mbti)


def t_profile_put_invalid_enneagram():
    r = c.put("/api/profile", headers=H_A, json={"enneagram": {"core": 99, "wing": 1}})
    return r.status_code == 422
run("PUT /api/profile (Enneagram core out of range, nested) -> 422", t_profile_put_invalid_enneagram)


def t_profile_put_invalid_clifton():
    """Server returns 400 (custom validator in profile.py raises HTTPException after Pydantic).
    The Pydantic validator is on length, the theme-name validator runs in profile.update_profile()."""
    r = c.put("/api/profile", headers=H_A, json={"clifton_top5": ["NotAReal Theme"]})
    if r.status_code not in (400, 422):
        return False
    body = r.json()
    detail = body.get("detail", "")
    return "INVALID_CLIFTON_THEME" in detail or "Clifton" in str(detail)
run("PUT /api/profile (invalid Clifton theme) -> 400/422 with INVALID_CLIFTON_THEME",
    t_profile_put_invalid_clifton)


def t_profile_put_too_many_clifton():
    r = c.put("/api/profile", headers=H_A,
              json={"clifton_top5": ["Achiever","Learner","Strategic","Analytical","Focus","Discipline"]})  # 6 > max 5
    return r.status_code == 422
run("PUT /api/profile (Clifton > 5 themes) -> 422", t_profile_put_too_many_clifton)


def t_profile_put_no_token():
    r = c.put("/api/profile", json={"mbti_type": "INTJ"})
    return r.status_code in (401, 403)
run("PUT /api/profile without token -> 401/403", t_profile_put_no_token)


# ─────────────────────────────────────────────────────────────────
section("4. MCP protocol surface")
# ─────────────────────────────────────────────────────────────────
mcp_ctx = {"raw": None, "token_id": None, "secret": None, "connector_path": None}


def t_mcp_info():
    r = c.get("/api/mcp/info", headers=H_A)
    if r.status_code != 200:
        return False
    j = r.json()
    mcp_ctx["secret"] = urlparse(j["mcp_connector_url"]).path.split("/")[-1]
    mcp_ctx["connector_path"] = urlparse(j["mcp_connector_url"]).path
    return j.get("version", "") == "7.0.0" or "7.0.0" in str(j.get("version", ""))
run("GET /api/mcp/info -> version 7.0.0 + connector_url has secret", t_mcp_info)


def t_mcp_tokens_create():
    r = c.post("/api/mcp/tokens", headers=H_A, json={"name": "smoke-test"})
    if r.status_code != 200:
        return False
    j = r.json()
    mcp_ctx["raw"] = j.get("raw_token")
    mcp_ctx["token_id"] = j.get("id")
    return bool(mcp_ctx["raw"]) and bool(mcp_ctx["token_id"])
run("POST /api/mcp/tokens -> 200 + raw_token + id", t_mcp_tokens_create)


def t_mcp_tokens_list():
    r = c.get("/api/mcp/tokens", headers=H_A)
    if r.status_code != 200:
        return False
    tokens = r.json().get("tokens", []) if isinstance(r.json(), dict) else r.json()
    return isinstance(tokens, list) and len(tokens) >= 1
run("GET /api/mcp/tokens -> >=1 token", t_mcp_tokens_list)


def t_mcp_initialize():
    if not (mcp_ctx["connector_path"] and mcp_ctx["raw"]):
        return False
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
    )
    if r.status_code != 200:
        return False
    s = r.json()["result"]["serverInfo"]
    return s["name"] == "personal-data-bank" and s["version"] == "7.0.0"
run("POST /mcp/{secret} initialize -> serverInfo.name='personal-data-bank' + v7.0.0", t_mcp_initialize)


def t_mcp_tools_list():
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 2},
    )
    if r.status_code != 200:
        return False
    tools = r.json().get("result", {}).get("tools", [])
    return isinstance(tools, list) and len(tools) >= 13  # plan says 13+ tools
run("POST /mcp/{secret} tools/list -> >=13 tools", t_mcp_tools_list)


def t_mcp_tools_call_get_overview():
    """get_overview returns 'Personal Data Bank — v4.1 (PDB)' system string (mcp_tools.py:1093)."""
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "tools/call", "id": 3,
              "params": {"name": "get_overview", "arguments": {}}},
    )
    if r.status_code != 200:
        return False
    body = r.json()
    if "error" in body:
        return False
    text = json.dumps(body.get("result", {}), ensure_ascii=False)
    return "Personal Data Bank" in text and "Project KEY" not in text
run("MCP tools/call get_overview -> 'Personal Data Bank' + no 'Project KEY'", t_mcp_tools_call_get_overview)


def t_mcp_tools_call_get_profile():
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "tools/call", "id": 4,
              "params": {"name": "get_profile", "arguments": {}}},
    )
    if r.status_code != 200:
        return False
    body = r.json()
    return "result" in body and "error" not in body
run("MCP tools/call get_profile -> success", t_mcp_tools_call_get_profile)


def t_mcp_tools_call_list_files():
    """MCP tools wrap response in result.content[0].text as a JSON-encoded string."""
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "tools/call", "id": 5,
              "params": {"name": "list_files", "arguments": {}}},
    )
    if r.status_code != 200:
        return False
    body = r.json()
    if "error" in body:
        return False
    content = body.get("result", {}).get("content", [])
    if not content or not isinstance(content, list):
        return False
    inner_text = content[0].get("text", "")
    try:
        inner = json.loads(inner_text)
    except (json.JSONDecodeError, ValueError):
        return False
    return "files" in inner and "Project KEY" not in inner_text
run("MCP tools/call list_files -> result.content[0].text parses to {files:...} + no 'Project KEY'",
    t_mcp_tools_call_list_files)


def t_mcp_tools_call_unknown():
    """Unknown tool name should JSON-RPC-error (not 500)."""
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "tools/call", "id": 6,
              "params": {"name": "no_such_tool_xyz", "arguments": {}}},
    )
    if r.status_code != 200:
        return False
    body = r.json()
    return "error" in body and body["error"].get("code") in (-32601, -32602, -32600)
run("MCP tools/call unknown_tool -> JSON-RPC error", t_mcp_tools_call_unknown)


def t_mcp_initialize_wrong_secret():
    r = c.post(
        f"/mcp/totally-fake-secret-{secrets.token_hex(8)}",
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "initialize", "id": 7},
    )
    # Wrong URL secret -> server can't route to a user -> JSON-RPC error or 401/404
    if r.status_code in (401, 404):
        return True
    if r.status_code == 200 and "error" in r.json():
        return True
    return False
run("MCP /initialize with wrong secret -> rejected", t_mcp_initialize_wrong_secret)


def t_mcp_initialize_no_bearer():
    """MCP auth model: URL secret IS the primary auth. Bearer is non-load-bearing here.
    initialize is the protocol handshake — should succeed with valid URL secret alone."""
    r = c.post(
        mcp_ctx["connector_path"],
        json={"jsonrpc": "2.0", "method": "initialize", "id": 8},
    )
    if r.status_code != 200:
        return False
    s = r.json().get("result", {}).get("serverInfo", {})
    # Branding still correct even without Bearer
    return s.get("name") == "personal-data-bank"
run("MCP /initialize without Bearer (URL secret = auth) -> 200 + correct serverInfo", t_mcp_initialize_no_bearer)


def t_mcp_token_revoke():
    r = c.delete(f"/api/mcp/tokens/{mcp_ctx['token_id']}", headers=H_A)
    return r.status_code in (200, 204)
run("DELETE /api/mcp/tokens/{id} -> 200/204", t_mcp_token_revoke)


def t_mcp_initialize_after_revoke():
    """initialize is URL-secret based, so revoking one bearer token doesn't affect it.
    This is by design (Bearer token only matters for tools/call user-data routing)."""
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "initialize", "id": 9},
    )
    return r.status_code == 200  # by design: URL secret still valid
run("MCP /initialize after Bearer revoke -> 200 (by design: URL secret = auth)", t_mcp_initialize_after_revoke)


# ─────────────────────────────────────────────────────────────────
section("5. Files (no LLM dependencies)")
# ─────────────────────────────────────────────────────────────────
def t_files_list_empty():
    r = c.get("/api/files", headers=H_A)
    return r.status_code == 200 and isinstance(r.json(), (list, dict))
run("GET /api/files -> 200 + list/dict", t_files_list_empty)


def t_files_list_no_auth():
    r = c.get("/api/files")
    return r.status_code in (401, 403)
run("GET /api/files without auth -> 401/403", t_files_list_no_auth)


def t_clusters_list_empty():
    r = c.get("/api/clusters", headers=H_A)
    return r.status_code == 200
run("GET /api/clusters -> 200", t_clusters_list_empty)


def t_unprocessed_count():
    r = c.get("/api/unprocessed-count", headers=H_A)
    if r.status_code != 200:
        return False
    j = r.json()
    return "unprocessed" in j and "total" in j and "processed" in j
run("GET /api/unprocessed-count -> 200 + {unprocessed,total,processed}", t_unprocessed_count)


def t_stats():
    r = c.get("/api/stats", headers=H_A)
    return r.status_code == 200
run("GET /api/stats -> 200", t_stats)


# ─────────────────────────────────────────────────────────────────
section("6. Plan / billing / usage")
# ─────────────────────────────────────────────────────────────────
def t_usage():
    r = c.get("/api/usage", headers=H_A)
    if r.status_code != 200:
        return False
    j = r.json()
    return "usage" in j or "files" in j or "plan" in j
run("GET /api/usage -> 200 + plan/usage data", t_usage)


def t_plan_limits():
    r = c.get("/api/plan-limits", headers=H_A)
    return r.status_code == 200
run("GET /api/plan-limits -> 200", t_plan_limits)


def t_billing_info():
    r = c.get("/api/billing/info", headers=H_A)
    return r.status_code == 200
run("GET /api/billing/info -> 200", t_billing_info)


# ─────────────────────────────────────────────────────────────────
section("7. Error format invariant — { error: { code, message } }")
# ─────────────────────────────────────────────────────────────────
def err_format_check(fn):
    """Assert response body is structured JSON failure: either FastAPI default
    {"detail": ...} or our convention {"error": {"code": ..., "message": ...}}."""
    r = fn()
    if r.status_code < 400:
        return False
    try:
        j = r.json()
    except Exception:
        return False
    return ("error" in j and isinstance(j["error"], dict)) or ("detail" in j)


run("Error: register dup email returns structured error",
    lambda: err_format_check(lambda: c.post("/api/auth/register",
        json={"email": email_a, "password": PWD, "display_name": "x"})))

run("Error: login wrong pwd returns structured error",
    lambda: err_format_check(lambda: c.post("/api/auth/login",
        json={"email": email_a, "password": "wrong"})))

run("Error: PUT profile with invalid nested MBTI returns structured error",
    lambda: err_format_check(lambda: c.put("/api/profile", headers=H_A,
        json={"mbti": {"type": "ZZZZ", "source": "official"}})))

run("Error: GET profile no token returns structured error",
    lambda: err_format_check(lambda: c.get("/api/profile")))

run("Error: GET file detail wrong-id returns structured error",
    lambda: err_format_check(lambda: c.get("/api/files/nonexistent-id-xyz/content", headers=H_A)))

run("Error: DELETE non-existent file returns structured error",
    lambda: err_format_check(lambda: c.delete("/api/files/nonexistent-id-xyz", headers=H_A)))

run("Error: MCP wrong secret returns structured JSON-RPC error",
    lambda: (lambda r:
        r.status_code in (401, 404) or
        (r.status_code == 200 and "error" in r.json())
    )(c.post(f"/mcp/fake-{secrets.token_hex(4)}",
             json={"jsonrpc":"2.0","method":"initialize","id":1})))


# ─────────────────────────────────────────────────────────────────
section("8. Branding correctness in API responses")
# ─────────────────────────────────────────────────────────────────
# Need a fresh MCP token since previous one was revoked
def t_fresh_token():
    r = c.post("/api/mcp/tokens", headers=H_A, json={"name": "branding-test"})
    if r.status_code != 200:
        return False
    mcp_ctx["raw"] = r.json().get("raw_token")
    return bool(mcp_ctx["raw"])
run("Refresh MCP token for branding tests", t_fresh_token)


def t_brand_in_root_html():
    r = c.get("/")
    return "Personal Data Bank" in r.text and r.text.count("Project KEY") == 0
run("Brand: HTML root has 'Personal Data Bank' + zero 'Project KEY'", t_brand_in_root_html)


def t_brand_in_app_js():
    r = c.get("/legacy/app.js")
    return "Personal Data Bank" in r.text and r.text.count("Project KEY") == 0
run("Brand: served app.js has 'Personal Data Bank' + zero 'Project KEY'", t_brand_in_app_js)


def t_brand_in_pricing():
    r = c.get("/legacy/pricing.html")
    # Email rebrand: Q1 confirmed user-answer
    return ("axis.solutions.team@gmail.com" in r.text
            and "boss@projectkey.dev" not in r.text)
run("Brand: pricing page has new email + no old 'boss@projectkey.dev'", t_brand_in_pricing)


def t_brand_mcp_init():
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "initialize", "id": 100},
    )
    s = r.json().get("result", {}).get("serverInfo", {})
    return s.get("name") == "personal-data-bank" and s.get("version") == "7.0.0"
run("Brand: MCP serverInfo.name='personal-data-bank' + version='7.0.0'", t_brand_mcp_init)


def t_brand_mcp_tools_list_descriptions_clean():
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 101},
    )
    text = json.dumps(r.json())
    # Tool descriptions should not leak old brand
    return "Project KEY" not in text
run("Brand: MCP tools/list descriptions do NOT contain 'Project KEY'", t_brand_mcp_tools_list_descriptions_clean)


def t_brand_mcp_get_overview():
    r = c.post(
        mcp_ctx["connector_path"],
        headers={"Authorization": f"Bearer {mcp_ctx['raw']}"},
        json={"jsonrpc": "2.0", "method": "tools/call", "id": 102,
              "params": {"name": "get_overview", "arguments": {}}},
    )
    text = json.dumps(r.json(), ensure_ascii=False)
    return "Personal Data Bank" in text and "Project KEY" not in text
run("Brand: MCP tools/call get_overview -> 'Personal Data Bank' + no 'Project KEY'", t_brand_mcp_get_overview)


# ─────────────────────────────────────────────────────────────────
section("9. KEEP invariants (plan rules — must NOT be touched)")
# ─────────────────────────────────────────────────────────────────
fly = open("fly.toml", encoding="utf-8").read()
run("KEEP: fly.toml app='project-key'", lambda: 'app = "project-key"' in fly)
run("KEEP: fly.toml volume source='project_key_data'",
    lambda: 'project_key_data' in fly)

cfg = open("backend/config.py", encoding="utf-8").read()
run("KEEP: config.py DATABASE_URL contains 'projectkey.db'", lambda: "projectkey.db" in cfg)
run("BUMP: config.py APP_VERSION = '7.0.0'", lambda: 'APP_VERSION = "7.0.0"' in cfg)

llm = open("backend/llm.py", encoding="utf-8").read()
run("KEEP: llm.py HTTP-Referer points to project-key.fly.dev (real URL)",
    lambda: '"HTTP-Referer": "https://project-key.fly.dev"' in llm)
run("CHANGE: llm.py X-Title = 'Personal Data Bank'",
    lambda: '"X-Title": "Personal Data Bank"' in llm)

appjs = open("legacy-frontend/app.js", encoding="utf-8").read()
run("KEEP: app.js localStorage 'projectkey_token'", lambda: "'projectkey_token'" in appjs)
run("KEEP: app.js localStorage 'projectkey_user'", lambda: "'projectkey_user'" in appjs)
run("KEEP: app.js localStorage 'projectkey_lang'", lambda: "'projectkey_lang'" in appjs)
run("CHANGE: app.js MCP template key 'personal-data-bank'", lambda: '"personal-data-bank":' in appjs)
run("CHANGE: app.js no leftover MCP template 'project-key'", lambda: '"project-key":' not in appjs)

main_py = open("backend/main.py", encoding="utf-8").read()
run("CHANGE: main.py FastAPI title='Personal Data Bank'",
    lambda: 'FastAPI(title="Personal Data Bank"' in main_py)
run("CHANGE: main.py serverInfo.name='personal-data-bank'",
    lambda: '"name": "personal-data-bank",' in main_py)

mcp_tools_py = open("backend/mcp_tools.py", encoding="utf-8").read()
run("CHANGE: mcp_tools.py system='Personal Data Bank — v4.1 (PDB)'",
    lambda: '"Personal Data Bank — v4.1 (PDB)"' in mcp_tools_py)

# Final stray-brand scan across actively-rebranded files
def t_no_stray_brand():
    targets = [
        "backend/main.py", "backend/llm.py", "backend/mcp_tools.py",
        "backend/billing.py", "backend/auth.py", "backend/database.py",
        "backend/config.py", "backend/__init__.py",
        "legacy-frontend/index.html", "legacy-frontend/pricing.html",
        "legacy-frontend/app.js",
        "tests/test_production.py", "tests/e2e-ui/ui.spec.js", "tests/e2e/test_full_e2e.py",
        "package.json", ".env.example",
        "docs/guides/USER_GUIDE_V3.md",
    ]
    for p in targets:
        with open(p, encoding="utf-8") as f:
            content = f.read()
        if "Project KEY" in content:
            print(f"      stray 'Project KEY' in {p}")
            return False
    return True
run("No stray 'Project KEY' in any actively-rebranded file", t_no_stray_brand)


# ─────────────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  RESULT: {PASS} passed / {FAIL} failed")
print(f"{'=' * 60}")
if ERRORS:
    print("\nFailures detail:")
    for n, e in ERRORS:
        print(f"  - {n}\n      {e}")
sys.exit(0 if FAIL == 0 else 1)
