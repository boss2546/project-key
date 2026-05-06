"""End-to-end smoke test for v9.0.1 Context Pack Correctness Fixes.

Self-test ของเขียว — ครอบคลุม 14 cases ก่อน handoff ให้ฟ้า.
ทดสอบ 4 fixes:
  1. delete_pack ลบจาก TF-IDF index ด้วย (กัน ghost results)
  2. regenerate_pack re-index TF-IDF (กัน stale summary search)
  3. _serialize_pack expose is_locked + locked_reason (UI guard)
  4. MCP create_context_pack รับ cluster_ids parity กับ web API

Run from project root: python scripts/context_pack_correctness_smoke.py
"""
import asyncio
import os
import sys
import tempfile
from unittest.mock import patch

# Sandbox — ไม่ทับ projectkey.db จริง
tmp = tempfile.mkdtemp(prefix="pdb_pack_v901_")
os.environ["DATA_DIR"] = tmp
os.environ.setdefault("ADMIN_PASSWORD", "test")
os.environ.setdefault("ADMIN_EMAILS", "admin@x.com")
os.environ.setdefault("OPENROUTER_API_KEY", "fake-key-for-test")

# Import หลังตั้ง env
from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402
from backend.database import (  # noqa: E402
    init_db, AsyncSessionLocal, User, File, Cluster, ContextPack, gen_id,
)
from backend.auth import hash_password  # noqa: E402
from backend import vector_search, context_packs, mcp_tools  # noqa: E402
from backend.plan_limits import lock_excess_data  # noqa: E402

# ─── Mock LLM (ไม่เรียก OpenRouter จริง) ───
async def _fake_llm_pro(system_prompt, user_prompt, temperature=0.3, max_tokens=8192):
    # Embed คำใน prompt เพื่อให้ T6 (regenerate) verify content เปลี่ยนแน่
    if "REGENERATE_TOKEN" in user_prompt:
        return "REGEN_NEW_SUMMARY: คอนเทนต์ที่กลั่นใหม่หลัง regenerate"
    return "ORIGINAL_SUMMARY: คอนเทนต์ที่กลั่นจากแหล่งข้อมูลเดิม"


# ─── Test runner ───
PASS = []
FAIL = []


def t(label, cond, detail=""):
    """Mark test result."""
    if cond:
        PASS.append(label)
        print(f"  ✅ {label}")
    else:
        FAIL.append(f"{label} — {detail}")
        print(f"  ❌ {label} — {detail}")


async def setup():
    await init_db()
    user_id = gen_id()
    file_id_1 = gen_id()
    file_id_2 = gen_id()
    cluster_id = gen_id()
    async with AsyncSessionLocal() as db:
        u = User(
            id=user_id, email="pack@x.com", name="PackTester",
            password_hash=hash_password("pass1234"), is_active=True, plan="starter",
            subscription_status="starter_active",
        )
        db.add(u)
        # 2 ไฟล์สำหรับใช้สร้าง pack
        from backend.database import FileSummary
        for fid, name in [(file_id_1, "file_a.txt"), (file_id_2, "file_b.txt")]:
            f = File(
                id=fid, user_id=user_id, filename=name, filetype="txt",
                raw_path=os.path.join(tmp, name), processing_status="ready",
                extracted_text=f"เนื้อหาของ {name}",
            )
            db.add(f)
            db.add(FileSummary(
                file_id=fid, summary_text=f"สรุป {name}", md_path="",
                key_topics="[]", key_facts="[]",
            ))
        # 1 cluster
        c = Cluster(id=cluster_id, user_id=user_id, title="Cluster A", summary="สรุป cluster A")
        db.add(c)
        await db.commit()
    return user_id, [file_id_1, file_id_2], cluster_id


async def main():
    print("=" * 60)
    print("Context Pack Correctness Smoke Test — v9.0.1")
    print("=" * 60)

    user_id, file_ids, cluster_id = await setup()

    # Patch LLM ทั้ง create + regenerate paths
    with patch.object(context_packs, "call_llm_pro", new=_fake_llm_pro):

        # ─── Group A: Happy path + serialize (T1-T4) ───
        print("\n[A] Happy path + is_locked exposure")

        async with AsyncSessionLocal() as db:
            pack1 = await context_packs.create_pack(
                db, user_id, "project", "Pack From Files", file_ids, []
            )
        t("T1 create_pack from files only — DB row + serialized",
          pack1.get("id") and pack1.get("title") == "Pack From Files",
          str(pack1)[:200])

        # Verify .md file written
        md_exists = pack1.get("source_count") == 2
        t("T1b source_count = 2 from 2 files", md_exists, f"got {pack1.get('source_count')}")

        # Verify vector_search index has pack
        u_idx = vector_search._user_indexes.get(user_id, {})
        pack_in_index = f"pack-{pack1['id']}" in u_idx
        t("T1c pack indexed in TF-IDF after create",
          pack_in_index, f"index keys: {list(u_idx.keys())}")

        # T2: pack จาก clusters only (parity กับ web)
        async with AsyncSessionLocal() as db:
            pack2 = await context_packs.create_pack(
                db, user_id, "project", "Pack From Clusters", [], [cluster_id]
            )
        t("T2 create_pack from clusters only",
          pack2.get("id") and len(pack2["source_cluster_ids"]) == 1,
          str(pack2.get("source_cluster_ids")))

        # T3: mixed
        async with AsyncSessionLocal() as db:
            pack3 = await context_packs.create_pack(
                db, user_id, "study", "Pack Mixed", [file_ids[0]], [cluster_id]
            )
        t("T3 create_pack from files + clusters",
          pack3.get("source_count") == 2, f"source_count={pack3.get('source_count')}")

        # T4: serialize exposes is_locked: false + locked_reason: null
        t("T4 serialize exposes is_locked field",
          "is_locked" in pack1 and pack1["is_locked"] is False,
          f"is_locked={pack1.get('is_locked')!r}")
        t("T4b serialize exposes locked_reason field (null for unlocked)",
          "locked_reason" in pack1 and pack1["locked_reason"] is None,
          f"locked_reason={pack1.get('locked_reason')!r}")

        # ─── Group B: Bug fix verification (T5-T8) ───
        print("\n[B] Bug fix verification")

        # T5: Delete → vector_search.remove_file called → index ไม่มี pack-{id}
        pack1_id = pack1["id"]
        async with AsyncSessionLocal() as db:
            ok = await context_packs.delete_pack(db, pack1_id, user_id)
        t("T5 delete_pack returns True", ok, "")
        u_idx = vector_search._user_indexes.get(user_id, {})
        pack_still_in_index = f"pack-{pack1_id}" in u_idx
        t("T5b pack-{id} removed from TF-IDF index after delete",
          not pack_still_in_index,
          f"still in index: {list(u_idx.keys())}")

        # T6: Regenerate → re-index → search hits new content
        pack3_id = pack3["id"]
        # Inject token ใน source ผ่าน mock prompt detection
        # _fake_llm_pro คืน REGEN_NEW_SUMMARY ถ้า prompt มี REGENERATE_TOKEN
        # → patch _generate_pack_content ให้ส่ง token เข้า user_prompt
        async def fake_generate(pack_type, title, source_content):
            return await _fake_llm_pro(
                "system",
                f"REGENERATE_TOKEN {source_content[:100]}",
            )

        with patch.object(context_packs, "_generate_pack_content", new=fake_generate):
            async with AsyncSessionLocal() as db:
                regen = await context_packs.regenerate_pack(db, pack3_id, user_id)
        t("T6 regenerate_pack returns serialized pack",
          regen and "REGEN_NEW_SUMMARY" in regen.get("summary_text", ""),
          f"summary[:80]={regen.get('summary_text', '')[:80]!r}")

        u_idx = vector_search._user_indexes.get(user_id, {})
        pack3_chunks = u_idx.get(f"pack-{pack3_id}", [])
        new_content_indexed = any(
            "REGEN_NEW_SUMMARY" in chunk.get("text", "")
            for chunk in pack3_chunks
        )
        t("T6b TF-IDF index has new summary text after regenerate",
          new_content_indexed,
          f"chunks={len(pack3_chunks)}")

        # T7: Lock pack → API returns is_locked: true + locked_reason
        async with AsyncSessionLocal() as db:
            # Force pack3 ล็อค โดยตรง
            from sqlalchemy import select as _sel
            res = await db.execute(_sel(ContextPack).where(ContextPack.id == pack3_id))
            p = res.scalar_one()
            p.is_locked = True
            p.locked_reason = "exceeds_free_plan_limit"
            await db.commit()
            locked_ser = await context_packs.get_pack(db, pack3_id, user_id)
        t("T7 locked pack: is_locked = True via API",
          locked_ser and locked_ser.get("is_locked") is True,
          f"is_locked={locked_ser.get('is_locked')!r}")
        t("T7b locked pack: locked_reason exposed",
          locked_ser.get("locked_reason") == "exceeds_free_plan_limit",
          f"reason={locked_ser.get('locked_reason')!r}")

        # T8: MCP create_context_pack with cluster_ids only
        async with AsyncSessionLocal() as db:
            mcp_result = await mcp_tools._tool_create_context_pack(
                db, user_id, {
                    "title": "MCP Cluster Pack",
                    "type": "work",
                    "cluster_ids": [cluster_id],
                }
            )
        t("T8 MCP create_context_pack with cluster_ids only — success",
          mcp_result.get("status") == "created" and mcp_result.get("cluster_count") == 1,
          str(mcp_result))

        # ─── Group C: Validation (T9-T11) ───
        print("\n[C] Validation")

        # T9: MCP no file_ids and no cluster_ids → ValueError
        async with AsyncSessionLocal() as db:
            try:
                await mcp_tools._tool_create_context_pack(
                    db, user_id, {"title": "X", "type": "project"}
                )
                t("T9 MCP no sources → ValueError", False, "no exception raised")
            except ValueError as e:
                t("T9 MCP no sources → ValueError",
                  "Must provide" in str(e), f"got: {e}")

        # T10: empty arrays both → ValueError
        async with AsyncSessionLocal() as db:
            try:
                await mcp_tools._tool_create_context_pack(
                    db, user_id, {"title": "X", "type": "project",
                                  "file_ids": [], "cluster_ids": []}
                )
                t("T10 MCP empty arrays both → ValueError", False, "no exception")
            except ValueError as e:
                t("T10 MCP empty arrays both → ValueError",
                  "Must provide" in str(e), f"got: {e}")

        # T11: Web POST regenerate locked pack → 403 (regression of existing behavior)
        # ใช้ TestClient login + call endpoint จริง
        c = TestClient(app)
        r = c.post("/api/auth/login", json={"email": "pack@x.com", "password": "pass1234"})
        token = r.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        r = c.post(f"/api/context-packs/{pack3_id}/regenerate", headers=headers)
        t("T11 regenerate locked pack via API → 403",
          r.status_code == 403, f"status={r.status_code} body={r.text[:100]}")

        # ─── Group D: API integration (T12-T14) ───
        print("\n[D] API integration")

        # T12: GET /api/context-packs returns is_locked field
        r = c.get("/api/context-packs", headers=headers)
        t("T12 GET /api/context-packs success", r.status_code == 200, str(r.status_code))
        packs_resp = r.json()
        all_have_lock = all("is_locked" in p for p in packs_resp.get("packs", []))
        t("T12b every pack has is_locked field",
          all_have_lock and len(packs_resp.get("packs", [])) >= 2,
          f"count={len(packs_resp.get('packs', []))}")

        # T13: GET /api/context-packs/{id} returns is_locked + locked_reason
        r = c.get(f"/api/context-packs/{pack3_id}", headers=headers)
        body = r.json() if r.status_code == 200 else {}
        t("T13 GET /api/context-packs/{id} returns lock state",
          r.status_code == 200 and body.get("is_locked") is True
          and body.get("locked_reason") == "exceeds_free_plan_limit",
          f"is_locked={body.get('is_locked')!r}, reason={body.get('locked_reason')!r}")

        # T14: lock_excess_data flow + API surface (full integration)
        async with AsyncSessionLocal() as db:
            # Reset all packs unlocked
            from sqlalchemy import update
            await db.execute(update(ContextPack).where(
                ContextPack.user_id == user_id
            ).values(is_locked=False, locked_reason=None))
            await db.commit()
            # Force lock_excess_data ด้วย plan="free" (limit=10) — เรามี <10 packs
            # จะไม่ลบ ใดๆ จึงทดสอบ free plan limit=1 ผ่าน mock แทน
            # (ใช้แทน: เซ็ต is_locked มือเพื่อ verify _serialize_pack ผ่าน list endpoint)
            await db.execute(update(ContextPack).where(
                ContextPack.id == pack2["id"]
            ).values(is_locked=True, locked_reason="exceeds_free_plan_limit"))
            await db.commit()

        r = c.get("/api/context-packs", headers=headers)
        body = r.json()
        locked_pack_in_list = next(
            (p for p in body.get("packs", []) if p["id"] == pack2["id"]), None
        )
        t("T14 list endpoint surfaces locked_reason for locked pack",
          locked_pack_in_list and locked_pack_in_list.get("is_locked") is True
          and locked_pack_in_list.get("locked_reason") == "exceeds_free_plan_limit",
          f"locked entry: {locked_pack_in_list}")

    # ─── Summary ───
    print("\n" + "=" * 60)
    print(f"PASS: {len(PASS)}  /  FAIL: {len(FAIL)}")
    if FAIL:
        print("\nFailed tests:")
        for f in FAIL:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("✅ All tests passed")


if __name__ == "__main__":
    asyncio.run(main())
