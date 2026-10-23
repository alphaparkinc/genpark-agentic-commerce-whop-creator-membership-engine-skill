# -*- coding: utf-8 -*-
"""Whop-style creator membership engine for GenPark Agentic Commerce.

Independent re-implementation of common creator-commerce patterns (plans, license keys,
entitlements, payouts, metrics). Not affiliated with Whop. Fee percentages are inputs,
not claims about any platform's actual pricing.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional

DAY = 86400


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class WhopCreatorMembershipEngine:
    # ------------------------------------------------------------------ plans
    @staticmethod
    def quote_pricing_plan(plan_type: str, price: float, billing_period_days: int = 30,
                           trial_days: int = 0, initial_fee: float = 0.0,
                           start_epoch: Optional[int] = None, renewals_to_project: int = 3) -> Dict[str, Any]:
        if price < 0 or initial_fee < 0:
            raise ValueError("price and initial_fee must be non-negative")
        start = int(start_epoch if start_epoch is not None else time.time())
        if plan_type == "free":
            return {"plan_type": "free", "due_today": 0.0, "renewals": [], "access_starts_epoch": start}
        if plan_type == "one_time":
            return {"plan_type": "one_time", "due_today": round(price + initial_fee, 2),
                    "renewals": [], "access_starts_epoch": start, "lifetime_access": True}
        if plan_type != "renewal":
            raise ValueError("plan_type must be one_time, renewal, or free")
        if billing_period_days <= 0:
            raise ValueError("billing_period_days must be positive")
        trial_end = start + max(0, trial_days) * DAY
        due_today = round(initial_fee + (0.0 if trial_days > 0 else price), 2)
        first_recurring = trial_end if trial_days > 0 else start + billing_period_days * DAY
        renewals = [{"charge_epoch": first_recurring + i * billing_period_days * DAY, "amount": round(price, 2)}
                    for i in range(max(0, renewals_to_project))]
        return {"plan_type": "renewal", "due_today": due_today, "trial_ends_epoch": trial_end if trial_days > 0 else None,
                "billing_period_days": billing_period_days, "renewals": renewals,
                "monthly_equivalent": round(price * 30.0 / billing_period_days, 2)}

    # ----------------------------------------------------------- license keys
    @staticmethod
    def issue_license_key(secret: str, membership_id: str, product_id: str,
                          device_fingerprint: str = "", expires_epoch: int = 0) -> Dict[str, Any]:
        if not secret:
            raise ValueError("secret is required")
        payload = {"m": membership_id, "p": product_id, "e": int(expires_epoch),
                   "d": hashlib.sha256(device_fingerprint.encode()).hexdigest()[:16] if device_fingerprint else ""}
        body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()[:18])
        return {"license_key": f"WHP-{body}.{sig}", "membership_id": membership_id, "product_id": product_id,
                "device_bound": bool(device_fingerprint), "expires_epoch": int(expires_epoch) or None}

    @staticmethod
    def validate_license_key(secret: str, license_key: str, device_fingerprint: str = "",
                             now_epoch: Optional[int] = None) -> Dict[str, Any]:
        now = int(now_epoch if now_epoch is not None else time.time())
        try:
            if not license_key.startswith("WHP-"):
                return {"valid": False, "reason": "BAD_PREFIX"}
            body, sig = license_key[4:].split(".", 1)
            expected = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()[:18])
            if not hmac.compare_digest(sig, expected):
                return {"valid": False, "reason": "BAD_SIGNATURE"}
            payload = json.loads(_unb64(body))
        except (ValueError, json.JSONDecodeError):
            return {"valid": False, "reason": "MALFORMED"}
        if payload.get("e") and now > payload["e"]:
            return {"valid": False, "reason": "EXPIRED", "membership_id": payload.get("m")}
        if payload.get("d"):
            presented = hashlib.sha256(device_fingerprint.encode()).hexdigest()[:16] if device_fingerprint else ""
            if not hmac.compare_digest(presented, payload["d"]):
                return {"valid": False, "reason": "DEVICE_MISMATCH", "membership_id": payload.get("m")}
        return {"valid": True, "reason": "OK", "membership_id": payload.get("m"), "product_id": payload.get("p")}

    # ----------------------------------------------------------- entitlements
    @staticmethod
    def resolve_entitlements(status: str, product_entitlements: List[str],
                             grace_period_days: int = 3, days_past_due: int = 0) -> Dict[str, Any]:
        full = {"trialing", "active", "canceling"}
        if status in full:
            granted, reason = list(product_entitlements), "ACTIVE_ACCESS"
        elif status == "past_due" and days_past_due <= grace_period_days:
            granted, reason = list(product_entitlements), "GRACE_PERIOD"
        else:
            granted, reason = [], "ACCESS_REVOKED"
        revoked = [e for e in product_entitlements if e not in granted]
        actions = []
        if status == "past_due":
            actions.append("send_payment_update_reminder")
        if status == "canceling":
            actions.append("offer_retention_discount")
        if revoked:
            actions.append("remove_community_roles")
        return {"status": status, "granted": granted, "revoked": revoked, "reason": reason, "follow_up_actions": actions}

    # ---------------------------------------------------------------- payouts
    @staticmethod
    def compute_creator_payout(orders: List[Dict[str, Any]], platform_fee_pct: float = 3.0,
                               processing_fee_pct: float = 2.9, processing_fixed_fee: float = 0.30,
                               affiliate_commission_pct: float = 0.0) -> Dict[str, Any]:
        gross = refunds = processing = affiliate = 0.0
        paid = 0
        for o in orders:
            amount = float(o.get("amount", 0.0))
            if amount <= 0:
                continue
            paid += 1
            gross += amount
            processing += amount * processing_fee_pct / 100.0 + processing_fixed_fee
            if o.get("refunded"):
                refunds += amount
            elif o.get("affiliate_id"):
                rate = float(o.get("affiliate_commission_pct", affiliate_commission_pct))
                affiliate += amount * rate / 100.0
        net_sales = gross - refunds
        platform = net_sales * platform_fee_pct / 100.0
        payout = net_sales - platform - processing - affiliate
        return {"orders_counted": paid, "gross_sales": round(gross, 2), "refunds": round(refunds, 2),
                "platform_fee": round(platform, 2), "processing_fees": round(processing, 2),
                "affiliate_commissions": round(affiliate, 2), "creator_payout": round(payout, 2),
                "effective_take_rate_pct": round((1 - payout / gross) * 100.0, 2) if gross else 0.0}

    # ---------------------------------------------------------------- metrics
    @staticmethod
    def compute_membership_metrics(memberships: List[Dict[str, Any]], period_start_active_count: int = 0,
                                   churned_in_period: int = 0) -> Dict[str, Any]:
        mrr = 0.0
        active = 0
        for m in memberships:
            if m.get("status") not in ("active", "past_due", "canceling"):
                continue
            period = max(1, int(m.get("billing_period_days", 30)))
            mrr += float(m.get("price", 0.0)) * 30.0 / period
            active += 1
        arpu = mrr / active if active else 0.0
        churn = churned_in_period / period_start_active_count if period_start_active_count else 0.0
        ltv = arpu / churn if churn > 0 else None
        return {"active_paying_members": active, "mrr": round(mrr, 2), "arr": round(mrr * 12, 2),
                "arpu_monthly": round(arpu, 2), "monthly_churn_pct": round(churn * 100, 2),
                "estimated_ltv": round(ltv, 2) if ltv is not None else None}
