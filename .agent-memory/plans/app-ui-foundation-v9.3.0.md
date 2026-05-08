# Plan: App UI Foundation Refresh — v9.3.0

> **Status:** `plan_pending_approval`
> **Author:** แดง (Daeng)
> **Date:** 2026-05-08
> **Scope:** App workspace (`/app`) ทุกหน้า (8 pages) — ไม่แตะ landing, ไม่แตะ admin (admin เก็บไว้รอ batch ถัดไป)
> **Brand vibe:** "ธนาคารดิจิทัล" — ปลอดภัย, น่าเชื่อถือ, ไว้ใจได้, ทันสมัย
> **Audience:** Investor demo + customer test จริง

---

## §1 Goal & Non-goals

### Goals

1. **Lock foundation ให้แข็ง** — design tokens + atoms + patterns เป็น canonical, ไม่ให้ feature ใหม่สร้าง variant ซ้ำ
2. **Visual refresh เบาๆ** — ทุกหน้าดู bank-grade (refined minimalism) โดยไม่ rewrite layout
3. **Future-proof** — เขียน "Future-dev rules" (§10) เป็นสัญญา, ใช้ verify feature ใหม่ก่อน merge
4. **คุณภาพ a11y/perf** — focus rings, tabular-nums, no layout shift, no perf regression

### Non-goals (ห้ามทำใน plan นี้)

- ❌ Rewrite layout / restructure HTML
- ❌ เปลี่ยน color palette ราก (indigo `#6366f1` คงไว้, แค่ลด saturation)
- ❌ เพิ่ม dependency (vanilla CSS/JS only)
- ❌ แตะ logic JS, API, backend
- ❌ แตะ landing.css, admin styles
- ❌ Component framework (React/Vue) — vanilla forever
- ❌ Theme switcher / light mode (dark only, ตามแบรนด์)

---

## §2 Audit — สภาพปัจจุบัน (สิ่งที่พบ)

### 2.1 Token inventory ใน `shared.css :root`

| หมวด | มี | ขาด |
|---|---|---|
| Color base | bg-primary/secondary/card/hover/active (5) | — |
| Surface | surface-1/2/3 (3) | — |
| Border | border, border-hover (2) | — |
| Text | primary/secondary/muted (3) | — |
| Node colors | 7 (file/entity/tag/...) | — |
| Layer colors | 5 | — |
| Accent | accent, accent-hover, accent-glow | accent ดู saturated มาก (ต้อง calm) |
| Status | success/warning/error (3) | — |
| Spacing layout | sidebar/detail-panel/sources-panel (3) | **❌ ไม่มี spacing scale** (4/8/12/16/20/24/32/48) |
| Radius | — | **❌ ไม่มี radius scale** — ใน CSS ใช้ 4/5/6/8/10/12/14/20px มั่ว |
| Elevation/shadow | — | **❌ ไม่มี shadow tokens** |
| Motion (timing/easing) | — | **❌ ไม่มี** — devs ใส่ 0.15s/0.2s/0.25s/0.3s scattered |
| Focus ring | — | **❌ ไม่มี** — a11y inconsistent |
| Typography scale | — | **❌ ไม่มี** — font-size 10/11/12/13/14/15/16/18/20/22px มั่ว |

### 2.2 Atoms inventory — มี **27+ atoms** เกินจำเป็น

**Buttons (11 variants):** `.btn` + `-primary, -outline, -danger, -sm, -close, -ghost, -glow, -glass, -lg, -block, -gold` → ✂️ ตัด `-glow, -glass, -gold` (landing-only)

**Cards (7 variants — ALL ต่างกัน radius/bg):**
| Class | radius | bg | ใช้ที่ |
|---|---|---|---|
| `.file-item` | 8px | surface-1 | Files page |
| `.cluster-card` | 10px | surface-1 | Knowledge tab |
| `.mcp-step-card` | 12px | surface-1 | MCP setup |
| `.mcp-tool-card` | 10px | surface-1 | MCP setup |
| `.token-card` | 10px | surface-1 | Tokens page |
| `.pack-card` | 10px | **var(--bg-tertiary) ❌ undefined** | Knowledge tab |
| `.admin-stat-card` | 12px | bg-card | Admin (out of scope) |

→ **fix:** สร้าง `.card` canonical (radius=10, bg=surface-1) + modifier เล็กๆ

**Chips/Pills (8 variants — radius 4/5/6/8/10/12/999px):**
- `.tag-chip` (4px), `.cluster-file-chip` (6px), `.filter-chip` (12px), `.source-chip` (5px), `.layer-chip` (12px), `.chip` (file-filter — **CSS undefined**), `.mcp-param-chip` (4px), `.fd-chips .chip` (12px)
→ **fix:** canonical `.chip` (radius=999px = pill), `.chip-square` (radius=6px = code-style)

**Status-pill / badges (10+ variants — radius 4/8/10px):**
- `.badge`, `.badge-count`, `.token-status-pill`, `.log-status-pill`, `.freshness-badge`, `.sensitivity-badge`, `.sot-badge`, `.storage-badge`, `.detail-type-badge`, `.locked-label`, `.injection-badge`
→ **fix:** canonical `.status-pill` (radius=999px) + `--status-color` modifier

**Tabs (3 patterns):**
- `.knowledge-tabs .tab-btn` (border-bottom-2 accent)
- `.admin-tabs .admin-tab` (just refactored, use as ref)
- `.mcp-platform-tabs .mcp-tab` (border-bottom-2 mcp-color)
→ **fix:** unify เป็น 1 pattern + variant

**Slide panels (3 ที่ทำเหมือนกันแต่ class ต่าง):**
- `.file-detail-panel` (520px, slideIn cubic-bezier)
- `.relation-sidebar` (320px, slideIn keyframe)
- `.detail-panel` (320px, slideIn keyframe)
→ **fix:** canonical `.slide-panel` + size modifier

**Loading (3 patterns ขัดแย้งสี):**
- `.loading-spinner` (16px, border-top accent indigo)
- `.loading-overlay-card` (purple gradient `#a78bfa` ❌ ไม่ตรงแบรนด์ indigo)
- `.ai-loading-spinner` (48px, accent indigo)
→ **fix:** unify สีเป็น indigo, premium loading ใช้ token เดียว

### 2.3 Pattern inventory

✅ มีและใช้ดี: `.page-header`, `.section-header`, `.empty-state`, `.upload-zone`
❌ ไม่มี: skeleton loader, sticky-bar, plan-card pattern, meter (storage/progress) pattern

### 2.4 Fragility risks (สำหรับ feature ใหม่)

| # | Risk | ความน่าจะเกิด | ผลกระทบ |
|---|---|---|---|
| R1 | Dev ใหม่สร้าง card variant ที่ 8 (radius=11px เพราะไม่มี scale) | สูง | UI fragmented |
| R2 | Dev ใหม่สร้าง chip variant ที่ 9 | สูง | เพิ่ม CSS bloat |
| R3 | Dev ใหม่ใช้ `var(--accent-primary)` ที่ undefined | กลาง | silent breakage |
| R4 | Dev ใหม่ใส่ `transition: all 0.18s` (timing นอก scale) | สูง | motion ไม่สม่ำเสมอ |
| R5 | Dev ใหม่ใส่ `font-size: 17px` (นอก scale) | สูง | typography ไม่ rhythmic |
| R6 | z-index ใหม่ไม่อยู่ใน registry → conflict | กลาง | overlay ซ้อนผิด |
| R7 | ไม่มี focus-ring → a11y ตก WCAG 2.1 AA | สูง | block enterprise/gov |
| R8 | Loading state สีไม่ตรงแบรนด์ → "ดู unprofessional" ใน demo | กลาง | ลด trust |
| R9 | Empty state เป็น "ไม่มีข้อมูล" ตัวเดียว → ดูไม่ helpful | สูง | first-impression แย่ |
| R10 | ไม่มี skeleton → ใช้ "loading..." → first-paint ดู janky | สูง | ลด trust |

### 2.5 Undefined tokens ที่ใช้อยู่จริง — **15 จุดใน styles.css**

```
var(--accent-primary)  — 11 จุด (file-detail-panel + pack-card)
var(--bg-tertiary)     — 4 จุด (pack-modal + form-input override)
```

→ ต้อง alias หรือ replace ใน Phase A1

---

## §3 Design Tokens (locked) — เพิ่มใน `shared.css :root`

```css
:root {
  /* ─── Existing (keep) ─── */
  /* (color base, surface, border, text, nodes, layers, status, layout sizes) */

  /* ─── REFINE: Accent (calm down for "bank") ─── */
  --accent: #6366f1;             /* unchanged for memory hash */
  --accent-hover: #818cf8;
  --accent-glow: rgba(99, 102, 241, 0.12);  /* was 0.15 — calmer */
  --accent-soft: rgba(99, 102, 241, 0.06);  /* NEW — subtle bg */

  /* ─── NEW: Spacing scale ─── */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;

  /* ─── NEW: Radius scale ─── */
  --radius-xs: 4px;     /* tiny chips, code blocks */
  --radius-sm: 6px;     /* small buttons, inputs */
  --radius-md: 8px;     /* default — buttons, cards-tight */
  --radius-lg: 10px;    /* cards (canonical) */
  --radius-xl: 14px;    /* large cards, modals */
  --radius-pill: 999px; /* pills, status, chips-rounded */

  /* ─── NEW: Elevation (shadow) — bank-grade soft ─── */
  --elev-0: none;
  --elev-1: 0 1px 2px rgba(0, 0, 0, 0.2);
  --elev-2: 0 4px 12px rgba(0, 0, 0, 0.25);
  --elev-3: 0 8px 24px -8px rgba(0, 0, 0, 0.4);
  --elev-4: 0 16px 48px -12px rgba(0, 0, 0, 0.5);
  --elev-popover: 0 8px 32px rgba(0, 0, 0, 0.45);

  /* ─── NEW: Motion ─── */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);   /* page transitions */
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1); /* panels */
  --duration-fast: 0.15s;
  --duration-base: 0.2s;
  --duration-slow: 0.3s;

  /* ─── NEW: Focus ring (a11y, "ปลอดภัย" signal) ─── */
  --ring-focus: 0 0 0 3px rgba(99, 102, 241, 0.35);
  --ring-error: 0 0 0 3px rgba(239, 68, 68, 0.30);

  /* ─── NEW: Typography scale ─── */
  --fs-xs: 11px;   /* meta, labels */
  --fs-sm: 12px;   /* secondary text */
  --fs-base: 13px; /* default body */
  --fs-md: 14px;   /* form input, buttons */
  --fs-lg: 16px;   /* card title */
  --fs-xl: 18px;   /* page subtitle */
  --fs-2xl: 22px;  /* page title (h1) */
  --tracking-tight: -0.02em;  /* headings */
  --tracking-num: 0;          /* default */

  /* ─── NEW: z-index registry ─── */
  --z-sticky: 50;
  --z-page-header-sticky: 80;
  --z-sidebar-mobile: 9800;
  --z-modal: 10500;
  --z-loading: 10800;
  --z-toast: 11000;

  /* ─── ALIAS: undefined tokens → existing ─── */
  --accent-primary: var(--accent);   /* fixes 11 silent uses */
  --bg-tertiary: var(--surface-1);   /* fixes 4 silent uses */
}
```

**ลด saturation accent หรือไม่?** — คงไว้ `#6366f1` เพื่อไม่ break visual identity. เปลี่ยนแค่ `accent-glow` จาก 0.15 → 0.12 (subtler).

---

## §4 Atoms Catalog (canonical)

### 4.1 Button (5 variants — ตัดจาก 11)

| Class | Use case | Style |
|---|---|---|
| `.btn` (base) | — | inline-flex, gap-2, padding `var(--space-2) var(--space-4)`, radius-md, fs-base |
| `.btn-primary` | Primary action (1 ต่อหน้า) | bg-accent, white text, **+ box-shadow on hover (elev-2)** |
| `.btn-outline` | Secondary | border + transparent, hover bg-hover |
| `.btn-ghost` | Tertiary, links | no border, hover bg-hover |
| `.btn-danger` | Destructive | bg-error, white text |
| `.btn-sm` modifier | Compact | smaller padding/fs |
| `.btn-block` modifier | Full width | 100% |

**Deprecate (ใช้ landing only, ย้ายออกจาก app):** `.btn-glow, .btn-glass, .btn-gold, .btn-lg`

**ทุกปุ่ม:** เพิ่ม `:focus-visible { box-shadow: var(--ring-focus); outline: none; }` (a11y)

### 4.2 Input

| Class | Style |
|---|---|
| `.form-input` (base) | radius-md, surface-1 bg, border, padding-3 |
| `.form-input:focus` | border-accent, **+ box-shadow var(--ring-focus)** |
| `.is-invalid` | border-error + ring-error |
| `.search-input` | unify เป็น `.form-input.form-input-search` (เลิกซ้ำ) |

### 4.3 Card (canonical — แก้ 7 variants → 1 + modifiers)

```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  transition: border-color var(--duration-base), box-shadow var(--duration-base), transform var(--duration-base);
}
.card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--elev-2);
  transform: translateY(-1px);  /* subtle, "alive" */
}
.card-tight  { padding: var(--space-3); }
.card-flat   { box-shadow: none; }
.card-flat:hover { transform: none; box-shadow: none; }  /* for list items */
```

**Migration:** `.file-item, .cluster-card, .mcp-step-card, .mcp-tool-card, .token-card, .pack-card` → ใช้ `.card` หรือ `.card .card-tight` ผสม class เดิม (ไม่ rename, แค่ extend)

### 4.4 Status pill (canonical — แก้ 10 variants → 1 + color modifier)

```css
.status-pill {
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: 2px var(--space-2);
  border-radius: var(--radius-pill);
  font-size: var(--fs-xs); font-weight: 600;
  background: var(--surface-2);
  color: var(--text-secondary);
}
.status-pill.is-active   { background: rgba(34, 197, 94, 0.12);  color: var(--success); }
.status-pill.is-warning  { background: rgba(245, 158, 11, 0.12); color: var(--warning); }
.status-pill.is-error    { background: rgba(239, 68, 68, 0.12);  color: var(--error); }
.status-pill.is-accent   { background: var(--accent-glow);       color: var(--accent-hover); }
```

**Migration:** `.token-status-pill, .log-status-pill, .freshness-badge, .badge` (เก็บ class เดิมเพื่อไม่กระทบ JS, เพิ่ม class `.status-pill` ขนานไป)

### 4.5 Chip (canonical — แก้ 8 variants → 2)

```css
.chip {
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  font-size: var(--fs-xs);
  background: var(--surface-1);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: background var(--duration-fast), border-color var(--duration-fast);
}
.chip:hover { background: var(--surface-2); border-color: var(--border-hover); }
.chip.is-active { background: var(--accent-glow); border-color: var(--accent); color: var(--accent-hover); }
.chip-square { border-radius: var(--radius-xs); }  /* code/tag chips */
```

### 4.6 Meter (NEW — Trust signal)

```css
.meter {
  position: relative;
  height: 6px;
  background: var(--surface-2);
  border-radius: var(--radius-pill);
  overflow: hidden;
}
.meter-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent-hover));
  border-radius: inherit;
  transition: width var(--duration-slow) var(--ease-out);
}
.meter.is-warning .meter-fill { background: var(--warning); }
.meter.is-error   .meter-fill { background: var(--error); }
```

Use case: storage usage (Profile), upload progress, plan limit.

### 4.7 Skeleton (NEW — แทน "loading...")

```css
.skeleton {
  background: linear-gradient(90deg, var(--surface-1) 25%, var(--surface-2) 50%, var(--surface-1) 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.6s ease-in-out infinite;
  border-radius: var(--radius-sm);
}
.skeleton-line { height: 12px; margin: 6px 0; }
.skeleton-card { height: 64px; margin-bottom: var(--space-2); }
.skeleton-circle { border-radius: 50%; }

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .skeleton { animation: none; opacity: 0.6; }
}
```

### 4.8 Status dot (canonical)

```css
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.status-dot.is-ready      { background: var(--success); }
.status-dot.is-processing { background: var(--warning); animation: pulse 2.4s ease-in-out infinite; }
.status-dot.is-error      { background: var(--error); }
.status-dot.is-idle       { background: var(--text-muted); }
```

(`.status-dot.ready/.processing` เก็บไว้ — alias)

---

## §5 Patterns Catalog (canonical)

### 5.1 Page header (refined)

```css
.page-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}
.page-header.is-sticky {
  position: sticky; top: 0; z-index: var(--z-page-header-sticky);
  background: linear-gradient(180deg, var(--bg-primary), var(--bg-primary) 70%, transparent);
  padding: var(--space-4) 0; margin: 0 0 var(--space-6);
  backdrop-filter: blur(8px);
}
.page-title { font-size: var(--fs-2xl); font-weight: 600; letter-spacing: var(--tracking-tight); }
.page-subtitle { font-size: var(--fs-base); color: var(--text-secondary); margin-top: 4px; }
```

### 5.2 Empty state (refined — Trust signal)

```css
.empty-state {
  text-align: center; padding: var(--space-12) var(--space-6);
  color: var(--text-muted);
  display: flex; flex-direction: column; align-items: center; gap: var(--space-3);
}
.empty-state-icon { width: 48px; height: 48px; opacity: 0.5; }
.empty-state-title { font-size: var(--fs-md); color: var(--text-secondary); font-weight: 500; }
.empty-state-hint { font-size: var(--fs-sm); max-width: 32ch; line-height: 1.6; }
.empty-state-cta { margin-top: var(--space-3); }  /* btn slot */
```

### 5.3 Slide panel (canonical)

```css
.slide-panel {
  position: fixed; top: 0; right: 0;
  height: 100vh; height: calc(var(--vh,1vh)*100); height: 100dvh;
  padding-bottom: env(safe-area-inset-bottom);
  background: var(--bg-secondary);
  border-left: 1px solid var(--border);
  z-index: 200;
  transform: translateX(100%);
  transition: transform var(--duration-slow) var(--ease-in-out);
  display: flex; flex-direction: column;
  box-shadow: var(--elev-3);
}
.slide-panel.is-open { transform: translateX(0); }
.slide-panel-sm { width: var(--detail-panel-width); }   /* 320 */
.slide-panel-md { width: min(520px, 90vw); }            /* file detail */
```

### 5.4 Plan card (NEW — Profile page Trust signal)

```html
<div class="plan-card">
  <div class="plan-card-header">
    <span class="status-pill is-accent">Starter</span>
    <span class="plan-card-price">฿299/เดือน</span>
  </div>
  <div class="plan-card-meter">
    <div class="meter"><div class="meter-fill" style="width:24%"></div></div>
    <div class="plan-card-meter-label">2.4 / 10 GB · 24%</div>
  </div>
  <div class="plan-card-detail">รอบบิลถัดไป: 7 มิ.ย. 2026</div>
</div>
```

### 5.5 Sticky filter/action bar

```css
.sticky-bar {
  position: sticky; top: 0; z-index: var(--z-sticky);
  background: rgba(10, 14, 26, 0.85);
  backdrop-filter: blur(12px);
  padding: var(--space-3) 0;
  margin: 0 calc(var(--space-8) * -1) var(--space-4);
  padding-left: var(--space-8); padding-right: var(--space-8);
  border-bottom: 1px solid var(--border);
}
```

---

## §6 Page-by-page mapping (8 pages)

| # | Page | Atoms ใช้ | Pattern ใช้ | Special pieces (เพิ่ม) |
|---|---|---|---|---|
| 1 | **My Data** (Files) | btn × 2, card × N, chip × 3, status-pill × N, status-dot, **skeleton** | page-header, upload-zone, **sticky-bar** (filter chips), **empty-state-refined** | drop-zone state, file count meter |
| 2 | **Knowledge View** | btn, card (cluster/pack), tabs, chip | page-header, view-toggle, slide-panel-sm (relation) | tabs unified |
| 3 | **Graph** | btn, chip (filter), zoom-btn | page-header, slide-panel-sm (detail) | bg-radial เดิม keep |
| 4 | **AI Chat** | btn-send, chip (layer), input | chat-bubble pattern (keep), slide-panel-sm (sources) | typing indicator (keep) |
| 5 | **Context Memory** | btn, card | page-header, **empty-state-refined** | — |
| 6 | **MCP Setup** | btn, card (step/tool), tabs (platform) | page-header | unify mcp-tabs → tabs |
| 7 | **Tokens** | card, status-pill | page-header, **empty-state-refined** | meter (token usage)? |
| 8 | **MCP Logs** | table, status-pill | page-header, sticky-bar (filter) | tabular-nums all numbers |
| + | **Sidebar shell** | nav-item, status-dot | — | **rail indicator** active state, plan badge, storage meter, **lang toggle** keep |

---

## §7 Bank-grade rules (Trust signals)

1. **Tabular numbers ทุกที่ที่มีตัวเลข** — `font-variant-numeric: tabular-nums;` บน `.stat-value, td, .file-meta, .plan-card-price, .meter-label, .badge-count, .log-time, .log-latency`
2. **Subtle motion only** — ห้าม bounce/elastic, ห้าม animation > 300ms, respect `prefers-reduced-motion`
3. **Focus rings everywhere** — `:focus-visible { box-shadow: var(--ring-focus); }` บนทุก interactive
4. **Empty states มีคำพูด + CTA** — ไม่ใช่ "ไม่มีข้อมูล" เปล่าๆ
5. **Skeleton แทน "loading..."** — ทุก async fetch ที่เกิน 200ms
6. **Status pills ทุก async entity** — file (uploaded/processing/ready/error), pack (locked), token (active/revoked)
7. **Sticky page header** เมื่อ scroll → trust ของ "navigation ไม่หาย"
8. **Storage meter หน้า Profile** — visual + tabular "2.4 / 10 GB"
9. **Security indicator** มุมล่างของ Profile — "🔒 ข้อมูลเข้ารหัส (E2E)" + "เข้าครั้งล่าสุด: 2 ชม.ที่แล้ว"
10. **Modal headers ใหญ่ขึ้นเล็กน้อย** — `fs-lg` (16px) → 17px, อ่านง่ายในแสงน้อย

---

## §8 Anti-AI-slop guard (อ้าง memory `reference_anti_ai_slop.md`)

ห้าม:
- ❌ Teal accent `#14b8a6` (เราใช้ indigo, อย่าเพิ่ม)
- ❌ Purple-pink gradient (เพิ่มเติม: ตอนนี้ `loading-overlay` ใช้ purple `#a78bfa` → ✂️ ใน Phase B5)
- ❌ Serif heading
- ❌ Uppercase + letter-spacing labels (ตอนนี้มีในหลายที่: `.detail-section h4, .nav-section-label, .token-meta-label, .log-table th, .form-group label` ใน pack-modal — ✂️ Phase B6)
- ❌ Glassmorphism over-the-top (limit blur ≤ 14px, opacity ≥ 0.7)
- ❌ Emoji ใน UI text (โอเค logo/status icon SVG, ไม่ใช่ "🪄✨")
- ❌ Generic stock copy ("Welcome!" "Get started!" "Boost your productivity")

---

## §9 Migration phases

3 phase. แต่ละ phase = 1 commit, verify ก่อนไป phase ถัดไป

### Phase A — Foundation (~3-4 ชม) — ⚠️ no visible visual change

**A1.** เพิ่ม tokens ใหม่ใน `shared.css :root` (spacing, radius, elevation, motion, focus-ring, typography, z-index)
**A2.** เพิ่ม alias `--accent-primary, --bg-tertiary` (fix 15 silent uses)
**A3.** เขียน atoms ใหม่ (`.card, .status-pill, .chip, .meter, .skeleton, .slide-panel`) ใน shared.css ส่วนล่าง
**A4.** เปลี่ยน `--accent-glow: 0.15 → 0.12` (calmer)
**A5.** เพิ่ม `:focus-visible` ring บน .btn / .form-input / .nav-item / interactive
**A6.** Visual regression: Playwright screenshot 8 หน้า → diff ก่อน/หลัง ≤ 1% (ต่างที่ focus ring เท่านั้น)

**Commit:** `feat(ui): foundation tokens + canonical atoms (no visible change) [v9.3.0-alpha]`

### Phase B — Atom refinement (~3-4 ชม) — visible cascading refresh

**B1.** Card hover: เพิ่ม `box-shadow var(--elev-2) + translateY(-1px)` ผ่าน `.card` canonical
**B2.** Sidebar nav `.nav-item.active` → เพิ่ม **rail indicator** (left 2px accent) + soft pill bg
**B3.** Sidebar plan badge — refine ให้ดู "bank-grade" (status-pill canonical)
**B4.** Tabular-nums บน selector list ใน §7
**B5.** Loading overlay: purple `#a78bfa` → `var(--accent)` indigo (anti-slop fix)
**B6.** Uppercase labels: `.detail-section h4, .nav-section-label, .token-meta-label, .log-table th, .pack-modal label, .fd-section h3` → ✂️ uppercase + letter-spacing
**B7.** Empty state: เพิ่ม icon + CTA ทุกหน้าที่ใช้ `.empty-state`
**B8.** Sticky page header: opt-in ผ่าน `.page-header.is-sticky` บน Files + Logs

**Commit:** `feat(ui): atom refinement — cards, nav, status, empty states [v9.3.0-beta]`

### Phase C — Trust signals (~3-4 ชม)

**C1.** Profile page: plan card + storage meter + security indicator
**C2.** Files page: drop-zone refined (active state), file count meter
**C3.** Skeleton loaders: replace "loading..." in 4 spots (file list, knowledge content, packs, audit)
**C4.** Page transition: enter animation `var(--ease-out)` 250ms
**C5.** Modal header polish: header bg subtle gradient
**C6.** Mobile sweep: verify all touch ≥ 44px (มาตรฐานเก่ายัง valid)

**Commit:** `feat(ui): bank-grade trust signals — plan card + meters + skeletons [v9.3.0]`

---

## §10 Future-dev rules (CONTRACT — ⭐ ส่วนสำคัญที่สุด)

> **กฎเหล่านี้ binding สำหรับทุก feature ใหม่หลัง v9.3.0.** ฟ้า (verifier) ต้อง check ก่อน approve PR

### 10.1 Token rules

- ❌ **ห้ามเพิ่ม CSS variable ใหม่ใน :root** ถ้าไม่ได้ผ่าน plan review (แดง). Feature ใหม่ใช้ token เดิม
- ❌ ห้ามใช้ literal value ที่ไม่อยู่ใน scale: `padding: 11px` ❌, `padding: var(--space-3)` ✅
- ❌ ห้ามใช้ literal color: `color: #6366f1` ❌, `color: var(--accent)` ✅
- ❌ ห้ามใส่ `transition: all 0.18s` (timing นอก scale) — ใช้ `var(--duration-base)`
- ✅ ถ้าจำเป็นต้องเพิ่ม token: PR แยก + plan + เหตุผล

### 10.2 Atom rules

- ❌ **ห้ามสร้าง card variant ที่ 8** — ใช้ `.card` + modifier
- ❌ ห้ามสร้าง chip/pill variant ใหม่ — ใช้ `.chip, .status-pill` + color modifier
- ❌ ห้ามสร้าง button variant ใหม่นอก 5 ตัว — ใช้ `.btn-{primary,outline,ghost,danger}` + size modifier
- ❌ ห้ามสร้าง slide-panel ใหม่ — ใช้ `.slide-panel + .slide-panel-{sm,md}`
- ❌ ห้ามสร้าง tabs pattern ใหม่ — ใช้ `.tabs` (canonical หลัง Phase A)

### 10.3 Pattern rules

- ✅ **หน้าใหม่ต้องมี `.page-header`** + h1 + subtitle + actions
- ✅ Empty state ต้องใช้ `.empty-state` พร้อม icon + title + hint + (optional) CTA
- ✅ Loading state เกิน 200ms ต้องใช้ `.skeleton-*`, ไม่ใช้ "loading..."
- ✅ Number/count/size ต้องมี `font-variant-numeric: tabular-nums`
- ✅ Interactive ต้องมี `:focus-visible { box-shadow: var(--ring-focus); }`
- ✅ Modal/sheet ต้องเคารพ z-index registry (§3)

### 10.4 Anti-slop pre-merge checklist

ก่อน merge feature ใหม่ ฟ้าเช็ค:
- [ ] Token usage 100% (no literal values in CSS rules)
- [ ] No new card/chip/pill/button variants
- [ ] Page header + empty state + focus ring ครบ
- [ ] Skeleton แทน loading text
- [ ] Tabular-nums บนตัวเลข
- [ ] No uppercase metric labels
- [ ] No purple gradient (loading/etc)
- [ ] Mobile touch ≥ 44px
- [ ] `prefers-reduced-motion` respected
- [ ] No `--accent-primary, --bg-tertiary` direct usage (ใช้ alias OK)

### 10.5 Documentation duty

หลัง v9.3.0 ship: เขียน `legacy-frontend/DESIGN-SYSTEM.md` (1 หน้า) — quick ref สำหรับ token + atom + pattern. แก้ตอนเพิ่ม token/atom ใหม่ (rare).

### 10.6 Conventions hook

เพิ่ม section "UI Foundation" ใน `.agent-memory/contracts/conventions.md` ลิงก์มา `app-ui-foundation-v9.3.0.md`. ฟ้า reference ก่อน review

---

## §11 Verification (Playwright per phase)

**ทุก phase รันทั้ง 3 ชุด:**

### 11.1 Visual regression (auto)

`tests/e2e-ui/v9.3.0-visual-baseline.spec.js`
- 8 pages × 3 viewports (375 / 768 / 1280) = 24 screenshots
- เทียบ before/after pixel diff
- Phase A: diff ≤ 1% (focus ring, accent-glow tweak)
- Phase B: diff 5-15% (atom refinement visible)
- Phase C: diff 10-25% (trust signals visible)

### 11.2 Functional smoke (auto)

`tests/e2e-ui/v9.3.0-smoke.spec.js`
- Login → all 8 pages clickable
- Empty state มี text + (optional) CTA
- Modal เปิด/ปิด ไม่ blocked
- Focus ring แสดงเมื่อ Tab
- Skeleton แสดงระหว่าง fetch (mock slow)

### 11.3 Manual review (user)

- Phase A: ผมส่ง screenshot pack 24 ภาพ → user check "no visible regression"
- Phase B: ผมส่ง screenshot pack เน้น sidebar/cards/empty state
- Phase C: ผมส่ง screenshot pack เน้น Profile + drop zone + skeleton

### 11.4 Cross-browser (manual / CI)

- Chrome ✅ (default)
- Safari (iOS real device) — focus ring + dvh
- Firefox — `:focus-visible` (supported), `:has()` (since 121, ok)

### 11.5 Performance gate

- No new CLS
- First-paint ไม่ช้าลง
- shared.css + styles.css รวมเพิ่ม ≤ 5 KB gzipped (token + atoms)

---

## §12 Rollback

**Per phase:** `git revert <commit>` ของ phase นั้น (แต่ละ phase 1 commit เดียว clean)

**Per file:** ทุก phase แตะ `shared.css` + `styles.css` เป็นหลัก. Phase C อาจแตะ `app.html` (เพิ่ม HTML element สำหรับ plan card + storage meter)

**Token alias rollback:** ถ้าต้อง revert `--accent-primary, --bg-tertiary` aliases (Phase A2) — ระวัง 15 จุดจะ silent break อีก. แนะนำ revert พร้อม phase ทั้ง chunk

**Pre-flight:** สร้าง git tag `v9.2.2-pre-foundation` ก่อนเริ่ม Phase A

---

## §13 Effort & timeline

| Phase | Effort | Calendar |
|---|---|---|
| A — Foundation | 3-4 ชม | day 1 |
| B — Atom refinement | 3-4 ชม | day 2 |
| C — Trust signals | 3-4 ชม | day 3 |
| Documentation + conventions hook | 1 ชม | day 3 (end) |
| **Total** | **~10-13 ชม** | **3 working days** |

User review รอบละ ~30 นาที × 3 = 1.5 ชม

---

## §14 Open questions / decisions for user

1. **Lower accent saturation** — แค่ปรับ `accent-glow: 0.15 → 0.12` (subtle) — OK ไหม? หรืออยากกล้ากว่านั้น (เช่น เปลี่ยนตัว `--accent` เป็น indigo เข้ม `#4f46e5`)?

2. **Storage meter** ใน sidebar — ใส่หรือไม่? ส่วนตัวผมแนะนำ "ไม่" (sidebar แน่นแล้ว) และไป Profile page แทน (ที่นั่น breathing room มากกว่า)

3. **Plan badge ใน sidebar** — แทนที่ `Admin Panel` button (เห็นเฉพาะ admin) ด้วย `Plan: Free / Starter / Admin` pill (เห็นทุกคน)?

4. **Empty state CTA** — ทุกหน้าหรือแค่บางหน้า? Files หน้าจะมี CTA "Drag a file to start" ชัดอยู่แล้ว, แต่ MCP/Memory/Tokens อาจไม่จำเป็น

5. **Future-dev rules — binding ระดับไหน?**
   - (a) แนะนำเฉย (ฟ้า advise)
   - (b) **binding** — ฟ้า reject PR ถ้าฝ่าฝืน
   ผมแนะนำ (b) เพื่อให้ "ฐานไม่พัง" ตามที่ user ตั้งใจ

6. **Documentation file** — สร้าง `legacy-frontend/DESIGN-SYSTEM.md` หรือใส่ใน `.agent-memory/contracts/`? (ส่วนตัว: ใน contracts/ เพราะ ฟ้า reference ง่าย)

---

## §15 Definition of Done

- [ ] Phase A,B,C commit เรียบร้อย
- [ ] Playwright visual regression pass
- [ ] Functional smoke pass
- [ ] User approve screenshots ทั้ง 3 phase
- [ ] APP_VERSION bumped 9.2.2 → 9.3.0
- [ ] Cache-bust `?v=9.3.0` ทุก reference (4 HTML)
- [ ] `DESIGN-SYSTEM.md` (or contracts) เขียนแล้ว
- [ ] `conventions.md` มี link
- [ ] No new linter warnings
- [ ] No console errors
- [ ] Mobile real device smoke (iOS Safari) pass

---

**End of plan**

แผนนี้กิน effort ~10-13 ชม รวม verify. **คุณภาพของ output คือ "ฐานที่ไม่พัง" สำหรับ feature ใหม่ทุกตัวหลัง v9.3.0** (กฎ §10 binding)
