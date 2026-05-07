# Plan: Context Pack Correctness Fixes — v8.3.0

> **Status:** `plan_pending_approval`
> **Author:** 🔴 แดง (Daeng) — 2026-05-07
> **Foundation:** v8.2.0 master HEAD `2fa251c`
> **Scope philosophy:** Correctness only — NO new features. Feature work (auto-suggest, cluster selector, refresh quota change, empty state redesign) เลื่อนไป v8.4.0
> **Estimated effort:** เขียว ~0.5–1 day · ฟ้า ~0.5 day
> **Risk:** 🟢 Low — แก้ data consistency, ไม่กระทบ contract สาธารณะ

---

## 🎯 Goal & Context

### Why
จาก deep-dive 2026-05-07: ระบบ Context Pack ใน DB จริงตอนนี้ **0 rows / 76 users** (adoption = 0%) แต่ก่อนพัฒนา feature ต่อ ต้องแน่ใจว่า "ของเดิมทำงานถูก" ก่อน — ไม่งั้นเพิ่ม feature ใหม่บนพื้นฐานที่บั๊ก = ขยายปัญหา

### Goals
1. **Vector search consistency** — Pack ที่ลบ/regenerate ต้อง reflect ใน TF-IDF index ทันที
2. **API contract complete** — `is_locked` ปรากฏใน serialize เพื่อ UI guard ถูกต้อง
3. **MCP/Web parity** — `create_context_pack` MCP tool รับ `cluster_ids` ตามที่ schema อนุญาต (ปัจจุบันตัดทิ้ง)
4. **UX consistency** — Frontend แสดง state locked ของ pack ก่อนที่ user จะกด regenerate แล้วเจอ 403

### Non-goals (เลื่อน v8.4.0+)
- ❌ Pack auto-suggest หลัง organize-new
- ❌ Cluster selector ใน UI Create Modal
- ❌ Free tier refresh quota change (ปัจจุบัน 0 → suggest 5 ครั้ง — เลื่อน)
- ❌ Empty state redesign + use case examples
- ❌ TF-IDF index persistence (architectural — แยก track)
- ❌ Duplicate title check
- ❌ Plan limit cost guard / rate-limit

---

## 📁 Files to Create / Modify

| File | Action | Reason |
|------|--------|--------|
| [backend/context_packs.py](../../backend/context_packs.py) | **modify** | (1) เพิ่ม `vector_search.remove_file()` ใน `delete_pack` (2) เพิ่ม re-index ใน `regenerate_pack` (3) expose `is_locked` + `locked_reason` ใน `_serialize_pack()` |
| [backend/mcp_tools.py](../../backend/mcp_tools.py) | **modify** | `_tool_create_context_pack` รับ `cluster_ids` + ส่งต่อให้ `create_pack` + อัปเดต tool schema descriptor |
| [legacy-frontend/app.js](../../legacy-frontend/app.js) | **modify** | Render: ถ้า `pack.is_locked` → แสดง badge "🔒 ล็อค" + ปุ่ม Regenerate disabled + tooltip; ใน `regeneratePack()` preflight ถ้า locked → toast แจ้งทันทีไม่เรียก API |
| [legacy-frontend/styles.css](../../legacy-frontend/styles.css) | **modify** | เพิ่ม `.pack-card.is-locked` + `.pack-locked-badge` style (~15 บรรทัด) |
| [scripts/context_pack_correctness_smoke.py](../../scripts/) | **create** | 14-case in-process smoke test (ฟ้าใช้ verify) |

**ไม่แตะ:** schema, plan_limits, billing, retriever, graph_builder, main.py routes (no API path/method change)

---

## 🔌 API Changes

### `GET /api/context-packs` + `GET /api/context-packs/{id}` — Response (additive only)

**Before (ใน `_serialize_pack`):**
```json
{
  "id": "...",
  "type": "project",
  "type_label": "โปรเจกต์",
  "type_icon": "🎯",
  "title": "...",
  "summary_text": "...",
  "source_file_ids": [...],
  "source_cluster_ids": [...],
  "source_count": 3,
  "created_at": "...",
  "updated_at": "..."
}
```

**After (เพิ่ม 2 fields):**
```json
{
  ...existing fields...,
  "is_locked": false,                          // NEW
  "locked_reason": null                        // NEW — null | "exceeds_free_plan_limit" | "subscription_expired"
}
```

**Backward compat:** ✅ Additive — old clients (ไม่อ่าน fields ใหม่) ทำงานต่อได้

### MCP Tool `create_context_pack` — Schema (additive only)

**Before:**
```json
{
  "name": "create_context_pack",
  "params": [
    {"name": "title", "type": "string", "required": true},
    {"name": "type", "type": "string", "required": true},
    {"name": "file_ids", "type": "array", "required": true}
  ]
}
```

**After:**
```json
{
  "name": "create_context_pack",
  "params": [
    {"name": "title", "type": "string", "required": true},
    {"name": "type", "type": "string", "required": true},
    {"name": "file_ids", "type": "array", "required": false},      // CHANGED required→false
    {"name": "cluster_ids", "type": "array", "required": false}    // NEW
  ]
}
```

**Validation rule (matches web API):** ต้องมี `file_ids` หรือ `cluster_ids` อย่างน้อย 1 list ที่ไม่ว่าง — ไม่งั้น `ValueError("Must provide file_ids or cluster_ids")`

**Backward compat:** ✅ Existing MCP clients ที่ส่งแค่ `file_ids` ทำงานต่อได้ (file_ids ยังรับเป็น array)

### `POST /api/context-packs/{id}/regenerate` — Side-effect change

**Before:** อัปเดต DB row + .md file → คืน serialized pack
**After:** อัปเดต DB row + .md file + **TF-IDF re-index** → คืน serialized pack

**Backward compat:** ✅ Response ไม่เปลี่ยน — แค่ side-effect ภายในถูกต้องขึ้น

### `DELETE /api/context-packs/{id}` — Side-effect change

**Before:** ลบ DB row + .md file → `{"status": "ok"}`
**After:** ลบ DB row + .md file + **TF-IDF index entry** → `{"status": "ok"}`

**Backward compat:** ✅ Response ไม่เปลี่ยน

---

## 🗄️ Data Model Changes

**ไม่มี** — schema คงเดิม (`is_locked`, `locked_reason` มีอยู่แล้วตั้งแต่ v5.9.3 — แค่เพิ่ม serialize)

---

## 🛠️ Step-by-Step Implementation (สำหรับเขียว)

### Phase 1 — Backend: `context_packs.py` (3 changes)

**Change 1.1: `_serialize_pack()` expose lock state**

ที่ไฟล์ [backend/context_packs.py:259-273](../../backend/context_packs.py#L259) — แก้ function ให้คืน 2 fields เพิ่ม:

```python
def _serialize_pack(pack: ContextPack) -> dict:
    """Serialize a ContextPack to dict."""
    return {
        "id": pack.id,
        "type": pack.type,
        "type_label": PACK_TYPE_LABELS.get(pack.type, pack.type),
        "type_icon": PACK_TYPE_ICONS.get(pack.type, "📦"),
        "title": pack.title,
        "summary_text": pack.summary_text or "",
        "source_file_ids": json.loads(pack.source_file_ids) if pack.source_file_ids else [],
        "source_cluster_ids": json.loads(pack.source_cluster_ids) if pack.source_cluster_ids else [],
        "source_count": len(json.loads(pack.source_file_ids or "[]")) + len(json.loads(pack.source_cluster_ids or "[]")),
        "created_at": pack.created_at.isoformat() if pack.created_at else "",
        "updated_at": pack.updated_at.isoformat() if pack.updated_at else "",
        # v8.3.0 — UI guard: client รู้ก่อนกด regenerate ว่า pack ล็อคหรือไม่
        "is_locked": bool(getattr(pack, "is_locked", False)),
        "locked_reason": getattr(pack, "locked_reason", None),
    }
```

**Change 1.2: `delete_pack()` remove from vector index**

ที่ไฟล์ [backend/context_packs.py:143-161](../../backend/context_packs.py#L143) — เพิ่ม `vector_search.remove_file()` หลัง delete DB row:

```python
async def delete_pack(db: AsyncSession, pack_id: str, user_id: str) -> bool:
    """Delete a context pack."""
    result = await db.execute(
        select(ContextPack).where(
            ContextPack.id == pack_id,
            ContextPack.user_id == user_id
        )
    )
    pack = result.scalar_one_or_none()
    if not pack:
        return False

    # Delete .md file
    if pack.md_path and os.path.exists(pack.md_path):
        os.remove(pack.md_path)

    await db.delete(pack)
    await db.commit()

    # v8.3.0 — Bug fix: ลบจาก TF-IDF index ด้วย กัน ghost results ใน chat/MCP search.
    # remove_file is no-op ถ้า pack-id ไม่อยู่ใน user's index (เช่น หลัง restart ก่อน rebuild)
    vector_search.remove_file(f"pack-{pack_id}", user_id=user_id)

    return True
```

**Change 1.3: `regenerate_pack()` re-index vector**

ที่ไฟล์ [backend/context_packs.py:164-216](../../backend/context_packs.py#L164) — เพิ่ม `vector_search.index_file()` ก่อน return (หลัง commit):

```python
    pack.summary_text = new_summary
    pack.updated_at = datetime.utcnow()

    # Update .md file
    if pack.md_path:
        with open(pack.md_path, 'w', encoding='utf-8') as f:
            f.write(f"---\ntype: {pack.type}\ntitle: {pack.title}\n---\n\n{new_summary}")

    await db.commit()

    # v8.3.0 — Bug fix: re-index TF-IDF เพื่อให้ search/RAG เห็น summary ใหม่
    # (index_file overwrites by file_id key — ปลอดภัย idempotent)
    vector_search.index_file(
        file_id=f"pack-{pack.id}",
        filename=f"context-pack:{pack.title}",
        text=new_summary,
        cluster_title=f"context-pack-{pack.type}",
        user_id=user_id,
    )

    return _serialize_pack(pack)
```

### Phase 2 — Backend: `mcp_tools.py` (2 changes)

**Change 2.1: Tool descriptor schema**

ที่ไฟล์ [backend/mcp_tools.py:127-137](../../backend/mcp_tools.py#L127) — แก้ `params`:

```python
"create_context_pack": {
    "name": "create_context_pack",
    "description": "Create a new context pack from selected files and/or collections. Types: profile, study, work, project. Must provide at least one of file_ids or cluster_ids.",
    "params": [
        {"name": "title", "type": "string", "required": True},
        {"name": "type", "type": "string", "required": True},
        {"name": "file_ids", "type": "array", "required": False},
        {"name": "cluster_ids", "type": "array", "required": False},  # v8.3.0
    ],
    "category": "edit",
    "annotations": {"title": "Create Pack", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
},
```

**Change 2.2: `_tool_create_context_pack()` accept cluster_ids**

ที่ไฟล์ [backend/mcp_tools.py:980-1003](../../backend/mcp_tools.py#L980) — แก้ function:

```python
async def _tool_create_context_pack(db: AsyncSession, user_id: str, params: dict) -> dict:
    """Create a new context pack."""
    title = params.get("title")
    pack_type = params.get("type")
    file_ids = params.get("file_ids", []) or []
    cluster_ids = params.get("cluster_ids", []) or []

    if not title:
        raise ValueError("title is required")
    if not pack_type:
        raise ValueError("type is required")
    if pack_type not in {"profile", "study", "work", "project"}:
        raise ValueError("type must be one of: profile, study, work, project")
    if not file_ids and not cluster_ids:
        raise ValueError("Must provide file_ids or cluster_ids (at least one non-empty list)")

    # v8.3.0 — parity กับ web POST /api/context-packs (เดิม MCP ตัด cluster_ids ทิ้ง)
    pack = await create_pack(db, user_id, pack_type, title, file_ids, cluster_ids)

    return {
        "status": "created",
        "pack_id": pack.get("id", ""),
        "title": title,
        "type": pack_type,
        "file_count": len(file_ids),
        "cluster_count": len(cluster_ids),
    }
```

### Phase 3 — Frontend: `app.js` + `styles.css`

**Change 3.1: Render locked state**

ที่ไฟล์ [legacy-frontend/app.js:2175-2190](../../legacy-frontend/app.js#L2175) — แก้ pack card template:

```javascript
html += data.packs.map(p => {
  const lockedClass = p.is_locked ? 'is-locked' : '';
  const lockedBadge = p.is_locked
    ? `<span class="pack-locked-badge" title="${getLang() === 'th' ? 'ล็อค (เกินโควต้าแพลน) — อัปเกรดเพื่อปลดล็อค' : 'Locked (exceeds plan limit) — upgrade to unlock'}">🔒</span>`
    : '';
  const regenDisabled = p.is_locked ? 'disabled' : '';
  const regenTitle = p.is_locked
    ? (getLang() === 'th' ? 'ล็อคอยู่ — regenerate ไม่ได้' : 'Locked — cannot regenerate')
    : 'Regenerate';
  return `
    <div class="pack-card ${lockedClass}" data-pack-id="${p.id}">
      <div class="pack-card-header">
        <div class="pack-card-title">${lockedBadge} ${escapeHtml(p.title)}</div>
        <div class="pack-card-actions">
          <button onclick="regeneratePack('${p.id}')" title="${regenTitle}" ${regenDisabled}>🔄</button>
          <button class="btn-danger" onclick="deletePack('${p.id}')" title="Delete">🗑</button>
        </div>
      </div>
      <div class="pack-card-summary">${escapeHtml(p.summary_text?.substring(0, 200) || '')}${p.summary_text?.length > 200 ? '...' : ''}</div>
      <div class="pack-card-meta">
        <span class="badge">${p.type}</span>
        ${p.created_at ? `<span>${formatDate(p.created_at)}</span>` : ''}
      </div>
    </div>`;
}).join('');
```

**Change 3.2: Preflight check ใน `regeneratePack()`**

ที่ไฟล์ [legacy-frontend/app.js:2376-2393](../../legacy-frontend/app.js#L2376) — เพิ่ม early return ถ้า card มี `.is-locked`:

```javascript
async function regeneratePack(packId) {
  // v8.3.0 — preflight: ถ้า pack ล็อค ไม่เรียก API (กัน 403 toast ที่ผู้ใช้สับสน)
  const card = document.querySelector(`[data-pack-id="${packId}"]`);
  if (card && card.classList.contains('is-locked')) {
    showToast(
      getLang() === 'th'
        ? 'Pack นี้ถูกล็อค — อัปเกรดเป็น Starter เพื่อปลดล็อค'
        : 'This pack is locked — upgrade to Starter to unlock',
      'warning'
    );
    return;
  }
  try {
    showToast(getLang() === 'th' ? 'กำลัง regenerate...' : 'Regenerating...', 'info');
    const res = await authFetch(`/api/context-packs/${packId}/regenerate`, { method: 'POST' });
    // ...rest unchanged
```

**Change 3.3: CSS for locked state**

ที่ไฟล์ [legacy-frontend/styles.css](../../legacy-frontend/styles.css) — เพิ่มต่อท้าย section pack (~บรรทัด 2470+):

```css
/* v8.3.0 — Locked pack visual state */
.pack-card.is-locked {
  opacity: 0.65;
  border-color: rgba(255, 255, 255, 0.06);
}
.pack-card.is-locked .pack-card-actions button:first-child {
  cursor: not-allowed;
  opacity: 0.5;
}
.pack-locked-badge {
  display: inline-block;
  margin-right: 4px;
  font-size: 0.85em;
  color: var(--warning);
}
```

### Phase 4 — Self-test script: `scripts/context_pack_correctness_smoke.py`

In-process test (ใช้ TestClient จาก FastAPI / direct SQLAlchemy ไม่ผ่าน HTTP เพื่อเร็ว) ตาม pattern [scripts/admin_e2e_test.py](../../scripts/admin_e2e_test.py).

ครอบคลุม Test Scenarios ด้านล่าง — เป้าหมาย **14/14 PASS**

---

## 🧪 Test Scenarios (สำหรับฟ้า — และ self-test ของเขียวก่อน handoff)

### Happy path (4)
- **T1** Create pack จาก files only → verify DB row + .md file + vector index มี `pack-{id}`
- **T2** Create pack จาก clusters only → verify success (web API path)
- **T3** Create pack จาก files + clusters mixed → verify combined source ใน LLM prompt
- **T4** API GET /api/context-packs returns `is_locked: false` for new pack

### Bug fix verification (4)
- **T5** Delete pack → vector_search.remove_file ถูกเรียก → search "pack-{id}" returns no hit
- **T6** Regenerate pack → summary เปลี่ยน → vector_search.index_file overwrites → search returns ใหม่
- **T7** Lock pack via `lock_excess_data` → API GET returns `is_locked: true` + `locked_reason: "exceeds_free_plan_limit"`
- **T8** MCP `create_context_pack` with `cluster_ids` only → DB row stores cluster_ids array, file_ids = []

### Validation (3)
- **T9** MCP `create_context_pack` with neither file_ids nor cluster_ids → ValueError
- **T10** MCP `create_context_pack` with empty arrays for both → ValueError
- **T11** Web POST regenerate locked pack → 403 (existing behavior, regression)

### Frontend integration (3 — Playwright หรือ manual smoke)
- **T12** UI: Create pack → card แสดงปุ่ม regenerate enabled, ไม่มี lock badge
- **T13** UI: Pack ล็อค (set is_locked=true ใน DB ตรง) → reload → card opacity drop + 🔒 badge + ปุ่ม regenerate disabled + tooltip
- **T14** UI: คลิก regenerate บน locked card → toast warning ทันที, ไม่มี network call

### Regression (run after change)
- 67/67 ของ admin_e2e (v8.2.0) ยัง pass
- Auth + signed URLs + email + plan limits regression — pass
- Python syntax all modified files

---

## ✅ Done Criteria

- [ ] 4 backend changes shipped + python syntax clean
- [ ] 3 frontend changes shipped + JS syntax clean
- [ ] 1 CSS change shipped
- [ ] `scripts/context_pack_correctness_smoke.py` 14/14 PASS
- [ ] v8.2.0 regression suite (admin + auth + plan_limits + signed_urls) ยัง PASS
- [ ] APP_VERSION bump 8.2.0 → 8.3.0 ใน [config.py:12](../../backend/config.py#L12) และ [app.html](../../legacy-frontend/app.html) version label
- [ ] Memory updated: pipeline-state.md → `built_pending_review` แล้วก็ done หลัง user approve
- [ ] Commit แยก 3 logical:
  1. `fix(context-pack): vector index sync on delete + regenerate [v8.3.0]`
  2. `fix(context-pack): expose is_locked in API + UI lock guard [v8.3.0]`
  3. `fix(mcp): create_context_pack accept cluster_ids parity with web [v8.3.0]`
  4. `chore: bump APP_VERSION 8.3.0 + plan + memory + smoke test`

---

## ⚠️ Risks / Open Questions

### Risks
1. **R1 — vector_search.remove_file ลบของผิดคน?** → Mitigation: function รับ `user_id` แล้ว check ใน per-user index dict — ลบเฉพาะของ user นั้น (verified [vector_search.py:316-326](../../backend/vector_search.py#L316))
2. **R2 — re-index ตอน regenerate ทำให้ chunk_index reset อาจ break ContextInjectionLog ที่อ้างอิง chunk เก่า?** → ไม่กระทบ: ContextInjectionLog เก็บ `context_pack_ids` ไม่ใช่ chunk-level — pack identity คงเดิม
3. **R3 — MCP cluster_ids: ถ้า cluster ไม่ใช่ของ user คนนี้ → leak data?** → ไม่กระทบ: `create_pack` มี `Cluster.user_id == user_id` filter อยู่แล้ว ([context_packs.py:91-97](../../backend/context_packs.py#L91))
4. **R4 — Frontend disable button วิธีนี้ inline disabled attr — accessibility?** → OK: `disabled` attr standard HTML, screen reader อ่านเป็น "disabled" + tooltip มี text alternative
5. **R5 — Existing locked packs ใน production (ถ้ามี) — UI จะเริ่มแสดง lock state ทันทีหลัง deploy** → Expected behavior: improve UX, ไม่ใช่ regression

### Open Questions (มี default ทุกข้อ — ถ้า user ไม่ตอบใช้ default)
- **Q1** ควรลบ `delete_pack` ของ locked pack ไปด้วยไหม (block ลบ locked)? → **Default: คงเดิม (อนุญาต)** — user ลบเพื่อลด footprint ให้ฟิตแพลนได้
- **Q2** ควร expose `locked_reason` หรือแค่ `is_locked` boolean? → **Default: expose ทั้งคู่** — UI ใช้ reason แสดงข้อความต่างกัน (`exceeds_free_plan_limit` vs `subscription_expired`) ในอนาคต (v8.4.0+) แม้ตอนนี้ยังไม่ใช้
- **Q3** Bundle 1 commit หรือแยก 4 commits? → **Default: แยก 4 commits** ตามที่ระบุใน Done Criteria — ง่าย revert + ตามแบบ v8.1/v8.2 commits
- **Q4** Frontend show lock badge ใน card title หรือ corner? → **Default: prefix ใน title** (`🔒 Title`) — minimal CSS change, accessible
- **Q5** Tooltip ภาษา TH default หรือ follow `getLang()`? → **Default: follow `getLang()`** ตามที่ codebase ใช้ทุกจุด

---

## 📝 Notes for เขียว (gotchas + reuse patterns)

### Gotchas
1. **`vector_search.remove_file()` ใช้ `file_id` parameter — ส่ง `f"pack-{pack_id}"` ไม่ใช่ raw pack_id** — ตรงกับ key ที่ `create_pack` index ลง ([context_packs.py:131-137](../../backend/context_packs.py#L131))
2. **`getattr(pack, "is_locked", False)` ใช้ default False** — รองรับ DB row เก่า (ถึง schema มี column นี้ตั้งแต่ v5.9.3 แล้วก็ตาม — defensive ไม่เสียหาย)
3. **`regenerate_pack` re-index หลัง commit เท่านั้น** — ห้ามเรียกก่อน commit (ถ้า commit fail แล้ว index จะ drift)
4. **Frontend `card.classList.contains('is-locked')` preflight** ทำงานบน DOM ที่เพิ่ง render — ถ้าทำ stale อาจพลาด → ปลอดภัย: ฝั่ง backend ยังมี is_locked guard ที่ regenerate endpoint อยู่ดี
5. **MCP tool annotation** ใน descriptor ไม่เปลี่ยน (ยังเป็น `destructiveHint: False`) — ถูกต้อง: create ไม่ destructive

### Reuse patterns
- ดู [scripts/admin_e2e_test.py](../../scripts/admin_e2e_test.py) เป็น template สำหรับ smoke test (TestClient + temporary user + assertions)
- ดู `lock_excess_data` ใน [plan_limits.py:378-425](../../backend/plan_limits.py#L378) เพื่อ setup T7 lock state
- ดู [context_packs.py:131-137](../../backend/context_packs.py#L131) (`vector_search.index_file` call ใน `create_pack`) เพื่อตามแบบเดียวกันใน `regenerate_pack`
- ดู [admin.html:243-264](../../legacy-frontend/admin.html#L243) เพื่อตามแบบ confirmation modal (ถ้าตัดสินใจเพิ่ม Q1 default → block)

### Out of scope guard
ถ้าระหว่าง build เจอประเด็นพวกนี้ — **อย่าทำในรอบนี้**:
- เพิ่ม cluster selector ใน UI Create Modal (v8.4.0)
- ใส่ duplicate title check (v8.4.0)
- เพิ่ม preview ของ summary เต็ม (v8.4.0)
- TF-IDF persistence to disk (architectural, separate plan)

ถ้าเจอประเด็นใหม่ที่ต้องตัดสิน → แจ้งผ่าน [inbox/for-แดง.md](../communication/inbox/for-แดง.md) ก่อนตัดสินใจ

---

## 📋 Pipeline Next

1. 🔴 **User review plan** — ตอบ Q1-Q5 (หรือยอมรับ default ทุกข้อ)
2. 🟢 **เขียวเริ่ม build** — Phase 1-3 ตาม step-by-step (ประมาณ 0.5-1 วัน)
3. 🟢 **เขียว self-test** — รัน `scripts/context_pack_correctness_smoke.py` (T1-T11) + manual T12-T14 ใน browser
4. 🔵 **ฟ้า review** — verify 14/14 + regression + commit message + memory updates
5. 🔴 **User approve + push + deploy**
