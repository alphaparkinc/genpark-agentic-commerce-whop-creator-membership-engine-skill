# -*- coding: utf-8 -*-
"""Example: price a plan, issue a license key, and compute a payout."""
from genpark_agentic_commerce_whop_creator_membership_engine_skill.core import WhopCreatorMembershipEngine as E

print(E.quote_pricing_plan("renewal", price=29.0, trial_days=7))
key = E.issue_license_key("my-secret", "mem_123", "prod_bot", device_fingerprint="machine-1")["license_key"]
print(E.validate_license_key("my-secret", key, device_fingerprint="machine-1"))
print(E.compute_creator_payout([{"amount": 29.0}, {"amount": 29.0, "affiliate_id": "aff_9"}], affiliate_commission_pct=20))
