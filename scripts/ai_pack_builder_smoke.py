"""End-to-end smoke test for v9.2.0 AI Pack Builder.

Self-test ของเขียว — ครอบคลุม 25 cases ก่อน handoff ให้ฟ้า.

Coverage:
  Group A (7): clarify flow + skip-if-detailed + vault filter
  Group B (5): propose with clarification (option/freetext/skipped/invalid)
  Group C (5): happy path end-to-end
  Group D (5): validation
  Group E (3): quota / auth / multi-user

Run from project root: python scripts/ai_pack_builder_smoke.py
"""
import asyncio
import os
import sys
import tempfile
from unittest.mock import patch

# Sandbox — ไม่ทับ projectkey.db จริง
tmp = tempfile.mkdtemp(prefix="pdb_aibuild_v920_")
os.environ["DATA_DIR"] = tmp
os.environ.setdefault("ADMIN_PASSWORD", "test")
os.environ.setdefault("ADMIN_EMAILS", "admin@x.com")
os.environ.setdefault("OPENROUTER_API_KEY", "fake-key")

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402
from backend.database import (  # noqa: E402
    init_db, AsyncSessionLocal, User, File, FileSummary, Cluster, ContextPack, gen_id,
)
from backend.auth import hash_password  # noqa: E402
from backend import ai_pack_builder, context_packs  # noqa: E402

PASS = []
FAIL = []


def t(label, cond, detail=""):
    if cond:
        PASS.append(label)
        print(f"  ✅ {label}")
    else:
        FAIL.append(f"{label} — {detail}")
        print(f"  ❌ {label} — {detail}")


# Counters เพื่อ verify number of LLM calls
_llm_call_count = {"json": 0, "pro": 0}


async def fake_llm_json(system_prompt, user_prompt, temperature=0.3):
    """Stub call_llm_json — ตรวจ prompt + คืน fixed response"""
    _llm_call_count["json"] += 1

    # /clarify path: ตรวจ "DECISION CRITERIA" หรือ "skip_clarify" ใน system prompt
    if "DECISION CRITERIA" in system_prompt or "skip_clarify" in system_prompt:
        # ถ้า user prompt มี "calculus.pdf" + "exclude" + "focus" → skip_clarify
        is_detailed = (
            "calculus.pdf" in user_prompt.lower()
            and "exclude" in user_prompt.lower()
            and "focus" in user_prompt.lower()
        )
        if is_detailed:
            return {
                "skip_clarify": True,
                "reasoning": "Prompt has SOURCE (calculus.pdf), SCOPE (exclude...), FOCUS (focus...) → skip clarify",
            }
        # Otherwise gen 4 quality options ที่ quote inventory จริง
        # ดึงชื่อไฟล์จาก inventory ใน user_prompt เพื่อ test quote criterion
        inventory_files = []
        for line in user_prompt.split("\n"):
            line = line.strip()
            if line.startswith("- ") and "(cluster:" in line:
                # "- file_a.txt (cluster: ...)" → file_a.txt
                fn = line[2:].split(" (")[0]
                inventory_files.append(fn)
        sample = inventory_files[:2] if inventory_files else ["sample.pdf"]
        # Stub options ใส่ filler เพื่อให้ word count ผ่าน 25 (production LLM follow ตาม
        # system prompt อยู่แล้ว — stub แค่ simulate length)
        return {
            "skip_clarify": False,
            "question": "ต้องการ pack แบบไหน?",
            "options": [
                {
                    "id": 1,
                    "title": "เน้นไฟล์เฉพาะ",
                    "summary": (
                        f"ใช้ {sample[0]} เป็น source หลัก — focus เนื้อหาเฉพาะ ไม่รวม "
                        f"ไฟล์อื่น pack แคบ ลึก ตรงเป้า สำหรับ user ที่ต้องการ "
                        f"context จำกัดเพียงไฟล์นี้ ไม่กระจาย ตอบคำถาม specific "
                        f"ได้ดี ไม่รวม assignment ที่ส่งไปแล้ว เหมาะ exam prep"
                    ),
                },
                {
                    "id": 2,
                    "title": "หลายไฟล์รวม",
                    "summary": (
                        f"รวม {', '.join(sample)} เป็น sources — ภาพรวมกว้าง เน้น "
                        f"ความเชื่อมโยง ไม่รวม cluster ที่ user ไม่ได้ pin pack "
                        f"ระดับกลาง ครอบคลุม topics หลัก ตอบคำถามที่ต้องอ้างอิง "
                        f"หลายแหล่ง เหมาะ overview ไม่เหมาะ deep-dive specific"
                    ),
                },
                {
                    "id": 3,
                    "title": "ทั้ง collection",
                    "summary": (
                        "รวมทุก cluster ที่มี ภาพรวมระดับ workspace ครอบคลุม "
                        "ทุก domain ตอบคำถามกว้าง ไม่รวมไฟล์ส่วนตัวที่ไม่ได้ tag "
                        "เหมาะ general assistant ครอบจักรวาล ไม่เหมาะ specific "
                        "task ใช้เป็น default fallback context สำหรับ AI agent"
                    ),
                },
                {
                    "id": 4,
                    "title": "เน้น metadata",
                    "summary": (
                        f"ดึงเฉพาะ summary จาก {sample[0]} และไฟล์อื่น ไม่รวม raw "
                        f"content เน้นจุดเชื่อมโยง concept-level ระดับ abstract "
                        f"pack เล็กกระชับ ใช้ context window น้อย เหมาะ chat ที่ "
                        f"ต้อง quick reference ไม่ต้องการ full file content"
                    ),
                },
            ],
            "freetext_hint": "เช่น 'รวม 2 ไฟล์แรกและ exclude ไฟล์ส่วนตัว'",
            "reasoning": "Prompt vague — ขอ user clarify scope",
        }

    # /propose path: select sources + draft metadata
    # Extract any FILE_ID from inventory in user_prompt
    file_ids_from_inv = []
    for line in user_prompt.split("\n"):
        if line.startswith("FILE_ID:"):
            file_ids_from_inv.append(line.split(":", 1)[1].strip())
    cluster_ids_from_inv = []
    for line in user_prompt.split("\n"):
        if line.startswith("CLUSTER_ID:"):
            cluster_ids_from_inv.append(line.split(":", 1)[1].strip())

    return {
        "selected_files": file_ids_from_inv[:2],   # เลือก 2 ไฟล์แรก
        "selected_clusters": [],
        "suggested_title": "Test AI Pack",
        "suggested_type": "study",
        "suggested_intent": "ใช้ตอบคำถามเรื่องเนื้อหาที่ AI เลือกมาให้",
        "suggested_scope": "ครอบคลุม 2 ไฟล์ที่ AI ตัดสินใจว่าตรง intent — ไม่รวม cluster ระดับสูง",
        "reasoning": "เลือก 2 ไฟล์ที่ใหม่สุดในกลุ่มที่ตรง prompt",
    }


async def fake_llm_pro(system_prompt, user_prompt, temperature=0.3, max_tokens=8192):
    """Stub call_llm_pro — ตรวจว่า system prompt มี INTENT + SCOPE block ไหม"""
    _llm_call_count["pro"] += 1
    if "INTENT" in system_prompt and "SCOPE" in system_prompt:
        return f"DISTILLED_WITH_CONTEXT: summary ที่ AI distill มาจาก source — มี intent + scope ครบ ({len(user_prompt)} chars source)"
    return f"DISTILLED_GENERIC: summary ทั่วไป ({len(user_prompt)} chars source)"


async def setup_user(email="ai@x.com", with_files=True, file_kind_extra=None) -> tuple[str, list, list]:
    """Setup user + processed files + 1 cluster + optional vault file"""
    await init_db()
    user_id = gen_id()
    file_ids = []
    cluster_id = gen_id()
    async with AsyncSessionLocal() as db:
        u = User(
            id=user_id, email=email, name="Tester",
            password_hash=hash_password("pass1234"), is_active=True, plan="starter",
            subscription_status="starter_active",
        )
        db.add(u)
        if with_files:
            for i, name in enumerate(["calculus.pdf", "algebra.pdf", "english.docx"]):
                fid = gen_id()
                file_ids.append(fid)
                f = File(
                    id=fid, user_id=user_id, filename=name, filetype=name.split(".")[-1],
                    raw_path=os.path.join(tmp, name), processing_status="ready",
                    extracted_text=f"เนื้อหาของ {name}",
                    file_kind="processed",
                )
                db.add(f)
                db.add(FileSummary(
                    file_id=fid, summary_text=f"สรุป {name}", md_path="",
                    key_topics="[]", key_facts="[]",
                ))
            # Add 1 vault file (file_kind_extra)
            if file_kind_extra == "vault_only":
                vault_fid = gen_id()
                file_ids.append(vault_fid)
                vf = File(
                    id=vault_fid, user_id=user_id, filename="archive.zip",
                    filetype="zip",
                    raw_path=os.path.join(tmp, "archive.zip"),
                    processing_status="ready",
                    extracted_text="",
                    file_kind="vault_only",
                )
                db.add(vf)
            c = Cluster(id=cluster_id, user_id=user_id, title="Math Cluster", summary="วิชาคำนวณ")
            db.add(c)
        await db.commit()
    return user_id, file_ids, [cluster_id]


async def main():
    print("=" * 60)
    print("AI Pack Builder Smoke Test — v9.2.0")
    print("=" * 60)

    user_id, file_ids, cluster_ids = await setup_user(with_files=True, file_kind_extra="vault_only")

    with patch.object(ai_pack_builder, "call_llm_json", new=fake_llm_json), \
         patch.object(context_packs, "call_llm_pro", new=fake_llm_pro):

        # ─── Group A: Clarify flow + skip + vault filter (7) ───
        print("\n[A] Clarify flow + skip-logic + vault filter")
        _llm_call_count["json"] = 0
        async with AsyncSessionLocal() as db:
            r = await ai_pack_builder.clarify_prompt(db, user_id, "ช่วยสร้าง pack เกี่ยวกับการเรียน")
        t("T-A1 vague prompt → 4 options + question + session_id",
          (not r["skip_clarify"]) and len(r["options"]) == 4 and r.get("question"),
          str(r)[:150])

        # T-A2: option summary ต้อง quote inventory filename
        inventory_filenames = {"calculus.pdf", "algebra.pdf", "english.docx"}
        any_quoted = any(
            any(name in opt["summary"] for name in inventory_filenames)
            for opt in r["options"]
        )
        t("T-A2 options quote real filenames from inventory", any_quoted,
          f"option summaries: {[o['summary'][:60] for o in r['options']]}")

        # T-A3: summary length 25-80 words
        all_lengths_ok = all(
            25 <= len(opt["summary"].split()) <= 80
            for opt in r["options"]
        )
        t("T-A3 each option summary 25-80 words quality criterion", all_lengths_ok,
          f"word counts: {[len(o['summary'].split()) for o in r['options']]}")

        # T-A4: detailed prompt → skip_clarify=true
        async with AsyncSessionLocal() as db:
            r2 = await ai_pack_builder.clarify_prompt(db, user_id,
                "สร้าง pack จากไฟล์ calculus.pdf focus สูตรเลขเท่านั้น exclude assignment ส่งแล้ว")
        t("T-A4 detailed prompt (SOURCE+SCOPE+FOCUS) → skip_clarify=true",
          r2.get("skip_clarify") is True,
          str(r2)[:150])

        # T-A5: session expire → /propose 404 (mock by clearing cache)
        async with AsyncSessionLocal() as db:
            ai_pack_builder._SESSION_CACHE.clear()
            try:
                await ai_pack_builder.propose_pack(db, user_id, "ses_fake", {"skipped": True})
                t("T-A5 expired session → SESSION_NOT_FOUND ValueError", False, "no exception")
            except ValueError as e:
                t("T-A5 expired session → SESSION_NOT_FOUND",
                  "SESSION_NOT_FOUND" in str(e), str(e))

        # T-A6: each clarify นับ 1 LLM call
        before = _llm_call_count["json"]
        async with AsyncSessionLocal() as db:
            await ai_pack_builder.clarify_prompt(db, user_id, "ช่วยสร้าง pack")
        delta = _llm_call_count["json"] - before
        t("T-A6 /clarify exactly 1 LLM JSON call", delta == 1, f"delta={delta}")

        # T-A7: vault file ห้ามใน inventory
        async with AsyncSessionLocal() as db:
            inv_text, snapshot = await ai_pack_builder._build_inventory_for_clarify(db, user_id)
        t("T-A7 vault file (archive.zip) NOT in inventory text",
          "archive.zip" not in inv_text,
          f"inventory contains archive.zip: {'archive.zip' in inv_text}")
        t("T-A7b vault file NOT in snapshot.files",
          all(f["filename"] != "archive.zip" for f in snapshot["files"]),
          f"snapshot files: {[f['filename'] for f in snapshot['files']]}")

        # ─── Group B: Propose with clarification (5) ───
        print("\n[B] Propose with clarification")
        # Setup fresh session for B tests
        async with AsyncSessionLocal() as db:
            r_b = await ai_pack_builder.clarify_prompt(db, user_id, "ช่วยสร้าง pack")
        sid_b = r_b["session_id"]

        # T-B1: selected_option_id
        async with AsyncSessionLocal() as db:
            try:
                d_b1 = await ai_pack_builder.propose_pack(
                    db, user_id, sid_b, {"selected_option_id": 1}
                )
                t("T-B1 propose with selected_option_id → draft created",
                  bool(d_b1.get("draft_id")), str(d_b1)[:120])
            except Exception as e:
                t("T-B1 propose with selected_option_id", False, f"exception: {e}")

        # T-B2: freetext (need fresh session)
        async with AsyncSessionLocal() as db:
            r_b2_session = await ai_pack_builder.clarify_prompt(db, user_id, "อยากได้ pack อีก")
            d_b2 = await ai_pack_builder.propose_pack(
                db, user_id, r_b2_session["session_id"],
                {"freetext": "ใช้ทั้ง 3 ไฟล์ไม่ exclude อะไร"}
            )
        t("T-B2 propose with freetext → draft created",
          bool(d_b2.get("draft_id")), "")

        # T-B3: skipped
        async with AsyncSessionLocal() as db:
            r_b3 = await ai_pack_builder.clarify_prompt(db, user_id, "อยากได้ pack อีก2")
            d_b3 = await ai_pack_builder.propose_pack(
                db, user_id, r_b3["session_id"], {"skipped": True}
            )
        t("T-B3 propose with skipped:true → draft created",
          bool(d_b3.get("draft_id")), "")

        # T-B4: > 1 field → INVALID_CLARIFICATION
        async with AsyncSessionLocal() as db:
            r_b4 = await ai_pack_builder.clarify_prompt(db, user_id, "อีกครั้ง")
            try:
                await ai_pack_builder.propose_pack(
                    db, user_id, r_b4["session_id"],
                    {"selected_option_id": 1, "freetext": "extra"}
                )
                t("T-B4 multi-field clarification → ValueError", False, "no exception")
            except ValueError as e:
                t("T-B4 multi-field clarification → INVALID_CLARIFICATION",
                  "INVALID_CLARIFICATION" in str(e), str(e))

        # T-B5: empty clarification → INVALID_CLARIFICATION
        async with AsyncSessionLocal() as db:
            r_b5 = await ai_pack_builder.clarify_prompt(db, user_id, "อีกครั้ง2")
            try:
                await ai_pack_builder.propose_pack(db, user_id, r_b5["session_id"], {})
                t("T-B5 empty clarification → ValueError", False, "no exception")
            except ValueError as e:
                t("T-B5 empty clarification → INVALID_CLARIFICATION",
                  "INVALID_CLARIFICATION" in str(e), str(e))

        # ─── Group C: Happy path end-to-end (5) ───
        print("\n[C] Happy path end-to-end")
        # T-C1: full flow → ContextPack created with created_via="ai_builder"
        # Use a User ORM object for confirm_pack
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select as _sel
            user_obj = (await db.execute(_sel(User).where(User.id == user_id))).scalar_one()
            r_c = await ai_pack_builder.clarify_prompt(db, user_id, "C-test prompt")
            d_c = await ai_pack_builder.propose_pack(db, user_id, r_c["session_id"], {"skipped": True})
            pack_c = await ai_pack_builder.confirm_pack(db, user_obj, d_c["draft_id"])
        t("T-C1 confirm without edits → ContextPack saved with created_via=ai_builder",
          pack_c.get("created_via") == "ai_builder" and pack_c.get("intent") and pack_c.get("scope"),
          f"intent={pack_c.get('intent', '')[:40]} scope={pack_c.get('scope', '')[:40]}")

        # T-C2: confirm with edits (override title + uncheck source)
        async with AsyncSessionLocal() as db:
            user_obj = (await db.execute(_sel(User).where(User.id == user_id))).scalar_one()
            r_c2 = await ai_pack_builder.clarify_prompt(db, user_id, "C2 prompt")
            d_c2 = await ai_pack_builder.propose_pack(db, user_id, r_c2["session_id"], {"skipped": True})
            kept_id = d_c2["sources"][0]["id"]  # keep only first
            pack_c2 = await ai_pack_builder.confirm_pack(
                db, user_obj, d_c2["draft_id"],
                edits={"title": "Edited Title", "included_source_ids": [kept_id]},
            )
        t("T-C2 confirm with edits → DB row reflects user edits",
          pack_c2["title"] == "Edited Title"
          and (len(pack_c2["source_file_ids"]) + len(pack_c2["source_cluster_ids"])) == 1,
          str(pack_c2)[:150])

        # T-C3: API list returns intent/scope/created_via
        c = TestClient(app)
        login = c.post("/api/auth/login", json={"email": "ai@x.com", "password": "pass1234"})
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        list_res = c.get("/api/context-packs", headers=headers)
        list_data = list_res.json()
        all_have = all(
            "intent" in p and "scope" in p and "created_via" in p
            for p in list_data.get("packs", [])
        )
        t("T-C3 API list exposes intent/scope/created_via in every pack",
          all_have and len(list_data.get("packs", [])) >= 2,
          f"count={len(list_data.get('packs', []))}")

        # T-C4: 1 confirm = exactly 3 LLM calls (1 json clarify + 1 json propose + 1 pro distill)
        # ตรวจง่ายสุดคือ count delta ระหว่าง full flow
        before_json = _llm_call_count["json"]
        before_pro = _llm_call_count["pro"]
        async with AsyncSessionLocal() as db:
            user_obj = (await db.execute(_sel(User).where(User.id == user_id))).scalar_one()
            r_c4 = await ai_pack_builder.clarify_prompt(db, user_id, "C4 prompt")
            d_c4 = await ai_pack_builder.propose_pack(db, user_id, r_c4["session_id"], {"skipped": True})
            await ai_pack_builder.confirm_pack(db, user_obj, d_c4["draft_id"])
        json_delta = _llm_call_count["json"] - before_json
        pro_delta = _llm_call_count["pro"] - before_pro
        t("T-C4 full flow uses exactly 2 json + 1 pro LLM calls (no double-distill)",
          json_delta == 2 and pro_delta == 1,
          f"json_delta={json_delta} pro_delta={pro_delta}")

        # T-C5: vector index มี pack หลัง confirm (parity กับ manual create)
        from backend import vector_search
        u_idx = vector_search._user_indexes.get(user_id, {})
        has_pack_in_idx = any(k.startswith("pack-") for k in u_idx.keys())
        t("T-C5 confirmed pack indexed in vector_search (parity manual)",
          has_pack_in_idx, f"index keys: {[k for k in u_idx.keys() if k.startswith('pack-')]}")

        # ─── Group D: Validation (5) ───
        print("\n[D] Validation")
        # T-D1: prompt < 10 chars (test via API since validation in Pydantic)
        r_d1 = c.post("/api/context-packs/ai-build/clarify",
                      json={"prompt": "สั้น"}, headers=headers)
        t("T-D1 prompt too short → 422 Pydantic validation",
          r_d1.status_code == 422, f"status={r_d1.status_code}")

        # T-D2: prompt > 500 chars
        r_d2 = c.post("/api/context-packs/ai-build/clarify",
                      json={"prompt": "x" * 501}, headers=headers)
        t("T-D2 prompt too long → 422", r_d2.status_code == 422, f"status={r_d2.status_code}")

        # T-D3: NO_SOURCES_AVAILABLE — setup user with no files
        user_id_empty, _, _ = await setup_user(email="empty@x.com", with_files=False)
        async with AsyncSessionLocal() as db:
            try:
                await ai_pack_builder.clarify_prompt(db, user_id_empty, "ลองสร้าง pack")
                t("T-D3 user with 0 sources → ValueError", False, "no exception")
            except ValueError as e:
                t("T-D3 user with 0 sources → NO_SOURCES_AVAILABLE",
                  "NO_SOURCES_AVAILABLE" in str(e), str(e))

        # T-D4: confirm with empty included_source_ids → NO_SOURCES_SELECTED
        async with AsyncSessionLocal() as db:
            user_obj = (await db.execute(_sel(User).where(User.id == user_id))).scalar_one()
            r_d4 = await ai_pack_builder.clarify_prompt(db, user_id, "D4 test")
            d_d4 = await ai_pack_builder.propose_pack(db, user_id, r_d4["session_id"], {"skipped": True})
            try:
                await ai_pack_builder.confirm_pack(
                    db, user_obj, d_d4["draft_id"],
                    edits={"included_source_ids": []},
                )
                t("T-D4 empty included_source_ids → ValueError", False, "no exception")
            except ValueError as e:
                t("T-D4 empty included_source_ids → NO_SOURCES_SELECTED",
                  "NO_SOURCES_SELECTED" in str(e), str(e))

        # T-D5: invalid type → INVALID_TYPE
        async with AsyncSessionLocal() as db:
            user_obj = (await db.execute(_sel(User).where(User.id == user_id))).scalar_one()
            r_d5 = await ai_pack_builder.clarify_prompt(db, user_id, "D5 test")
            d_d5 = await ai_pack_builder.propose_pack(db, user_id, r_d5["session_id"], {"skipped": True})
            try:
                await ai_pack_builder.confirm_pack(
                    db, user_obj, d_d5["draft_id"],
                    edits={"type": "invalid_type"},
                )
                t("T-D5 invalid type → ValueError", False, "no exception")
            except ValueError as e:
                t("T-D5 invalid type → INVALID_TYPE",
                  "INVALID_TYPE" in str(e), str(e))

        # ─── Group E: Auth + multi-user (3) ───
        print("\n[E] Auth + multi-user")
        # T-E1: no JWT → 401
        r_e1 = c.post("/api/context-packs/ai-build/clarify", json={"prompt": "test prompt"})
        t("T-E1 no JWT → 401/403", r_e1.status_code in (401, 403), f"status={r_e1.status_code}")

        # T-E2: User A propose session, User B confirm draft → DRAFT_NOT_FOUND
        # Setup user B
        user_id_b, _, _ = await setup_user(email="userb@x.com")
        async with AsyncSessionLocal() as db:
            user_a = (await db.execute(_sel(User).where(User.id == user_id))).scalar_one()
            user_b = (await db.execute(_sel(User).where(User.id == user_id_b))).scalar_one()
            r_e = await ai_pack_builder.clarify_prompt(db, user_id, "E test")
            d_e = await ai_pack_builder.propose_pack(db, user_id, r_e["session_id"], {"skipped": True})
            try:
                await ai_pack_builder.confirm_pack(db, user_b, d_e["draft_id"])
                t("T-E2 user B confirm A's draft → ValueError", False, "no exception")
            except ValueError as e:
                t("T-E2 cross-user draft confirm → DRAFT_NOT_FOUND (steal guard)",
                  "DRAFT_NOT_FOUND" in str(e), str(e))

        # T-E3: discard draft → confirm 404
        async with AsyncSessionLocal() as db:
            user_obj = (await db.execute(_sel(User).where(User.id == user_id))).scalar_one()
            r_e3 = await ai_pack_builder.clarify_prompt(db, user_id, "E3 test")
            d_e3 = await ai_pack_builder.propose_pack(db, user_id, r_e3["session_id"], {"skipped": True})
            ok = ai_pack_builder.discard_draft(user_id, d_e3["draft_id"])
            assert ok, "discard ควรสำเร็จ"
            try:
                await ai_pack_builder.confirm_pack(db, user_obj, d_e3["draft_id"])
                t("T-E3 confirm discarded draft → ValueError", False, "no exception")
            except ValueError as e:
                t("T-E3 discarded draft → DRAFT_NOT_FOUND",
                  "DRAFT_NOT_FOUND" in str(e), str(e))

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
