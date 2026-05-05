# 🔗 Two-Worker Coordination — Browser + Backend

**Setup:** 2 AI agents ทำงานขนานกัน เล่นคนละบทบาท
**Supervisor:** 🔴 แดง (Daeng) — ผ่าน inbox protocol
**Date:** 2026-05-02

---

## 👥 Roles

### 🌐 Browser Worker
- **Prompt:** [prompts/prompt-worker-browser.md](../prompts/prompt-worker-browser.md)
- **Tools needed:** Browser + terminal (Fly CLI)
- **Tasks:** Phase 0 only
  - LINE Developer Account
  - 2 channels (Messaging API + Login)
  - Resend account
  - Set Fly secrets (9 secrets)
- **Estimated:** ~1-2 hours
- **Output:** Fly secrets configured + report ใน inbox/for-แดง.md

### 🤖 Backend Worker
- **Prompt:** [prompts/prompt-worker-backend.md](../prompts/prompt-worker-backend.md)
- **Tools needed:** File system + terminal (Python, Git, no browser)
- **Tasks:** 9 code phases
  - Section C (signed URLs)
  - LINE Bot Phase D-K
- **Estimated:** ~3-4 weeks
- **Output:** Code + tests + commits + final report

---

## 🔄 Parallel Workflow

```
Time T0 (start)
├── 🌐 Browser Worker → Phase 0 (1-2 hr)
└── 🤖 Backend Worker → Section C (1-2 days)
                         ↓
Time T1 (~1 hr)
├── 🌐 Browser done → report ใน inbox/for-แดง.md
└── 🤖 Backend wip Section C
                         ↓
Time T2 (~1-2 days)
├── 🌐 Browser done — idle
└── 🤖 Backend done Section C → check Phase 0 done?
                                  ↓ yes
                                 Phase D start
                         ↓
Time T3 (~3-4 weeks)
└── 🤖 Backend done Phase K → Final report
                         ↓
Time T4
└── User: review + push + fly deploy → 🎉 LINE bot live
```

---

## 🔗 Dependency Graph

```
Phase A (DONE)
   ↓
Section C (Backend)        Phase 0 (Browser)
       ↓                          ↓
       └─────── joins at ─────────┘
                  ↓
              Phase D (Backend)
                  ↓
              Phase E
                  ↓
              ... K
                  ↓
              Deploy (User)
```

**Section C ทำได้เลย ไม่ต้องรอ Phase 0** — ใช้ JWT_SECRET_KEY ที่มีอยู่แล้ว

**Phase D เริ่มได้ทันทีถ้า Phase 0 เสร็จ** — ต้องการ LINE_CHANNEL_SECRET ใน Fly secrets

**Phases E-K ขึ้นอยู่กับ Phase D** — sequential

---

## 📞 Communication Channels

| File | Writer | Reader |
|---|---|---|
| `inbox/for-แดง.md` | Both workers | แดง |
| `inbox/for-Executor.md` | แดง | **Both** workers (read-only) |
| `inbox/for-User.md` | แดง / Backend Worker | User |

→ แดงเป็น central coordinator ระหว่าง 2 workers

---

## ⚠️ Synchronization Points

### SP-1: Phase 0 → Phase D handoff
**When:** Browser Worker write report ว่า Fly secrets ครบ 9 ตัว
**Action:** แดงเขียน inbox/for-Executor.md ให้ Backend Worker เริ่ม Phase D
**Verify:** Backend Worker check `fly secrets list` มี LINE_* + RESEND_*

### SP-2: Section C → Phase D handoff (ของ Backend Worker)
**When:** Backend Worker เสร็จ Section C
**Action:** Check Phase 0 done? → ถ้าใช่ Phase D, ถ้าไม่ใช่ wait
**Verify:** Backend อ่าน inbox/for-Executor.md ว่ามี "Phase 0 verified" message ไหม

### SP-3: Phase K → Deploy
**When:** Backend Worker เสร็จทุก phase + write Final report
**Action:** User review → push + deploy

---

## 🎯 What if Workers Conflict?

### Scenario 1: Browser Worker เสร็จก่อน Backend
- 🌐 Browser idle รอ
- 🤖 Backend ทำ Section C ต่อ
- ✅ ไม่มีปัญหา

### Scenario 2: Backend เสร็จ Section C ก่อน Browser
- 🤖 Backend หยุดที่จุด Phase D ต้นๆ
- 🤖 Backend ทำ test cleanup / refactor / docs ระหว่างรอ
- ⚠️ อย่าเริ่มเขียน LINE webhook code จนกว่า Phase 0 เสร็จ
- ✅ ไม่มีปัญหา

### Scenario 3: Browser Worker ติดปัญหา (login fail / DNS issue)
- 🌐 Browser write BLOCK-XXX ใน inbox/for-แดง.md
- 🔴 แดงตอบ + อาจถาม user
- 🤖 Backend continue ตามปกติ (Section C ไม่ขึ้นกับ Phase 0)

### Scenario 4: Backend ทำ scope creep
- 🔴 แดงเจอ + revert + course correct (เหมือนรอบที่แล้ว)
- 🤖 Backend resume ตาม plan

---

## 🚀 Kickoff Sequence

### User เริ่มยังไง

**Option A: Sequential (ปลอดภัย)**
1. เปิดแชท Browser Worker → paste prompt → ทำ Phase 0 (~1-2 hr)
2. เมื่อเสร็จ → เปิดแชท Backend Worker → paste prompt → ทำ Section C → Phase D-K

**Option B: Parallel (เร็วขึ้น)** ⭐ แนะนำ
1. เปิด **2 แชท** พร้อมกัน:
   - แชท 1: Browser Worker prompt
   - แชท 2: Backend Worker prompt
2. Browser Worker → Phase 0
3. Backend Worker → Section C (ไม่ต้องรอ Browser)
4. ทั้งคู่ report ผ่าน inbox protocol
5. Backend สลับเป็น Phase D หลัง Phase 0 เสร็จ + Section C เสร็จ

**Time saving Option B vs A:**
- Option A: 1-2 hr (Browser) + 3-4 weeks (Backend) = ~3-4 weeks
- Option B: max(1-2 hr, 1-2 days Section C) + 3-3.5 weeks (D-K) = ~3-3.5 weeks
- → ไม่ได้ประหยัดเยอะเพราะ Backend ใช้เวลานานกว่ามาก

---

## 📊 Status Tracking

แดง update `current/pipeline-state.md` ตาม progress:

```
| Phase | Owner | Status |
|---|---|---|
| Phase A | (done) | ✅ COMMITTED |
| Phase 0 | 🌐 Browser | 🔴 In progress |
| Section C | 🤖 Backend | 🔴 In progress |
| Phase D | 🤖 Backend | ⏸️ Waiting Phase 0 + Section C |
| Phase E-K | 🤖 Backend | ⏸️ Waiting Phase D |
| Deploy | 👤 User | ⏸️ Waiting Phase K |
```

---

## ✅ Success Criteria

ทั้งหมดถือว่าเสร็จเมื่อ:
- [ ] Browser Worker: Phase 0 done (9 Fly secrets)
- [ ] Backend Worker: Section C + Phase D-K done (~65 tests pass)
- [ ] Backend Worker: Final report ใน inbox/for-User.md
- [ ] User: review + push + fly deploy
- [ ] Verify: production smoke test ผ่าน (mobile LINE app)
- [ ] APP_VERSION bumped 7.5.0 → 8.0.0

---

**End of coordination doc.** ผ่าน inbox protocol = single source of truth

— แดง (Daeng)
