# ============================================================
# mcp_servers/social_server.py — 社交媒体 MCP Server
#
# 为 Market Research / Trend Forecast Agent 提供社媒数据。
# 生产环境对接：Google Trends API (pytrends)、TikTok API、
# Instagram Graph API、YouTube Data API
# ============================================================

from __future__ import annotations

import json
import time
import hashlib
from typing import Any, Dict, Optional

from .amazon_server import MCPServer


class SocialMediaMCPServer(MCPServer):
    """
    社交媒体数据 MCP Server

    设计约束：社媒数据（Google Trends / TikTok / Instagram）被多个 Agent
    共享使用（Market Agent 分析竞品热度，Trend Agent 分析趋势）。
    MCP 解耦后 Agent 只管消费数据，不关心数据来源。
    """

    def __init__(self, tiktok_api_key: Optional[str] = None):
        super().__init__(name="social-media-mcp-server", version="2.0.0")
        self.tiktok_api_key = tiktok_api_key
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = 86400  # 24h

        self.register_tool(
            name="google_trends_fetch",
            description="Fetch Google Trends data for multiple keywords. "
                        "Returns interest over time, regional breakdown, "
                        "and related queries.",
            parameters={
                "keywords": {"type": "array", "items": {"type": "string"}},
                "timeframe": {"type": "string",
                             "enum": ["today 1-m", "today 3-m", "today 12-m",
                                     "today 5-y", "2004-present"],
                             "default": "today 12-m"},
                "region": {"type": "string", "default": "US"},
            },
            handler=self._google_trends,
            agent="all",
        )

        self.register_tool(
            name="social_media_sentiment",
            description="Analyze social media buzz and sentiment for a keyword. "
                        "Aggregates TikTok, Instagram, YouTube data.",
            parameters={
                "keyword": {"type": "string"},
                "platforms": {"type": "array",
                             "items": {"type": "string",
                                      "enum": ["tiktok", "instagram", "youtube"]},
                             "default": ["tiktok", "instagram"]},
                "timeframe_days": {"type": "integer", "default": 90},
            },
            handler=self._social_sentiment,
            agent="all",
        )

        self.register_tool(
            name="seasonality_detection",
            description="Detect seasonal patterns for a product category. "
                        "Uses Google Trends 5-year data + holiday calendars.",
            parameters={
                "category": {"type": "string"},
                "market": {"type": "string", "default": "US"},
                "years_back": {"type": "integer", "default": 5},
            },
            handler=self._seasonality,
            agent="trend_forecast",
        )

    def _cache_key(self, tool: str, args: Dict) -> str:
        raw = f"{tool}:{json.dumps(args, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def _google_trends(self, args: Dict) -> Dict:
        keywords = args.get("keywords", [])
        region = args.get("region", "US")
        timeframe = args.get("timeframe", "today 12-m")

        cache_k = self._cache_key("trends", args)
        if cache_k in self._cache:
            if time.time() - self._cache[cache_k]["ts"] < self._cache_ttl:
                return self._cache[cache_k]["data"]

        # Try real pytrends API first, fallback to mock on failure
        try:
            from pytrends.request import TrendReq

            pytrends = TrendReq(hl="en-US", tz=360, retries=2, backoff_factor=0.5)
            pytrends.build_payload(keywords, timeframe=timeframe, geo=region)

            # Interest over time
            iot_df = pytrends.interest_over_time()
            if iot_df.empty:
                raise ValueError("pytrends returned empty data")

            iot_df = iot_df.drop(columns=["isPartial"], errors="ignore")
            latest = iot_df.iloc[-1]
            first = iot_df.iloc[0]
            max_vals = iot_df.max()
            min_vals = iot_df.min()

            keyword_data = {}
            for kw in keywords:
                if kw in iot_df.columns:
                    yoy = (
                        (latest[kw] - first[kw]) / first[kw] * 100
                        if first[kw] != 0 else 0
                    )
                    keyword_data[kw] = {
                        "current_value": int(latest[kw]),
                        "period_high": int(max_vals[kw]),
                        "period_low": int(min_vals[kw]),
                        "yoy_change_pct": round(yoy, 1),
                    }

            # Interest by region
            regional_df = pytrends.interest_by_region()
            regional_breakdown = []
            if not regional_df.empty and keywords:
                top_regions = regional_df[keywords[0]].sort_values(ascending=False).head(10)
                regional_breakdown = [
                    {"region": r, "interest": int(v)}
                    for r, v in top_regions.items()
                ]

            # Related queries
            related_queries_rising = []
            try:
                rq = pytrends.related_queries()
                if rq and keywords[0] in rq and rq[keywords[0]]["rising"] is not None:
                    rising_df = rq[keywords[0]]["rising"].head(5)
                    related_queries_rising = rising_df["query"].tolist()
            except Exception:
                related_queries_rising = []

            result = {
                "keywords": keywords,
                "region": region,
                "timeframe": timeframe,
                "data_quality": "REAL — fetched from Google Trends via pytrends",
                "trend_direction": "rising" if all(
                    v["yoy_change_pct"] > 0 for v in keyword_data.values()
                ) else "stable",
                "confidence": 0.85,
                "interest_over_time": keyword_data,
                "regional_breakdown": regional_breakdown,
                "related_queries_rising": related_queries_rising,
            }

        except Exception as e:
            # 在线 API 不可用时回退到离线画像数据，保证链路可运行
            result = {
                "keywords": keywords,
                "region": region,
                "timeframe": timeframe,
                "trend_direction": "rising",
                "confidence": 0.78,
                "interest_over_time": {
                    "current_value": 72,
                    "12m_high": 100,
                    "12m_low": 35,
                    "yoy_change_pct": "+18%",
                },
                "regional_breakdown": [
                    {"region": "California", "interest": 100},
                    {"region": "Texas", "interest": 85},
                    {"region": "Florida", "interest": 78},
                ],
                "related_queries_rising": [
                    f"sustainable {keywords[0] if keywords else 'product'}",
                    f"organic {keywords[0] if keywords else 'product'}",
                ],
                "data_quality": (
                    f"MOCK — pytrends unavailable ({str(e)}). "
                    "Run: pip install pytrends"
                ),
            }

        self._cache[cache_k] = {"ts": time.time(), "data": result}
        return result

    async def _social_sentiment(self, args: Dict) -> Dict:
        keyword = args.get("keyword", "")
        platforms = args.get("platforms", ["tiktok", "instagram"])

        result = {
            "keyword": keyword,
            "analysis_period_days": args.get("timeframe_days", 90),
            "platforms": {},
        }

        if "tiktok" in platforms:
            result["platforms"]["tiktok"] = {
                "total_videos": 12500,
                "total_views": 8500000,
                "avg_engagement_rate": "4.2%",
                "sentiment_score": 0.72,  # 0-1, higher = more positive
                "trend_direction": "rising",
                "top_hashtags": [f"#{keyword.replace(' ', '')}", "#amazonfinds",
                                "#tiktokmademebuyit"],
                "data_quality": "MOCK — production uses TikTok Research API",
            }

        if "instagram" in platforms:
            result["platforms"]["instagram"] = {
                "total_posts": 8900,
                "avg_likes_per_post": 1250,
                "sentiment_score": 0.68,
                "influencer_mentions_30d": 45,
                "trend_direction": "stable",
                "data_quality": "MOCK — production uses Instagram Graph API",
            }

        result["overall_buzz_score"] = 78  # 0-100
        result["overall_sentiment"] = "positive"
        result["recommendation"] = (
            "Strong social media presence with positive sentiment. "
            "Recommend leveraging TikTok influencer marketing."
        )
        return result

    async def _seasonality(self, args: Dict) -> Dict:
        category = args.get("category", "")
        years = args.get("years_back", 5)

        # 常见品类季节性模式
        seasonal_patterns = {
            "pet_supplies": {
                "has_seasonality": True,
                "peak_months": [11, 12],       # Q4 holiday
                "off_peak_months": [1, 2, 3],  # Q1 post-holiday
                "peak_amplitude_pct": "+35%",
                "trend": "growing_yoy",
            },
            "toys": {
                "has_seasonality": True,
                "peak_months": [10, 11, 12],   # Q4
                "off_peak_months": [1, 2],     # Jan-Feb
                "peak_amplitude_pct": "+120%", # Toys extremely seasonal
                "trend": "stable",
            },
            "home_kitchen": {
                "has_seasonality": True,
                "peak_months": [11, 12, 5],    # Holiday + Mother's Day
                "off_peak_months": [2, 7],
                "peak_amplitude_pct": "+25%",
                "trend": "growing_yoy",
            },
        }

        pattern = seasonal_patterns.get(
            category,
            {
                "has_seasonality": "unknown",
                "recommendation": f"Run Google Trends 5-year analysis for '{category}'",
            }
        )
        pattern["category"] = category
        pattern["years_analyzed"] = years
        pattern["data_quality"] = "MOCK — production uses pytrends 5-year data"
        return pattern
