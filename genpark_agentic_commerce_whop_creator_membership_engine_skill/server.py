# -*- coding: utf-8 -*-
"""MCP stdio server for Whop-Style Creator Membership, License Key & Payout Engine Skill."""
import json
import sys

from .core import WhopCreatorMembershipEngine as Engine

TOOLS = [
    {
        "name": "quote_pricing_plan",
        "description": "Quote a membership plan: first charge, trial end, and the next N renewal dates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_type": {
                    "type": "string",
                    "enum": [
                        "one_time",
                        "renewal",
                        "free"
                    ]
                },
                "price": {
                    "type": "number"
                },
                "billing_period_days": {
                    "type": "integer"
                },
                "trial_days": {
                    "type": "integer"
                },
                "initial_fee": {
                    "type": "number"
                },
                "start_epoch": {
                    "type": "integer"
                },
                "renewals_to_project": {
                    "type": "integer"
                }
            },
            "required": [
                "plan_type",
                "price"
            ]
        }
    },
    {
        "name": "issue_license_key",
        "description": "Issue an HMAC-signed license key bound to a membership and optional device fingerprint.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "secret": {
                    "type": "string"
                },
                "membership_id": {
                    "type": "string"
                },
                "product_id": {
                    "type": "string"
                },
                "device_fingerprint": {
                    "type": "string"
                },
                "expires_epoch": {
                    "type": "integer"
                }
            },
            "required": [
                "secret",
                "membership_id",
                "product_id"
            ]
        }
    },
    {
        "name": "validate_license_key",
        "description": "Validate a license key signature, expiry, and device binding.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "secret": {
                    "type": "string"
                },
                "license_key": {
                    "type": "string"
                },
                "device_fingerprint": {
                    "type": "string"
                },
                "now_epoch": {
                    "type": "integer"
                }
            },
            "required": [
                "secret",
                "license_key"
            ]
        }
    },
    {
        "name": "resolve_entitlements",
        "description": "Map a membership status to access entitlements (community role, courses, apps, downloads).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": [
                        "trialing",
                        "active",
                        "past_due",
                        "canceling",
                        "canceled",
                        "expired"
                    ]
                },
                "product_entitlements": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "grace_period_days": {
                    "type": "integer"
                },
                "days_past_due": {
                    "type": "integer"
                }
            },
            "required": [
                "status",
                "product_entitlements"
            ]
        }
    },
    {
        "name": "compute_creator_payout",
        "description": "Payout waterfall: gross sales minus refunds, platform fee, processing fees, and affiliate commissions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "orders": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "platform_fee_pct": {
                    "type": "number"
                },
                "processing_fee_pct": {
                    "type": "number"
                },
                "processing_fixed_fee": {
                    "type": "number"
                },
                "affiliate_commission_pct": {
                    "type": "number"
                }
            },
            "required": [
                "orders"
            ]
        }
    },
    {
        "name": "compute_membership_metrics",
        "description": "Compute MRR, monthly churn rate, ARPU, and estimated LTV from a membership list.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "memberships": {
                    "type": "array",
                    "items": {
                        "type": "object"
                    }
                },
                "period_start_active_count": {
                    "type": "integer"
                },
                "churned_in_period": {
                    "type": "integer"
                }
            },
            "required": [
                "memberships"
            ]
        }
    }
]


def handle(req):
    method, msg_id = req.get("method"), req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
            "serverInfo": {"name": "genpark-agentic-commerce-whop-creator-membership-engine-skill", "version": "1.0.0"}}}
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        if name not in {t["name"] for t in TOOLS}:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
        try:
            result = getattr(Engine, name)(**params.get("arguments", {}))
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}
        except Exception as exc:  # report tool errors per MCP convention
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"isError": True, "content": [{"type": "text", "text": str(exc)}]}}
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def call(name, **args):
    out = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": args}})
    assert "isError" not in out["result"], out
    return json.loads(out["result"]["content"][0]["text"])


def run_test():
    assert handle({"id": 0, "method": "initialize"})["result"]["serverInfo"]["name"] == "genpark-agentic-commerce-whop-creator-membership-engine-skill"
    assert len(handle({"id": 1, "method": "tools/list"})["result"]["tools"]) == len(TOOLS)
    q = call("quote_pricing_plan", plan_type="renewal", price=20, billing_period_days=30, trial_days=7, start_epoch=0)
    assert q["due_today"] == 0 and q["renewals"][0]["charge_epoch"] == 7 * 86400
    key = call("issue_license_key", secret="s3", membership_id="mem_1", product_id="prod_1", device_fingerprint="dev-A")["license_key"]
    assert call("validate_license_key", secret="s3", license_key=key, device_fingerprint="dev-A")["valid"]
    assert call("validate_license_key", secret="s3", license_key=key, device_fingerprint="dev-B")["reason"] == "DEVICE_MISMATCH"
    assert call("validate_license_key", secret="wrong", license_key=key, device_fingerprint="dev-A")["reason"] == "BAD_SIGNATURE"
    e = call("resolve_entitlements", status="past_due", product_entitlements=["discord_role"], days_past_due=5)
    assert e["granted"] == [] and "remove_community_roles" in e["follow_up_actions"]
    p = call("compute_creator_payout", orders=[{"amount": 100}, {"amount": 50, "refunded": True},
                                               {"amount": 100, "affiliate_id": "a1", "affiliate_commission_pct": 30}])
    assert p["affiliate_commissions"] == 30.0 and p["refunds"] == 50.0
    m = call("compute_membership_metrics", memberships=[{"status": "active", "price": 30}, {"status": "active", "price": 120, "billing_period_days": 90}],
             period_start_active_count=20, churned_in_period=2)
    assert m["mrr"] == 70.0 and m["monthly_churn_pct"] == 10.0 and m["estimated_ltv"] == 350.0
    print("All self-tests passed.")
    return True


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(0 if run_test() else 1)
    for line in sys.stdin:
        if line.strip():
            resp = handle(json.loads(line))
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
