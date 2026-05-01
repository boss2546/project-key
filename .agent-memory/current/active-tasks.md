# 🎯 Active Tasks (Pipeline Mode — currently PARALLEL per user 2026-04-30)

> Source of truth คือ [pipeline-state.md](pipeline-state.md) — ไฟล์นี้เป็น overview
> User สั่ง parallel work → 2 features ใน pipeline พร้อมกัน (default rule suspended)

---

## 🔄 Current Pipeline (PARALLEL MODE)

### 🔵 v6.1.0 Rebrand — **review_passed** (owned by ฟ้า)
- เขียว build เสร็จ + 76/76 self-test pass
- ฟ้า review + fix version drift + APPROVED
- Branch: `rebrand-pdb-v6.1.0` (6 commits)
- **Pending:** user merge to master + Fly.io deploy → state: `done`

### 🟢 v7.0.0 Google Drive BYOS — **e2e_verified** ✅ (owned by ฟ้า, full dev)
- เขียว build Phase 1+2+3 เสร็จ + 182/182 self-test pass
- ฟ้า took over Phase 4 + live E2E → critical fixes applied:
  - ✅ PKCE fix (code_verifier for Google OAuth token exchange)
  - ✅ Storage Mode "Loading..." fix
  - ✅ 401 spam logout debounce
  - ✅ Post-OAuth context restore (auto-open profile modal)
  - ✅ Register → workspace direct (skip pricing redirect)
  - ✅ Full OAuth E2E: Login → Connect → Google Consent → BYOS mode → Drive folder created
- Branch: `byos-v7.0.0-foundation` (uncommitted changes — pending commit + push + deploy)
- **Remaining:** commit + push + flyctl secrets + flyctl deploy + prod smoke test

---

## 📋 Backlog (after v7.0.0 ships)

- [ ] [BACKLOG-001] BYOS multi-account (personal + work Drive per user)
  - Priority: 🟢 Low (Phase 2 of BYOS roadmap)
  - Estimated effort: M
- [ ] [BACKLOG-002] Real-time sync via Drive Push Notifications webhook
  - Priority: 🟢 Low (currently using poll-based 5-min sync)
  - Estimated effort: M
- [ ] [BACKLOG-003] Full `drive` scope (CASA verification $25K-85K/yr)
  - Priority: 🟢 Low (defer to revenue threshold)
  - Estimated effort: L (incl. verification submission)
- [ ] [BACKLOG-004] BYOS for OneDrive / Dropbox / iCloud
  - Priority: 🟢 Low (Phase 3+)
  - Estimated effort: L per provider
- [ ] [BACKLOG-005] Custom domain (replace `project-key.fly.dev`)
  - Priority: 🟢 Low (deferred per rebrand Q2)
  - Estimated effort: S (DNS) + M (rotate URL refs)
- [ ] [BACKLOG-006] OAuth verification submission for production mode
  - Priority: 🟡 Medium (unblock public launch)
  - Estimated effort: M (Privacy Policy + Demo video + scope justification)
- [ ] [BACKLOG-007] Frontend migration to React/Vue
  - Priority: 🟢 Low (per FE-001 decision — defer)
  - Estimated effort: L

---

## ✅ Completed Features

- [x] **v6.0.0 — Personality Profile (MBTI/Enneagram/CliftonStrengths/VIA + History)**
  - Plan: [plans/personality-profile.md](../plans/personality-profile.md)
  - Built by: เขียว
  - Reviewed by: ฟ้า
  - Merged: 2026-04-30 (commit `3f4b4b9`)
  - Deployed: 2026-04-30 to https://project-key.fly.dev/

- [x] **v6.1.0 — Rebrand "Project KEY" → "Personal Data Bank" (PDB)**
  - Plan: [plans/rebrand-pdb.md](../plans/rebrand-pdb.md)
  - Readiness notes: [plans/rebrand-pdb-readiness-notes.md](../plans/rebrand-pdb-readiness-notes.md)
  - Built by: เขียว (5 commits + comprehensive smoke test 76/76)
  - Reviewed by: ฟ้า (APPROVE + version drift fix `1b7fd98`)
  - Status: `review_passed` — pending user merge + deploy
  - Branch: `rebrand-pdb-v6.1.0`

---

## 🚧 In Progress

- [⏳] **v7.0.0 — Google Drive BYOS** (E2E verified — pending commit + deploy)
  - Plan: [plans/google-drive-byos.md](../plans/google-drive-byos.md)
  - Built by: เขียว (Phase 1+2+3) + ฟ้า (Phase 4 + E2E + fixes)
  - Status: `e2e_verified` — pending commit + push + deploy
  - Branch: `byos-v7.0.0-foundation`
  - Credentials: integrated in `.env` (gitignored)

---

## ⚠️ ระบบ Pipeline ทำงานยังไง

```
Default sequential (1 feature at a time):
1. User เลือก feature จาก backlog
2. แดง วาง plan
3. User approve plan
4. เขียว build code
5. ฟ้า review + tests
6. User approve review
7. Merge → ย้ายไป Completed

Parallel override (per user — current state):
- 2 features in pipeline simultaneously
- Different agents own different features
- Authority extended (e.g., ฟ้า can dev + commit + push without review-back)
```

Default = sequential. Parallel = explicit user override only.
