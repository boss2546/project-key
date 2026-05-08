# 🎨 UI Foundation Contract — v9.3.0+

> **Binding for all UI work after v9.3.0.** ฟ้า (verifier) ต้อง check ก่อน approve PR
>
> Full plan: [plans/app-ui-foundation-v9.3.0.md](../plans/app-ui-foundation-v9.3.0.md)

---

## §1 Tokens — never use literal values

**Where:** `legacy-frontend/shared.css :root`

### Use these (no literals)

| Domain | Tokens |
|---|---|
| Spacing | `--space-1` (4) `--space-2` (8) `--space-3` (12) `--space-4` (16) `--space-5` (20) `--space-6` (24) `--space-8` (32) `--space-12` (48) |
| Radius | `--radius-xs` (4) `--radius-sm` (6) `--radius-md` (8) `--radius-lg` (10) `--radius-xl` (14) `--radius-pill` (999) |
| Elevation | `--elev-0` `--elev-1` `--elev-2` `--elev-3` `--elev-4` `--elev-popover` |
| Motion | `--ease-out` `--ease-in-out` · `--duration-fast` (150) `--duration-base` (200) `--duration-slow` (300) |
| Focus rings | `--ring-focus` `--ring-error` |
| Typography | `--fs-xs` (11) `--fs-sm` (12) `--fs-base` (13) `--fs-md` (14) `--fs-lg` (16) `--fs-xl` (18) `--fs-2xl` (22) · `--tracking-tight` |
| z-index | `--z-sticky` (50) `--z-page-header-sticky` (80) `--z-sidebar-mobile` (9800) `--z-modal` (10500) `--z-loading` (10800) `--z-toast` (11000) |
| Color | `--accent` `--accent-hover` `--accent-glow` `--accent-soft` · `--success` `--warning` `--error` · `--bg-primary..card` · `--surface-1..3` · `--border` `--border-hover` · `--text-primary..muted` |

### Rules

```css
/* ❌ ห้าม */
.thing { padding: 11px; border-radius: 7px; transition: all 0.18s; color: #6366f1; }

/* ✅ ต้อง */
.thing {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  transition: opacity var(--duration-base);
  color: var(--accent);
}
```

**ห้ามเพิ่ม CSS variable ใหม่ใน `:root`** ถ้าไม่มี plan review (แดง). Feature ใหม่ใช้ token เดิม. ถ้าจำเป็นจริง — PR แยก + plan + เหตุผล

---

## §2 Atoms — reuse, don't create new variants

**Where:** `legacy-frontend/shared.css` (canonical atoms section)

| Atom | Use case |
|---|---|
| `.btn .btn-primary/-outline/-ghost/-danger` (+ `.btn-sm`, `.btn-block`) | Button — 5 variants only |
| `.form-input` (+ `.is-invalid`) | Input/select/textarea |
| `.card` (+ `.card-tight`, `.card-flat`) | Card container — replaces 7+ legacy variants |
| `.status-pill` (+ `.is-active/-warning/-error/-accent`) | Status indicator — replaces 10+ badge variants |
| `.chip` (+ `.is-active`, `.chip-square`) | Chip/tag/filter |
| `.meter` (+ `.meter-fill`) | Storage/progress/quota visualization (Trust signal) |
| `.skeleton` (+ `-line/-card/-circle`) | Loading placeholder — replaces "loading..." |
| `.slide-panel` (+ `.slide-panel-sm/-md`) | Right-side detail panel |

### Rules

- ❌ ห้ามสร้าง card/chip/pill/button variant ใหม่
- ❌ ห้าม rename atom class (JS อาจใช้ class เป็น hook)
- ✅ ถ้าต้องการ visual variation ใช้ modifier เช่น `.card.card-tight` หรือ `.status-pill.is-active`
- ✅ ถ้าจำเป็นต้อง variant ใหม่จริงๆ — PR แยก + plan + เหตุผลธุรกิจ

---

## §3 Patterns — required structures

| Pattern | Required for |
|---|---|
| `.page-header > h1.page-title + p.page-subtitle + .header-actions` | ทุก `.page` section |
| `.empty-state > .empty-state-icon + .empty-state-title + .empty-state-hint + .empty-state-cta` | empty list/grid |
| `.skeleton-*` | async fetch ที่ใช้เวลา > 200ms (แทน "loading...") |
| `.page-header.is-sticky` | หน้าที่มี long list/scroll |
| `.modal-overlay > .modal > .modal-header/-body/-footer` | ทุก modal |

---

## §4 Bank-grade trust signals

ทุก feature ใหม่ต้อง:

- [ ] **Tabular numbers** — `font-variant-numeric: tabular-nums;` บน element ที่มีตัวเลข (count/size/date/percent)
- [ ] **Focus ring** — `:focus-visible { box-shadow: var(--ring-focus); }` บน interactive (auto-applied to .btn / .form-input — extend สำหรับ atom ใหม่)
- [ ] **Empty state** — มี icon + title + hint (ไม่ใช่ "ไม่มีข้อมูล" เปล่า)
- [ ] **Skeleton** — แทน "loading..." text
- [ ] **Status pill** — สำหรับ entity ที่มี state (file, pack, token, plan)
- [ ] **Subtle motion** — ห้าม > 300ms, ห้าม bounce/elastic, respect `@media (prefers-reduced-motion: reduce)`

---

## §5 Anti-AI-slop guard

ห้าม:

- ❌ Teal accent `#14b8a6`, `#06b6d4` — เราใช้ indigo `#6366f1`
- ❌ Purple-pink gradient ใน loading/CTA — ของ MCP layer (`#a78bfa`) คงไว้แต่ไม่ขยาย
- ❌ Serif heading
- ❌ **Uppercase metric labels** (`text-transform: uppercase` + `letter-spacing > 0.03em` บน label/heading) — sentence case only
- ❌ Glassmorphism over-the-top — limit blur ≤ 14px, opacity ≥ 0.7
- ❌ Emoji ใน UI text (icon SVG OK)
- ❌ Generic AI stock copy ("Welcome!", "Get started!", "Boost your productivity")

---

## §6 Pre-merge checklist (ฟ้า ใช้ก่อน approve PR)

```
[ ] Token usage 100% — no literal padding/radius/color/duration in CSS
[ ] No new card/chip/pill/button/atom variants (or PR has plan)
[ ] Page header + empty state + focus ring ครบ (ถ้ามีหน้าใหม่)
[ ] Skeleton แทน loading text (ถ้ามี async fetch)
[ ] Tabular-nums บนตัวเลข
[ ] No uppercase metric labels (text-transform: none, letter-spacing: 0)
[ ] No purple gradient (loading / CTA)
[ ] No emoji in UI text
[ ] Mobile touch ≥ 44px (ตาม shared.css mobile media query existing)
[ ] @media (prefers-reduced-motion: reduce) respected (สำหรับ animation ใหม่)
[ ] z-index ใช้ token จาก registry (--z-*)
[ ] No --accent-primary / --bg-tertiary direct usage in NEW code (alias OK ใน legacy)
```

---

## §7 Files — สำคัญ + ห้ามแตะ

| File | บทบาท |
|---|---|
| `legacy-frontend/shared.css` | ⭐ Foundation — tokens, atoms, universal patterns. แก้ระวัง |
| `legacy-frontend/styles.css` | App-only patterns. Phase B cascade rules อยู่ท้ายไฟล์ |
| `.agent-memory/plans/app-ui-foundation-v9.3.0.md` | Plan ฉบับเต็ม — reference |
| `.agent-memory/contracts/ui-foundation.md` | (ไฟล์นี้) — quick contract |

**ห้าม:**
- แก้ `:root` token block โดยไม่มี plan
- เปลี่ยน atom signature (rename class, change selector)
- เพิ่ม CSS file ใหม่ (vanilla project, ทุกอย่างใน 3 ไฟล์เดิม: shared/styles/landing)

---

## §8 Sub-version exceptions

ถ้า feature ขนาดใหญ่ที่จำเป็นต้องเพิ่ม atom/pattern ใหม่ — ทำ PR แยก:

1. PR แรก: plan file + audit + atom proposal → user review
2. PR สอง: เพิ่ม atom ใน shared.css + ทดสอบ
3. PR สาม: feature ใช้ atom ใหม่

ไม่ทำใน PR เดียว — ป้องกันการ "เพิ่ม atom ลับๆ" โดยไม่มี review

---

**End — เก็บไว้ใช้ทุก feature ใหม่หลัง v9.3.0**
