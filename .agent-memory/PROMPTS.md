# 🎯 Bootstrap Prompts — Index

> ระบบ Pipeline Sequential — agent ทำงานเป็นทอดๆ ทีละตัว
> เปิดไฟล์ของ agent ที่ต้องการ → copy code block → paste ในแชทใหม่

---

## 🔄 Pipeline Order

```
1. 🔴 แดง (นักวางแผน)  →  วาง plan
        ↓
   User approve plan
        ↓
2. 🟢 เขียว (นักพัฒนา)  →  เขียน code
        ↓
3. 🔵 ฟ้า (นักตรวจสอบ)  →  รีวิว + tests
        ↓
   User approve → merge
```

---

## 📋 เลือก agent ที่ต้องการ

| Step | Icon | Agent | Prompt File | เปิดเมื่อไหร่? |
|------|------|-------|-------------|---------------|
| 1 | 🔴 | **แดง (Daeng)** — นักวางแผน | [prompts/prompt-แดง.md](prompts/prompt-แดง.md) | เริ่ม feature ใหม่ |
| 2 | 🟢 | **เขียว (Khiao)** — นักพัฒนา | [prompts/prompt-เขียว.md](prompts/prompt-เขียว.md) | หลัง user approve plan |
| 3 | 🔵 | **ฟ้า (Fah)** — นักตรวจสอบ | [prompts/prompt-ฟ้า.md](prompts/prompt-ฟ้า.md) | หลังเขียว build เสร็จ |

---

## 🚀 ขั้นตอนการใช้งาน

### Phase 1: Planning (แดง)
1. คุณรู้ว่าจะทำ feature อะไร
2. เปิดแชทใหม่ใน Antigravity
3. Copy prompt จาก [prompt-แดง.md](prompts/prompt-แดง.md) → paste → send
4. แดงรายงานตัว → คุณบอก feature ที่ต้องการ
5. แดงเขียน plan ใน `plans/[feature].md`
6. แดงรายงานเสร็จ → คุณ review plan
7. **Approve** → "OK plan ผ่าน เริ่ม build ได้" → ปิดแชทแดง
8. **Revise** → "แก้ตรงนี้ X, Y" → แดงแก้แล้วรายงานใหม่

### Phase 2: Building (เขียว)
1. เปิดแชทใหม่
2. Copy prompt จาก [prompt-เขียว.md](prompts/prompt-เขียว.md) → paste → send
3. เขียวรายงานตัว — จะอ่าน plan ที่ approve แล้วจาก `plans/`
4. คุณบอก "เริ่ม build ตาม plan ได้เลย"
5. เขียวเขียน code + commit
6. เขียวรายงานเสร็จ → ปิดแชทเขียว

### Phase 3: Review (ฟ้า)
1. เปิดแชทใหม่
2. Copy prompt จาก [prompt-ฟ้า.md](prompts/prompt-ฟ้า.md) → paste → send
3. ฟ้ารายงานตัว — จะอ่าน plan + code ที่เขียวทำ
4. คุณบอก "review + เขียน tests ได้เลย"
5. ฟ้าเขียน tests + review report
6. ฟ้ารายงาน verdict:
   - ✅ **APPROVE** → คุณ merge → feature done
   - ⚠️ **NEEDS_CHANGES** → กลับไป Phase 2 (เปิดเขียวใหม่ บอก "ดู review จากฟ้า แล้วแก้")
   - ❌ **BLOCK** → หยุด, อาจต้องกลับไป Phase 1 (แก้ plan)

---

## ⏱️ เวลาที่ใช้ (ประมาณ)

| Phase | เวลา | คุณทำอะไร |
|-------|------|---------|
| Planning | 10-30 นาที | บอก feature → review plan |
| Building | 30-90 นาที | รอเขียวทำ |
| Reviewing | 15-45 นาที | รอฟ้าทำ → ตัดสินใจ merge |
| **Total** | **~1-3 ชั่วโมง** ต่อ feature | ขึ้นกับขนาด feature |

---

## ⚠️ ข้อควรระวัง

### ✅ ทำ
- เปิดแชทใหม่ทุก phase (clean state ดีกว่า)
- Approve plan อย่างจริงจังก่อน build (ดูทุก section)
- Read review report อย่างละเอียดก่อน merge
- Commit memory updates พร้อม code

### ❌ ห้าม
- ห้ามเปิด 2 agents พร้อมกัน — pipeline = sequential
- ห้าม skip phase (ต้อง plan ก่อน build, ต้อง build ก่อน review)
- ห้ามให้ agent ทำ role อื่น (ฟ้าอย่าแก้ code, เขียวอย่าเขียน tests)
- ห้ามลืม update pipeline-state.md

---

## 📝 Format สรุปงานสุดท้าย (Reference)

ทุก agent ต้องสรุปด้วย format ที่ระบุชื่อชัดเจน — ดูเต็มๆ ใน [00-START-HERE.md](00-START-HERE.md)

```
✅ [icon] [ชื่อ] ([role]) รายงานผลงาน

🎯 ที่ทำเสร็จ: ...
📁 Output: ...
🔄 Pipeline ต่อไป: ...
📝 Memory ที่ update: ...
🔖 Commit: ... | Author-Agent: [ชื่อ] ([English])

— [ชื่อ]
```

---

## 🎬 ตัวอย่างจริง

### ตัวอย่าง: เพิ่ม feature "Export ข้อมูลเป็น JSON"

**Phase 1 (10 นาที):**
```
You: [paste prompt-แดง.md]
🔴 แดง: รายงานตัว...
You: ทำ feature export ข้อมูลเป็น JSON ให้ user download
🔴 แดง: [ถามคำถาม + เขียน plan ใน plans/export-json.md]
🔴 แดง: Plan เสร็จแล้ว ดูใน plans/export-json.md
You: [อ่าน plan] OK plan ผ่าน เริ่ม build ได้
🔴 แดง: [update pipeline-state, commit]
```

**Phase 2 (45 นาที):**
```
You: [เปิดแชทใหม่ + paste prompt-เขียว.md]
🟢 เขียว: รายงานตัว... อ่าน plan แล้ว
You: เริ่ม build ตาม plan
🟢 เขียว: [เขียน code + commit]
🟢 เขียว: Build เสร็จ ส่งต่อให้ฟ้า
```

**Phase 3 (20 นาที):**
```
You: [เปิดแชทใหม่ + paste prompt-ฟ้า.md]
🔵 ฟ้า: รายงานตัว... อ่าน plan + code แล้ว
You: review + เขียน tests
🔵 ฟ้า: [เขียน tests + รัน + review]
🔵 ฟ้า: Verdict: APPROVE — 12 tests pass, coverage 85%
You: OK merge ได้
```

---

ดู [README.md](README.md) สำหรับภาพรวมระบบทั้งหมด
