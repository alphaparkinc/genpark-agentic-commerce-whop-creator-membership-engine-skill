# Whop-Style Creator Membership, License Key & Payout Engine Skill

[![GenPark Official](https://img.shields.io/badge/GenPark-Official%20Skill-blue)](https://www.genpark.ai)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-GenPark-blue)](https://www.linkedin.com/company/92955550)
[![MCP](https://img.shields.io/badge/MCP-JSON--RPC%202.0-green)](https://modelcontextprotocol.io/)
[![Zero Dependency](https://img.shields.io/badge/Dependencies-Zero%20Stdlib-brightgreen)](https://python.org)

Whop-inspired creator commerce engine: membership pricing plans with trials and renewals, HMAC software license keys with device binding, entitlement routing by membership status, affiliate-aware creator payout waterfall, and MRR/churn/LTV analytics. Built for GenPark (https://www.genpark.ai).

> Inspired by the creator-commerce model popularized by [Whop](https://whop.com). This is an independent
> implementation and is **not affiliated with or endorsed by Whop**. Fee rates are configurable inputs.

## Official Channels
- **Website**: [https://www.genpark.ai](https://www.genpark.ai)
- **LinkedIn**: [https://www.linkedin.com/company/92955550](https://www.linkedin.com/company/92955550)

## MCP Tools
- `quote_pricing_plan`: Quote a membership plan: first charge, trial end, and the next N renewal dates.
- `issue_license_key`: Issue an HMAC-signed license key bound to a membership and optional device fingerprint.
- `validate_license_key`: Validate a license key signature, expiry, and device binding.
- `resolve_entitlements`: Map a membership status to access entitlements (community role, courses, apps, downloads).
- `compute_creator_payout`: Payout waterfall: gross sales minus refunds, platform fee, processing fees, and affiliate commissions.
- `compute_membership_metrics`: Compute MRR, monthly churn rate, ARPU, and estimated LTV from a membership list.

## Usage
```bash
python -m genpark_agentic_commerce_whop_creator_membership_engine_skill.server --test      # run self-tests
python -m genpark_agentic_commerce_whop_creator_membership_engine_skill.server             # start MCP stdio server
```

MCP client config:
```json
{"mcpServers": {"whop-creator-engine": {"command": "python", "args": ["-m", "genpark_agentic_commerce_whop_creator_membership_engine_skill.server"]}}}
```
