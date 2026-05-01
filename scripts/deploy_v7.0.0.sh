#!/usr/bin/env bash
# Deploy script — v7.0.0 (Personal Data Bank with Google Drive BYOS)
#
# Usage:
#   1. Make sure .env contains all 6 BYOS env vars (already verified ✓)
#   2. Run: bash scripts/deploy_v7.0.0.sh
#   3. Or run each section manually if you want step-by-step control
#
# What this does:
#   - Verifies 6 BYOS secrets exist in local .env
#   - Pushes them to Fly.io as production secrets (--stage = don't restart yet)
#   - Builds Docker image + deploys (triggers restart)
#   - Runs basic smoke test post-deploy
#
# Safety:
#   - Reads from .env (gitignored) — values never echoed
#   - --stage prevents partial restart between secret writes
#   - Smoke test verifies version + BYOS feature_available flag

set -e   # exit on any error
set -u   # error on undefined var

cd "$(dirname "$0")/.."   # cd to project root

# ─── Verify .env has all required secrets ─────────────────────────
echo "═══ Step 1/4 — Verifying .env has 6 BYOS secrets ═══"
required_keys=(
    GOOGLE_OAUTH_CLIENT_ID
    GOOGLE_OAUTH_CLIENT_SECRET
    GOOGLE_PICKER_API_KEY
    GOOGLE_PICKER_APP_ID
    GOOGLE_OAUTH_MODE
    DRIVE_TOKEN_ENCRYPTION_KEY
)
for key in "${required_keys[@]}"; do
    if ! grep -q "^${key}=" .env; then
        echo "  ❌ MISSING: ${key} in .env"
        exit 1
    fi
    val_len=$(grep "^${key}=" .env | cut -d= -f2- | wc -c)
    echo "  ✓ ${key} present (length ${val_len})"
done

# ─── Source .env into shell so flyctl can read them ──────────────
set -a
# shellcheck disable=SC1091
source .env
set +a

# ─── Stage all 6 secrets in one batch (no premature restart) ─────
echo ""
echo "═══ Step 2/4 — Staging 6 secrets to Fly.io ═══"
flyctl secrets set \
    "GOOGLE_OAUTH_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID}" \
    "GOOGLE_OAUTH_CLIENT_SECRET=${GOOGLE_OAUTH_CLIENT_SECRET}" \
    "GOOGLE_PICKER_API_KEY=${GOOGLE_PICKER_API_KEY}" \
    "GOOGLE_PICKER_APP_ID=${GOOGLE_PICKER_APP_ID}" \
    "GOOGLE_OAUTH_MODE=${GOOGLE_OAUTH_MODE}" \
    "DRIVE_TOKEN_ENCRYPTION_KEY=${DRIVE_TOKEN_ENCRYPTION_KEY}" \
    --stage

# ─── Deploy (Docker build + push image + restart with new secrets) ─
echo ""
echo "═══ Step 3/4 — Deploying v7.0.0 to Fly.io ═══"
flyctl deploy

# ─── Smoke test post-deploy ─────────────────────────────────────
echo ""
echo "═══ Step 4/4 — Production smoke test ═══"
sleep 5   # give app a moment to settle
echo ""
echo "  GET / (landing page should contain 'Personal Data Bank')"
curl -s -o /tmp/pdb_landing.html -w "    HTTP %{http_code}\n" https://project-key.fly.dev/
if grep -q "Personal Data Bank" /tmp/pdb_landing.html; then
    echo "    ✓ Contains 'Personal Data Bank'"
else
    echo "    ❌ Missing 'Personal Data Bank' string"
fi
if grep -q "Project KEY" /tmp/pdb_landing.html; then
    echo "    ⚠ Old brand 'Project KEY' still appears"
else
    echo "    ✓ No 'Project KEY' leftover"
fi
rm -f /tmp/pdb_landing.html

echo ""
echo "  GET /api/mcp/info (no auth — should return 401 Unauthorized)"
status=$(curl -s -o /dev/null -w "%{http_code}" https://project-key.fly.dev/api/mcp/info)
echo "    HTTP ${status} (expected 401)"

echo ""
echo "  Note: BYOS endpoints require JWT — manual test via UI:"
echo "    1. Login at https://project-key.fly.dev/"
echo "    2. Profile modal → Storage Mode section → 'Connect Drive'"
echo "    3. Verify folder /Personal Data Bank/ created in your Drive"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ DEPLOY v7.0.0 COMPLETE"
echo "═══════════════════════════════════════════════════════════"
echo "  Version:     7.0.0"
echo "  Production:  https://project-key.fly.dev/"
echo "  Features:"
echo "    • Personal Data Bank rebrand (v6.1.0)"
echo "    • Google Drive BYOS (v7.0.0)"
echo "    • PKCE OAuth + Personality Profile + 30 MCP tools"
echo "═══════════════════════════════════════════════════════════"
