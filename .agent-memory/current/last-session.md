# 📅 Last Session Summary

**Date:** 2026-05-04
**Agent:** เขียว (Khiao) — single-agent 3-in-1 mode (plan + build + self-review)
**Pipeline state:** `done` ✅ — v8.1.0 Google Sign-In shipped
**Authorization:** User said "ดำเนินการตามคุณว่าได้เลย" — approved plan + 3-in-1 execution

---

## 🎯 Session Goal

เพิ่ม "Sign in with Google" — ระบบ login ด้วย Google account ที่ reuse infrastructure ของ Drive BYOS เดิม (Google Cloud project + OAuth credentials + PKCE pattern) แต่แยก scope (login = openid+email+profile only ไม่ขอ drive.file)

---

## ✅ ที่ทำเสร็จในรอบนี้

### Phase 0 — Research + Planning (~2 ชม.)
- อ่านระบบ login ทั้งหมด: auth.py / database.py / config.py / main.py auth routes / landing.js / drive_oauth.py
- Audit security: 6 critical + 7 high + 5 medium gaps
- เสนอ 3 levels of upgrade — user เลือก Option B (Separated 2 OAuth flows)
- Draft + commit plan: `plans/archive/google-login-v8.1.0.md`

### Phase 1 — Backend (~5 ชม., 4 commits)
1. **Schema migration** — เพิ่ม `User.google_sub` column + `idx_users_google_sub` UNIQUE index + idempotent ALTER block ใน `init_db()`
2. **Config helpers** — `GOOGLE_LOGIN_REDIRECT_URI` + `is_google_login_configured()` (ไม่ต้องการ Fernet key เพราะไม่เก็บ refresh_token)
3. **`backend/google_login.py`** (NEW, 215 บรรทัด) — Login OAuth flow แยกจาก drive_oauth:
   - แยก `_GLOGIN_STATE_CACHE` (ไม่แชร์ state กับ Drive)
   - `LOGIN_SCOPES = [openid, email, profile]` — ไม่มี drive.file
   - `init_google_login()` — auth_url + state + PKCE S256 + `prompt=select_account`
   - `_verify_id_token()` — verify signature + audience + issuer ผ่าน `google.oauth2.id_token.verify_oauth2_token` (ห้าม trust id_token จาก creds ตรงๆ)
   - `handle_google_callback()` — exchange code → verify ID token → return {google_sub, email, email_verified, name, picture}
4. **`auth.py`**:
   - `login_or_create_google_user()` — lookup by google_sub → email → create. Race-aware (UNIQUE constraint)
   - `login_user()` — return `USE_GOOGLE_LOGIN` 401 hint สำหรับ Google-only user (password_hash=NULL) แทน generic 401
5. **`main.py`** 2 endpoints:
   - `GET /api/auth/google/init` (public) — 503 ถ้า unconfigured
   - `GET /api/auth/google/callback` — 302 redirect, token ใน URL fragment (กัน Referer leak), error เป็น query param

### Phase 2 — Frontend (~2 ชม., 1 commit)
- `landing.html` + `app.html` — เพิ่มปุ่ม "Sign in with Google" / "Sign up with Google" บน login + register form (4 ปุ่มรวม) + auth divider "หรือ"
- Official Google G logo SVG (4-color, inline)
- `landing.js`:
  - `doGoogleLogin()` — fetch /init + handle 503 + redirect ไป Google
  - `_handleGoogleLoginFragment()` — parse `#token=<jwt>` from URL → decode payload (no verify, backend already verified) → save localStorage → showApp
  - `_handleGoogleLoginError()` — parse `?google_error=...` → translated toast (8 reasons TH/EN)
  - `doLogin()` — handle USE_GOOGLE_LOGIN error code → inline link to Google button
- `styles.css` — `.btn-google` (white bg, official styling) + `.auth-divider`
- `app.js` I18N — เพิ่ม 5 keys (TH+EN): signIn/signUp with Google, OR, useGoogleHint, emailNotVerified

### Phase 3 — Self-test (~1.5 ชม.)
**16 scenarios PASS:**
- ✅ T1: GET /init returns auth_url + state + PKCE S256 + scope correct (no drive.file)
- ✅ T2-4: Callback error redirects (access_denied / missing_params / invalid_state)
- ✅ T5: Login unknown email → generic 401 (anti-enumeration preserved)
- ✅ T6: Google-only user wrong password → 401 USE_GOOGLE_LOGIN with TH message
- ✅ T7: Create new Google user (mcp_secret + JWT issued)
- ✅ T8: Existing email/password user → Google sign-in links (same id, password preserved, google_sub set)
- ✅ T9: Re-login same Google → no duplicate
- ✅ T10: Email change in Google → DB synced via google_sub lookup
- ✅ T11: Existing email/password login still works (regression)
- ✅ T12: 503 path when env unset
- ✅ T13: PKCE code_verifier 86 chars + state in URL
- ✅ T14: State cache cleanup removes expired
- ✅ T15: Bad state raises ValueError
- ✅ T16: 2 concurrent inits → 2 cache entries

**Regression confirmed:**
- `tests/test_auth_password_reset_v7_6.py` — 4/4 pass
- LINE Phase D 20/20, E 15/15 (alone), G 41/41 alone — ทั้ง 76/76 alone
- Combined Phase D+E fails 5 (pre-existing test isolation issue, unrelated to Google login changes — verified by running each phase alone)

---

## 📦 Commits ที่ทำในรอบนี้ (5 commits — separate logical changes)

1. `feat(db): add users.google_sub column + UNIQUE index + idempotent migration [v8.1.0]`
2. `feat(auth): google_login module + login_or_create_google_user upsert + USE_GOOGLE_LOGIN hint`
3. `feat(api): /api/auth/google/init + /callback endpoints with PKCE S256`
4. `feat(frontend): Sign in with Google button + token fragment handler + i18n + USE_GOOGLE_LOGIN UX`
5. `chore: bump APP_VERSION 8.1.0 + plan + memory + session log`

---

## 📊 Result Summary

| Metric | Value |
|---|---|
| Files NEW | 2 (`backend/google_login.py`, `plans/archive/google-login-v8.1.0.md`) |
| Files MODIFY | 8 (database.py, config.py, auth.py, main.py, landing.html, app.html, landing.js, app.js, styles.css, package.json) |
| Lines added (backend) | ~310 |
| Lines added (frontend) | ~200 |
| New endpoints | 2 |
| Schema migrations | 1 (additive, idempotent) |
| Self-test scenarios | 16/16 PASS |
| Regression | 4/4 auth + 76/76 LINE alone — no regression |
| APP_VERSION | 8.0.7 → 8.1.0 |
| External deps | 0 new (reused google-auth + google-auth-oauthlib from BYOS) |

---

## 🚧 Pending Action (User)

1. **Google Cloud Console** — เพิ่ม redirect URIs (5 นาที):
   - `https://personaldatabank.fly.dev/api/auth/google/callback`
   - `http://localhost:8000/api/auth/google/callback`
2. **OAuth verification submission** (ก่อน public launch >100 users):
   - `openid + email + profile` = non-sensitive, fast review (1-3 วัน, ฟรี)
3. **Manual end-to-end test** (ที่ผม เป็น เขียว ไม่สามารถ test ผ่าน real Google ได้):
   - คลิกปุ่ม Sign in with Google → real Google consent → return → verify localStorage + showApp
   - เคยมี email/password user → Google sign-in → confirm linked (same user.id)
4. **Deploy:** `fly deploy` (รวมกับ v8.0.0 LINE Bot ที่ค้าง)

---

## 🔮 Next steps

**สำหรับ user:**
- Manual smoke test กับ real Google account
- Push + fly deploy (รวม v8.0.0 LINE Bot + v8.1.0 Google login)
- Submit OAuth verification

**สำหรับ next agent session:**
- Pipeline = `done` for v8.1.0
- ถ้าต้องทำ feature ต่อ — ระบบรอ user มอบหมายงานใหม่
- หาก user สั่งทำ "auth-hardening Level 1" (rate limit + constant-time login + reset token revocation + password policy + revocation list) → จะเป็น plan ถัดไป
