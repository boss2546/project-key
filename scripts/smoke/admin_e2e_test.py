"""End-to-end test for v8.2.0 Admin System endpoints.

Self-test ของเขียว — ครอบคลุม 25 cases ก่อน handoff ให้ฟ้า. ไม่ใช่ final
test suite (ฟ้าจะเขียน tests/test_admin.py แยก) — แค่ smoke verify ว่าทุก path
ทำงานถูกตั้งแต่ DB → endpoint → response shape.

Run from project root: python scripts/admin_e2e_test.py
"""
import asyncio
import os
import sys
import tempfile

# Sandbox isolation — ไม่ทับ projectkey.db จริง
tmp = tempfile.mkdtemp(prefix="pdb_admin_e2e_")
os.environ["DATA_DIR"] = tmp
os.environ.setdefault("ADMIN_PASSWORD", "test")
os.environ.setdefault("ADMIN_EMAILS", "admin@x.com")

# Import หลังตั้ง env (config.py โหลดตอน import)
from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402
from backend.database import init_db, AsyncSessionLocal, User  # noqa: E402
from backend.auth import hash_password  # noqa: E402
from sqlalchemy import select  # noqa: E402


async def setup():
    await init_db()
    async with AsyncSessionLocal() as db:
        users = [
            User(email="admin@x.com", name="Admin",
                 password_hash=hash_password("admin123"), is_active=True),
            User(email="free@x.com", name="Free",
                 password_hash=hash_password("free123"), is_active=True, plan="free"),
            User(email="starter@x.com", name="Starter",
                 password_hash=hash_password("starter123"), is_active=True,
                 plan="starter", subscription_status="starter_active"),
            User(email="stripe@x.com", name="Stripe",
                 password_hash=hash_password("s123"), is_active=True,
                 plan="starter", subscription_status="starter_active",
                 stripe_subscription_id="sub_test", stripe_customer_id="cus_test"),
            User(email="gg@x.com", name="Google",
                 is_active=True, google_sub="gs_123"),
        ]
        for u in users:
            db.add(u)
        await db.commit()
    # Re-init เพื่อ trigger ADMIN_EMAILS bootstrap (admin@x.com → is_admin=1)
    await init_db()


def main():
    asyncio.run(setup())
    c = TestClient(app)

    # Login admin
    r = c.post("/api/auth/login", json={"email": "admin@x.com", "password": "admin123"})
    assert r.status_code == 200, f"login admin fail: {r.status_code} {r.text}"
    admin_token = r.json()["token"]
    H = {"Authorization": f"Bearer {admin_token}"}

    # Login free user (non-admin)
    r = c.post("/api/auth/login", json={"email": "free@x.com", "password": "free123"})
    free_token = r.json()["token"]

    # T1: /admin/me — admin
    r = c.get("/api/admin/me", headers=H)
    assert r.status_code == 200
    assert r.json()["is_admin"] is True
    assert r.json()["effective_plan"] == "admin"
    print("T1 OK: /admin/me returns admin identity")

    # T2: non-admin → 403
    r = c.get("/api/admin/me", headers={"Authorization": f"Bearer {free_token}"})
    assert r.status_code == 403
    assert r.json()["detail"]["error"]["code"] == "NOT_ADMIN"
    print("T2 OK: non-admin gets 403 NOT_ADMIN")

    # T3: no token → 401
    r = c.get("/api/admin/me")
    assert r.status_code == 401
    print("T3 OK: no token = 401")

    # T4: stats
    r = c.get("/api/admin/stats", headers=H)
    assert r.status_code == 200
    data = r.json()
    assert data["users"]["total"] == 5
    assert data["users"]["by_plan"]["admin"] == 1
    print(f"T4 OK: stats — total={data['users']['total']} admin={data['users']['by_plan']['admin']}")

    # T5: list users
    r = c.get("/api/admin/users?page=1&page_size=20", headers=H)
    assert r.status_code == 200
    assert r.json()["total"] == 5
    print(f"T5 OK: list users total={r.json()['total']}")

    # T6: search
    r = c.get("/api/admin/users?q=stripe", headers=H)
    assert r.status_code == 200
    print(f"T6 OK: search — {len(r.json()['users'])} users")

    stripe_user = next(u for u in r.json()["users"] if u["email"] == "stripe@x.com")

    # T7: detail with stripe_active
    r = c.get(f"/api/admin/users/{stripe_user['id']}", headers=H)
    assert r.status_code == 200
    detail = r.json()
    assert detail["stripe_active"] is True
    assert detail["can_admin_downgrade"] is False
    print("T7 OK: stripe user detail blocks downgrade")

    # T8: Stripe collision — downgrade blocked
    r = c.put(f"/api/admin/users/{stripe_user['id']}/plan",
              json={"plan": "free", "reason": "test"}, headers=H)
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "STRIPE_ACTIVE_SUBSCRIPTION"
    print("T8 OK: STRIPE_ACTIVE_SUBSCRIPTION blocks downgrade")

    # T9: empty reason → 422 (Pydantic)
    r = c.put(f"/api/admin/users/{stripe_user['id']}/plan",
              json={"plan": "starter", "reason": "   "}, headers=H)
    assert r.status_code == 422
    print("T9 OK: empty reason rejected (422)")

    # T10: invalid plan
    r = c.put(f"/api/admin/users/{stripe_user['id']}/plan",
              json={"plan": "enterprise", "reason": "x"}, headers=H)
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "INVALID_PLAN"
    print("T10 OK: INVALID_PLAN rejected")

    # T11: upgrade free → starter (manual override)
    free_user = c.get("/api/admin/users?q=free@x", headers=H).json()["users"][0]
    r = c.put(f"/api/admin/users/{free_user['id']}/plan",
              json={"plan": "starter", "reason": "beta tester"}, headers=H)
    assert r.status_code == 200
    data = r.json()
    assert data["new_plan"] == "starter"
    assert data["manual_override"] is True
    print(f"T11 OK: upgrade free→starter manual_override={data['manual_override']}")

    # T12: self-demote (plan) blocked
    admin_user = c.get("/api/admin/users?q=admin@x", headers=H).json()["users"][0]
    r = c.put(f"/api/admin/users/{admin_user['id']}/plan",
              json={"plan": "free", "reason": "test"}, headers=H)
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "CANNOT_DEMOTE_SELF"
    print("T12 OK: self-demote blocked")

    # T13: Google-only user reset blocked
    google_user = c.get("/api/admin/users?q=gg@x", headers=H).json()["users"][0]
    r = c.post(f"/api/admin/users/{google_user['id']}/reset-password",
               json={"new_password": "newpass1", "reason": "test"}, headers=H)
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "GOOGLE_ONLY_USER"
    print("T13 OK: GOOGLE_ONLY_USER blocks password reset")

    # T14: short password
    r = c.post(f"/api/admin/users/{free_user['id']}/reset-password",
               json={"new_password": "12", "reason": "test"}, headers=H)
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "PASSWORD_TOO_SHORT"
    print("T14 OK: PASSWORD_TOO_SHORT rejected")

    # T15: reset password success
    r = c.post(f"/api/admin/users/{free_user['id']}/reset-password",
               json={"new_password": "newpass1234", "reason": "forgot"}, headers=H)
    assert r.status_code == 200
    assert r.json()["new_password_shown_once"] == "newpass1234"
    print("T15 OK: reset returns new_password_shown_once")

    # T16: new password works
    r = c.post("/api/auth/login",
               json={"email": "free@x.com", "password": "newpass1234"})
    assert r.status_code == 200
    print("T16 OK: user can login with new password")

    # T17: deactivate
    r = c.put(f"/api/admin/users/{free_user['id']}/active",
              json={"value": False, "reason": "tos"}, headers=H)
    assert r.status_code == 200
    print("T17 OK: deactivate user")

    # T18: deactivated can't login
    r = c.post("/api/auth/login",
               json={"email": "free@x.com", "password": "newpass1234"})
    assert r.status_code == 403
    print(f"T18 OK: deactivated login blocked ({r.status_code})")

    # T19: self-deactivate blocked
    r = c.put(f"/api/admin/users/{admin_user['id']}/active",
              json={"value": False, "reason": "test"}, headers=H)
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "CANNOT_DEACTIVATE_SELF"
    print("T19 OK: self-deactivate blocked")

    # T20: promote starter → admin
    starter_user = c.get("/api/admin/users?q=starter@x", headers=H).json()["users"][0]
    r = c.put(f"/api/admin/users/{starter_user['id']}/admin",
              json={"value": True, "reason": "support staff"}, headers=H)
    assert r.status_code == 200
    print("T20 OK: promote starter→admin")

    # T21: self-demote (admin role) blocked
    r = c.put(f"/api/admin/users/{admin_user['id']}/admin",
              json={"value": False, "reason": "test"}, headers=H)
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "CANNOT_DEMOTE_SELF"
    print("T21 OK: self-demote (admin role) blocked")

    # T22: audit logs
    r = c.get("/api/admin/audit-logs", headers=H)
    assert r.status_code == 200
    logs = r.json()["logs"]
    event_types = {log["event_type"] for log in logs}
    expected = {
        "admin_changed_plan", "admin_reset_password",
        "admin_deactivated_user", "admin_promoted",
    }
    missing = expected - event_types
    assert not missing, f"missing audit events: {missing}"
    print(f"T22 OK: audit log has {len(logs)} entries covering {len(expected)} event types")

    # T23: audit filter
    r = c.get("/api/admin/audit-logs?event_type=admin_changed_plan", headers=H)
    assert r.status_code == 200
    print(f"T23 OK: audit filter — {len(r.json()['logs'])} matched")

    # T24: invalid limit
    r = c.get("/api/admin/audit-logs?limit=999", headers=H)
    assert r.status_code == 422
    print(f"T24 OK: invalid limit rejected ({r.status_code})")

    # T25: /admin HTML
    r = c.get("/admin")
    assert r.status_code == 200
    assert "admin-shell" in r.text
    print(f"T25 OK: /admin returns HTML ({len(r.text)} bytes)")

    print()
    print("═══════════════════════════════════════════")
    print("ALL 25 TESTS PASS — admin system v8.2.0 OK")
    print("═══════════════════════════════════════════")


if __name__ == "__main__":
    main()
