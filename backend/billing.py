"""Billing module for Project KEY — v5.9.2 Stripe Payment System.

Handles Stripe Checkout, Customer Portal, and Webhook processing.
Stripe Webhook is the source of truth for subscription status.
"""
import logging
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

# Configure Stripe
stripe.api_key = STRIPE_SECRET_KEY


# ─── Checkout Session ───

async def create_checkout_session(user: User, db: AsyncSession) -> str:
    """Create a Stripe Checkout Session for Starter plan.
    Returns the checkout URL.
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")
    if not STRIPE_STARTER_PRICE_ID:
        raise HTTPException(status_code=503, detail="Starter plan price is not configured.")

    # Already on Starter?
    if user.subscription_status == "starter_active":
        raise HTTPException(status_code=400, detail="You are already on the Starter plan.")

    # Reuse existing Stripe customer or create new
    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": user.id},
        )
        customer_id = customer.id
        user.stripe_customer_id = customer_id
        db.add(user)
        await db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": STRIPE_STARTER_PRICE_ID, "quantity": 1}],
        success_url=f"{APP_BASE_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{APP_BASE_URL}/billing/cancelled",
        metadata={"user_id": user.id},
    )

    return session.url


# ─── Customer Portal ───

async def create_portal_session(user: User) -> str:
    """Create a Stripe Customer Portal session.
    Returns the portal URL.
    """
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Billing account not found. Please contact support.")

    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{APP_BASE_URL}",
    )
    return session.url


# ─── Webhook Processing ───

async def process_webhook(request: Request, db: AsyncSession) -> dict:
    """Verify and process a Stripe webhook event."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify signature
    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            logger.warning("Webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")
        except Exception as e:
            logger.warning(f"Webhook construct error: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        # Dev mode — no signature verification (for Stripe CLI testing)
        import json as _json
        try:
            raw = _json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        if "id" not in raw or "type" not in raw:
            raise HTTPException(status_code=400, detail="Not a valid Stripe event")
        event = raw  # Use as plain dict in dev mode

    # Extract fields — handle both StripeObject and plain dict
    event_id = event.get("id", "") if isinstance(event, dict) else event.id
    event_type = event.get("type", "") if isinstance(event, dict) else event.type
    data_object = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Missing event id or type")

    # Idempotency — skip if already processed
    existing = await db.execute(select(WebhookLog).where(WebhookLog.event_id == event_id))
    if existing.scalar_one_or_none():
        logger.info(f"Webhook {event_id} already processed, skipping")
        return {"status": "already_processed"}

    # Determine stripe_object_id from data
    obj_id = data_object.get("id", "") if isinstance(data_object, dict) else getattr(data_object, "id", "")

    # Process event
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
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")

        # Log success
        log = WebhookLog(
            id=gen_id(), event_id=event_id, event_type=event_type,
            stripe_object_id=obj_id,
            status="processed",
        )
        db.add(log)
        await db.commit()
        logger.info(f"Webhook processed: {event_type} ({event_id})")
        return {"status": "processed"}

    except Exception as e:
        # Log error
        log = WebhookLog(
            id=gen_id(), event_id=event_id, event_type=event_type,
            stripe_object_id=obj_id,
            status="error", error_message=str(e),
        )
        db.add(log)
        await db.commit()
        logger.error(f"Webhook error: {event_type} ({event_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Event Handlers ───

async def _find_user_by_customer(customer_id: str, db: AsyncSession) -> User | None:
    """Find user by stripe_customer_id."""
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    return result.scalar_one_or_none()


def _first_or_empty(obj: dict, *keys: str) -> dict:
    """Safely traverse nested dict→list[0]→dict structures from Stripe payloads.

    Returns {} if any key is missing OR the list at any step is empty,
    avoiding IndexError when Stripe sends an empty `data` array.

    Example: _first_or_empty(sub_obj, "items", "data") -> first item dict or {}
    """
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(k)
    if isinstance(cur, list):
        return cur[0] if cur and isinstance(cur[0], dict) else {}
    return cur if isinstance(cur, dict) else {}


async def _handle_checkout_completed(session_obj, db: AsyncSession):
    """checkout.session.completed — User just paid.
    
    UPGRADE UNLOCK (PRD v5.9.3):
    - Plan changes to 'starter' immediately
    - All Starter limits apply instantly:
      * Files: 50 (up from 5)
      * Packs: 5 (up from 1)
      * AI Summary: 100/month (up from 5)
      * Export: 300/month (up from 10)
      * Refresh: 10/month (up from 0)
      * Semantic Search: enabled
      * File types: +png, +jpg
      * Max file size: 20MB (up from 10MB)
    - Existing data beyond Free limits becomes fully accessible again
    """
    customer_id = session_obj.get("customer")
    subscription_id = session_obj.get("subscription")
    user_id = session_obj.get("metadata", {}).get("user_id")

    # Find user by metadata user_id or customer_id
    user = None
    if user_id:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    if not user and customer_id:
        user = await _find_user_by_customer(customer_id, db)
    if not user:
        logger.error(f"checkout.session.completed: user not found (customer={customer_id}, user_id={user_id})")
        return

    previous_plan = user.plan
    user.stripe_customer_id = customer_id
    user.stripe_subscription_id = subscription_id
    user.plan = "starter"
    user.subscription_status = "starter_active"
    user.updated_at = datetime.utcnow()
    db.add(user)

    # Unlock previously locked data (PRD v5.9.3)
    from .plan_limits import unlock_data_for_plan, log_audit
    unlock_result = await unlock_data_for_plan(db, user.id, "starter")

    # Audit log
    await log_audit(db, user.id, "plan_changed",
                    old_value=previous_plan or "free",
                    new_value="starter",
                    triggered_by="stripe_webhook")
    if unlock_result["unlocked_packs"] > 0 or unlock_result["unlocked_files"] > 0:
        await log_audit(db, user.id, "data_unlocked",
                        new_value=f"packs:{unlock_result['unlocked_packs']}, files:{unlock_result['unlocked_files']}",
                        triggered_by="stripe_webhook")

    # Log upgrade event for tracking
    from .database import UsageLog
    upgrade_log = UsageLog(user_id=user.id, action="upgrade")
    db.add(upgrade_log)

    await db.commit()
    logger.info(
        f"User {user.id} upgraded: {previous_plan} → starter via checkout. "
        f"All Starter limits now active. "
        f"Unlocked: {unlock_result['unlocked_packs']} packs, {unlock_result['unlocked_files']} files."
    )


async def _handle_subscription_created(sub_obj, db: AsyncSession):
    """customer.subscription.created — New subscription."""
    customer_id = sub_obj.get("customer")
    user = await _find_user_by_customer(customer_id, db)
    if not user:
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
    """customer.subscription.updated — Status change, cancel, etc."""
    customer_id = sub_obj.get("customer")
    user = await _find_user_by_customer(customer_id, db)
    if not user:
        return

    user.subscription_status = _map_stripe_status(sub_obj.get("status"))
    user.current_period_start = _ts_to_dt(sub_obj.get("current_period_start"))
    user.current_period_end = _ts_to_dt(sub_obj.get("current_period_end"))
    user.cancel_at_period_end = sub_obj.get("cancel_at_period_end", False)
    user.updated_at = datetime.utcnow()
    db.add(user)
    await db.commit()


async def _handle_subscription_deleted(sub_obj, db: AsyncSession):
    """customer.subscription.deleted — Subscription ended.

    DOWNGRADE BEHAVIOR (PRD v5.9.3 section 16):
    - Data is NEVER deleted — user's files, packs, summaries remain intact
    - Plan reverts to Free — enforcement checks will limit actions
    - User can re-upgrade anytime to restore full Starter access

    A8 GUARD: Stripe sends this event when a subscription truly ends, but as
    defensive insurance against test webhooks / edge cases / replays we
    re-check `ended_at`. If the subscription claims to be deleted but
    `ended_at` is still in the future, keep the user on starter_canceled
    with period_end intact (matches PRD section 15 "active until period end").
    """
    customer_id = sub_obj.get("customer")
    user = await _find_user_by_customer(customer_id, db)
    if not user:
        return

    # Record downgrade info for audit trail
    previous_plan = user.plan
    previous_status = user.subscription_status

    # A8 — defensive: only fully downgrade if subscription has actually ended
    ended_at = sub_obj.get("ended_at") or sub_obj.get("canceled_at")
    ended_dt = _ts_to_dt(ended_at) if ended_at else None
    period_end_dt = _ts_to_dt(sub_obj.get("current_period_end"))
    now = datetime.utcnow()

    still_active = (
        (ended_dt is not None and ended_dt > now)
        or (ended_dt is None and period_end_dt is not None and period_end_dt > now)
    )

    if still_active:
        # Stripe says deleted but period not over — treat as canceled, keep access
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
        logger.info(
            f"User {user.id} subscription.deleted received but period not over "
            f"(ends {period_end_dt}); kept as starter_canceled"
        )
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

    # Lock excess data beyond Free limits (PRD v5.9.3)
    from .plan_limits import lock_excess_data, log_audit
    lock_result = await lock_excess_data(db, user.id, "free")

    # Audit log
    await log_audit(db, user.id, "plan_changed",
                    old_value=f"{previous_plan}/{previous_status}",
                    new_value="free",
                    triggered_by="stripe_webhook")
    await log_audit(db, user.id, "downgrade_completed",
                    new_value=f"locked_packs:{lock_result['locked_packs']}, locked_files:{lock_result['locked_files']}",
                    triggered_by="stripe_webhook")

    # Log downgrade event for tracking
    from .database import UsageLog
    downgrade_log = UsageLog(user_id=user.id, action="downgrade")
    db.add(downgrade_log)

    await db.commit()
    logger.info(
        f"User {user.id} downgraded: {previous_plan}/{previous_status} → free. "
        f"Data preserved — locked: {lock_result['locked_packs']} packs, {lock_result['locked_files']} files."
    )


async def _handle_payment_succeeded(invoice_obj, db: AsyncSession):
    """invoice.payment_succeeded — Recurring payment OK."""
    customer_id = invoice_obj.get("customer")
    user = await _find_user_by_customer(customer_id, db)
    if not user:
        return

    subscription_id = invoice_obj.get("subscription")
    if subscription_id:
        user.stripe_subscription_id = subscription_id
    user.plan = "starter"
    user.subscription_status = "starter_active"

    # Update period from subscription data in invoice
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
    logger.info(f"User {user.id} payment succeeded, starter renewed")


async def _handle_payment_failed(invoice_obj, db: AsyncSession):
    """invoice.payment_failed — Payment issue."""
    customer_id = invoice_obj.get("customer")
    user = await _find_user_by_customer(customer_id, db)
    if not user:
        return

    user.subscription_status = "starter_past_due"
    user.updated_at = datetime.utcnow()
    db.add(user)
    await db.commit()
    logger.warning(f"User {user.id} payment failed")


# ─── Helpers ───

def _map_stripe_status(stripe_status: str) -> str:
    """Map Stripe subscription status to our internal status."""
    mapping = {
        "active": "starter_active",
        "past_due": "starter_past_due",
        "canceled": "starter_canceled",
        "incomplete": "starter_incomplete",
        "incomplete_expired": "free",
        "trialing": "starter_active",
        "unpaid": "starter_past_due",
    }
    return mapping.get(stripe_status, "free")


def _ts_to_dt(ts) -> datetime | None:
    """Convert Unix timestamp to datetime."""
    if ts:
        return datetime.utcfromtimestamp(int(ts))
    return None


# ─── User Billing Info ───

def get_billing_info(user: User) -> dict:
    """Return billing info for the current user."""
    return {
        "plan": user.plan or "free",
        "subscription_status": user.subscription_status or "free",
        "current_period_end": user.current_period_end.isoformat() if user.current_period_end else None,
        "cancel_at_period_end": user.cancel_at_period_end or False,
        "has_stripe_customer": bool(user.stripe_customer_id),
    }
