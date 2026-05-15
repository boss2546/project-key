# 🔬 Incident Report: Antigravity Cascade ค้าง — Claude Code Collision

**Author:** Claude Opus 4.7 (1M context)
**Date:** 2026-05-14
**Incident window:** 5/13 23:21 → 5/14 09:06 (~10 ชั่วโมง)
**Status:** ✅ Resolved + memory updated
**Severity:** High (workspace-blocking — IDE chat ใช้งานไม่ได้ทั้ง project)

---

## 🎯 TL;DR

1. **Antigravity Cascade chat ค้าง** ใน workspace d:/PDB หลัง Claude Code agent ทำ mass cleanup → workspace อื่นใช้ได้ปกติ
2. **Root cause = collision 3 ชั้น** ที่ Claude Code (subprocess) ทิ้งไว้ใน workspace แล้ว Antigravity Go language server รับไม่ได้: broken symlinks + git worktreeConfig + orphan lock
3. **แก้ใน 4 commands + reload window** — ใช้เวลาแก้จริง ~30 วินาที หลังจาก diagnosis 45 นาที

---

## 1️⃣ Symptoms

User report: "ส่งคำส่งแล้วมันไม่ทำงาน" + "เป็นแค่ในโปรเจ็คนี้"

ที่สังเกตได้:
- Cascade UI พิมพ์ได้ + กด send ได้ + tab title อัปเดต ("HI ดีครับ")
- แต่ไม่มี response stream กลับมา
- เปิด new chat ใน Cascade panel ก็ไม่ตอบเหมือนกัน → ไม่ใช่ conversation-specific corruption
- Model selected = Claude Opus 4.6 (Thinking) — ไม่ใช่ None
- Workspace อื่นใน Antigravity ใช้งานได้ปกติ → workspace-specific

---

## 2️⃣ Diagnostic timeline

### Phase 1: Hypothesis ผิด — Network/Quota

**สมมติฐานแรก:** network ขาด / quota หมด

หลักฐานที่พบ:
- `auth.log`: `getaddrinfo ENOTFOUND daily-cloudcode-pa.googleapis.com` (5/13 22:55, 5/14 07:09)
- `ls-main.log`: `RESOURCE_EXHAUSTED (code 429): You have exhausted your capacity on this model` (5/13 21:07 — Claude Opus 4.6 Thinking)
- User เปิด `henrikdev.ag-quota` extension มาเช็ค

**ทำไมผิด:**
- หลัง network drop ที่ 07:09 — polls กลับมาทำงานปกติทุก 6 นาทีจนถึง 08:16
- หลัง quota error 21:07 — chat ยังทำงานได้ที่ 23:21 (verified ใน brain log `2dfac309/.system_generated/logs/overview.txt`)
- หลังสุด: `streamGenerateContent` calls 07:19 ส่งไป 2 traces แต่ไม่มี response = backend reject — ไม่ใช่ network/quota issue ใหม่

### Phase 2: Hypothesis ผิด — worktreeConfig เป็น blocker

**สมมติฐานสอง:** Antigravity Go go-git library ไม่ support `extensions.worktreeConfig`

หลักฐานที่พบ:
- `ls-main.log` repeated: `core.repositoryformatversion does not support extension: worktreeconfig`
- `cascade_manager.go:2512] Failed to resolve workspace infos, continuing without...`
- `d:/PDB/.git/config` มี `[extensions] worktreeConfig = true`

**ทำไมผิด:**
- Log ระบุชัด "**non-fatal**: continuing without" — degrade workspace context แต่ไม่ block
- Session ก่อนหน้ามี error เดียวกันแต่ chat ทำงาน (verified ใน sessions 20260512T*)
- Chat 23:21 ทำงานได้แม้มี worktreeConfig แล้ว

### Phase 3: Hypothesis ผิด — Conversation file corruption

**สมมติฐานสาม:** `2fde1e7e-3c3f-410d-97f1-57dfc9cde13b.pb` conversation file เสีย

หลักฐานที่พบ:
- `ls-main.log` 08:10:53: `Failed to load trajectory 2fde1e7e: open ...pb: The system cannot find the file specified`
- Brain folder ของ conversation นี้ว่างเปล่า (ไม่มี `.system_generated/`)

**ทำไมผิด:**
- User ลอง new chat (กด +) → ก็ไม่ตอบเหมือนกัน → ปัญหาไม่ใช่เฉพาะ conversation นี้

### Phase 4: Root cause จริง — Filesystem collision

ขุดลึกในไฟล์ workspace → เจอ 3 ตัวการ:

**A. Broken symlinks ใน `.claude/skills/`**
```
stripe-best-practices → /d/PDB/.agents/skills/stripe-best-practices  [BROKEN]
stripe-projects       → /d/PDB/.agents/skills/stripe-projects       [BROKEN]
upgrade-stripe        → /d/PDB/.agents/skills/upgrade-stripe        [BROKEN]
```
`.agents/skills/` ถูกลบใน commit `814f8c7` (08:12) แต่ untracked symlinks บน filesystem ยังเหลือ — git ไม่ track symlinks ที่ไม่ commit จึงไม่ clean

**B. Git worktree state orphan**
- `.git/config.worktree` empty file (mtime May 4)
- `extensions.worktreeConfig = true` ใน `.git/config`
- 3 prunable worktrees: `sad-cerf-76bb7e`, `kind-bhabha-c0f559`, `dazzling-mirzakhani-07f8b9`
- ทั้งหมดจาก Claude Code Agent tool `isolation: "worktree"` mode ที่ผ่านไปแล้ว

**C. Orphan lock file**
- `.claude/scheduled_tasks.lock` ระบุ PID 16276
- `Get-Process -Id 16276` → process ไม่ alive (mtime May 10, 4 วันก่อน)

---

## 3️⃣ Why ปัญหานี้ trigger ตอน 07:19

Git log ระหว่าง broken window:

| Time | Commit | What |
|------|--------|------|
| 23:19 (5/13) | 4f965e0 | chore(repo): organize root + scripts into subfolders |
| 23:36 | 983df3b | retire project-key.fly.dev references |
| **07:19 (5/14)** | **bc5feaa** | **docs(manifest): inventory of 71 active production files** |
| 07:26 | e8dbd72 | docs(deployment): complete portable deployment kit |
| 07:42 | 8a89eee | chore(cleanup): **remove non-production files (306 deletions)** |
| 08:12 | 814f8c7 | chore(cleanup): remove orphaned caches + tracked skills dirs |
| 08:20 | 1df093b | chore(cleanup): remove orphan skills/ symlinks + lock |
| 08:27 | 95797d6 | chore(memory): remove inbox files from retired agent system |

**Trigger event:** Claude Code agent ทำ mass cleanup workflow 07:19 → 08:27 ลบ `.agents/`, `tests/`, `sandbox/`, `node_modules/`, etc. (306 ไฟล์ใน commit เดียว)

**Race condition:** ระหว่างที่ agent ลบ filesystem objects, Antigravity Go LS:
1. Re-scan workspace หลัง file change events
2. Resolve workspace info → trip on broken symlinks
3. Cache invalidated state → reject ทุก new chat request silently

หลัง 08:14, Cascade UI ยังเขียน `.pb` files ได้ (1019 → 1931 bytes) แต่ไม่ trigger `streamGenerateContent` ไป backend อีกเลย

---

## 4️⃣ Fix (รันจริง)

```bash
# 1. ลบ broken symlinks (target ไม่มีอยู่แล้ว — ปลอดภัย)
rm d:/PDB/.claude/skills/stripe-best-practices \
   d:/PDB/.claude/skills/stripe-projects \
   d:/PDB/.claude/skills/upgrade-stripe

# 2. ลบ orphan lock (verified PID 16276 dead)
rm d:/PDB/.claude/scheduled_tasks.lock

# 3. Clean git worktree state
git -C d:/PDB worktree prune                  # ลบ 3 prunable records
git -C d:/PDB config --unset extensions.worktreeConfig
rm d:/PDB/.git/config.worktree

# 4. ใน Antigravity: Ctrl+Shift+P → "Developer: Reload Window"
```

**Verification ก่อน reload:**
- `.claude/skills/` empty ✓
- `git worktree list` แสดงแค่ `D:/PDB [master]` ✓
- `.git/config` ไม่มี `[extensions]` section ✓
- `.git/config.worktree` หาย ✓

**ผลลัพธ์หลัง reload:** User confirm ใช้งานได้ปกติ

---

## 5️⃣ Architecture insight — Claude Code × Antigravity overlap

ระบบ AI/agent **5 ชั้นซ้อนกัน** ใน workspace นี้:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Antigravity Cascade (Google)                                  │
│    - State: ~/.gemini/antigravity/{brain,conversations,...}     │
│    - Language Server: Go binary, ใช้ go-git library             │
│    - Workspace scanner: ไม่ทน broken symlinks + worktreeConfig  │
└─────────────────────────────────────────────────────────────────┘
                            ↓ runs inside
┌─────────────────────────────────────────────────────────────────┐
│ 2. Claude Code extension (anthropic.claude-code-2.1.131)         │
│    - subprocess: claude.exe → Anthropic API /v1/messages        │
│    - Memory: ~/.claude/projects/<hash>/memory/MEMORY.md         │
│    - Hooks: ~/.claude/settings.json                             │
│    - Tool: Agent (isolation: "worktree" → spawn git worktrees)  │
└─────────────────────────────────────────────────────────────────┘
                            ↓ writes artifacts to
┌─────────────────────────────────────────────────────────────────┐
│ 3. Workspace .claude/                                            │
│    - settings.local.json (Bash permission allowlist)            │
│    - skills/ (เคยมี symlinks → .agents/)                        │
│    - worktrees/ (git worktrees จาก Agent tool)                  │
│    - scheduled_tasks.lock                                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓ overlaps with
┌─────────────────────────────────────────────────────────────────┐
│ 4. Workspace .agents/ (Anthropic Plugin Skills — DELETED)        │
│    - skills/stripe-* — ถูกลบ commit 8a89eee                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓ user's parallel system
┌─────────────────────────────────────────────────────────────────┐
│ 5. Workspace .agent-memory/ (User's custom structured memory)    │
│    - communication/, contracts/, current/, handoff/, history/,  │
│      plans/, project/, prompts/, research/                      │
│    - ไม่ overlap กับระบบอื่น — safe                              │
└─────────────────────────────────────────────────────────────────┘
```

### Collision points

| Collision | จุดทับ | ผลกระทบ | Fix |
|-----------|--------|---------|-----|
| Symlinks cross-system | `.claude/skills/` → `.agents/skills/` | Go workspace scanner trip | ลบ symlinks หรือไม่ใช้เลย |
| Git worktree extension | `.git/config` + `.git/config.worktree` | Go go-git ไม่ support `worktreeConfig` | unset extension + prune |
| Lock files | `.claude/*.lock` | False busy state | ลบ orphan + check pid |
| Process tree | claude.exe inside Antigravity.exe ext host | ห้าม kill Antigravity (kill ตัวเอง) | aware เท่านั้น |

---

## 6️⃣ Prevention rules

### สำหรับ user

1. **อย่าสร้าง symlinks ใน `.claude/skills/`** บน Windows — ใช้ copy/git submodule แทน. Filesystem ไม่ auto-cleanup broken symlinks
2. **หลัง Claude Code agent ใช้ `isolation: "worktree"`** — รัน `git worktree prune` ทันที (ไม่ต้องรอ orphan)
3. **หลัง agent ทำ mass cleanup ใน workspace ที่ Antigravity เปิด** — `Ctrl+Shift+P` → "Developer: Reload Window" ทุกครั้ง

### สำหรับ Claude Code agent (ผม) — เพิ่ม CLAUDE.md rule

```markdown
## Workspace cleanup discipline (Antigravity-aware)

When running heavy file mutations in workspace that Antigravity is using:
1. After deleting folders containing symlink targets — find/remove dangling symlinks
2. After using Agent isolation: "worktree" — `git worktree prune` immediately
3. After 50+ file deletions — note to user: "reload Antigravity window via Ctrl+Shift+P"
```

### `.gitignore` additions (ถ้ายัง track)

```
.claude/skills/
.claude/worktrees/
.claude/scheduled_tasks.lock
.agents/
```

---

## 7️⃣ Diagnostic playbook (ครั้งหน้า)

ถ้าเห็น symptom **"Antigravity Cascade chat ส่งแล้วไม่ตอบในเฉพาะ workspace นี้"** ตรวจตามลำดับ:

```bash
# 1. หา broken symlinks
find <workspace>/.claude -type l -xtype l

# 2. ตรวจ git worktree state
grep worktreeConfig <workspace>/.git/config
ls <workspace>/.git/config.worktree 2>/dev/null
git -C <workspace> worktree list

# 3. ตรวจ orphan locks
find <workspace>/.claude -name "*.lock" 2>/dev/null

# 4. ตรวจ Antigravity LS log
tail -50 ~/AppData/Roaming/Antigravity/logs/<latest>/ls-main.log | \
  grep -E "worktreeconfig|workspace infos|trajectory|streamGenerateContent"

# 5. ตรวจ Cascade extension log
tail -50 ~/AppData/Roaming/Antigravity/logs/<latest>/window1/exthost/google.antigravity/Antigravity.log
```

**Decision tree:**
- มี broken symlinks → ลบ
- มี `worktreeConfig` + ไม่ได้ใช้ worktree → unset + prune + ลบ config.worktree
- มี orphan lock → ตรวจ pid → ลบถ้า dead
- ไม่มี `streamGenerateContent` ใน log แม้ user พิมพ์ chat → Cascade backend reject silently → reload window
- ใน log มี `Model Selection from None to X` ที่หายไป → ปัญหาคนละ class (ดู [reference_antigravity_chat_input_locked.md](../../../../../Users/meuok/.claude/projects/d--PDB/memory/reference_antigravity_chat_input_locked.md))

---

## 8️⃣ Files modified ใน fix

| Path | Before | After |
|------|--------|-------|
| `d:/PDB/.claude/skills/stripe-best-practices` | broken symlink | ลบแล้ว |
| `d:/PDB/.claude/skills/stripe-projects` | broken symlink | ลบแล้ว |
| `d:/PDB/.claude/skills/upgrade-stripe` | broken symlink | ลบแล้ว |
| `d:/PDB/.claude/scheduled_tasks.lock` | orphan PID 16276 | ลบแล้ว |
| `d:/PDB/.git/config.worktree` | empty file | ลบแล้ว |
| `d:/PDB/.git/config` | มี `[extensions] worktreeConfig=true` | ลบ section แล้ว |
| `.git/worktrees/{sad-cerf,kind-bhabha,dazzling-mirzakhani}` | prunable records | pruned |

**ไม่กระทบ:** Production build (`Dockerfile`/`fly.toml`/`backend/` ไม่ใช้ของที่ลบ), `.agent-memory/`, source code

---

## 9️⃣ Memory updates

บันทึกใน user-level Claude Code memory:
- **เพิ่ม:** `~/.claude/projects/d--PDB/memory/reference_claude_code_antigravity_collision.md`
- **อัปเดต:** `~/.claude/projects/d--PDB/memory/MEMORY.md` index

memory เก่า `reference_antigravity_chat_input_locked.md` (Model=None case) ยัง valid — เป็นคนละ root cause class

---

## 🔚 Postmortem questions

1. **ทำไม Antigravity Go LS handle broken symlinks ไม่ดี?** — เป็น scanner design choice; Go go-git library follow symlinks เพื่อ resolve workspace tree, ไม่มี graceful fallback
2. **ทำไม `extensions.worktreeConfig` ยังเปิดไว้แม้ไม่มี active worktrees?** — Git ไม่ auto-cleanup; user/agent ต้อง `worktree prune` + `config --unset` เอง
3. **ป้องกันที่ Claude Code SDK ได้ไหม?** — Agent tool `isolation: "worktree"` ควร auto-cleanup เมื่อ task จบ (currently only auto-cleans worktree dir ถ้าไม่มี changes — ไม่ unset extension config)

---

**End of report.**
