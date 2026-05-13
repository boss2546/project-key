"""Load test ของ admin endpoints — verify performance กับ 2000 users.

Sandbox isolated. ไม่แตะ production DB.
"""
import asyncio
import os
import tempfile
import time

tmp = tempfile.mkdtemp(prefix="pdb_admin_load_")
os.environ["DATA_DIR"] = tmp
os.environ.setdefault("ADMIN_PASSWORD", "test")
os.environ.setdefault("ADMIN_EMAILS", "admin@x.com")

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402
from backend.database import init_db, AsyncSessionLocal, User  # noqa: E402
from backend.auth import hash_password  # noqa: E402


N = 2000  # match production size hint


async def setup():
    await init_db()
    # Pre-hash password ครั้งเดียว (bcrypt ช้า ~ 100ms/hash → 2000 hashes = 200s)
    pre_hashed = hash_password("p")
    admin_hash = hash_password("admin123")
    async with AsyncSessionLocal() as db:
        admin_u = User(email="admin@x.com", name="Admin",
                       password_hash=admin_hash, is_active=True)
        db.add(admin_u)
        users = []
        for i in range(N - 1):
            email = f"user{i:04d}@example.com"
            plan = "starter" if i % 5 == 0 else "free"
            sub_status = "starter_active" if plan == "starter" else "free"
            users.append(User(
                email=email, name=f"User {i}",
                password_hash=pre_hashed,  # share hash — fine for load test
                is_active=(i % 50 != 0),
                plan=plan, subscription_status=sub_status,
            ))
        db.add_all(users)
        await db.commit()
    await init_db()


def main():
    asyncio.run(setup())
    c = TestClient(app)

    r = c.post("/api/auth/login", json={"email": "admin@x.com", "password": "admin123"})
    H = {"Authorization": f"Bearer {r.json()['token']}"}

    # Stats — measure
    t0 = time.perf_counter()
    r = c.get("/api/admin/stats", headers=H)
    t_stats = time.perf_counter() - t0
    assert r.status_code == 200
    data = r.json()
    print(f"L1: /api/admin/stats — {t_stats*1000:.0f}ms total={data['users']['total']} (expected {N})")
    assert data['users']['total'] == N

    # List users — paginate
    t0 = time.perf_counter()
    r = c.get("/api/admin/users?page=1&page_size=20", headers=H)
    t_list = time.perf_counter() - t0
    assert r.status_code == 200
    print(f"L2: /api/admin/users?page=1 — {t_list*1000:.0f}ms ({len(r.json()['users'])} users in page)")
    assert len(r.json()['users']) == 20

    # List users — last page
    last_page = (N + 19) // 20
    t0 = time.perf_counter()
    r = c.get(f"/api/admin/users?page={last_page}&page_size=20", headers=H)
    t_last = time.perf_counter() - t0
    print(f"L3: /api/admin/users?page={last_page} — {t_last*1000:.0f}ms")

    # Search by email
    t0 = time.perf_counter()
    r = c.get("/api/admin/users?q=user0042", headers=H)
    t_search = time.perf_counter() - t0
    print(f"L4: /api/admin/users?q=user0042 — {t_search*1000:.0f}ms ({len(r.json()['users'])} matched)")

    # Filter by plan=starter (post-process in Python)
    t0 = time.perf_counter()
    r = c.get("/api/admin/users?plan=starter&page_size=100", headers=H)
    t_filter = time.perf_counter() - t0
    print(f"L5: /api/admin/users?plan=starter — {t_filter*1000:.0f}ms ({len(r.json()['users'])} matched)")

    # Audit logs (empty)
    t0 = time.perf_counter()
    r = c.get("/api/admin/audit-logs", headers=H)
    t_audit = time.perf_counter() - t0
    print(f"L6: /api/admin/audit-logs — {t_audit*1000:.0f}ms ({len(r.json()['logs'])} entries)")

    # Acceptance thresholds
    print()
    print("=== Performance Check ===")
    issues = []
    if t_stats > 5.0:
        issues.append(f"⚠️ stats too slow: {t_stats*1000:.0f}ms (>5s)")
    if t_list > 1.0:
        issues.append(f"⚠️ list page=1 too slow: {t_list*1000:.0f}ms (>1s)")
    if t_search > 1.0:
        issues.append(f"⚠️ search too slow: {t_search*1000:.0f}ms (>1s)")
    if t_filter > 2.0:
        issues.append(f"⚠️ plan filter too slow: {t_filter*1000:.0f}ms (>2s)")

    if not issues:
        print(f"✅ All endpoints <{5.0}s threshold for {N} users")
    else:
        print(f"⚠️ {len(issues)} performance issue(s) at {N} users:")
        for i in issues:
            print(f"   {i}")

    print()
    print(f"Sample latencies @ {N} users:")
    print(f"  stats={t_stats*1000:.0f}ms  list={t_list*1000:.0f}ms  search={t_search*1000:.0f}ms  filter={t_filter*1000:.0f}ms")


if __name__ == "__main__":
    main()
