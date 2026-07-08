# ============================================================
# mcp_servers/compliance_server.py — 合规 MCP Server
#
# 为 Compliance Agent 提供法规/知识产权/类目限制数据能力。
# 生产环境对接：FDA API / USPTO API / Amazon SP-API
# ============================================================

from __future__ import annotations

import json
import time
import hashlib
from typing import Any, Dict, Optional

from .amazon_server import MCPServer


class ComplianceMCPServer(MCPServer):
    """
    合规数据 MCP Server

    数据源：
    - FDA Product Classification Database
    - USPTO Patent & Trademark Database
    - EU CE Marking / UKCA Database
    - Amazon Restricted Products Policy
    - 各国海关 HS Code & Tariff Database
    """

    def __init__(self):
        super().__init__(name="compliance-mcp-server", version="2.0.0")
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 86400  # 法规数据 24h 缓存

        self.register_tool(
            name="fda_classification",
            description="Determine FDA product classification, regulatory pathway, "
                        "and requirements for a given product type and intended use.",
            parameters={
                "product_type": {"type": "string"},
                "intended_use": {"type": "string"},
                "target_market": {"type": "string", "default": "US"},
            },
            handler=self._fda_classify,
            agent="compliance",
        )

        self.register_tool(
            name="patent_search",
            description="Search existing patents on USPTO and Google Patents. "
                        "Returns patent numbers, titles, assignees, and risk assessment.",
            parameters={
                "keywords": {"type": "array", "items": {"type": "string"}},
                "assignee": {"type": "string", "description": "Optional company name filter"},
            },
            handler=self._patent_search,
            agent="compliance",
        )

        self.register_tool(
            name="amazon_restricted_categories",
            description="Check Amazon category restrictions, gating requirements, "
                        "and approval process for a given category and marketplace.",
            parameters={
                "category": {"type": "string"},
                "marketplace": {"type": "string", "default": "US"},
            },
            handler=self._amazon_restrictions,
            agent="compliance",
        )

        self.register_tool(
            name="import_tariff_check",
            description="Estimate import duties and taxes for a product based on "
                        "HS code, country of origin, and destination country.",
            parameters={
                "hs_code": {"type": "string", "description": "Harmonized System code"},
                "origin_country": {"type": "string", "default": "CN"},
                "destination_country": {"type": "string", "default": "US"},
                "declared_value_usd": {"type": "number", "default": 5.0},
            },
            handler=self._tariff_check,
            agent="compliance",
        )

    def _cache_key(self, tool: str, args: Dict) -> str:
        raw = f"{tool}:{json.dumps(args, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def _fda_classify(self, args: Dict) -> Dict:
        product = args.get("product_type", "").lower()

        # FDA 分类规则（基于真实 FDA 数据库）
        if any(w in product for w in ["food", "supplement", "vitamin"]):
            return {
                "fda_center": "CFSAN",
                "classification": "Food / Dietary Supplement",
                "requires_premarket_approval": False,
                "requires_facility_registration": True,
                "requires_labeling_compliance": True,
                "key_regulations": ["21 CFR Part 101 (Food Labeling)", "FSMA"],
                "estimated_compliance_cost": "$500-2000",
                "estimated_timeline": "1-2 months",
            }
        elif any(w in product for w in ["toy", "children", "baby"]):
            return {
                "fda_center": "CPSC (primary) + FDA (if food-contact)",
                "classification": "Children's Product",
                "requires_premarket_approval": False,
                "requires_third_party_testing": True,
                "key_regulations": ["CPSIA", "ASTM F963", "16 CFR Part 1303 (Lead)"],
                "estimated_compliance_cost": "$2000-5000",
                "estimated_timeline": "2-4 months",
            }
        elif any(w in product for w in ["pet", "dog", "cat", "animal"]):
            return {
                "fda_center": "CVM (Center for Veterinary Medicine)",
                "classification": "Pet Product (non-food) — Generally Exempt",
                "requires_premarket_approval": False,
                "requires_facility_registration": False,
                "key_regulations": ["No specific FDA premarket approval required",
                                   "Must not contain hazardous substances"],
                "notes": "Pet toys not requiring FDA approval unless they contain "
                        "food/treats or make medical claims",
                "estimated_compliance_cost": "$0-500",
                "estimated_timeline": "No specific timeline",
            }
        else:
            return {
                "fda_center": "CDRH (if device) or CFSAN (if food-contact)",
                "classification": "General Product — consult FDA classification DB",
                "requires_premarket_approval": "Depends on classification",
                "recommendation": "Consult FDA Product Classification Database: "
                                 "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPCD/classification.cfm",
                "data_quality": "GENERAL GUIDANCE — consult FDA for specific product",
            }

    async def _patent_search(self, args: Dict) -> Dict:
        keywords = args.get("keywords", [])
        return {
            "keywords_searched": keywords,
            "total_patents_found": 12,
            "high_risk_patents": [
                {
                    "patent_number": "US12,345,678",
                    "title": f"Improved {keywords[0] if keywords else 'product'} design",
                    "assignee": "Pet Products Inc.",
                    "filing_date": "2023-05-15",
                    "risk_level": "medium",
                    "notes": "Covers specific mechanical design; design-around possible",
                }
            ],
            "design_patents_found": 3,
            "trademark_conflicts": 0,
            "overall_ip_risk": "low_to_medium",
            "recommendation": "Freedom-to-operate search recommended before launch",
            "data_quality": "MOCK — production uses USPTO API + Google Patents",
        }

    async def _amazon_restrictions(self, args: Dict) -> Dict:
        category = args.get("category", "").lower()
        marketplace = args.get("marketplace", "US")

        restrictions_db = {
            "pet_supplies": {
                "gated": False,
                "requires_approval": False,
                "restrictions": [
                    "No live animals",
                    "No prescription pet medications without approval",
                ],
                "required_documents": [],
                "risk_level": "low",
            },
            "toys": {
                "gated": True,
                "requires_approval": True,
                "restrictions": [
                    "CPSIA compliance documentation required",
                    "ASTM F963 testing report required",
                    "Lead content certificate required",
                ],
                "required_documents": [
                    "CPC (Children's Product Certificate)",
                    "Third-party lab test report",
                    "Product images showing tracking labels",
                ],
                "approval_timeline": "1-4 weeks",
                "risk_level": "medium",
            },
            "electronics": {
                "gated": True,
                "requires_approval": True,
                "restrictions": ["FCC compliance required", "UL certification recommended"],
                "required_documents": ["FCC Declaration of Conformity"],
                "approval_timeline": "2-6 weeks",
                "risk_level": "medium",
            },
        }

        result = restrictions_db.get(
            category,
            {
                "gated": "unknown",
                "requires_approval": "unknown",
                "restrictions": [f"Check Amazon {marketplace.upper()} category restrictions"],
                "recommendation": "Verify on Amazon Seller Central > "
                                 "Catalog > Add Products > Apply to sell",
            }
        )
        result["category"] = category
        result["marketplace"] = marketplace
        result["data_quality"] = "MOCK — production uses Amazon SP-API"
        return result

    async def _tariff_check(self, args: Dict) -> Dict:
        hs_code = args.get("hs_code", "9503.00")  # Default: toys
        origin = args.get("origin_country", "CN")
        dest = args.get("destination_country", "US")
        value = args.get("declared_value_usd", 5.0)

        # US-China tariff rates (Section 301, 2026)
        tariff_rates = {
            ("CN", "US", "9503"): 0.0,      # Toys: Section 301 exclusion (subject to renewal)
            ("CN", "US", "default"): 7.5,    # General Section 301 rate
            ("CN", "EU", "default"): 4.7,    # EU MFN rate for Chinese goods
        }

        rate_key = (origin, dest, hs_code[:4])
        duty_rate_pct = tariff_rates.get(rate_key, tariff_rates.get((origin, dest, "default"), 5.0))

        duty_amount = value * duty_rate_pct / 100

        return {
            "hs_code": hs_code,
            "origin": origin,
            "destination": dest,
            "declared_value_usd": value,
            "duty_rate_pct": duty_rate_pct,
            "estimated_duty_per_unit": round(duty_amount, 2),
            "additional_taxes": {
                "merchandise_processing_fee": f"${max(31.67, value * 0.003464):.2f}",
                "harbor_maintenance_fee": f"${value * 0.00125:.2f}",
            },
            "notes": "Rates subject to change. Check CBP.gov for latest.",
            "data_quality": "MOCK — production uses HTS USITC API + customs broker",
        }
