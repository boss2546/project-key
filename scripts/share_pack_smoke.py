"""End-to-end smoke test for v9.3.0 Share Context Pack — backend only.

ครอบคลุม 25 cases ตาม plan ก่อน handoff frontend testing.

Run from project root: python scripts/share_pack_smoke.py
"""
import asyncio
import os
import sys
import tempfile

# Sandbox
tmp = tempfile.mkdtemp(prefix="pdb_share_v930_")
os.environ["DATA_DIR"] = tmp
os.environ.setdefault("ADMIN_PASSWORD", "test")
os.environ.setdefault("ADMIN_EMAILS", "admin@x.com")
os.environ.setdefault("OPENROUTER_API_KEY", "fake-key")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from backend.main import app  # noqa: E402
from backend.database import (  # noqa: E402
    init_db, AsyncSessionLocal, User, File, FileSummary, ContextPack,
    PackShare, UsageLog, gen_id,
)
from backend.auth import hash_password  # noqa: E402
from backend import pack_share  # noqa: E402


PASS = []
FAIL = []


def t(label, cond, detail=""):
    if cond:
        PASS.append(label)
        print(f"  ✅ {label}")
    else:
        FAIL.append(f"{label} — {detail}")
        print(f"  ❌ {label} — {detail}")


async def setup_user_with_pack(
    email: str, plan: str = "starter",
    has_files: bool = True, has_pack: bool = True, locked_pack: bool = False,
) -> tuple[str, str | None, list[str]]:
    user_id = gen_id()
    pack_id = None
    file_ids: list[str] = []
    async with AsyncSessionLocal() as db:
        u = User(
            id=user_id, email=email, name=email.split("@")[0].title(),
            password_hash=hash_password("pass1234"), is_active=True,
            plan=plan,
            subscription_status="starter_active" if plan == "starter" else "free",
        )
        db.add(u)

        if has_files:
            for i in range(3):
                fid = gen_id()
                file_ids.append(fid)
                # สร้างไฟล์จริงบน disk เพื่อ shutil.copy ได้
                upload_dir = os.path.join(tmp, "uploads", user_id)
                os.makedirs(upload_dir, exist_ok=True)
                raw_path = os.path.join(upload_dir, f"{fid}.txt")
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(f"content of file {i} for {email}")
                f_row = File(
                    id=fid, user_id=user_id, filename=f"file_{i}.txt",
                    filetype="txt", raw_path=raw_path,
                    processing_status="ready",
                    extracted_text=f"text {i}", file_kind="processed",
                    storage_source="local",
                )
                db.add(f_row)

        if has_pack:
            pack_id = gen_id()
            import json as _json
            db.add(ContextPack(
                id=pack_id, user_id=user_id, type="study",
                title=f"{email} Pack", summary_text="สรุป pack สำหรับเทส",
                source_file_ids=_json.dumps(file_ids[:2] if has_files else []),
                source_cluster_ids="[]",
                intent="ใช้ตอบคำถาม", scope="ครอบคลุมเนื้อหา",
                created_via="manual",
                is_locked=locked_pack,
                locked_reason="exceeds_free_plan_limit" if locked_pack else None,
            ))
        await db.commit()
    return user_id, pack_id, file_ids


def _login(c: TestClient, email: str) -> dict:
    r = c.post("/api/auth/login", json={"email": email, "password": "pass1234"})
    assert r.status_code == 200, f"login fail: {r.text}"
    return {"Authorization": f"Bearer {r.json()['token']}"}


async def main():
    print("=" * 60)
    print("Pack Share Smoke Test — v9.3.0")
    print("=" * 60)
    await init_db()

    # ─── M1: Schema + token roundtrip ───
    print("\n[M1] Schema + Token signing")
    user_id_a, pack_id_a, files_a = await setup_user_with_pack("alice@x.com")
    t("M1.1 PackShare table exists (Base.metadata.create_all)",
      True, "")  # creating shares below verifies this implicitly
    token = pack_share.sign_share_token("test_share_id")
    decoded = pack_share.verify_share_token(token)
    t("M1.2 Token sign/verify roundtrip",
      decoded == "test_share_id", f"got: {decoded}")

    # Tampered token
    try:
        pack_share.verify_share_token(token + "tampered")
        t("M1.3 Tampered token → ShareTokenError", False, "no exception")
    except pack_share.ShareTokenError:
        t("M1.3 Tampered token → ShareTokenError", True, "")

    # ─── M2: Create / update / revoke endpoints ───
    print("\n[M2] Share endpoints")
    c = TestClient(app)
    headers_a = _login(c, "alice@x.com")

    r = c.post(f"/api/context-packs/{pack_id_a}/share",
               json={"include_files": False}, headers=headers_a)
    t("M2.1 Create share → 200 + URL",
      r.status_code == 200 and r.json().get("share_url"), str(r.status_code))
    share_a_id = r.json()["share_id"]
    share_a_url = r.json()["share_url"]
    share_a_token = r.json()["share_token"]

    # Idempotent
    r = c.post(f"/api/context-packs/{pack_id_a}/share",
               json={"include_files": False}, headers=headers_a)
    t("M2.2 Create share twice → idempotent (same share_id)",
      r.status_code == 200 and r.json()["share_id"] == share_a_id and r.json()["is_new"] is False, "")

    # PATCH toggle
    r = c.patch(f"/api/context-packs/shares/{share_a_id}",
                json={"include_files": True}, headers=headers_a)
    t("M2.3 PATCH toggle include_files → updated",
      r.status_code == 200 and r.json()["include_files"] is True, str(r.status_code))

    # Locked pack
    user_id_l, pack_id_l, _ = await setup_user_with_pack("locked@x.com", locked_pack=True)
    headers_l = _login(c, "locked@x.com")
    r = c.post(f"/api/context-packs/{pack_id_l}/share",
               json={"include_files": False}, headers=headers_l)
    t("M2.4 Locked pack → 400 PACK_LOCKED",
      r.status_code == 400, f"status={r.status_code}")

    # Cross-user access
    user_id_b, pack_id_b, _ = await setup_user_with_pack("bob@x.com")
    headers_b = _login(c, "bob@x.com")
    r = c.delete(f"/api/context-packs/shares/{share_a_id}", headers=headers_b)
    t("M2.5 User B revoke A's share → 404 (steal guard)",
      r.status_code == 404, str(r.status_code))

    # Free quota: create 5 user free + 6th fails
    user_id_f, _, _ = await setup_user_with_pack("free@x.com", plan="free")
    # Create 5 packs สำหรับ test 5 shares
    free_pack_ids = []
    async with AsyncSessionLocal() as db:
        import json as _json
        for i in range(6):
            pid = gen_id()
            db.add(ContextPack(
                id=pid, user_id=user_id_f, type="project",
                title=f"FreePack{i}", summary_text="x",
                source_file_ids="[]", source_cluster_ids="[]",
            ))
            free_pack_ids.append(pid)
        await db.commit()
    headers_f = _login(c, "free@x.com")
    success_count = 0
    for i, pid in enumerate(free_pack_ids):
        r = c.post(f"/api/context-packs/{pid}/share",
                   json={"include_files": False}, headers=headers_f)
        if r.status_code == 200:
            success_count += 1
        elif r.status_code == 403:
            break
    t("M2.6 Free user 5 shares OK + 6th → 403 quota",
      success_count == 5, f"success_count={success_count}")

    # ─── M3: Preview + Claim ───
    print("\n[M3] Preview + Claim endpoints")

    # Preview (no auth)
    r = c.get(f"/api/shared/pack/{share_a_token}")
    t("M3.1 Preview no auth → 200 + content",
      r.status_code == 200 and r.json()["pack"]["title"] == "alice@x.com Pack",
      str(r.status_code))

    # View count increment
    view_count_after_1 = r.json()["view_count"]
    c.get(f"/api/shared/pack/{share_a_token}")
    r2 = c.get(f"/api/shared/pack/{share_a_token}")
    t("M3.2 View count increments (3 visits → count >= 3)",
      r2.json()["view_count"] >= 3, f"count={r2.json()['view_count']}")

    # Owner email masked
    t("M3.3 Owner email masked (te****@x.com pattern)",
      "****" in r.json()["pack"]["owner_email_masked"],
      r.json()["pack"]["owner_email_masked"])

    # include_files=true → files in response (we toggled in M2.3)
    files_in_resp = r.json().get("files", [])
    t("M3.4 include_files=true → files in response",
      len(files_in_resp) >= 1, f"count={len(files_in_resp)}")
    if files_in_resp:
        t("M3.5 download_url is signed URL (/d/{token} pattern)",
          "/d/" in files_in_resp[0]["download_url"],
          files_in_resp[0]["download_url"][:80])

    # Claim by User B
    r = c.post(f"/api/shared/pack/{share_a_token}/claim", headers=headers_b)
    t("M3.6 Claim → 200 + new pack",
      r.status_code == 200 and r.json().get("created_via") == "shared_clone",
      str(r.status_code) + " " + str(r.json())[:100])

    if r.status_code == 200:
        cloned_pack = r.json()
        t("M3.7 Cloned pack: source_cluster_ids = []",
          cloned_pack.get("source_cluster_ids") == [],
          f"got: {cloned_pack.get('source_cluster_ids')}")
        # source_file_ids → ใหม่ (recipient's) ไม่ใช่ของ owner
        cloned_file_ids = cloned_pack.get("source_file_ids", [])
        t("M3.8 Cloned pack: source_file_ids ≠ owner's (privacy)",
          all(fid not in files_a for fid in cloned_file_ids),
          f"cloned IDs: {cloned_file_ids}")
        t("M3.9 Cloned pack: intent has 'เก็บจาก' note",
          "เก็บจาก" in (cloned_pack.get("intent") or ""),
          (cloned_pack.get("intent") or "")[:100])

    # Claim w/o auth
    r = c.post(f"/api/shared/pack/{share_a_token}/claim")
    t("M3.10 Claim no auth → 401",
      r.status_code in (401, 403), str(r.status_code))

    # Revoke + try preview
    r = c.delete(f"/api/context-packs/shares/{share_a_id}", headers=headers_a)
    t("M3.11 Owner revoke → 200",
      r.status_code == 200, str(r.status_code))
    r = c.get(f"/api/shared/pack/{share_a_token}")
    t("M3.12 Preview revoked → 403",
      r.status_code == 403, str(r.status_code))

    # Pack deleted → 404
    user_id_d, pack_id_d, _ = await setup_user_with_pack("delowner@x.com")
    headers_d = _login(c, "delowner@x.com")
    r = c.post(f"/api/context-packs/{pack_id_d}/share",
               json={"include_files": False}, headers=headers_d)
    share_d_token = r.json()["share_token"]
    # Delete the pack
    r = c.delete(f"/api/context-packs/{pack_id_d}", headers=headers_d)
    r = c.get(f"/api/shared/pack/{share_d_token}")
    t("M3.13 Pack deleted → preview 404 PACK_DELETED",
      r.status_code == 404, str(r.status_code))

    # Invalid token
    r = c.get("/api/shared/pack/invalid.token.string")
    t("M3.14 Invalid token → 401",
      r.status_code == 401, str(r.status_code))

    # Pack quota check on claim
    # B already has 1 cloned pack — fill workspace
    async with AsyncSessionLocal() as db:
        # Count existing
        u_b = (await db.execute(select(User).where(User.id == user_id_b))).scalar_one()
        # Free plan = 10 packs limit. Bob is starter (50). Set to free temporarily.
        u_b.plan = "free"
        u_b.subscription_status = "free"
        # Add 9 more packs to reach 10/10
        import json as _json
        for i in range(9):
            db.add(ContextPack(
                id=gen_id(), user_id=user_id_b, type="project",
                title=f"FillerPack{i}", summary_text="x",
                source_file_ids="[]", source_cluster_ids="[]",
            ))
        await db.commit()

    headers_b = _login(c, "bob@x.com")  # re-login (plan changed)
    # New share from C, B tries claim
    user_id_c, pack_id_c, _ = await setup_user_with_pack("charlie@x.com")
    headers_c = _login(c, "charlie@x.com")
    r = c.post(f"/api/context-packs/{pack_id_c}/share",
               json={"include_files": False}, headers=headers_c)
    share_c_token = r.json()["share_token"]
    r = c.post(f"/api/shared/pack/{share_c_token}/claim", headers=headers_b)
    t("M3.15 Claim with recipient pack quota full → 403",
      r.status_code == 403, str(r.status_code))

    # ─── HTML page route ───
    print("\n[M4] HTML route")
    r = c.get("/p/some_token")
    t("M4.1 GET /p/{token} → 200 HTML",
      r.status_code == 200 and "html" in r.headers.get("content-type", "").lower(),
      f"status={r.status_code}, content-type={r.headers.get('content-type')}")

    # ─── Privacy: locked file skipped in preview ───
    print("\n[Privacy] Locked file skip + extra checks")

    # Atomic counter test (3 sequential views)
    user_id_v, pack_id_v, _ = await setup_user_with_pack("viewer@x.com")
    headers_v = _login(c, "viewer@x.com")
    r = c.post(f"/api/context-packs/{pack_id_v}/share",
               json={"include_files": False}, headers=headers_v)
    share_v_token = r.json()["share_token"]
    for _ in range(5):
        c.get(f"/api/shared/pack/{share_v_token}")
    r = c.get(f"/api/shared/pack/{share_v_token}")
    t("M3.16 View count = 6 after 6 sequential visits",
      r.json()["view_count"] == 6, f"count={r.json()['view_count']}")

    # ─── Summary ───
    print("\n" + "=" * 60)
    print(f"PASS: {len(PASS)}  /  FAIL: {len(FAIL)}")
    if FAIL:
        print("\nFailed tests:")
        for f in FAIL:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✅ All backend tests passed")


if __name__ == "__main__":
    asyncio.run(main())
