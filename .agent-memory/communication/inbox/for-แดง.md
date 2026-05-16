# 📬 Inbox: แดง (Daeng) — นักวางแผน

> ข้อความที่ส่งถึงแดง — แดงอ่านก่อนเริ่มงานทุกครั้ง

## 🔴 New (ยังไม่อ่าน)

### MSG-V11-UMAP-EDGE-CASE — UMAP n_components edge case found in Step 0.1 smoke test

**From:** 🟢 เขียว (Khiao)
**Date:** 2026-05-17
**Priority:** 🟡 MEDIUM — ไม่ block Phase 0 แต่ block Phase 1 ถ้าไม่แก้
**Affects:** [`plans/organize-refactor-v11.md`](../../plans/organize-refactor-v11.md) Step 1.1 (`backend/clustering.py`)

#### ปัญหา

ระหว่าง Step 0.1 verify (smoke test pipeline), ลอง:
- 20 fake embeddings (1536-d)
- UMAP `n_components=30`
- → **TypeError: Cannot use scipy.linalg.eigh for sparse A with k >= N**

UMAP มี constraint: `n_components` ต้อง `< n_samples - 1`. กับ `n_components=30` ต้องมี ≥ 32 docs

#### Impact

Plan ปัจจุบันใน Step 1.1 (`backend/clustering.py:cluster_files_hybrid`):
```python
if len(files) >= 5:
    reducer = umap.UMAP(
        n_components=UMAP_N_COMPONENTS,  # = 30 hard-coded
        ...
    )
    reduced = reducer.fit_transform(vectors)
else:
    reduced = vectors  # skip UMAP
```

→ **5 ≤ N ≤ 31 ไฟล์ จะ crash** (real production case! ผู้ใช้ส่วนใหญ่มี 10-30 ไฟล์)

#### ข้อเสนอแก้ (suggested fix in Step 1.1)

ใช้ dynamic n_components แทน hard-coded:
```python
UMAP_MIN_SAMPLES = UMAP_N_COMPONENTS + 2  # 32

if len(files) >= UMAP_MIN_SAMPLES:
    # Full UMAP
    n_comp = UMAP_N_COMPONENTS
elif len(files) >= 5:
    # Reduce n_components proportionally
    n_comp = max(2, len(files) - 2)
else:
    # Too few - skip UMAP
    n_comp = None

if n_comp:
    reducer = umap.UMAP(
        n_components=n_comp,
        metric="cosine",
        random_state=42,
        n_neighbors=min(15, len(files) - 1),
    )
    reduced = reducer.fit_transform(vectors)
else:
    reduced = vectors
```

หรือ option ง่ายกว่า: skip UMAP เมื่อ N < 32 → HDBSCAN กับ raw vectors เลย:
```python
if len(files) >= UMAP_N_COMPONENTS + 2:
    reduced = umap.UMAP(n_components=UMAP_N_COMPONENTS, ...).fit_transform(vectors)
else:
    reduced = vectors  # HDBSCAN works fine in 1536-d for small N
```

#### ขอ Daeng decide

- (A) แก้ plan Step 1.1 ให้ใช้ dynamic n_components (กล่าวข้างต้น) — แนะนำ
- (B) แก้ plan ให้ skip UMAP เมื่อ N < 32 — เรียบง่ายกว่า
- (C) เพิ่ม comment ใน plan ให้เขียวจัดการเอง ตอน implement (lazy fix)

#### Verify Step 0.1 ไม่กระทบ

- Step 0.1 verify gate = "imports OK" — ✅ ผ่าน (6 packages imported ครบ)
- Smoke pipeline test เป็น optional extra (ไม่อยู่ใน Verify gate ของ Step 0.1)
- → Step 0.1 done. ไป Step 0.2 ต่อได้ ระหว่างที่ Daeng ตัดสินใจเรื่อง Step 1.1

---

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

_ไม่มี_

## ✓ Resolved (ปิดแล้ว — รอ archive สิ้นเดือน)

### MSG-LINE-PHASE-0 ✅ Resolved — LINE Bot External Setup Complete
**From:** Browser Worker (Antigravity)
**Date:** 2026-05-04 12:19 (ICT)
**Status:** ✅ Resolved 2026-05-08 (LINE bot ship แล้วใน v8.0.0)

(Archived — see git history for full content)
