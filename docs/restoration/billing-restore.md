# 🔁 Restoration Guide — Stripe Billing System

> **ลบเมื่อ:** v9.6.0 · 2026-05-14
> **เหตุผลที่ลบ:** Pre-launch — ยังไม่มี Stripe account / Thai card processor ที่พร้อม + ลด external dependency
> **อะไรที่ "ไม่" ถูกแตะ:**
> - `plan_limits.py` ทั้งไฟล์ (quota system ยังทำงาน)
> - `User.plan`, `User.subscription_status` + Stripe-related columns (DB schema ครบ — restore แล้ว resume ได้ทันที)
> - Admin manual plan change (`/api/admin/users/{id}/plan`) ยังเปลี่ยน free ↔ starter ↔ admin ได้
> - Drive BYOS, MCP, LINE bot — ไม่กระทบ

---

## 📌 ก่อน restore — สิ่งที่ต้องเตรียม

1. **Stripe account** + verified business
2. **Stripe Product + Price ID** สำหรับ Starter plan (subscription)
3. **Stripe Webhook signing secret** จาก Stripe Dashboard
4. **Env vars** ใน `.env`:
   ```bash
   STRIPE_SECRET_KEY=sk_live_xxx       # or sk_test_xxx
   STRIPE_PUBLISHABLE_KEY=pk_live_xxx
   STRIPE_WEBHOOK_SECRET=whsec_xxx
   STRIPE_STARTER_PRICE_ID=price_xxx
   APP_BASE_URL=https://yourdomain     # already set if Drive BYOS works
   ```
5. **Stripe Webhook endpoint** ใน Stripe Dashboard:
   - URL: `https://yourdomain/api/stripe/webhook`
   - Events: `checkout.session.completed`, `customer.subscription.{created,updated,deleted}`, `invoice.payment_{succeeded,failed}`
6. **pip install stripe** — ถ้าลบ dependency ออกแล้วต้อง add back
7. **Existing user data:**
   - `User.stripe_customer_id`, `User.plan`, `User.subscription_status` etc. ยังอยู่ใน DB
   - Users ที่ admin upgrade เป็น starter manually (`manual_plan_override=True`) — Stripe webhook จะ skip จนกว่า admin จะ set กลับเป็น `False`

---

## 🛠️ Restore Steps (7 phases · ~1 ชม.)

### Phase 1 — สร้างไฟล์ `backend/billing.py`

สร้างไฟล์ใหม่ที่ [backend/billing.py](../../backend/billing.py) ด้วยเนื้อหาเต็มนี้:

```python
"""Billing module for Personal Data Bank (PDB) — Stripe Payment System.

Handles Stripe Checkout, Customer Portal, and Webhook processing.
Stripe Webhook is the source of truth for subscription status.
"""
import logging
import os
from datetime import datetime

import stripe
from fastapi import Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import User, WebhookLog, gen_id
from .config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_STARTER_PRICE_ID,
    APP_BASE_URL,
)

logger = logging.getLogger(__name__)
stripe.api_key = STRIPE_SECRET_KEY


async def create_checkout_session(user: User, db: AsyncSession) -> str:
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")
    if not STRIPE_STARTER_PRICE_ID:
        raise HTTPException(status_code=503, detail="Starter plan price is not configured.")
    if user.subscription_status == "starter_active":
        raise HTTPException(status_code=400, detail="You are already on the Starter plan.")

    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email, name=user.name,
            metadata={"user_id": user.id},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        db.add(user)
        await db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id, mode="subscription",
        line_items=[{"price": STRIPE_STARTER_PRICE_ID, "quantity": 1}],
        success_url=f"{APP_BASE_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{APP_BASE_URL}/billing/cancelled",
        metadata={"user_id": user.id},
    )
    return session.url


async def create_portal_session(user: User) -> str:
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Billing account not found.")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{APP_BASE_URL}",
    )
    return session.url


async def process_webhook(request: Request, db: AsyncSession) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    _dev_bypass = os.getenv("STRIPE_WEBHOOK_DEV_BYPASS") == "1"
    if not STRIPE_WEBHOOK_SECRET and not _dev_bypass:
        logger.error("Webhook received but STRIPE_WEBHOOK_SECRET is unset.")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        import json as _json
        try:
            event = _json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        if "id" not in event or "type" not in event:
            raise HTTPException(status_code=400, detail="Not a valid Stripe event")

    event_id = event.get("id", "") if isinstance(event, dict) else event.id
    event_type = event.get("type", "") if isinstance(event, dict) else event.type
    data_object = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object
    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Missing event id or type")

    existing = await db.execute(select(WebhookLog).where(WebhookLog.event_id == event_id))
    if existing.scalar_one_or_none():
        return {"status": "already_processed"}

    obj_id = data_object.get("id", "") if isinstance(data_object, dict) else getattr(data_object, "id", "")

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(data_object, db)
        elif event_type == "customer.subscription.created":
            await _handle_subscription_created(data_object, db)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(data_object, db)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(data_object, db)
        elif event_type == "invoice.payment_succeeded":
            await _handle_payment_succeeded(data_object, db)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(data_object, db)

        log = WebhookLog(
            id=gen_id(), event_id=event_id, event_type=event_type,
            stripe_object_id=obj_id, status="processed",
        )
        db.add(log)
        await db.commit()
        return {"status": "processed"}
    except Exception as e:
        log = WebhookLog(
            id=gen_id(), event_id=event_id, event_type=event_type,
            stripe_object_id=obj_id, status="error", error_message=str(e),
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))


async def _find_user_by_customer(customer_id: str, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    return result.scalar_one_or_none()


def _first_or_empty(obj: dict, *keys: str) -> dict:
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(k)
    if isinstance(cur, list):
        return cur[0] if cur and isinstance(cur[0], dict) else {}
    return cur if isinstance(cur, dict) else {}


async def _handle_checkout_completed(session_obj, db: AsyncSession):
    customer_id = session_obj.get("customer")
    subscription_id = session_obj.get("subscription")
    user_id = session_obj.get("metadata", {}).get("user_id")

    user = None
    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if not user and customer_id:
        user = await _find_user_by_customer(customer_id, db)
    if not user:
        return

    previous_plan = user.plan
    user.stripe_customer_id = customer_id
    user.stripe_subscription_id = subscription_id
    user.plan = "starter"
    user.subscription_status = "starter_active"
    user.manual_plan_override = False
    user.updated_at = datetime.utcnow()
    db.add(user)

    from .plan_limits import unlock_data_for_plan, log_audit
    unlock_result = await unlock_data_for_plan(db, user.id, "starter")
    await log_audit(db, user.id, "plan_changed",
                    old_value=previous_plan or "free", new_value="starter",
                    triggered_by="stripe_webhook")

    from .database import UsageLog
    db.add(UsageLog(user_id=user.id, action="upgrade"))
    await db.commit()


async def _handle_subscription_created(sub_obj, db: AsyncSession):
    user = await _find_user_by_customer(sub_obj.get("customer"), db)
    if not user or getattr(user, "manual_plan_override", False):
        return
    user.stripe_subscription_id = sub_obj.get("id")
    first_item = _first_or_empty(sub_obj, "items", "data")
    user.stripe_price_id = (first_item.get("price") or {}).get("id", "") if isinstance(first_item.get("price"), dict) else ""
    user.plan = "starter"
    user.subscription_status = _map_stripe_status(sub_obj.get("status"))
    user.current_period_start = _ts_to_dt(sub_obj.get("current_period_start"))
    user.current_period_end = _ts_to_dt(sub_obj.get("current_period_end"))
    user.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)
    user.updated_at = datetime.utcnow()
    db.add(user)
    await db.commit()


async def _handle_subscription_updated(sub_obj, db: AsyncSession):
    user = await _find_user_by_customer(sub_obj.get("customer"), db)
    if not user or getattr(user, "manual_plan_override", False):
        return
    user.subscription_status = _map_stripe_status(sub_obj.get("status"))
    user.current_period_start = _ts_to_dt(sub_obj.get("current_period_start"))
    user.current_period_end = _ts_to_dt(sub_obj.get("current_period_end"))
    user.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)
    user.updated_at = datetime.utcnow()
    db.add(user)
    await db.commit()


async def _handle_subscription_deleted(sub_obj, db: AsyncSession):
    user = await _find_user_by_customer(sub_obj.get("customer"), db)
    if not user or getattr(user, "manual_plan_override", False):
        return

    previous_plan = user.plan
    previous_status = user.subscription_status
    ended_at = sub_obj.get("ended_at") or sub_obj.get("canceled_at")
    ended_dt = _ts_to_dt(ended_at) if ended_at else None
    period_end_dt = _ts_to_dt(sub_obj.get("current_period_end"))
    now = datetime.utcnow()

    still_active = (
        (ended_dt is not None and ended_dt > now)
        or (ended_dt is None and period_end_dt is not None and period_end_dt > now)
    )

    if still_active:
        from .plan_limits import log_audit
        user.subscription_status = "starter_canceled"
        user.cancel_at_period_end = True
        if period_end_dt:
            user.current_period_end = period_end_dt
        user.updated_at = now
        db.add(user)
        await log_audit(db, user.id, "subscription_status_changed",
                        old_value=f"{previous_plan}/{previous_status}",
                        new_value=f"starter/starter_canceled (period_end={period_end_dt})",
                        triggered_by="stripe_webhook")
        await db.commit()
        return

    user.plan = "free"
    user.subscription_status = "free"
    user.stripe_subscription_id = None
    user.stripe_price_id = None
    user.current_period_start = None
    user.current_period_end = None
    user.cancel_at_period_end = False
    user.updated_at = now
    db.add(user)

    from .plan_limits import lock_excess_data, log_audit
    await lock_excess_data(db, user.id, "free")
    await log_audit(db, user.id, "plan_changed",
                    old_value=f"{previous_plan}/{previous_status}", new_value="free",
                    triggered_by="stripe_webhook")
    from .database import UsageLog
    db.add(UsageLog(user_id=user.id, action="downgrade"))
    await db.commit()


async def _handle_payment_succeeded(invoice_obj, db: AsyncSession):
    user = await _find_user_by_customer(invoice_obj.get("customer"), db)
    if not user or getattr(user, "manual_plan_override", False):
        return
    if invoice_obj.get("subscription"):
        user.stripe_subscription_id = invoice_obj.get("subscription")
    user.plan = "starter"
    user.subscription_status = "starter_active"
    first_line = _first_or_empty(invoice_obj, "lines", "data")
    period = first_line.get("period") if isinstance(first_line.get("period"), dict) else {}
    period = period or {}
    if period.get("start"):
        user.current_period_start = _ts_to_dt(period["start"])
    if period.get("end"):
        user.current_period_end = _ts_to_dt(period["end"])
    user.updated_at = datetime.utcnow()
    db.add(user)
    await db.commit()


async def _handle_payment_failed(invoice_obj, db: AsyncSession):
    user = await _find_user_by_customer(invoice_obj.get("customer"), db)
    if not user or getattr(user, "manual_plan_override", False):
        return
    user.subscription_status = "starter_past_due"
    user.updated_at = datetime.utcnow()
    db.add(user)
    await db.commit()


def _map_stripe_status(stripe_status: str) -> str:
    mapping = {
        "active": "starter_active", "past_due": "starter_past_due",
        "canceled": "starter_canceled", "incomplete": "starter_incomplete",
        "incomplete_expired": "free", "trialing": "starter_active",
        "unpaid": "starter_past_due",
    }
    return mapping.get(stripe_status, "free")


def _ts_to_dt(ts) -> datetime | None:
    return datetime.utcfromtimestamp(int(ts)) if ts else None


def get_billing_info(user: User) -> dict:
    return {
        "plan": user.plan or "free",
        "subscription_status": user.subscription_status or "free",
        "current_period_end": user.current_period_end.isoformat() if user.current_period_end else None,
        "cancel_at_period_end": user.cancel_at_period_end or False,
        "has_stripe_customer": bool(user.stripe_customer_id),
    }
```

---

### Phase 2 — `backend/config.py` (เพิ่ม Stripe env vars)

หา comment ที่เขียน `# Stripe Payment removed in v9.6.0` ที่ประมาณบรรทัด 126 แล้วแทนด้วย:

```python
# ─── Stripe Payment ───
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_STARTER_PRICE_ID = os.getenv("STRIPE_STARTER_PRICE_ID", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")
```
**Note:** ถ้า `APP_BASE_URL` มีอยู่แล้วใต้ comment นั้น ให้ลบ duplicate ออก 1 บรรทัด

---

### Phase 3 — `backend/main.py` (เพิ่ม import + 4 endpoints + 3 redirect routes)

ในส่วน import (ประมาณบรรทัด 41) เปลี่ยน:
```python
# Billing (Stripe) removed in v9.6.0 ...
```
กลับเป็น:
```python
from .billing import create_checkout_session, create_portal_session, process_webhook, get_billing_info
```

หา comment `# Billing (Stripe) endpoints removed in v9.6.0` (หลัง MCP block) แล้วแทนด้วย:

```python
# ─── BILLING API ───

class CheckoutRequest(BaseModel):
    plan: str = "starter"

@app.post("/api/billing/create-checkout-session")
async def api_create_checkout(body: CheckoutRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if body.plan != "starter":
        raise HTTPException(status_code=400, detail="Only Starter plan is available for checkout.")
    try:
        url = await create_checkout_session(user, db)
        return {"checkout_url": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=500, detail="We could not start checkout right now.")

@app.post("/api/billing/create-portal-session")
async def api_create_portal(user: User = Depends(get_current_user)):
    try:
        url = await create_portal_session(user)
        return {"portal_url": url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portal creation failed: {e}")
        raise HTTPException(status_code=500, detail="Could not open billing portal.")

@app.post("/api/stripe/webhook")
async def api_stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    return await process_webhook(request, db)

@app.get("/api/billing/info")
async def api_billing_info(user: User = Depends(get_current_user)):
    return get_billing_info(user)
```

หา comment `# Billing redirect routes ... removed in v9.6.0` ใกล้ๆ `_serve_html` แล้วแทนด้วย:

```python
@app.get("/billing/success")
async def serve_billing_success():
    return RedirectResponse(url="/app?billing=success", status_code=302)

@app.get("/pricing")
async def serve_pricing():
    pricing_path = os.path.join(BASE_DIR, "legacy-frontend", "pricing.html")
    if os.path.exists(pricing_path):
        resp = FileResponse(pricing_path, media_type="text/html")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp
    raise HTTPException(status_code=404)

@app.get("/billing/cancelled")
async def serve_billing_cancelled():
    return RedirectResponse(url="/app?billing=cancelled", status_code=302)
```

ที่ `get_file_content` (ประมาณบรรทัด 1346) เปลี่ยน:
```python
raise HTTPException(status_code=403, detail="ไฟล์นี้ถูกล็อค (เกินโควต้าแพลน) — ติดต่อแอดมินเพื่อปลดล็อก")
```
กลับเป็น:
```python
raise HTTPException(status_code=403, detail="ไฟล์นี้ถูกล็อค — อัปเกรดเป็น Starter เพื่อเข้าถึงไฟล์ที่ล็อค")
```

---

### Phase 4 — `backend/admin.py` (restore Stripe collision guards)

**4a.** ใน `get_user_detail` หา:
```python
# v9.6.0 — Stripe ถูกลบ; admin downgrade ไม่ถูก block แล้ว
stripe_active = False
can_admin_downgrade = True
block_reason = None
```
แทนด้วย:
```python
stripe_active = bool(
    user.stripe_subscription_id
    and user.subscription_status in ("starter_active", "starter_past_due")
)
can_admin_downgrade = not stripe_active
block_reason = "STRIPE_ACTIVE_SUBSCRIPTION" if stripe_active else None
```

**4b.** ใน `change_user_plan` หา:
```python
# v9.6.0 — Stripe collision guard removed (billing system ถูกลบ).
# Admin downgrade ทำได้อิสระ; ไม่มี active Stripe subscription ให้กังวลแล้ว.
old_plan_effective = _effective_plan(target)
```
แทนด้วย:
```python
stripe_active = bool(
    target.stripe_subscription_id
    and target.subscription_status in ("starter_active", "starter_past_due")
)
target_eff = _effective_plan(target)
is_downgrade_to_free = (
    target_eff in ("starter", "admin") and new_plan == "free"
)
if stripe_active and is_downgrade_to_free:
    raise HTTPException(
        status_code=409,
        detail={"error": {
            "code": "STRIPE_ACTIVE_SUBSCRIPTION",
            "message": "ผู้ใช้นี้มี Stripe subscription กำลังใช้งาน — ให้ผู้ใช้ยกเลิกที่ Customer Portal ก่อน",
        }},
    )
old_plan_effective = target_eff
```

---

### Phase 5 — Frontend `app.js` + `landing.js`

**5a.** ใน `app.js` หา comment `// Billing (Stripe) removed in v9.6.0` แล้วแทนด้วยฟังก์ชันเต็ม (ดู git history `git show 406387a:legacy-frontend/app.js` ก่อน v9.6.0 — มี `initBilling`, `showPlanModal`, `closePlanModal`, `loadBillingInfo`, `updateBillingUI`, `doStarterCheckout`, `doOpenPortal`, `checkBillingRedirect`)

**5b.** ใน `app.js` `initAppData()` เพิ่ม:
```javascript
loadBillingInfo();
initBilling();
```

**5c.** ใน `app.js` ใน `DOMContentLoaded` listener (ท้ายไฟล์) เพิ่ม:
```javascript
try { checkBillingRedirect?.(); } catch {}
```

**5d.** ใน `app.js` `showUpgradeModal` — restore original body ที่มี `/pricing` CTA:
```javascript
overlay.innerHTML = `
 <div class="upgrade-modal">
 <div class="upgrade-modal-icon"></div>
 <h3 class="upgrade-modal-title">${getLang() === 'th' ? 'อัปเกรดแพลนของคุณ' : 'Upgrade Your Plan'}</h3>
 <p class="upgrade-modal-message">${message}</p>
 <div class="upgrade-modal-actions">
 <button class="btn btn-primary upgrade-modal-btn" onclick="window.location.href='/pricing'">
 ${getLang() === 'th' ? 'ดูแพลน Starter — ฿99/เดือน' : 'View Starter Plan — ฿99/mo'}
 </button>
 <button class="btn btn-outline upgrade-modal-dismiss" onclick="this.closest('.upgrade-modal-overlay').remove()">
 ${getLang() === 'th' ? 'ไว้ทีหลัง' : 'Maybe Later'}
 </button>
 </div>
 </div>`;
```

**5e.** ใน `landing.js` `initAuth()` หา `// v9.6.0 — pricing buttons removed` แล้วเพิ่มกลับ:
```javascript
document.getElementById('btn-pricing-free')?.addEventListener('click', () => showAuthModal('register'));
document.getElementById('btn-pricing-starter')?.addEventListener('click', () => {
 if (state.authToken) {
  window.location.href = '/pricing';
 } else {
  showAuthModal('register');
  showToast(getLang() === 'th' ? 'สมัครก่อน แล้วอัปเกรดในโปรไฟล์' : 'Register first, then upgrade', 'info');
 }
});
```

---

### Phase 6 — Frontend HTML

**6a.** `legacy-frontend/pricing.html` — restore เต็มไฟล์จาก git history:
```bash
git show 406387a:legacy-frontend/pricing.html > legacy-frontend/pricing.html
```

**6b.** `legacy-frontend/landing.html` — restore pricing section (~150 lines) จาก git history:
หา comment `<!-- Pricing section removed in v9.6.0 -->` แล้วแทนด้วย pricing-section block + comparison table + executive plans + trust note. ดู git diff: `git show 406387a:legacy-frontend/landing.html`

Restore pricing FAQ items (3 items: Free/Starter, Starter เป็น Digital Twin, Starter จ่ายผ่านอะไร) — หา `<!-- Pricing FAQ items removed in v9.6.0 -->` แล้วแทนด้วย 3 `<div class="faq-item">` blocks

**6c.** `legacy-frontend/app.html` — restore billing-plan-card + plan-modal:

ใน profile-modal หา `<!-- Subscription / billing UI removed in v9.6.0 -->` แล้วแทนด้วย:
```html
<div class="billing-section" id="billing-section">
 <div class="billing-plan-card" id="billing-plan-card">
  <div class="billing-plan-info">
   <span class="billing-plan-badge" id="billing-plan-badge">Free</span>
   <span class="billing-plan-name" id="billing-plan-name">Personal AI Context</span>
  </div>
  <div class="billing-plan-detail" id="billing-plan-detail">แพลนปัจจุบัน: Free</div>
  <div class="billing-actions" id="billing-actions">
   <button class="btn btn-primary btn-sm" id="btn-upgrade-starter" style="display:none;">Upgrade to Starter — ฿99/mo</button>
   <button class="btn btn-outline btn-sm" id="btn-manage-billing" style="display:none;">จัดการการชำระเงิน</button>
  </div>
 </div>
</div>
```

ใน usage-section header เพิ่ม `<span class="usage-plan-label" id="usage-plan-label">🆓 Free</span>` กลับ

หา `<!-- Plan selection modal removed in v9.6.0 -->` แล้วแทนด้วย plan-modal เต็ม (Free + Starter + Core/Pro/Elite cards) จาก git history: `git show 406387a:legacy-frontend/app.html`

---

### Phase 7 — Dependencies + Stripe Dashboard setup

```bash
# Install Stripe SDK
pip install stripe

# (ถ้า requirements-fly.txt ลบ stripe ออกแล้ว — ใส่กลับ)
echo "stripe>=7.0.0" >> requirements-fly.txt

# Set secrets ใน Fly.io
flyctl secrets set \
  STRIPE_SECRET_KEY=sk_live_xxx \
  STRIPE_PUBLISHABLE_KEY=pk_live_xxx \
  STRIPE_WEBHOOK_SECRET=whsec_xxx \
  STRIPE_STARTER_PRICE_ID=price_xxx
```

**Stripe Dashboard:**
1. Create Product "PDB Starter" with recurring price ฿99/month (THB)
2. Copy Price ID → `STRIPE_STARTER_PRICE_ID`
3. Create Webhook endpoint: `https://yourdomain/api/stripe/webhook`
4. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created` / `.updated` / `.deleted`
   - `invoice.payment_succeeded` / `.payment_failed`
5. Copy signing secret → `STRIPE_WEBHOOK_SECRET`
6. Configure Customer Portal — allow cancel + update payment method

---

## ✅ Smoke test หลัง restore

```bash
# 1. Import
python -c "from backend.main import app; routes=[r for r in app.routes if hasattr(r,'path')]; print(len(routes))"
# Expected: 124 routes (117 + 4 billing API + 3 redirect routes)

# 2. Boot
python -m uvicorn backend.main:app --reload --port 8000

# 3. Endpoints
curl http://localhost:8000/api/billing/info -H "Authorization: Bearer $TOKEN"
# Expected: 200 with {"plan":"free",...}

curl http://localhost:8000/pricing
# Expected: 200 HTML

# 4. Stripe CLI webhook test
stripe listen --forward-to localhost:8000/api/stripe/webhook
stripe trigger checkout.session.completed
```

## 🧪 Manual UI test

1. Login → เปิด profile modal → เห็น "Upgrade to Starter — ฿99/mo" button
2. คลิก → redirect ไปหน้า `/pricing` → คลิก "Get Starter" → redirect ไป Stripe Checkout
3. ใช้ test card `4242 4242 4242 4242` → กรอก expiry/cvc → กด Pay
4. Redirect กลับ → toast " อัปเกรดสำเร็จ!"
5. Profile modal → badge เปลี่ยนเป็น "Starter"
6. Trigger quota → คลิก quota → `showUpgradeModal` แสดง CTA ไป `/pricing` (ไม่ใช่ generic message)

---

## 📊 Files changed in this restoration

| File | Action |
|---|---|
| `backend/billing.py` | **CREATE** (Phase 1) |
| `backend/config.py` | Edit — restore 4 STRIPE_* env vars |
| `backend/main.py` | Edit — restore import + 4 endpoints + 3 redirect routes + file-lock message |
| `backend/admin.py` | Edit — restore Stripe collision guards (2 blocks) |
| `legacy-frontend/app.js` | Edit — restore 8 billing functions + initAppData calls + showUpgradeModal /pricing CTA + checkBillingRedirect on DOMContentLoaded |
| `legacy-frontend/landing.js` | Edit — restore btn-pricing-free / btn-pricing-starter handlers |
| `legacy-frontend/pricing.html` | **CREATE** (from git history) |
| `legacy-frontend/landing.html` | Edit — restore pricing section + 3 FAQ items |
| `legacy-frontend/app.html` | Edit — restore billing-plan-card + usage-plan-label + plan-modal |
| `requirements-fly.txt` | Edit — add `stripe>=7.0.0` |

---

## 💡 Notes

- **DB schema ไม่ต้องแก้** — `User.stripe_*`, `plan`, `subscription_status`, `current_period_*`, `cancel_at_period_end`, `manual_plan_override` ทุก column ยังอยู่ (จาก migration v5.9.2 + v8.2.0)
- **plan_limits.py ไม่ต้องแก้** — `_effective_plan`, `_get_billing_period_start` ทำงานเหมือนเดิม. หลัง restore Stripe webhook จะ set `subscription_status` กลับเป็น `starter_active`/`starter_canceled` ตามจริง
- **WebhookLog table** — ยังอยู่ใน DB schema (database.py) ไม่ต้องสร้าง migration
- **Existing admin-promoted starter users** (`manual_plan_override=True`): หลัง restore — Stripe webhook จะ **ข้าม** users คนนี้จนกว่า admin จะ set `manual_plan_override=False` ผ่าน DB direct (มี comment ใน `_handle_subscription_created` อธิบายไว้)
- **CSS classes** — `.btn-google`, `.upgrade-modal*`, `.billing-*`, `.plan-modal`, `.pricing-*` ทั้งหมดยังอยู่ใน styles.css / landing.css — ไม่ต้องเพิ่ม CSS

---

**Source code snapshot:** `git show <SHA before v9.6.0>:backend/billing.py` (commit ของ v9.5.0)
