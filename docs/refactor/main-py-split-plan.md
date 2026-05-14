# 📐 Plan: Split `backend/main.py` into APIRouters

> **Status:** PLAN ONLY — not executed.
> **Generated:** 2026-05-14
> **Author:** Cleanup session audit
> **Risk level:** Medium-High. Must be done in dedicated session with smoke testing per chunk.

---

## Why split?

[backend/main.py](../../backend/main.py) is **4,240 lines** with **122 HTTP endpoints** in one file. Symptoms:

- 5 functions over 100 lines (`upload_files`=180, `mcp_streamable_http`=136, `upload_status`=126, `line_confirm_link`=104, `reset_all`=103)
- Code navigation slow (Ctrl+F across 4K lines)
- Git merge conflicts amplified when multiple features touch routing
- New contributor onboarding harder — one file ≠ feature boundary

**Goal:** modular `routes/` package with FastAPI `APIRouter` per feature.

**Non-goal:** changing behavior. Pure mechanical extraction. URL paths unchanged.

---

## Current endpoint distribution (122 total)

| Path prefix | Count | Lines (est.) | Target router |
|---|---|---|---|
| `/api/context-packs` | 13 | ~500 | `routes/context_packs.py` |
| `/api/admin` | 9 | ~400 | `routes/admin.py` |
| `/api/mcp` | 9 | ~450 | `routes/mcp.py` |
| `/api/files` | 8 | ~380 | `routes/files.py` |
| `/api/auth` (incl. google) | 7 | ~300 | `routes/auth.py` |
| `/api/graph` | 6 | ~280 | `routes/graph.py` |
| `/api/line` + `/webhook/line` | 5 + 1 | ~250 | `routes/line.py` |
| `/api/contexts` | 5 | ~200 | `routes/contexts.py` |
| `/api/drive` | 5 | ~280 | `routes/drive.py` |
| `/api/upload` + `/api/upload-status` | 4 + 1 | ~400 (upload_files=180!) | `routes/upload.py` |
| `/api/shared`, `/api/profile`, `/api/suggestions`, `/api/metadata`, `/api/billing` | 3 each (15 total) | ~400 | `routes/misc.py` or split per concern |
| `/api/clusters`, `/api/summary`, `/api/relations` | 2 each (6 total) | ~150 | merged into related routers |
| One-offs (`/api/healthz`, `/api/organize`, etc.) | ~10 | ~250 | stay in `main.py` |
| Static + page routes (`/`, `/app`, `/admin`, `/pricing`, `/legacy`, etc.) | ~10 | ~150 | `routes/pages.py` |
| `/billing/success`, `/billing/cancelled` | 2 | ~30 | `routes/billing_redirects.py` or stay |

Result: **~13 routers**, target ~150-400 lines each, plus `main.py` shrunk to ~500-800 lines (app setup, startup/shutdown, root/healthz, model classes).

---

## Phased execution plan

### Pre-work (do ONCE, before any extraction)

1. **Tag current state** so rollback is one command:
   ```bash
   git tag pre-main-split-2026-05-14
   git push origin pre-main-split-2026-05-14   # if pushing
   ```
2. **Restore `tests/` from git history** OR set up a manual smoke script:
   ```bash
   # Option A: restore deleted tests
   git checkout 8a89eee~1 -- tests/
   # Option B: capture current endpoint list as smoke baseline
   python -c "from backend.main import app; \
     [print(f'{m}  {r.path}') for r in app.routes if hasattr(r,'path') \
      for m in r.methods if hasattr(r,'methods') and m != 'HEAD']" \
     | sort > .baseline_routes.txt
   ```
3. **Verify production-active in sync**:
   ```bash
   diff -rq backend/ production-active/backend/
   # expected: empty
   ```

### Phase A — Low-risk extractions (safe, well-bounded)

Each phase = 1 router. After each: `python -c "from backend.main import app; print(len(app.routes))"` to verify
route count unchanged + smoke a few endpoints.

| Order | Router | Why this first |
|---|---|---|
| A1 | `routes/auth.py` | 7 endpoints, clean boundary, no startup hooks |
| A2 | `routes/admin.py` | 9 endpoints, already isolated in admin module |
| A3 | `routes/billing.py` | 3 endpoints, plus 2 redirect routes |
| A4 | `routes/drive.py` | 5 endpoints, isolated BYOS feature |
| A5 | `routes/line.py` | 5+1 endpoints, isolated bot feature |
| A6 | `routes/pages.py` | 10 static/page routes — pure file serving |

Pattern for each:
```python
# routes/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db, User
from ..auth import register_user, login_user, get_current_user
# ... (only what THIS router uses)

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register")
async def api_register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    return await register_user(db, req.email, req.password, req.name)

# ... rest of auth endpoints
```

```python
# backend/main.py — registration changes only
from .routes import auth as auth_router
app.include_router(auth_router.router)
```

### Phase B — Medium-risk (cross-cutting concerns)

| Order | Router | Why higher risk |
|---|---|---|
| B1 | `routes/upload.py` | `upload_files()` = 180 lines, complex multi-step, background tasks |
| B2 | `routes/mcp.py` | `mcp_streamable_http()` = 136 lines, custom protocol handling |
| B3 | `routes/files.py` | 8 endpoints, many touch the duplicate_detector |
| B4 | `routes/graph.py`, `routes/context_packs.py` | Large endpoint count (6 + 13) |

### Phase C — Final consolidation

| Order | Action |
|---|---|
| C1 | Move all Pydantic request models to `routes/_models.py` (or per-router if domain-bound) |
| C2 | Move `_serve_html()` helper to `routes/pages.py` |
| C3 | Move startup/shutdown hooks to a `lifespan` context manager |
| C4 | Sweep `main.py` for any remaining inline endpoints — should be empty except `/`, `/api/healthz`, maybe lifespan glue |
| C5 | Update [docs/manifest/ACTIVE-PRODUCTION-FILES.md](../manifest/ACTIVE-PRODUCTION-FILES.md) to reflect new layout |
| C6 | Regenerate `production-active/` snapshot |

---

## Acceptance criteria (per phase)

For each router extracted:

1. **Route count unchanged**: `len(app.routes)` before == after
2. **Route paths unchanged**: sorted route paths diff == empty
3. **Server boots clean**: `python -c "from backend.main import app"` returns within 5s with no new warnings
4. **Smoke endpoints respond**: `GET /api/healthz`, `GET /`, `GET /api/mcp/info` (with auth) return 200
5. **One endpoint per router**: at least one endpoint exercised end-to-end via `curl`
6. **`main.py` line count drops**: documented in commit message

---

## Risk register

| Risk | Mitigation |
|---|---|
| Pydantic models in main.py break imports when moved | Keep models in `main.py` until Phase C; routers import from there |
| Background tasks (`BackgroundTasks`) lose context | Verify each task call still in scope after extraction |
| Closure over module-level vars in main.py | Audit each function for `nonlocal`/global state before move |
| Custom dependencies (`Depends(...)`) break | Re-export dependency functions from `routes/_deps.py` |
| Production deploy breaks mid-migration | Each phase = atomic commit; revert single commit if smoke fails |
| `/{filename}` catch-all conflicts with new prefix | Keep catch-all in `main.py` registered LAST |

---

## Why I'm NOT executing this in this session

1. Tests were just removed (`tests/` deleted in commit 8a89eee) — no automated regression coverage during refactor
2. 122 endpoints × manual smoke = many hours
3. Better as a dedicated session with focus + production data backup + ability to rollback
4. User asked for "manage code modularity" — this plan IS the management for now; execution is a separate decision

---

## Estimated effort

- **Pre-work:** 30 min (tag + smoke baseline + verify sync)
- **Phase A (6 routers):** 4-6 hours
- **Phase B (4 routers):** 4-6 hours
- **Phase C (cleanup):** 2 hours
- **Total:** ~10-14 hours across 2-3 sessions

---

## How to execute (when ready)

1. Open this plan + [backend/main.py](../../backend/main.py) side by side
2. Pick one row from Phase A table
3. Create `backend/routes/__init__.py` if not exists
4. Create `backend/routes/{router_name}.py` with the pattern above
5. Cut endpoints from main.py, paste into router file
6. Update imports in router file (only what's needed)
7. Add `app.include_router(...)` in main.py
8. Run acceptance criteria
9. Commit with message: `refactor(routes): extract {feature} into routes/{name}.py (-N lines from main.py)`
10. Repeat
