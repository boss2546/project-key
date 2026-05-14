# 🚀 Deployment Runbook — Personal Data Bank

> **Goal:** Take a fresh machine and bring the PDB server up to feature-parity with
> production (`personaldatabank.fly.dev`).
>
> **Source:** [production-active/](../../production-active/) snapshot (71 code files)
> **What this gets you:** Level 2 — all features functional on fresh empty install.
> **What this does NOT do:** restore your existing users, files, or sessions (those
> live on the Fly.io volume — see [Section 7](#7-disaster-recovery-from-volume-backup)).

---

## 0. Prerequisites

| Tool | Purpose | Install |
|---|---|---|
| Docker | Build + run the container locally | https://docs.docker.com/get-docker |
| `flyctl` (optional) | Deploy to Fly.io | https://fly.io/docs/flyctl/install |
| `openssl` | Generate secrets | Pre-installed on Linux/macOS; Git Bash on Windows |
| Google Cloud account | OAuth client + Gemini API key | https://console.cloud.google.com |
| OpenRouter account | LLM API key | https://openrouter.ai |
| Resend account | Transactional email | https://resend.com (optional) |
| Stripe account | Billing | https://dashboard.stripe.com (optional) |
| LINE Developer account | LINE bot | https://developers.line.biz (optional) |

---

## 1. Lay the code down

```bash
# Option A — clone full repo (recommended; tracks future updates)
git clone https://github.com/boss2546/project-key.git pdb
cd pdb

# Option B — use the snapshot only (frozen point-in-time, no git history)
# cp -r /path/to/production-active /opt/pdb
# cd /opt/pdb
```

The 71 files needed are: `Dockerfile`, `fly.toml`, `requirements-fly.txt`,
`backend/`, `legacy-frontend/`. See [docs/manifest/ACTIVE-PRODUCTION-FILES.md](../manifest/ACTIVE-PRODUCTION-FILES.md) for the exact list.

---

## 2. Generate secrets

The two file-based fallback secrets (`JWT_SECRET_KEY`, `MCP_SECRET`) auto-generate
on first boot, but production should set them explicitly so they survive volume
migrations.

```bash
# JWT signing key (NEVER rotate after first deploy — invalidates all sessions)
openssl rand -base64 64

# MCP server-wide secret
openssl rand -base64 32

# Admin override password
openssl rand -base64 32

# Fernet key for Drive token encryption (required for BYOS)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Stash the outputs somewhere safe (password manager). They go into `.env` next.

---

## 3. Fill in `.env`

```bash
cp docs/deployment/.env.example .env
$EDITOR .env
```

Minimum to **boot**: `ADMIN_PASSWORD` + `ADMIN_EMAILS`.

Minimum for **feature parity** with production:

| Required | What you need to provision elsewhere first |
|---|---|
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
| `GOOGLE_API_KEY` | https://aistudio.google.com/apikey (Gemini multimodal) |
| `GOOGLE_OAUTH_CLIENT_ID` / `_SECRET` | OAuth 2.0 client in Google Cloud Console (see §4) |
| `DRIVE_TOKEN_ENCRYPTION_KEY` | `openssl` output from §2 |
| `GOOGLE_PICKER_API_KEY` / `_APP_ID` | Picker API enabled in same Cloud project |
| `RESEND_API_KEY` | https://resend.com (skip if no email needed) |
| `STRIPE_SECRET_KEY` / `_PUBLISHABLE_KEY` / `_WEBHOOK_SECRET` / `STRIPE_STARTER_PRICE_ID` | Stripe Dashboard (skip if no billing) |
| `LINE_CHANNEL_SECRET` / `_ACCESS_TOKEN` / `_LOGIN_CHANNEL_ID` / `_LOGIN_CHANNEL_SECRET` | LINE Developers Console (skip if no LINE bot) |

Everything else has safe defaults or is auto-disabled when unset (the server
returns 503 with a clear error code for missing optional features).

---

## 4. Register OAuth redirect URIs

Code-perfect snapshot won't help if the provider rejects redirects to your new
domain. For each service used, **update the redirect URI in the provider's
dashboard before users try to log in**.

| Provider | Where | Add this URI |
|---|---|---|
| **Google OAuth** | [Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials) → your OAuth client → "Authorized redirect URIs" | `{APP_BASE_URL}/api/auth/google/callback` AND `{APP_BASE_URL}/api/drive/oauth/callback` |
| **Stripe webhook** | [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks) → "Add endpoint" | `{APP_BASE_URL}/api/billing/webhook` (events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`) |
| **LINE Messaging API** | [LINE Developers Console](https://developers.line.biz/console) → your Messaging channel → "Messaging API" → "Webhook URL" | `{APP_BASE_URL}/webhook/line` (toggle "Use webhook" ON) |
| **LINE Login** | [LINE Developers Console](https://developers.line.biz/console) → your LINE Login channel → "LINE Login" → "Callback URL" | `{APP_BASE_URL}/api/auth/line/callback` |

Replace `{APP_BASE_URL}` with your actual public URL (matches the `APP_BASE_URL`
env var in `.env`).

---

## 5. Build & run

### 5a. Local Docker

```bash
docker build -t pdb .
docker run -d \
  --name pdb \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  pdb

# Tail logs
docker logs -f pdb
```

Visit http://localhost:8000 → landing page should load.

Health check: `curl http://localhost:8000/api/mcp/info` should return JSON with
the current `APP_VERSION`.

### 5b. Fly.io

```bash
# First-time only: create the app + volume
flyctl apps create your-app-name
flyctl volumes create pdb_data --region sin --size 3 -a your-app-name

# Set secrets (all the [REQUIRED] / [FEATURE] vars from .env)
flyctl secrets set \
  ADMIN_PASSWORD=... \
  JWT_SECRET_KEY=... \
  MCP_SECRET=... \
  OPENROUTER_API_KEY=... \
  GOOGLE_API_KEY=... \
  GOOGLE_OAUTH_CLIENT_ID=... \
  GOOGLE_OAUTH_CLIENT_SECRET=... \
  DRIVE_TOKEN_ENCRYPTION_KEY=... \
  GOOGLE_PICKER_API_KEY=... \
  GOOGLE_PICKER_APP_ID=... \
  RESEND_API_KEY=... \
  STRIPE_SECRET_KEY=... \
  STRIPE_PUBLISHABLE_KEY=... \
  STRIPE_WEBHOOK_SECRET=... \
  STRIPE_STARTER_PRICE_ID=... \
  LINE_CHANNEL_SECRET=... \
  LINE_CHANNEL_ACCESS_TOKEN=... \
  LINE_LOGIN_CHANNEL_ID=... \
  LINE_LOGIN_CHANNEL_SECRET=... \
  -a your-app-name

# Edit fly.toml to match your app name + mount source
$EDITOR fly.toml

# Deploy
flyctl deploy -a your-app-name
```

---

## 6. Smoke test (post-deploy)

```bash
BASE=https://your-domain.example.com

# Public endpoints (no auth)
curl -fsS $BASE/                          | grep -o "Personal Data Bank" | head -1
curl -fsS $BASE/pricing                   | grep -o "Personal Data Bank" | head -1
curl -fsS $BASE/api/mcp/info              | python -m json.tool

# Register a test user
curl -fsS -X POST $BASE/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"smoke@test.com","password":"Test1234!","name":"Smoke"}'

# Login + capture token
TOKEN=$(curl -fsS -X POST $BASE/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"smoke@test.com","password":"Test1234!"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Authenticated endpoints
curl -fsS $BASE/api/auth/me   -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -fsS $BASE/api/stats     -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -fsS $BASE/api/usage     -H "Authorization: Bearer $TOKEN" | python -m json.tool
curl -fsS $BASE/api/drive/status -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

A full canonical smoke script lives at [scripts/smoke/admin_e2e_test.py](../../scripts/smoke/admin_e2e_test.py).

---

## 7. Disaster recovery from volume backup

The snapshot in `production-active/` is code only. User data — `projectkey.db`,
`uploads/`, `summaries/`, `context_packs/`, `backups/` — lives on the Fly volume
(`/app/data`) and is **not** captured here. To restore an existing deployment's
data on a new machine you need a volume snapshot.

```bash
# List available snapshots (Fly auto-snapshots daily, retained 5 days by default)
flyctl volumes snapshots list -a personaldatabank

# Restore: create a new volume from a snapshot
flyctl volumes create pdb_data_restored \
  --region sin --size 3 \
  --snapshot-id vs_XXXXXXX \
  -a your-app-name

# Update fly.toml [mounts] source to point at the new volume, then deploy
```

**Manual export** (alternative — pull a tarball over SSH):

```bash
flyctl ssh console -a personaldatabank
# Inside the VM:
cd /app/data && tar czf /tmp/data_backup.tar.gz .
exit
flyctl ssh sftp get /tmp/data_backup.tar.gz ./data_backup.tar.gz -a personaldatabank
# Restore on target by extracting into the target machine's data volume
```

---

## 8. Verifying snapshot is in sync with live code

Whenever the source repo changes structure (new module, new asset), regenerate
the `production-active/` snapshot:

```bash
rm -rf production-active/backend production-active/legacy-frontend
rm -f production-active/Dockerfile production-active/fly.toml production-active/requirements-fly.txt
cp Dockerfile fly.toml requirements-fly.txt production-active/
cp -r backend production-active/ && rm -rf production-active/backend/__pycache__
cp -r legacy-frontend production-active/
cp docs/deployment/.env.example docs/deployment/RUNBOOK.md production-active/

# Verify the trace still finds zero dead modules
python -c "
import ast
from pathlib import Path
graph = {}
for f in Path('backend').glob('*.py'):
    if f.name == '__init__.py': continue
    imports = set()
    tree = ast.parse(f.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module: imports.add(node.module.split('.')[0])
            else: imports.update(a.name for a in node.names)
    graph[f.stem] = imports
reachable, todo = set(), ['main']
while todo:
    m = todo.pop()
    if m in reachable or m not in graph: continue
    reachable.add(m); todo.extend((graph[m] & set(graph)) - reachable)
print(f'Reachable: {len(reachable)}/{len(graph)}; dead: {sorted(set(graph) - reachable)}')
"
# Expected: Reachable: 43/43; dead: []
```

---

## 9. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `FATAL: ADMIN_PASSWORD env var is required` on boot | `.env` missing or `ADMIN_PASSWORD=` blank |
| `WARN: JWT_SECRET_KEY env var not set` | OK on first boot; set `JWT_SECRET_KEY` before scaling to multi-machine |
| `/api/drive/status` returns `503 GOOGLE_OAUTH_NOT_CONFIGURED` | Missing `GOOGLE_OAUTH_CLIENT_ID/_SECRET` or `DRIVE_TOKEN_ENCRYPTION_KEY` |
| `/api/auth/google/init` returns `503 GOOGLE_LOGIN_NOT_CONFIGURED` | Missing `GOOGLE_OAUTH_CLIENT_ID/_SECRET` |
| `POST /webhook/line` returns 503 | Missing `LINE_CHANNEL_SECRET` or `LINE_CHANNEL_ACCESS_TOKEN` |
| Stripe checkout creates session but webhook never fires | Webhook endpoint URL not registered, or `STRIPE_WEBHOOK_SECRET` mismatch |
| Google login succeeds then redirects to `/?google_error=invalid_state` | Browser cookie blocked, or system clock skew >5 min |
| OCR-only PDFs extract empty text | Tesseract OR pdf2image not installed in container — check Dockerfile build logs |

---

## Last reviewed

2026-05-14 — `APP_VERSION` = 9.4.8
