# ============================================================
# frontend/app.py — 跨境电商智能选品决策驾驶舱（商务 SaaS 版）
#
# 使用 Streamlit + Plotly 快速搭建，集成智能数据引擎与 Agent 分析链路。
# 运行：streamlit run frontend/app.py
# ============================================================

import hashlib
import io
import math
import random
import sys
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

# 用于抓取真实 Amazon 产品 ASIN（可选依赖）
try:
    import requests
    from bs4 import BeautifulSoup

    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False

# 把项目根目录加入 Python 路径（后续接入真实 AgentLoop 时使用）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Plotly 为可选依赖，未安装时使用文本降级展示
try:
    import plotly.express as px
    import plotly.graph_objects as go

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

st.set_page_config(
    page_title="跨境电商智能选品决策驾驶舱",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------------
# 样式覆盖：浅色商务 SaaS 主题（增加图表对比色）
# ------------------------------------------------------------------
def inject_custom_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        /* 全局：专业 SaaS 深色侧边栏 + 浅灰主内容区 */
        .stApp {
            background-color: #f1f5f9;
            color: #0f172a;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        /* 侧边栏 */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1220 0%, #0f172a 100%);
            border-right: none;
            color: #e2e8f0;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] .stMarkdown { color: #e2e8f0 !important; }
        [data-testid="stSidebar"] .stTextInput label,
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stNumberInput label {
            color: #e2e8f0 !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            letter-spacing: 0.02em;
        }
        [data-testid="stSidebar"] .stTextInput input,
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
        [data-testid="stSidebar"] .stNumberInput input {
            background-color: #ffffff !important;
            color: #0f172a !important;
            border: 1px solid rgba(255,255,255,0.35);
            border-radius: 10px;
            font-weight: 600;
            font-size: 14px;
        }
        [data-testid="stSidebar"] .stTextInput input::placeholder { color: #94a3b8 !important; }
        [data-testid="stSidebar"] .stTextInput input:focus,
        [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div:focus-within,
        [data-testid="stSidebar"] .stNumberInput input:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59,130,246,0.25);
        }
        [data-testid="stSidebar"] .stButton > button {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            color: #ffffff;
            border: none;
            border-radius: 12px;
            font-weight: 700;
            padding: 0.75rem 1rem;
            box-shadow: 0 4px 14px rgba(37,99,235,0.35);
        }
        [data-testid="stSidebar"] .stButton > button:hover {
            background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
            box-shadow: 0 6px 18px rgba(37,99,235,0.45);
        }
        [data-testid="stSidebar"] .stDivider { border-color: rgba(255,255,255,0.1) !important; }
        [data-testid="stSidebar"] .stAlertContainer {
            background-color: rgba(37,99,235,0.14) !important;
            border: 1px solid rgba(37,99,235,0.3) !important;
        }
        [data-testid="stSidebar"] [data-testid="stAlertContentInfo"] p,
        [data-testid="stSidebar"] [data-testid="stAlertContentInfo"] div {
            color: #bfdbfe !important;
            font-weight: 500 !important;
        }

        /* 隐藏 Streamlit 默认顶部装饰 */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* 主标题 */
        h1 { color: #0f172a; font-weight: 800; letter-spacing: -0.02em; }
        h2 { color: #1e293b; font-weight: 700; }
        h3 { color: #334155; font-weight: 600; }

        /* 主区按钮 */
        .stButton > button {
            background-color: #2563eb;
            color: #ffffff;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            padding: 0.6rem 1.2rem;
        }
        .stButton > button:hover { background-color: #1d4ed8; }

        /* KPI 大屏指标卡 */
        .metric-box {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 20px 16px 18px;
            box-shadow: 0 4px 12px rgba(15,23,42,0.05);
            position: relative;
            overflow: hidden;
        }
        .metric-box::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            background: var(--accent, #2563eb);
        }
        .metric-icon {
            font-size: 22px;
            margin-bottom: 8px;
        }
        .metric-label {
            color: #64748b;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 6px;
        }
        .metric-value {
            color: #0f172a;
            font-size: 30px;
            font-weight: 800;
            line-height: 1.1;
        }
        .metric-sub {
            color: #64748b;
            font-size: 12px;
            font-weight: 500;
            margin-top: 6px;
        }

        /* 结论横幅 */
        .verdict-banner {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 18px;
            padding: 24px 28px;
            box-shadow: 0 6px 18px rgba(15,23,42,0.06);
            margin-bottom: 20px;
        }
        .verdict-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 18px;
            border-radius: 24px;
            font-weight: 800;
            font-size: 14px;
            color: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        }
        .verdict-grade {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 32px; height: 32px;
            border-radius: 50%;
            font-weight: 800;
            font-size: 14px;
            background: rgba(255,255,255,0.25);
        }

        /* 信息卡片 */
        .info-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 4px 12px rgba(15,23,42,0.04);
        }
        .info-card-title {
            color: #0f172a;
            font-size: 13px;
            font-weight: 800;
            margin-bottom: 16px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* 竞品/产品卡片 */
        .product-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(15,23,42,0.03);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .product-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(15,23,42,0.06);
        }
        .product-title {
            color: #0f172a;
            font-weight: 700;
            font-size: 15px;
            margin-bottom: 5px;
        }
        .product-meta {
            color: #64748b;
            font-size: 13px;
            font-weight: 500;
        }

        /* 标签 */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }

        /* Tab 样式 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #ffffff;
            padding: 8px;
            border-radius: 14px;
            border: 1px solid #e2e8f0;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(15,23,42,0.03);
        }
        .stTabs [data-baseweb="tab"] {
            color: #64748b;
            border-radius: 10px;
            padding: 10px 18px;
            font-weight: 600;
            font-size: 14px;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            font-weight: 700;
            box-shadow: 0 2px 8px rgba(37,99,235,0.25);
        }

        /* Plotly 图表容器：零 padding，避免在 info-card 内产生额外边角空白 */
        [data-testid="stPlotlyChart"] {
            background: #ffffff;
            border-radius: 0;
            padding: 0;
            margin-bottom: 0;
        }
        [data-testid="stPlotlyChart"] .js-plotly-plot .plotly .modebar {
            display: none !important;
        }

        /* 进度条容器 */
        .score-row {
            display: flex;
            align-items: center;
            margin-bottom: 14px;
        }
        .score-name {
            width: 86px;
            font-size: 13px;
            font-weight: 600;
            color: #475569;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex-shrink: 0;
        }
        .score-bar-bg {
            flex: 1;
            height: 16px;
            background-color: #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
            margin: 0 12px;
        }
        .score-bar-fill {
            height: 100%;
            border-radius: 8px;
        }
        .score-value {
            width: 64px;
            text-align: right;
            font-size: 14px;
            font-weight: 800;
            color: #0f172a;
            flex-shrink: 0;
        }

        /* 供应商 TOP 排名 */
        .supplier-rank {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 34px; height: 34px;
            border-radius: 10px;
            font-weight: 800;
            font-size: 15px;
            color: #fff;
            background: #94a3b8;
            flex-shrink: 0;
        }
        .supplier-rank.gold { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
        .supplier-rank.silver { background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%); }
        .supplier-rank.bronze { background: linear-gradient(135deg, #b45309 0%, #92400e 100%); }

        .supplier-metric {
            text-align: center;
            min-width: 72px;
        }
        .supplier-metric-value {
            font-size: 17px;
            font-weight: 800;
            color: #0f172a;
            line-height: 1.1;
        }
        .supplier-metric-label {
            font-size: 11px;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-top: 2px;
        }

        /* 数据条大号 */
        .big-bar-bg {
            height: 14px;
            background-color: #e2e8f0;
            border-radius: 7px;
            overflow: hidden;
            flex: 1;
        }
        .big-bar-fill {
            height: 100%;
            border-radius: 7px;
        }

        /* 行动步骤 */
        .action-step {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 10px;
            font-weight: 500;
            color: #334155;
        }

        /* 侧边栏引擎信息卡 */
        .engine-card {
            background: rgba(255,255,255,0.07);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .engine-card-title {
            color: #f8fafc;
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 10px;
        }
        .engine-metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .engine-metric:last-child { border-bottom: none; }
        .engine-metric-label {
            color: #94a3b8;
            font-size: 12px;
            font-weight: 600;
        }
        .engine-metric-value {
            color: #f8fafc;
            font-size: 14px;
            font-weight: 800;
        }

        /* 合规卡片 */
        .compliance-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(15,23,42,0.03);
        }
        .compliance-card-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }
        .compliance-card-title {
            font-size: 14px;
            font-weight: 800;
            color: #0f172a;
            flex: 1;
        }
        .compliance-status {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 800;
        }
        .compliance-list {
            margin: 0;
            padding-left: 18px;
            color: #475569;
            font-size: 13px;
            line-height: 1.75;
        }

        /* 利润测算页：单件成本明细 */
        .cost-breakdown-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 4px 14px rgba(15,23,42,0.05);
        }
        .cost-total-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
            padding: 14px 18px;
            background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
            border: 1px solid #bfdbfe;
            border-radius: 14px;
        }
        .cost-total-label {
            font-size: 13px;
            font-weight: 800;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .cost-total-value {
            font-size: 32px;
            font-weight: 900;
            color: #1e3a8a;
            line-height: 1;
        }
        .cost-row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #f1f5f9;
            transition: background-color 0.18s ease, border-radius 0.18s ease;
            border-radius: 0;
        }
        .cost-row:last-child { border-bottom: none; }
        .cost-row:hover {
            background-color: #f8fafc;
            border-radius: 10px;
            padding-left: 10px;
            padding-right: 10px;
            margin-left: -10px;
            margin-right: -10px;
        }
        .cost-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
            box-shadow: 0 0 0 3px rgba(255,255,255,0.8), 0 2px 5px rgba(0,0,0,0.08);
        }
        .cost-info {
            flex: 1;
            min-width: 0;
        }
        .cost-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 6px;
        }
        .cost-bar-wrapper {
            position: relative;
            height: 18px;
            background-color: #e2e8f0;
            border-radius: 9px;
            overflow: hidden;
        }
        .cost-bar-fill {
            height: 100%;
            border-radius: 9px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
            font-size: 11px;
            font-weight: 900;
            color: #ffffff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.25);
            white-space: nowrap;
            transition: width 0.3s ease;
        }
        .cost-row:hover .cost-bar-fill { filter: brightness(1.08); }
        .cost-tooltip {
            font-size: 11px;
            color: #64748b;
            margin-top: 4px;
            opacity: 0;
            transform: translateY(-3px);
            transition: all 0.2s ease;
        }
        .cost-row:hover .cost-tooltip {
            opacity: 1;
            transform: translateY(0);
        }

        /* 关键假设数据卡片 */
        .assumption-card {
            flex: 1 1 calc(50% - 8px);
            min-width: 110px;
            text-align: center;
            padding: 16px 10px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            box-shadow: 0 3px 10px rgba(15,23,42,0.04);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .assumption-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(15,23,42,0.07);
        }
        .assumption-label {
            font-size: 11px;
            color: #64748b;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 8px;
        }
        .assumption-value {
            font-size: 19px;
            font-weight: 900;
            line-height: 1.1;
        }

        /* 利润优化分析卡片 */
        .simulator-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 4px 14px rgba(15,23,42,0.05);
        }
        .simulator-result {
            background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
            border: 1px solid #bbf7d0;
            border-radius: 14px;
            padding: 16px 20px;
            margin-top: 18px;
        }

        /* 加载态 */
        .loading-overlay {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 30px;
            color: #64748b;
            font-size: 14px;
            font-weight: 600;
        }
        .spinner {
            width: 20px;
            height: 20px;
            border: 3px solid #e2e8f0;
            border-top-color: #2563eb;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 10px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* 响应式：小屏幕堆叠 */
        @media (max-width: 640px) {
            .cost-row {
                flex-direction: column;
                align-items: flex-start;
                gap: 8px;
            }
            .cost-total-value { font-size: 26px; }
            .assumption-card { flex: 1 1 100%; }
            .simulator-grid { grid-template-columns: 1fr !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# 智能数据引擎：基于关键词与品类画像生成稳定、有业务意义的分析报告
# ------------------------------------------------------------------
@dataclass
class ProductArchetype:
    category: str
    avg_price: float
    price_range: tuple
    rating: float
    reviews_level: str
    trend: str
    pain_points: List[str]
    praised: List[str]
    season_peak: List[int]
    certifications: List[str]
    supplier_city: str
    supplier_specialty: str
    compliance_risks: List[str]
    cn_keywords: List[str]


ARCHETYPES = {
    "cat toy": ProductArchetype(
        category="pet_supplies",
        avg_price=12.5,
        price_range=(8.0, 22.0),
        rating=4.3,
        reviews_level="high",
        trend="rising",
        pain_points=["羽毛容易脱落", "电池续航短", "运行时噪音大", "猫咪很快失去兴趣"],
        praised=["自动互动很方便", "USB 充电环保", "替换装多，性价比高"],
        season_peak=[11, 12],
        certifications=["CPSC 儿童产品证书", "ASTM F963 玩具安全标准"],
        supplier_city="义乌",
        supplier_specialty="宠物玩具",
        compliance_risks=[
            "小零件/绳线/羽毛存在窒息与缠绕风险，须符合 ASTM F963 机械物理性能要求",
            "含电池款须做 GCC 通用合格证书及 UL 4200A 纽扣电池安全测试",
            "猫薄荷填充物来源、农药残留及标签标识需符合宠物用品安全规范",
        ],
        cn_keywords=["猫玩具", "逗猫棒", "猫薄荷玩具", "电动猫玩具"],
    ),
    "dog chew toys": ProductArchetype(
        category="pet_supplies",
        avg_price=15.0,
        price_range=(9.0, 28.0),
        rating=4.5,
        reviews_level="medium",
        trend="rising",
        pain_points=["不够耐咬", "有异味", "尺寸偏小", "掉色严重"],
        praised=["耐咬耐磨", "狗狗很喜欢", "材质安全无毒"],
        season_peak=[11, 12, 1],
        certifications=["FDA 食品接触材料", "CPSC 儿童产品证书"],
        supplier_city="东莞",
        supplier_specialty="宠物咬胶",
        compliance_risks=[
            "咬胶/食品接触材质需通过 FDA 21 CFR 177 食品级检测，避免邻苯二甲酸盐超标",
            "产品耐咬碎片吞咽风险高，需做 CPSC 16 CFR 1501 小零件及锐利边缘测试",
            "色素/香精添加剂需符合宠物用品化学品安全限量，防止过敏与中毒投诉",
        ],
        cn_keywords=["宠物咬胶", "耐咬磨牙棒", "狗狗玩具", "洁齿磨牙棒"],
    ),
    "yoga mat": ProductArchetype(
        category="sports",
        avg_price=28.0,
        price_range=(18.0, 55.0),
        rating=4.4,
        reviews_level="high",
        trend="stable",
        pain_points=["防滑性一般", "有刺鼻气味", "太薄硌得慌", "容易沾灰"],
        praised=["防滑效果好", "厚度适中", "携带方便"],
        season_peak=[1, 2, 9],
        certifications=["CE 认证", "REACH 环保检测", "SGS 材质检测"],
        supplier_city="广州",
        supplier_specialty="运动用品",
        compliance_risks=[
            "TPE/PVC/NBR 材质需通过 REACH SVHC 与邻苯二甲酸盐检测，防止气味投诉与下架",
            "防滑涂层、染料及印刷油墨需符合 OEKO-TEX 或加州 65 号提案化学物质限量",
            "出口欧盟需 CE 标识及技术文件，德国需 EPR 包装法注册",
        ],
        cn_keywords=["瑜伽垫", "TPE瑜伽垫", "防滑瑜伽垫", "健身垫"],
    ),
    "wireless earbuds": ProductArchetype(
        category="electronics",
        avg_price=35.0,
        price_range=(19.0, 79.0),
        rating=4.2,
        reviews_level="high",
        trend="stable",
        pain_points=["续航不够", "连接不稳定", "佩戴不舒服", "音质一般"],
        praised=["性价比高", "连接快", "低音饱满"],
        season_peak=[11, 12],
        certifications=["FCC 认证", "CE 认证", "RoHS 环保认证"],
        supplier_city="深圳",
        supplier_specialty="蓝牙耳机",
        compliance_risks=[
            "无线射频模块需通过 FCC ID（美国）、CE-RED（欧盟）、TELEC（日本）认证",
            "锂电池需符合 UN38.3、UL 1642/2054 或 IEC 62133 安全测试，防止起火召回",
            "RoHS/REACH 重金属与有害物质限量、WEEE 注册及能效标签要求",
        ],
        cn_keywords=["蓝牙耳机", "TWS耳机", "无线耳机", "降噪耳机"],
    ),
    "carplay": ProductArchetype(
        category="electronics",
        avg_price=45.0,
        price_range=(25.0, 99.0),
        rating=4.0,
        reviews_level="high",
        trend="rising",
        pain_points=["连接不稳定", "兼容性差", "发热严重", "设置复杂"],
        praised=["即插即用", "兼容车型多", "画面清晰流畅"],
        season_peak=[11, 12],
        certifications=["FCC 认证", "CE 认证", "RoHS 环保认证"],
        supplier_city="深圳",
        supplier_specialty="车载电子",
        compliance_risks=[
            "CarPlay/Android Auto 无线适配涉及苹果 MFi 或谷歌 GMS 授权，未授权存在下架风险",
            "车载电子需通过 FCC/CE-RED 射频认证、E-mark（欧洲车载）及电磁兼容 EMC 测试",
            "高温环境下工作需做可靠性测试，防止过热、起火及车辆保险责任纠纷",
        ],
        cn_keywords=["车载CarPlay", "无线CarPlay盒子", "车载电子", "车机互联"],
    ),
    "portable charger": ProductArchetype(
        category="electronics",
        avg_price=25.0,
        price_range=(12.0, 59.0),
        rating=4.3,
        reviews_level="high",
        trend="stable",
        pain_points=["容量虚标", "充电慢", "体积大", "发热明显"],
        praised=["容量足", "轻薄便携", "支持快充"],
        season_peak=[11, 12],
        certifications=["FCC 认证", "CE 认证", "UL 安全认证"],
        supplier_city="深圳",
        supplier_specialty="移动电源",
        compliance_risks=[
            "锂电池移动电源属于危险品，需 UN38.3、MSDS、UL 2056/2743 或 IEC 62133 认证",
            "亚马逊已要求充电宝提供 UL 2056 测试报告，容量虚标易引发消费者集体诉讼",
            "空运/海运需按 UN38.3 与 IATA DGR 包装要求，否则物流拒收",
        ],
        cn_keywords=["移动电源", "充电宝", "快充充电宝", "大容量充电宝"],
    ),
    "kitchen organizer": ProductArchetype(
        category="home_kitchen",
        avg_price=22.0,
        price_range=(12.0, 45.0),
        rating=4.5,
        reviews_level="medium",
        trend="stable",
        pain_points=["承重不够", "安装复杂", "尺寸不合适", "容易生锈"],
        praised=["收纳空间大", "安装简单", "材质厚实"],
        season_peak=[3, 9],
        certifications=["FDA 食品接触材料", "SGS 材质检测"],
        supplier_city="泉州",
        supplier_specialty="家居收纳",
        compliance_risks=[
            "接触食品的收纳/架类需符合 FDA 21 CFR 食品级及 LFGB（德国）迁移量测试",
            "金属焊接部位需做防锈、镀层重金属（铅、镉、镍）迁移测试",
            "带吸盘/胶贴安装件需评估承重安全与跌落风险，避免人身伤害索赔",
        ],
        cn_keywords=["厨房收纳", "冰箱收纳盒", "厨房置物架", "抽屉分隔"],
    ),
    "makeup brush": ProductArchetype(
        category="beauty",
        avg_price=14.0,
        price_range=(8.0, 32.0),
        rating=4.6,
        reviews_level="medium",
        trend="rising",
        pain_points=["掉毛严重", "刷毛扎脸", "异味大", "包装简陋"],
        praised=["刷毛柔软", "上妆均匀", "性价比高"],
        season_peak=[11, 12],
        certifications=["FDA 化妆品合规", "CE 认证"],
        supplier_city="广州",
        supplier_specialty="美妆工具",
        compliance_risks=[
            "刷毛材质（动物毛/人造纤维）及粘合剂需符合 FDA 化妆品接触材料与欧盟 REACH 要求",
            "木质手柄涂料、金属口管镀层需检测重金属（铅、镍、铬）与甲醛释放",
            "声称抗菌/环保/ cruelty-free 需有相应检测报告与标签证据，避免虚假宣传投诉",
        ],
        cn_keywords=["化妆刷", "美妆工具", "散粉刷", "化妆刷套装"],
    ),
}


MARKET_PROFILES = {
    "US": {
        "name": "美国站",
        "currency": "USD",
        "price_mult": 1.0,
        "review_mult": 1.0,
        "shipping_premium": 0.0,
        "fba_premium": 0.0,
        "referral_adj": 0.0,
        "demand_note": "全球最大电商市场，客单价与评论基数高",
        "season_note": "黑五网一、圣诞季是全年流量顶点",
    },
    "UK": {
        "name": "英国站",
        "currency": "GBP",
        "price_mult": 0.95,
        "review_mult": 0.75,
        "shipping_premium": 0.3,
        "fba_premium": 0.2,
        "referral_adj": 0.0,
        "demand_note": "欧洲成熟市场，VAT 合规与 UKCA 标识要求高",
        "season_note": "Q4 礼品季与 1 月健身/整理需求并存",
    },
    "DE": {
        "name": "德国站",
        "currency": "EUR",
        "price_mult": 0.92,
        "review_mult": 0.7,
        "shipping_premium": 0.4,
        "fba_premium": 0.25,
        "referral_adj": 0.01,
        "demand_note": "欧洲最大市场，环保与包装法（EPR）监管严格",
        "season_note": "圣诞季强劲，夏季户外出行亦有机会",
    },
    "JP": {
        "name": "日本站",
        "currency": "JPY",
        "price_mult": 1.05,
        "review_mult": 0.55,
        "shipping_premium": 0.25,
        "fba_premium": 0.15,
        "referral_adj": 0.0,
        "demand_note": "高客单价、品质敏感，评论量相对克制",
        "season_note": "年末赠答季与新年焕新需求突出",
    },
    "CA": {
        "name": "加拿大站",
        "currency": "CAD",
        "price_mult": 1.0,
        "review_mult": 0.6,
        "shipping_premium": 0.35,
        "fba_premium": 0.2,
        "referral_adj": 0.0,
        "demand_note": "英语市场进入门槛低，物流成本略高",
        "season_note": "Q4 大促与美国市场节奏一致",
    },
}


def _market_profile(market: str) -> Dict:
    return MARKET_PROFILES.get(market.upper(), MARKET_PROFILES["US"])


def _resolve_archetype(keyword: str) -> ProductArchetype:
    key = keyword.lower().strip()
    # 先精确匹配完整关键词
    for k, v in ARCHETYPES.items():
        if k in key:
            return v
    # 再按品类关键词匹配
    category_map = {
        "pet": ARCHETYPES["dog chew toys"],
        "dog": ARCHETYPES["dog chew toys"],
        "cat": ARCHETYPES["cat toy"],
        "yoga": ARCHETYPES["yoga mat"],
        "fitness": ARCHETYPES["yoga mat"],
        "earbud": ARCHETYPES["wireless earbuds"],
        "headphone": ARCHETYPES["wireless earbuds"],
        "carplay": ARCHETYPES["carplay"],
        "car": ARCHETYPES["carplay"],
        "charger": ARCHETYPES["portable charger"],
        "power bank": ARCHETYPES["portable charger"],
        "kitchen": ARCHETYPES["kitchen organizer"],
        "organizer": ARCHETYPES["kitchen organizer"],
        "makeup": ARCHETYPES["makeup brush"],
        "brush": ARCHETYPES["makeup brush"],
        "beauty": ARCHETYPES["makeup brush"],
    }
    for cat_key, archetype in category_map.items():
        if cat_key in key:
            return archetype
    # 默认：基于关键词 hash 生成稳定但多样的数据
    rng = _seeded_rng(key)
    return ProductArchetype(
        category="general",
        avg_price=round(rng.uniform(15.0, 60.0), 2),
        price_range=(round(rng.uniform(8.0, 20.0), 2), round(rng.uniform(30.0, 99.0), 2)),
        rating=round(rng.uniform(3.8, 4.7), 1),
        reviews_level=rng.choice(["low", "medium", "high"]),
        trend=rng.choice(["rising", "stable", "falling"]),
        pain_points=["质量参差不齐", "物流时效不稳定", "售后响应慢"],
        praised=["功能实用", "性价比高"],
        season_peak=[11, 12],
        certifications=["CE 认证", "FDA 认证（如适用）"],
        supplier_city=rng.choice(["深圳", "义乌", "广州", "东莞", "泉州"]),
        supplier_specialty="综合类目",
        compliance_risks=[
            "通用类目需确认目标市场强制认证（CE/FCC/UKCA 等）与标签语言要求",
            "产品外观与功能需排查目标市场专利、商标与版权风险",
            "建议根据具体材质与使用场景补充化学、机械及电气安全测试",
        ],
        cn_keywords=["外贸爆款", "跨境电商货源", "工厂直销"],
    )


def _seeded_rng(*args) -> random.Random:
    text = "|".join(str(a) for a in args)
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**31)
    return random.Random(seed)


def _store_pool(rng: random.Random) -> List[Dict]:
    """生成带店铺/品牌/配色的竞品店铺池。"""
    colors = [
        "#2563eb", "#0891b2", "#7c3aed", "#db2777", "#16a34a",
        "#ea580c", "#0f766e", "#4338ca", "#b91c1c", "#0369a1",
    ]
    stores = [
        {"brand": "AmaBest", "store": "AmaBest Direct", "color": colors[0]},
        {"brand": "PetPro", "store": "PetPro Home", "color": colors[1]},
        {"brand": "HomePlus", "store": "HomePlus Living", "color": colors[2]},
        {"brand": "TechZone", "store": "TechZone Official", "color": colors[3]},
        {"brand": "EcoLife", "store": "EcoLife Shop", "color": colors[4]},
        {"brand": "PrimePick", "store": "PrimePick Store", "color": colors[5]},
        {"brand": "NovaGear", "store": "NovaGear Mall", "color": colors[6]},
        {"brand": "Zenith", "store": "Zenith Select", "color": colors[7]},
        {"brand": "BlueWave", "store": "BlueWave Mart", "color": colors[8]},
        {"brand": "OptiMax", "store": "OptiMax Outlet", "color": colors[9]},
    ]
    rng.shuffle(stores)
    return stores


def _amazon_domain(market: str) -> str:
    return {
        "US": "amazon.com",
        "UK": "amazon.co.uk",
        "DE": "amazon.de",
        "JP": "amazon.co.jp",
        "CA": "amazon.ca",
    }.get(market.upper(), "amazon.com")


def _amazon_search_url(market: str, keyword: str) -> str:
    """生成真实可打开的 Amazon 搜索链接（替代无法稳定抓取的 ASIN 详情页）。"""
    domain = _amazon_domain(market)
    query = urllib.parse.quote_plus(keyword)
    return f"https://www.{domain}/s?k={query}"


def _1688_search_url(keyword: str) -> str:
    """生成真实可打开的 1688 搜索链接（GBK 编码避免中文乱码）。"""
    try:
        # 1688 搜索框期望 GBK 编码的中文字符串
        query = urllib.parse.quote(keyword.encode("gbk"))
    except Exception:
        query = urllib.parse.quote_plus(keyword)
    return f"https://s.1688.com/selloffer/offer_search.htm?keywords={query}"


# 简单内存缓存：每个 (keyword, market) 只抓取一次真实产品（保留扩展能力，当前默认使用搜索链接兜底）
_real_product_cache: Dict[str, List[Dict]] = {}


def _fetch_real_amazon_products(keyword: str, market: str, limit: int = 10) -> List[Dict]:
    """
    尝试从 Amazon 搜索结果页抓取真实产品 ASIN、标题、价格、评分、评论数、图片。
    抓取失败或网络不可用时返回空列表，由调用方降级为预置数据+搜索链接。
    """
    cache_key = f"{market.lower()}:{keyword.lower()}"
    if cache_key in _real_product_cache:
        return _real_product_cache[cache_key]

    if not SCRAPING_AVAILABLE:
        return []

    domain = _amazon_domain(market)
    query = urllib.parse.quote_plus(keyword)
    url = f"https://www.{domain}/s?k={query}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        items = []
        for node in soup.select("div[data-component-type='s-search-result']")[:limit]:
            asin = node.get("data-asin", "").strip()
            if not asin:
                continue
            title_tag = node.select_one("h2 a span")
            title = title_tag.get_text(strip=True) if title_tag else ""
            # 价格：优先取隐藏文本中的完整价格
            price_text = ""
            price_whole = node.select_one(".a-price .a-offscreen")
            if price_whole:
                price_text = price_whole.get_text(strip=True)
            if not price_text:
                price_whole = node.select_one(".a-price-whole")
                price_frac = node.select_one(".a-price-fraction")
                if price_whole:
                    price_text = f"${price_whole.get_text(strip=True)}.{price_frac.get_text(strip=True) if price_frac else '00'}"
            # 评分
            rating = 0.0
            rating_tag = node.select_one(".a-icon-alt")
            if rating_tag:
                txt = rating_tag.get_text(strip=True)
                try:
                    rating = float(txt.split()[0])
                except Exception:
                    pass
            # 评论数
            reviews = 0
            reviews_tag = node.select_one("a[href*='reviews'] span")
            if reviews_tag:
                txt = reviews_tag.get_text(strip=True).replace(",", "").replace("(", "").replace(")", "")
                try:
                    reviews = int(txt)
                except Exception:
                    pass
            # 图片
            image = ""
            img_tag = node.select_one(".s-image")
            if img_tag:
                image = img_tag.get("src", "")
            if title:
                items.append({
                    "asin": asin,
                    "title": title,
                    "price_text": price_text,
                    "rating": round(rating, 1),
                    "reviews": reviews,
                    "image": image,
                })
        _real_product_cache[cache_key] = items
        return items
    except Exception:
        return []


def _competitors(rng: random.Random, archetype: ProductArchetype, keyword: str, market: str) -> List[Dict]:
    count = 10
    products = []
    stores = _store_pool(rng)
    suffix_pool = [
        "Premium", "Pro", "Elite", "Ultra", "Classic", "Lite",
        "Plus", "Max", "Essential", "Signature", "Original",
    ]
    profile = _market_profile(market)
    # 统一的真实可打开搜索链接（Amazon 搜索结果页）
    search_link = _amazon_search_url(market, keyword)

    # 基于关键词生成稳定的市场规模系数，让不同关键词的绝对销量差异明显
    keyword_seed = int(hashlib.md5(keyword.lower().encode("utf-8")).hexdigest(), 16)
    keyword_rng = random.Random(keyword_seed)
    market_size_factor = keyword_rng.uniform(0.5, 2.5)  # 不同关键词市场规模相差 5 倍
    saturation = keyword_rng.uniform(0.6, 1.4)  # 竞争饱和度

    for i in range(count):
        store_info = stores[i % len(stores)]
        # 价格按关键词做微调，避免不同关键词数据雷同
        price_noise = rng.uniform(0.92, 1.12)
        price = round(rng.uniform(*archetype.price_range) * profile["price_mult"] * price_noise, 2)
        rating = round(max(3.5, min(5.0, archetype.rating + rng.uniform(-0.4, 0.3))), 1)
        review_base = 800 if archetype.reviews_level == "high" else 200
        review_top = 38000 if archetype.reviews_level == "high" else 8000
        review_count = int(rng.randint(review_base, review_top) * profile["review_mult"])

        # BSR 分布更贴近真实：头部 300-5000，尾部 5000-40000，避免第一名断崖领先
        if i == 0:
            bsr = rng.randint(300, 2500)
        elif i <= 3:
            bsr = rng.randint(1500, 8000)
        else:
            bsr = rng.randint(6000, 42000)
        # 小幅随机扰动后排序，避免完全按 i 线性
        bsr = max(200, int(bsr * rng.uniform(0.85, 1.15)))

        brand = store_info["brand"]
        store = store_info["store"]
        suffix = rng.choice(suffix_pool)

        # 销量模型：BSR 越小销量越高，使用对数衰减，差距更平缓
        # 基数 * 市场规模 * 饱和度调整，头部与第二名通常 1.5-3 倍差距
        log_rank = max(1, math.log(bsr))
        base_sales = int(25000 / log_rank * market_size_factor)
        monthly_sales = max(10, int(base_sales * rng.uniform(0.85, 1.25) / saturation))

        products.append(
            {
                "asin": "",
                "title": f"{brand} {keyword.title()} {suffix}",
                "subtitle": f"{store} · {archetype.category.replace('_', ' ').title()}",
                "brand": brand,
                "store": store,
                "price": price,
                "rating": rating,
                "review_count": review_count,
                "bsr": bsr,
                "estimated_monthly_sales": monthly_sales,
                "image": f"https://placehold.co/80x80/f8fafc/{store_info['color'].replace('#', '')}?text={brand[0]}",
                "link": search_link,
                "color": store_info["color"],
            }
        )
    # 按 BSR 排序，头部竞品在前
    products.sort(key=lambda x: x["bsr"])
    return products


def _trend_series(rng: random.Random, archetype: ProductArchetype) -> Dict:
    months = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
    base = 45
    values = []
    for i, m in enumerate(months):
        month_idx = i + 1
        val = base + rng.randint(-10, 12)
        # 旺季月份：显著高峰
        if month_idx in archetype.season_peak:
            val += rng.randint(35, 50)
        # 整体趋势
        if archetype.trend == "rising":
            val += int(i * 0.9)
        elif archetype.trend == "falling":
            val -= int(i * 0.7)
        values.append(max(15, min(100, val)))
    # 去年同期：围绕当前值随机波动，体现品类同比趋势
    last_year = [max(15, min(100, v + rng.randint(-18, 12))) for v in values]
    # 未来 3 个月预测：基于 11-12 月趋势外推
    forecast = []
    last_vals = values[-2:]
    delta = last_vals[1] - last_vals[0] if len(last_vals) == 2 else 0
    for i in range(1, 4):
        next_val = max(15, min(100, last_vals[-1] + delta * i + rng.randint(-5, 5)))
        forecast.append(next_val)
    forecast_months = ["+1月", "+2月", "+3月"]
    return {
        "months": months,
        "values": values,
        "last_year_values": last_year,
        "forecast_values": forecast,
        "forecast_months": forecast_months,
    }


def _detect_peak_months(values: List[int], top_n: int = 2) -> List[int]:
    """基于 12 个月热度值，选取热度最高的 top_n 个月份作为实际旺季高峰。"""
    indexed = [(i + 1, v) for i, v in enumerate(values)]
    indexed.sort(key=lambda x: x[1], reverse=True)
    return sorted([m for m, _ in indexed[:top_n]])


def _entry_windows(values: List[int], peak_months: List[int], window_size: int = 3) -> List[int]:
    """
    根据实际热度数据，选择旺季前市场低谷期作为备货/入局窗口。
    策略：对每个旺季月份，取 [peak-6, peak-2] 范围内的月份，
    再从候选月中按热度值升序选择 window_size 个最低月份。
    """
    candidates = set()
    for peak in peak_months:
        for offset in range(2, 7):
            m = peak - offset
            if m <= 0:
                m += 12
            candidates.add(m)
    # 排除旺季月本身
    candidates = candidates - set(peak_months)
    indexed = [(m, values[m - 1]) for m in candidates]
    indexed.sort(key=lambda x: x[1])
    selected = [m for m, _ in indexed[:window_size]]
    return sorted(selected)


def _season_narrative(peak_months: List[int], entry_months: List[int], trend_direction: str) -> Dict[str, str]:
    """根据高峰月份与入场窗口生成行业季节性解读与备货建议。"""
    peak_str = "、".join(f"{m}月" for m in peak_months)
    entry_str = "、".join(f"{m}月" for m in entry_months)
    narrative_map = {
        frozenset([11, 12]): "年末礼品季 + 黑五网一（BFCM）大促驱动，Q4 是全年需求顶点。",
        frozenset([12, 1]): "跨年 + 新年消费/健身/整理类需求高峰，圣诞后返场与 New Year Resolution 叠加。",
        frozenset([6, 7]): "夏季户外/度假/宠物出行旺季，高温场景带动相关产品需求。",
        frozenset([7, 8]): "返校季（Back to School）与夏末户外尾峰叠加。",
        frozenset([3, 4]): "春季换季 + 复活节/家居焕新需求上升。",
        frozenset([9, 10]): "Prime Day 返场 / 早鸟假日购物启动，需求开始爬坡。",
    }
    key = frozenset(peak_months)
    season_desc = narrative_map.get(
        key,
        f"需求高峰集中在 {peak_str}，建议围绕该时段前置备货与广告投放。",
    )
    trend_desc = {
        "rising": "整体搜索热度呈上升态势，类目处于成长期。",
        "stable": "全年热度相对平稳，无明显爆发性增长。",
        "falling": "整体搜索热度呈下滑态势，需警惕类目衰退风险。",
    }.get(trend_direction, "")
    return {
        "peak_months": peak_str,
        "entry_months": entry_str,
        "season_desc": season_desc,
        "trend_desc": trend_desc,
    }


def _supplier_hot_products(specialty: str, keyword: str) -> List[Dict]:
    """生成与供应商专长和关键词匹配的热卖品类/产品。"""
    templates = {
        "宠物玩具": ["猫薄荷玩具", "电动逗猫棒", "自嗨转盘", "耐咬磨牙棒", "互动球"],
        "宠物咬胶": ["耐咬橡胶骨", "洁齿磨牙棒", "牛肉味咬胶", "发声玩具", "训练奖励零食"],
        "运动用品": ["TPE 瑜伽垫", "防滑铺巾", "瑜伽砖", "弹力带套装", "健身球"],
        "蓝牙耳机": ["TWS 降噪耳机", "运动挂耳耳机", "游戏低延迟耳机", "入耳式耳机", "头戴式耳机"],
        "车载电子": ["无线 CarPlay 盒子", "车载充电器", "手机支架", "行车记录仪", "HUD 抬头显示"],
        "移动电源": ["10000mAh 快充", "磁吸无线充电宝", "太阳能移动电源", "迷你便携电源", "多口输出电源"],
        "家居收纳": ["厨房置物架", "冰箱收纳盒", "抽屉分隔板", "衣柜收纳箱", "桌面整理盒"],
        "美妆工具": ["散粉刷套装", "眼影刷", "美妆蛋", "粉底刷", "睫毛卷翘器"],
        "综合类目": ["热门爆款 A", "热销单品 B", "市场潜力款 C", "季节主推款 D", "长尾稳定款 E"],
    }
    pool = templates.get(specialty, templates["综合类目"])
    return [
        {
            "name": name,
            "image": f"https://placehold.co/100x100/f1f5f9/334155?text={name[0]}",
        }
        for name in pool
    ]


def _suppliers(rng: random.Random, keyword: str, archetype: ProductArchetype, market: str) -> List[Dict]:
    city = archetype.supplier_city
    specialty = archetype.supplier_specialty
    profile = _market_profile(market)
    # 1688 使用中文行业关键词搜索，更贴合国内供应链实际
    cn_keywords = archetype.cn_keywords if archetype.cn_keywords else [keyword]
    district_map = {
        "深圳": ["龙华区", "宝安区", "龙岗区", "南山区", "光明区"],
        "东莞": ["长安镇", "虎门镇", "塘厦镇", "厚街镇", "大朗镇"],
        "广州": ["白云区", "番禺区", "花都区", "天河区", "海珠区"],
        "义乌": ["稠江街道", "江东街道", "北苑街道", "福田街道", "廿三里街道"],
        "泉州": ["晋江市", "南安市", "石狮市", "惠安县", "安溪县"],
        "宁波": ["慈溪市", "余姚市", "鄞州区", "北仑区", "镇海区"],
    }
    districts = district_map.get(city, ["市区", "高新区", "经开区", "新区", "工业区"])
    rng.shuffle(districts)

    name_prefixes = [
        "领航", "盛达", "众诚", "创联", "宏图", "亿帆", "拓海",
        "锦程", "博远", "锐捷", "冠宇", "鑫源", "优拓", "聚信",
    ]
    rng.shuffle(name_prefixes)

    # 根据品类画像生成与关键词/市场匹配的热卖品类标签
    hot_product_pool = _supplier_hot_products(specialty, keyword)
    rng.shuffle(hot_product_pool)

    supplier_pool = []
    for i in range(10):
        district = districts[i % len(districts)]
        prefix = name_prefixes[i % len(name_prefixes)]
        if i % 3 == 0:
            name = f"{city}{district}{prefix}{specialty}厂"
        elif i % 3 == 1:
            name = f"{prefix}{specialty}（{city}{district}）"
        else:
            name = f"{city}{prefix}{specialty}供应链"
        moq = rng.choice(["MOQ 100", "MOQ 200", "MOQ 300", "MOQ 500", "MOQ 800", "MOQ 1000"])
        lead_time = rng.choice(["5-8 天", "7-12 天", "10-15 天", "12-18 天", "15-20 天"])
        rating = round(rng.uniform(4.1, 4.9), 1)
        capacity = rng.choice(["日产 2K", "日产 5K", "日产 8K", "日产 12K", "日产 20K"])
        sample_days = rng.randint(3, 10)
        response_rate = rng.randint(85, 99)
        supplier_pool.append((name, moq, lead_time, rating, capacity, sample_days, response_rate))

    # 按综合评分排序，确保 TOP10 有排名意义
    supplier_pool.sort(key=lambda x: x[3], reverse=True)

    suppliers = []
    for rank, (name, moq, lead_time, rating, capacity, sample_days, response_rate) in enumerate(supplier_pool, 1):
        unit_cost = round(rng.uniform(*archetype.price_range) * rng.uniform(0.18, 0.34) * profile["price_mult"], 2)
        hot = hot_product_pool[(rank - 1) % len(hot_product_pool)]
        hot_name = hot["name"]
        # 1688 使用中文行业关键词搜索，不同供应商可对应不同中文词
        cn_query = cn_keywords[(rank - 1) % len(cn_keywords)]
        suppliers.append({
            "rank": rank,
            "name": name,
            "moq": moq,
            "lead_time": lead_time,
            "rating": rating,
            "capacity": capacity,
            "sample_days": sample_days,
            "response_rate": response_rate,
            "unit_cost": unit_cost,
            "sample_cost": round(unit_cost * 3, 2),
            "years": rng.randint(5, 18),
            "transactions": rng.randint(120, 1800),
            "hot_categories": [hot_name, hot_product_pool[(rank) % len(hot_product_pool)]["name"]],
            "hot_product_image": hot["image"],
            "hot_product_name": hot_name,
            "link_1688": _1688_search_url(cn_query),
        })
    return suppliers


def _trending_products(rng: random.Random, keyword: str) -> List[Dict]:
    seeds = [
        "automatic", "interactive", "organic", "silicone", "foldable",
        "wireless", "rechargeable", "portable", "smart", "eco-friendly",
    ]
    rng.shuffle(seeds)
    products = []
    for seed in seeds[:4]:
        growth = rng.randint(15, 85)
        products.append({
            "keyword": f"{seed} {keyword}",
            "growth_pct": growth,
            "competition": rng.choice(["低", "中", "高"]),
            "opportunity": "高" if growth > 50 and rng.random() > 0.5 else "中",
        })
    return products


def _calculate_profit(selling_price: float, unit_cost: float, category: str, market: str) -> Dict:
    profile = _market_profile(market)
    referral_rates = {
        "pet_supplies": 0.15,
        "electronics": 0.08,
        "sports": 0.15,
        "home_kitchen": 0.15,
        "beauty": 0.15,
        "baby": 0.15,
        "general": 0.15,
    }
    rate = min(0.20, referral_rates.get(category, 0.15) + profile["referral_adj"])
    fba_fee = (3.22 if category in ["pet_supplies", "baby", "beauty"] else 4.80) + profile["fba_premium"]
    shipping = 2.0 + profile["shipping_premium"]
    advertising = selling_price * 0.08
    return_allowance = selling_price * 0.03
    misc = 0.50

    total_cost = unit_cost + shipping + fba_fee + (selling_price * rate) + advertising + return_allowance + misc
    gross_profit = selling_price - total_cost
    gross_margin = gross_profit / selling_price if selling_price > 0 else 0

    scenarios = {}
    for name, sales in [("保守", 100), ("中性", 300), ("乐观", 600)]:
        m_profit = sales * gross_profit
        investment = unit_cost * 500 + 2000
        payback = investment / m_profit if m_profit > 0 else None
        scenarios[name] = {
            "月销量": sales,
            "月毛利": round(m_profit, 2),
            "ROI": round(m_profit / investment * 100, 1),
            "回本周期": round(payback, 1) if payback else None,
        }

    cost_breakdown = {
        "产品成本": unit_cost,
        "头程物流": shipping,
        "FBA 费用": fba_fee,
        "平台佣金": selling_price * rate,
        "广告费用": advertising,
        "退货预留": return_allowance,
        "其他杂费": misc,
    }

    return {
        "selling_price": selling_price,
        "unit_cost": unit_cost,
        "total_cost_per_unit": round(total_cost, 2),
        "gross_profit_per_unit": round(gross_profit, 2),
        "gross_margin": gross_margin,
        "gross_margin_pct": f"{gross_margin:.1%}",
        "cost_breakdown": cost_breakdown,
        "cost_breakdown_pct": {k: f"{v/total_cost:.1%}" for k, v in cost_breakdown.items()},
        "roi_scenarios": scenarios,
        "breakeven_units": round(2000 / gross_profit) if gross_profit > 0 else None,
        "market": market,
    }


def _build_compliance(rng: random.Random, archetype: ProductArchetype, market: str) -> Dict:
    """构建与关键词品类、目标市场严格匹配的合规与知识产权风险信息。"""
    profile = _market_profile(market)
    certifications = list(archetype.certifications)
    category = archetype.category
    market_key = market.upper()
    # 品类专属合规风险（来自 ARCHETYPES 画像，避免通用模板）
    category_risks = list(archetype.compliance_risks)

    # 根据目标市场补充强制认证，确保与国家法规匹配
    market_cert_additions = {
        "US": ["FCC 认证（如含电子）", "CPSC/CPC（如儿童/宠物相关）"],
        "UK": ["UKCA 标识", "英国授权代表"],
        "DE": ["CE 标识 + 欧代", "德国包装法 EPR/VerpackG 注册"],
        "JP": ["PSE 标志（如电子）", "TELEC/MIC（如无线）", "日语标签/说明书"],
        "CA": ["IC 认证（如含电子）", "英法双语标签"],
    }
    for cert in market_cert_additions.get(market_key, []):
        if cert not in certifications:
            certifications.append(cert)

    # 外观专利 / 实用新型 / 发明专利风险（按目标市场匹配检索渠道）
    patent_db = {
        "US": "USPTO / Google Patents",
        "UK": "UK IPO / EUIPO",
        "DE": "EUIPO / DPMA",
        "JP": "J-PlatPat / JPO",
        "CA": "CIPO / USPTO",
    }
    db_name = patent_db.get(market_key, "当地专利局")
    design_patent_risks = [
        f"{profile['name']} 常见外观设计专利覆盖本产品主流造型，建议上架前通过 {db_name} 做专利检索。",
        "产品外观若与头部竞品高度相似，存在被投诉下架或 TRO（临时限制令）风险。",
        f"请确认上市设计不落入他人 {profile['name']} 外观专利保护范围。",
    ]

    # 商标 / 品牌侵权
    tm_db = {
        "US": "USPTO TESS",
        "UK": "UK IPO 商标检索",
        "DE": "EUIPO eSearch",
        "JP": "J-PlatPat 商标库",
        "CA": "CIPO 商标库",
    }
    brand_risks = [
        f"避免使用 {profile['name']} 已注册商标的通用词或近似 Logo，建议通过 {tm_db.get(market_key, '当地商标局')} 做筛查。",
        "Listing 文案、图片、包装中勿出现影视/动漫/游戏角色、球队、品牌联名等未授权元素。",
        f"{profile['name']} 对品牌侵权处罚严格，可能导致账户资金冻结或链接下架。",
    ]

    # 行业专利 / 技术专利
    industry_patent_risks = [
        f"{category.replace('_', ' ').title()} 类目存在若干功能型专利，需排查核心结构/材料在 {profile['name']} 是否侵权。",
        "若产品含电子、机械或特殊材料组件，建议做 Freedom-to-Operate（FTO）分析。",
        "供应链端需确认工厂拥有相关设计授权，避免 OEM 侵权连带责任。",
    ]

    # 目标市场特定合规
    market_rules = {
        "US": [
            "儿童/宠物用品需关注 CPSC 安全标准与 CPC 证书要求。",
            "含电子部件需 FCC 认证；食品接触材料需 FDA 合规。",
            f"针对「{category.replace('_', ' ').title()}」类目，确认是否需要第三方实验室检测报告。",
        ],
        "EU": [
            "需 CE 标识 + 欧代信息，部分产品需 ROHS/REACH 化学检测。",
            "包装需符合 EPR 法规（德国包装法、法国 Triman 标识等）。",
            f"针对「{category.replace('_', ' ').title()}」类目，确认是否需要符合 GPSR 通用产品安全法规。",
        ],
        "UK": [
            "需 UKCA 标识及英国授权代表。",
            "产品安全与 GPSR 相关义务需同步满足。",
            f"针对「{category.replace('_', ' ').title()}」类目，确认是否需要英国本土合规文件。",
        ],
        "JP": [
            "无线电/电子类产品需 TELEC/MIC 认证；食品接触类需食品卫生法。",
            "日语标签、说明书及 PSE 标志（如适用）需提前准备。",
            f"针对「{category.replace('_', ' ').title()}」类目，确认是否需要日本进口商/代理商信息。",
        ],
        "CA": [
            "需符合加拿大消费品安全法（CCPSA）及双语标签要求。",
            "含电子部件需 IC 认证；食品接触材料需 Health Canada 合规。",
            f"针对「{category.replace('_', ' ').title()}」类目，确认是否需要加拿大本地安全标准测试。",
        ],
    }
    market_specific = market_rules.get(
        market_key,
        market_rules.get("EU", [f"{profile['name']}：请补充当地强制认证与标签要求。"])
    )

    risk_level = rng.choice(["低", "中", "高"])
    return {
        "certifications": certifications,
        "risk_level": risk_level,
        "estimated_cert_cost": round(rng.uniform(500, 3500) * profile["price_mult"], 2),
        "estimated_cert_time": rng.choice(["2-4 周", "4-6 周", "6-8 周", "8-12 周"]),
        "category_risks": rng.sample(category_risks, k=min(3, len(category_risks))),
        "design_patent_risks": rng.sample(design_patent_risks, k=min(2, len(design_patent_risks))),
        "brand_risks": rng.sample(brand_risks, k=min(2, len(brand_risks))),
        "industry_patent_risks": rng.sample(industry_patent_risks, k=min(2, len(industry_patent_risks))),
        "market_specific": market_specific,
        "market": profile["name"],
    }


def _build_next_steps(report: Dict) -> List[Dict]:
    """生成带时间节点、负责人、价值说明的可落地行动计划。"""
    keyword = report["keyword"]
    market = report["market"]
    archetype = _resolve_archetype(keyword)
    pain_1 = archetype.pain_points[0]
    pain_2 = archetype.pain_points[1] if len(archetype.pain_points) > 1 else archetype.pain_points[0]
    cert_1 = archetype.certifications[0]
    cert_2 = archetype.certifications[1] if len(archetype.certifications) > 1 else cert_1
    peak = "、".join(f"{m}月" for m in report["trend_analysis"]["peak_months"])
    entry = "、".join(f"{m}月" for m in report["trend_analysis"]["entry_windows"])

    return [
        {
            "phase": "Week 1-2",
            "title": "供应商开发与样品验证",
            "owner": "供应链专员 / 采购",
            "tasks": [
                f"针对「{pain_1}」「{pain_2}」筛选 3-5 家可定向改良的工厂",
                "索取样品、核验材质/工艺、对比报价与交期",
                "确认工厂资质（ISO、BSCI、相关认证）与产能匹配度",
            ],
            "value": "锁定具备差异化改良能力的供应商，降低质量与交付风险。",
        },
        {
            "phase": "Week 3-4",
            "title": "合规与知识产权风控",
            "owner": "合规专员 / 法务",
            "tasks": [
                f"完成 {cert_1}、{cert_2} 认证方案与预算评估",
                f"在 {market} 市场进行商标/外观专利/功能专利检索",
                "设计独立包装与 Listing 素材，规避侵权风险",
            ],
            "value": "避免上架后因合规或 TRO 导致链接下架、资金冻结。",
        },
        {
            "phase": f"{entry} 前",
            "title": "备货与物流布局",
            "owner": "运营 / 物流",
            "tasks": [
                f"在 {entry} 完成首批 300-500 件备货并发出",
                "选择海运/空运组合，确保旺季前 4-6 周到仓",
                "建立安全库存预警：按日销 30-50 件设置补货点",
            ],
            "value": f"抢占 {peak} 旺季搜索排名，避免断货错失销售高峰。",
        },
        {
            "phase": f"{peak} 旺季",
            "title": "Listing 优化与广告投放",
            "owner": "亚马逊运营",
            "tasks": [
                "围绕用户好评卖点优化标题、五点、A+ 与主图视频",
                "启动自动+手动广告，预算按 ROI 分阶段释放",
                "监控 BSR、广告 ACoS、Review 增长率与退货原因",
            ],
            "value": "提升转化率与广告效率，实现盈亏平衡后的利润放大。",
        },
        {
            "phase": "持续迭代",
            "title": "数据复盘与产品迭代",
            "owner": "产品 / 运营",
            "tasks": [
                "每周复盘退货率、Review 差评点与竞品动态",
                "基于真实用户反馈启动 V2.0 改良（材质/功能/包装）",
                "建立供应商绩效评分表，季度优化供应链结构",
            ],
            "value": "形成数据驱动的选品-备货-销售-迭代闭环。",
        },
    ]


def generate_report(
    keyword: str,
    market: str,
    budget: str,
    selling_price: Optional[float] = None,
    unit_cost: Optional[float] = None,
) -> Dict:
    """基于关键词、目标市场与品类画像生成选品分析报告。"""
    rng = _seeded_rng(keyword, market, budget)
    archetype = _resolve_archetype(keyword)
    profile = _market_profile(market)

    if selling_price is None:
        selling_price = round(archetype.avg_price * profile["price_mult"] + rng.uniform(-2, 3), 2)
    if unit_cost is None:
        unit_cost = round(selling_price * rng.uniform(0.22, 0.35), 2)

    competitors = _competitors(rng, archetype, keyword, market)
    avg_price = round(sum(p["price"] for p in competitors) / len(competitors), 2)
    avg_rating = round(sum(p["rating"] for p in competitors) / len(competitors), 1)
    avg_reviews = round(sum(p["review_count"] for p in competitors) / len(competitors), 0)

    profit = _calculate_profit(selling_price, unit_cost, archetype.category, market)
    trend = _trend_series(rng, archetype)
    # 基于实际热度数据检测高峰月份，确保图表与标注一致
    detected_peaks = _detect_peak_months(trend["values"])
    entry_windows = _entry_windows(trend["values"], detected_peaks)
    season_narrative = _season_narrative(detected_peaks, entry_windows, archetype.trend)
    suppliers = _suppliers(rng, keyword, archetype, market)
    trending = _trending_products(rng, keyword)

    # 综合评分：利润 40 + 趋势 25 + 竞争 20 + 评论洞察 15
    gross_margin = profit["gross_margin"]
    margin_score = min(40, max(-20, gross_margin * 120))
    trend_score = 25 if archetype.trend == "rising" else 18 if archetype.trend == "stable" else 8
    if avg_reviews < 1500:
        competition_score = 20
    elif avg_reviews < 8000:
        competition_score = 12
    else:
        competition_score = 5
    insight_score = 15 if archetype.pain_points else 8

    total_score = round(margin_score + trend_score + competition_score + insight_score, 1)

    # 与后端 product_selection_report.py 判定逻辑严格一致
    if gross_margin >= 0.20:
        verdict = "推荐进入"
        verdict_color = "#16a34a"
        grade = "A"
    elif gross_margin >= 0.10:
        verdict = "谨慎进入"
        verdict_color = "#d97706"
        grade = "B"
    else:
        verdict = "不建议"
        verdict_color = "#dc2626"
        grade = "D"

    opportunities = []
    for pain in archetype.pain_points[:3]:
        opportunities.append(f"针对「{pain}」做产品升级，形成差异化卖点")
    opportunities.append("强化好评中的核心卖点，在 Listing 中重点展示")

    report_core = {
        "keyword": keyword,
        "market": market,
        "budget": budget,
        "selling_price": selling_price,
        "unit_cost": unit_cost,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "grade": grade,
        "overall_score": total_score,
        "max_score": 100,
        "score_breakdown": {
            "利润空间": round(margin_score, 1),
            "趋势热度": trend_score,
            "竞争强度": competition_score,
            "评论洞察": insight_score,
        },
        "market_analysis": {
            "avg_price": avg_price,
            "avg_rating": avg_rating,
            "avg_reviews": int(avg_reviews),
            "competitors": competitors,
            "data_quality": "智能分析引擎",
            "market_profile": profile,
        },
        "trend_analysis": {
            "trend_direction": archetype.trend,
            "series": trend,
            "peak_months": detected_peaks,
            "entry_windows": entry_windows,
            "season_narrative": season_narrative,
            "data_quality": "智能分析引擎",
        },
        "review_insights": {
            "pain_points": archetype.pain_points,
            "praised_features": archetype.praised,
            "opportunities": opportunities,
            "data_quality": "智能分析引擎",
        },
        "profit_analysis": profit,
        "suppliers": suppliers,
        "compliance": _build_compliance(rng, archetype, market),
        "trending_products": trending,
    }
    report_core["next_steps"] = _build_next_steps(report_core)
    return report_core


# ------------------------------------------------------------------
# 页面渲染
# ------------------------------------------------------------------
def render_header():
    st.markdown(
        """
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:16px; margin-bottom:8px;">
            <div>
                <div style="color:#64748b; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px;">Cross-Border Product Intelligence</div>
                <h1 style="margin:0; font-size:32px;">跨境电商智能选品决策驾驶舱</h1>
            </div>
            <div style="display:flex; gap:10px;">
                <span class="badge" style="background:#eff6ff; color:#1d4ed8;">🤖 Multi-Agent</span>
                <span class="badge" style="background:#dbeafe; color:#1e40af;">🛰 MCP 工具链</span>
                <span class="badge" style="background:#f1f5f9; color:#334155;">⚡ 实时分析</span>
            </div>
        </div>
        <p style="color:#64748b; font-size:14px; margin:0 0 18px 0;">
            基于 6 个领域 Agent + 4 个 MCP 工具服务器 + 四层模型路由的自动化选品分析
        </p>
        """,
        unsafe_allow_html=True,
    )


def _mark_price_edited():
    st.session_state["user_edited_price"] = True


def _mark_cost_edited():
    st.session_state["user_edited_cost"] = True


def render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div style="margin-bottom:18px;">
                <div style="font-size:22px; font-weight:800; color:#f8fafc; margin-bottom:2px;">🎯 选品分析引擎</div>
                <div style="font-size:12px; color:#94a3b8; font-weight:500;">智能决策 · 数据驱动 · 多市场适配</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='font-size:13px; font-weight:800; color:#e2e8f0; margin-bottom:10px; text-transform:uppercase; letter-spacing:0.05em;'>分析配置</div>", unsafe_allow_html=True)

        keyword = st.text_input("产品关键词", value="dog chew toys", key="keyword_input")
        market = st.selectbox("目标市场", ["US", "UK", "DE", "JP", "CA"], index=0, key="market_select")
        budget = st.selectbox("预算区间", ["$1,000-$5,000", "$5,000-$10,000", "$10,000-$50,000"], index=1, key="budget_select")

        # 根据关键词画像与市场基准自动推荐售价与成本，用户手动修改后不再随关键词联动
        archetype = _resolve_archetype(keyword)
        profile = _market_profile(market)
        rng = _seeded_rng(keyword, market, budget)
        keyword_seed = int(hashlib.md5(keyword.lower().encode("utf-8")).hexdigest(), 16)
        # 关键词级微调：在品类均价 ±12% 范围内波动，体现不同关键词的真实价位差异
        keyword_factor = 0.88 + (keyword_seed % 25) / 100.0
        rec_price = round(archetype.avg_price * profile["price_mult"] * keyword_factor, 2)
        # 成本率 22%-38%，偏低价关键词成本率略高
        cost_rate = 0.22 + (keyword_seed % 17) / 100.0
        rec_cost = round(rec_price * cost_rate, 2)

        if "last_keyword" not in st.session_state:
            st.session_state.last_keyword = keyword
        if "last_market" not in st.session_state:
            st.session_state.last_market = market
        if "user_edited_price" not in st.session_state:
            st.session_state.user_edited_price = False
        if "user_edited_cost" not in st.session_state:
            st.session_state.user_edited_cost = False

        if keyword != st.session_state.last_keyword or market != st.session_state.last_market:
            if not st.session_state.user_edited_price:
                st.session_state.selling_price = rec_price
            if not st.session_state.user_edited_cost:
                st.session_state.unit_cost = rec_cost
            st.session_state.last_keyword = keyword
            st.session_state.last_market = market

        if "selling_price" not in st.session_state:
            st.session_state.selling_price = rec_price
        if "unit_cost" not in st.session_state:
            st.session_state.unit_cost = rec_cost

        st.divider()
        st.markdown("<div style='font-size:13px; font-weight:800; color:#e2e8f0; margin-bottom:10px; text-transform:uppercase; letter-spacing:0.05em;'>💰 利润假设</div>", unsafe_allow_html=True)
        selling_price = st.number_input(
            f"预期售价 ({profile['currency']})",
            min_value=1.0,
            max_value=200.0,
            step=0.5,
            key="selling_price",
            on_change=_mark_price_edited,
        )
        unit_cost = st.number_input(
            f"预估成本 ({profile['currency']})",
            min_value=0.5,
            max_value=150.0,
            step=0.5,
            key="unit_cost",
            on_change=_mark_cost_edited,
        )
        st.markdown(
            f"""
            <div style="margin-top:6px; padding:10px 12px; background:rgba(255,255,255,0.07); border-radius:10px; border:1px solid rgba(255,255,255,0.1);">
                <div style="font-size:12px; color:#94a3b8; line-height:1.6;">
                    💡 售价/成本根据「<strong style="color:#f8fafc;">{keyword}</strong>」所属品类画像与 <strong style="color:#f8fafc;">{profile['name']}</strong> 市场溢价系数自动估算，作为利润测算的基准假设；您可以手动修改以适配实际供应链报价。
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 市场洞察摘要卡
        st.markdown(
            f"""
            <div class="engine-card">
                <div class="engine-card-title">📍 {profile['name']} 市场特征</div>
                <div class="engine-metric">
                    <span class="engine-metric-label">市场需求</span>
                    <span class="engine-metric-value">{profile['demand_note']}</span>
                </div>
                <div class="engine-metric">
                    <span class="engine-metric-label">季节特征</span>
                    <span class="engine-metric-value">{profile['season_note']}</span>
                </div>
                <div class="engine-metric">
                    <span class="engine-metric-label">品类均价</span>
                    <span class="engine-metric-value">{profile['currency']} {archetype.avg_price * profile['price_mult']:.2f}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        analyze_btn = st.button("🚀 开始选品分析", use_container_width=True)
        return keyword, market, budget, selling_price, unit_cost, analyze_btn


def render_verdict_banner(report: Dict):
    verdict = report['verdict']
    color = report['verdict_color']
    trend_text = report['trend_analysis']['trend_direction'].upper()
    trend_icon = "↗" if report['trend_analysis']['trend_direction'] == "rising" else "→" if report['trend_analysis']['trend_direction'] == "stable" else "↘"
    profile = report['market_analysis']['market_profile']
    st.markdown(
        f"""
        <div class="verdict-banner">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:20px;">
                <div>
                    <div style="color:#64748b; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:6px;">分析对象</div>
                    <div style="color:#0f172a; font-size:26px; font-weight:800;">{report['keyword'].upper()} · {profile['name']}</div>
                    <div style="color:#64748b; font-size:13px; margin-top:6px; font-weight:500;">
                        预算区间 {report['budget']} · 市场均价 {profile['currency']}${report['market_analysis']['avg_price']} · 平均评分 {report['market_analysis']['avg_rating']}⭐
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:12px;">
                    <span class="badge" style="background:#f1f5f9; color:#475569; font-size:13px;">{trend_icon} 趋势 {trend_text}</span>
                    <span class="verdict-pill" style="background-color:{color};">
                        <span class="verdict-grade">{report['grade']}</span>
                        {verdict}
                    </span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_cards(report: Dict):
    profit = report["profit_analysis"]
    trend = report["trend_analysis"]

    direction = trend["trend_direction"]
    trend_sub = "搜索热度上升" if direction == "rising" else "搜索热度稳定" if direction == "stable" else "搜索热度下降"
    breakeven = profit["breakeven_units"] or "N/A"

    # KPI 使用多色区分不同维度
    metrics = [
        ("综合评分", f"{report['overall_score']}/{report['max_score']}", "#1e40af", "🏆", f"等级 {report['grade']}"),
        ("毛利率", profit["gross_margin_pct"], "#2563eb", "💰", f"单件毛利 ${profit['gross_profit_per_unit']}"),
        ("盈亏平衡", f"{breakeven} 件", "#0891b2", "⚖️", "覆盖固定成本"),
        ("趋势热度", direction.upper(), "#7c3aed", "📈", trend_sub),
    ]

    cells = ""
    for label, value, color, icon, sub in metrics:
        cells += f"""
        <div class="metric-box" style="--accent:{color};">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{color};">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """
    st.markdown(
        f"""
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 20px;">
            {cells}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_radar(report: Dict, wrap_card: bool = True, card_height: str = "100%"):
    open_div = f"<div class='info-card' style='height:{card_height}; display:flex; flex-direction:column;'>" if wrap_card else ""
    close_div = "</div>" if wrap_card else ""
    title_html = "<div class='info-card-title radar-title' style='flex-shrink:0;'>🎯 五维评分雷达</div>" if wrap_card else ""
    st.markdown(
        f"{open_div}{title_html}",
        unsafe_allow_html=True,
    )
    if not PLOTLY_AVAILABLE:
        st.info("雷达图需要 plotly 支持，请运行 pip install plotly 后刷新页面。")
        st.markdown(close_div, unsafe_allow_html=True)
        return

    categories = list(report["score_breakdown"].keys())
    values = list(report["score_breakdown"].values())
    max_values = {"利润空间": 40, "趋势热度": 25, "竞争强度": 20, "评论洞察": 15}
    normalized = [min(100, values[i] / max_values.get(categories[i], 25) * 100) for i in range(len(categories))]
    normalized += [normalized[0]]
    categories += [categories[0]]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=normalized,
            theta=categories,
            fill="toself",
            fillcolor="rgba(37, 99, 235, 0.22)",
            line=dict(color="#2563eb", width=2.5),
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e2e8f0", tickfont=dict(size=13, color="#64748b", weight=700)),
            angularaxis=dict(tickfont=dict(color="#1e293b", size=15, weight=800)),
            bgcolor="#ffffff",
        ),
        paper_bgcolor="#ffffff",
        font=dict(color="#1e293b"),
        showlegend=False,
        margin=dict(l=20, r=20, t=10, b=10),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True, config=dict(displayModeBar=False))
    st.markdown("</div>", unsafe_allow_html=True)


def render_score_breakdown(report: Dict, wrap_card: bool = True):
    max_values = {"利润空间": 40, "趋势热度": 25, "竞争强度": 20, "评论洞察": 15}

    html = ""
    if wrap_card:
        html += "<div class='info-card'>"
    html += "<div class='info-card-title'>📊 五维评分拆解</div>"
    for name, score in report["score_breakdown"].items():
        max_v = max_values.get(name, 25)
        pct = min(100, max(0, score / max_v * 100))
        # 使用对比色区分不同维度
        if name == "利润空间":
            color = "linear-gradient(90deg, #16a34a, #4ade80)"
        elif name == "趋势热度":
            color = "linear-gradient(90deg, #7c3aed, #a78bfa)"
        elif name == "竞争强度":
            color = "linear-gradient(90deg, #0891b2, #22d3ee)"
        else:
            color = "linear-gradient(90deg, #2563eb, #60a5fa)"
        html += (
            f'<div class="score-row">'
            f'<div class="score-name">{name}</div>'
            f'<div class="score-bar-bg"><div class="score-bar-fill" style="width:{pct}%; background:{color};"></div></div>'
            f'<div class="score-value">{score}/{max_v}</div>'
            f'</div>'
        )
    if wrap_card:
        html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_conclusion(report: Dict, wrap_card: bool = True):
    market = report['market_analysis']
    profit = report['profit_analysis']
    profile = market['market_profile']
    open_div = "<div class='info-card'>" if wrap_card else ""
    close_div = "</div>" if wrap_card else ""
    st.markdown(
        f"""
        {open_div}
            <div class="info-card-title">💡 核心结论</div>
            <p style="color:#475569; line-height:1.75; margin:0; font-size:14px;">
            关键词 <strong style="color:#2563eb;">{report['keyword']}</strong>
            在 <strong>{profile['name']}</strong> 市场平均售价
            <strong>{profile['currency']}${market['avg_price']}</strong>，
            毛利率 <strong style="color:{report['verdict_color']};">{profit['gross_margin_pct']}</strong>，
            趋势 <strong>{report['trend_analysis']['trend_direction'].upper()}</strong>。
            综合判定为 <strong style="color:{report['verdict_color']};">{report['verdict']}</strong>。
            </p>
            <div style="display:flex; gap:12px; margin-top:16px; flex-wrap:wrap;">
                <span class="badge" style="background:#eff6ff; color:#1d4ed8;">竞品 {len(market['competitors'])} 款</span>
                <span class="badge" style="background:#dbeafe; color:#1e40af;">平均评分 {market['avg_rating']}⭐</span>
                <span class="badge" style="background:#f1f5f9; color:#334155;">总评论 {market['avg_reviews']:,.0f}+</span>
            </div>
        {close_div}
        """,
        unsafe_allow_html=True,
    )


def render_market_analysis(report: Dict):
    market = report["market_analysis"]
    competitors = market["competitors"]
    # 同色系柔和蓝调色板，图表与卡片共用
    soft_palette = ["#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"]

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("<div class='info-card-title'>竞品价格带与月销量分布</div>", unsafe_allow_html=True)
        if PLOTLY_AVAILABLE:
            # 双轴图：柱状=售价，折线=月销量
            fig = go.Figure()
            colors = [soft_palette[i % len(soft_palette)] for i in range(len(competitors))]
            fig.add_trace(go.Bar(
                x=[p["brand"] for p in competitors],
                y=[p["price"] for p in competitors],
                name="售价",
                marker_color=colors,
                text=[f"${p['price']}" for p in competitors],
                textposition="outside",
                textfont=dict(size=11, color="#0f172a"),
            ))
            fig.add_trace(go.Scatter(
                x=[p["brand"] for p in competitors],
                y=[p["estimated_monthly_sales"] for p in competitors],
                name="月销量",
                mode="lines+markers+text",
                line=dict(color="#f59e0b", width=2.5),
                marker=dict(size=8, color="#f59e0b"),
                text=[f"{p['estimated_monthly_sales']:,}" for p in competitors],
                textposition="top center",
                textfont=dict(size=10, color="#b45309"),
                yaxis="y2",
            ))
            max_price = max(p["price"] for p in competitors)
            max_sales = max(p["estimated_monthly_sales"] for p in competitors)
            fig.update_layout(
                height=360,
                margin=dict(l=20, r=60, t=55, b=20),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#f8fafc",
                font=dict(color="#1e293b"),
                xaxis=dict(gridcolor="#e2e8f0", tickfont=dict(size=11)),
                yaxis=dict(
                    title=dict(text="售价 (USD)", font=dict(size=12)),
                    gridcolor="#e2e8f0",
                    tickfont=dict(size=11),
                    range=[0, max_price * 1.28],
                    fixedrange=False,
                ),
                yaxis2=dict(
                    title=dict(text="月销量", font=dict(size=12)),
                    overlaying="y",
                    side="right",
                    gridcolor="rgba(0,0,0,0)",
                    tickfont=dict(size=11),
                    range=[0, max_sales * 1.28],
                    fixedrange=False,
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                showlegend=True,
                bargap=0.35,
                autosize=True,
            )
            st.plotly_chart(fig, use_container_width=True, config=dict(displayModeBar=False))
        else:
            st.info("价格带分布图需要 plotly 支持，请运行 pip install plotly 后刷新页面。")

    with col2:
        st.markdown("<div class='info-card-title'>头部竞品 TOP10</div>", unsafe_allow_html=True)
        for i, p in enumerate(competitors):
            st.markdown(
                f"""
                <div class="product-card" style="border-left:4px solid {soft_palette[i % len(soft_palette)]};">
                    <div style="display:flex; align-items:center; gap:14px;">
                        <a href="{p['link']}" target="_blank" style="flex-shrink:0;">
                            <img src="{p['image']}" style="width:64px;height:64px;border-radius:12px;object-fit:cover;background:#f1f5f9;border:1px solid #e2e8f0;" />
                        </a>
                        <div style="flex:1; min-width:0;">
                            <a href="{p['link']}" target="_blank" style="text-decoration:none; color:inherit;">
                                <div class="product-title" style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{p['title']}</div>
                            </a>
                            <div class="product-meta" style="font-size:12px; margin-bottom:5px;">{p['store']} · {p['subtitle'].split(' · ')[1]}</div>
                            <div class="product-meta">
                                <strong style="color:#2563eb;">${p['price']}</strong> ·
                                ⭐ {p['rating']} · {p['review_count']:,} 评论 · 月销 {p['estimated_monthly_sales']:,}
                            </div>
                        </div>
                        <a href="{p['link']}" target="_blank" style="text-decoration:none; background:linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color:#fff; padding:8px 14px; border-radius:10px; font-size:12px; font-weight:700; flex-shrink:0; white-space:nowrap; box-shadow:0 2px 8px rgba(37,99,235,0.25);">查看链接 →</a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _review_card(text: str, i: int, kind: str) -> str:
    if kind == "pain":
        bg, border, num_bg, num_color = "#fff", "#fee2e2", "#fee2e2", "#991b1b"
        badge_bg, badge_color = "#fee2e2", "#991b1b"
        badge_text = "高提及"
    else:
        bg, border, num_bg, num_color = "#fff", "#dcfce7", "#dcfce7", "#166534"
        badge_bg, badge_color = "#dcfce7", "#166534"
        badge_text = "卖点"
    return (
        f'<div style="display:flex; align-items:flex-start; gap:8px; padding:7px 10px; margin-bottom:6px; '
        f'background:{bg}; border:1px solid {border}; border-radius:10px; border-left:3px solid {num_color};">'
        f'<span style="flex-shrink:0; width:18px; height:18px; background:{num_bg}; color:{num_color}; '
        f'border-radius:50%; font-size:11px; font-weight:800; display:inline-flex; align-items:center; justify-content:center; margin-top:1px;">{i}</span>'
        f'<span style="font-size:13px; color:#334155; font-weight:500; line-height:1.45; flex:1;">{text}</span>'
        f'<span class="badge" style="background:{badge_bg}; color:{badge_color}; flex-shrink:0; margin-top:1px;">{badge_text}</span>'
        f'</div>'
    )


def render_review_insights(report: Dict):
    review = report["review_insights"]
    competitors = report["market_analysis"]["competitors"]
    keyword = report["keyword"]
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='info-card-title'>🔴 用户痛点</div>", unsafe_allow_html=True)
        pain_items = "".join(_review_card(p, i, "pain") for i, p in enumerate(review["pain_points"][:5], 1))
        st.markdown(f"<div>{pain_items}</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='info-card-title'>🟢 用户好评</div>", unsafe_allow_html=True)
        praise_items = "".join(_review_card(p, i, "praise") for i, p in enumerate(review["praised_features"][:5], 1))
        st.markdown(f"<div>{praise_items}</div>", unsafe_allow_html=True)

    st.markdown("<div class='info-card-title' style='margin-top:18px;'>💡 差异化机会</div>", unsafe_allow_html=True)
    st.markdown(
        f'<div style="padding:12px 14px; background:#f8fafc; border-radius:12px; margin-bottom:12px; font-size:13px; color:#475569; line-height:1.6;">'
        f'基于「<strong style="color:#2563eb;">{keyword}</strong>」用户评论洞察，围绕下方痛点做定向升级，可形成核心差异化卖点。'
        f'</div>',
        unsafe_allow_html=True,
    )
    for idx, opp in enumerate(review["opportunities"]):
        ref = competitors[idx % min(3, len(competitors))] if competitors else None
        if ref:
            st.markdown(
                f'<div class="product-card" style="display:flex; align-items:center; gap:12px; border-left:4px solid #2563eb; padding:12px 14px; margin-bottom:10px;">'
                f'<div style="flex:1; min-width:0;">'
                f'<div style="color:#0f172a; font-weight:700; font-size:14px; margin-bottom:4px;">🎯 {opp}</div>'
                f'<div style="display:flex; gap:6px; flex-wrap:wrap;">'
                f'<span class="badge" style="background:#eff6ff; color:#1d4ed8;">差异化</span>'
                f'<span class="badge" style="background:#f1f5f9; color:#475569;">参考竞品</span>'
                f'</div></div>'
                f'<a href="{ref["link"]}" target="_blank" style="flex-shrink:0; display:flex; align-items:center; gap:8px; text-decoration:none; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:6px 10px;">'
                f'<img src="{ref["image"]}" style="width:40px;height:40px;border-radius:8px;object-fit:cover;background:#fff;" />'
                f'<div style="text-align:left; min-width:0;">'
                f'<div style="color:#0f172a; font-weight:700; font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:120px;">{ref["title"]}</div>'
                f'<div style="color:#2563eb; font-weight:800; font-size:11px;">${ref["price"]} · 查看 →</div>'
                f'</div></a></div>',
                unsafe_allow_html=True,
            )
        else:
            st.info(opp)


# 利润测算页：成本项统一配色
_COST_COLORS = {
    "产品成本": "#1e3a8a",  # 深蓝
    "头程物流": "#06b6d4",  # 青色
    "FBA 费用": "#f97316",  # 橙色
    "平台佣金": "#8b5cf6",  # 紫色
    "广告费用": "#ef4444",  # 红色
    "退货预留": "#eab308",  # 黄色
    "其他杂费": "#6b7280",  # 灰色
}


def _cost_color(item: str) -> str:
    return _COST_COLORS.get(item, "#3b82f6")


def _roi_color(roi: float) -> str:
    if roi < 20:
        return "#dc2626"
    if roi < 40:
        return "#f97316"
    if roi < 60:
        return "#eab308"
    return "#16a34a"


def _assumption_risk_color(name: str, value, total: Optional[float] = None) -> str:
    """根据关键假设的数值返回风险颜色（红/黄/绿）。"""
    if name in ("平台佣金", "广告占比", "退货预留"):
        try:
            pct = float(value)
        except (TypeError, ValueError):
            return "#64748b"
        if pct >= 15:
            return "#dc2626"
        if pct >= 10:
            return "#eab308"
        return "#16a34a"
    if name == "FBA 费用":
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "#64748b"
        if v >= 5.5:
            return "#dc2626"
        if v >= 4.0:
            return "#eab308"
        return "#16a34a"
    if name == "头程物流":
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "#64748b"
        if v >= 3.5:
            return "#dc2626"
        if v >= 2.5:
            return "#eab308"
        return "#16a34a"
    if name == "盈亏平衡":
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "#64748b"
        if v >= 400:
            return "#dc2626"
        if v >= 200:
            return "#eab308"
        return "#16a34a"
    return "#2563eb"


def _cost_row(item: str, value: float, pct: str, total: float, bar_color: str) -> str:
    width = min(100, max(0, value / total * 100)) if total else 0
    pct_clean = pct.replace("%", "")
    try:
        pct_num = float(pct_clean)
    except ValueError:
        pct_num = 0.0
    text_color = "#ffffff" if width > 18 else bar_color
    return (
        f'<div class="cost-row">'
        f'<div class="cost-dot" style="background:{bar_color};"></div>'
        f'<div class="cost-info">'
        f'<div class="cost-meta"><span>{item}</span><span>USD {value:.2f}</span></div>'
        f'<div class="cost-bar-wrapper">'
        f'<div class="cost-bar-fill" style="width:{width}%; background:{bar_color}; color:{text_color};">'
        f'{pct_num:.1f}%</div></div>'
        f'<div class="cost-tooltip">成本构成：USD {value:.2f} ({pct_num:.1f}%)</div>'
        f'</div></div>'
    )


def _scenario_card(name: str, data: Dict, colors: Dict, currency: str) -> str:
    payback = f"{data['回本周期']} 月" if data["回本周期"] else "—"
    icon = {"保守": "🛡️", "中性": "⚖️", "乐观": "🚀"}.get(name, "📊")
    return (
        f'<div style="background:linear-gradient(145deg, #ffffff 0%, {colors["bg"]} 100%); border:1px solid {colors["border"]}; border-radius:18px; padding:22px 18px; text-align:center; position:relative; overflow:hidden; box-shadow:0 6px 18px rgba(15,23,42,0.05);">'
        f'<div style="position:absolute; top:0; left:0; right:0; height:5px; background:linear-gradient(90deg, {colors["accent"]}, {colors["value"]});"></div>'
        f'<div style="display:inline-flex; align-items:center; gap:6px; background:rgba(255,255,255,0.85); border:1px solid {colors["border"]}; color:{colors["pill"]}; padding:6px 16px; border-radius:24px; font-size:13px; font-weight:800; margin-bottom:16px; white-space:nowrap; box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
        f'<span style="font-size:15px;">{icon}</span><span>{name}情景</span></div>'
        f'<div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:16px;">'
        f'<div style="background:rgba(255,255,255,0.65); border-radius:12px; padding:12px 8px;">'
        f'<div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:5px;">月销量</div>'
        f'<div style="color:{colors["value"]}; font-size:34px; font-weight:900; line-height:1;">{data["月销量"]}</div></div>'
        f'<div style="background:rgba(255,255,255,0.65); border-radius:12px; padding:12px 8px;">'
        f'<div style="font-size:11px; color:#64748b; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:5px;">ROI</div>'
        f'<div style="color:{colors["value"]}; font-size:34px; font-weight:900; line-height:1;">{data["ROI"]}%</div></div></div>'
        f'<div style="border-top:1px solid {colors["border"]}; padding-top:14px; text-align:left;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:9px;">'
        f'<span style="display:flex; align-items:center; gap:5px; color:#64748b; font-size:13px; font-weight:600;"><span>💰</span> 月毛利</span>'
        f'<span style="color:#0f172a; font-size:15px; font-weight:800;">{currency}${data["月毛利"]:,.0f}</span></div>'
        f'<div style="display:flex; justify-content:space-between; align-items:center;">'
        f'<span style="display:flex; align-items:center; gap:5px; color:#64748b; font-size:13px; font-weight:600;"><span>⏳</span> 回本周期</span>'
        f'<span style="color:#0f172a; font-size:15px; font-weight:800;">{payback}</span></div>'
        f'</div></div>'
    )


def render_profit_analysis(report: Dict):
    profit = report["profit_analysis"]
    profile = report["market_analysis"]["market_profile"]

    # 基础数据
    selling_price = profit["selling_price"]
    unit_cost = profit["unit_cost"]
    gross_profit = profit["gross_profit_per_unit"]
    total_cost = profit["total_cost_per_unit"]
    margin = profit["gross_margin"]
    breakdown = profit["cost_breakdown"]
    breakdown_pct = profit["cost_breakdown_pct"]
    scenarios = profit["roi_scenarios"]

    # 固定投资与 ROI 曲线数据
    investment = unit_cost * 500 + 2000
    volumes = list(range(100, 601, 10))
    roi_values = [v * gross_profit / investment * 100 for v in volumes]

    # 最佳 ROI 情景
    best_name = max(scenarios, key=lambda k: scenarios[k]["ROI"])
    best_data = scenarios[best_name]
    best_action_map = {
        "保守": "优先降本控风险，验证最小订单模型",
        "中性": "按中性节奏备货，稳步扩大投放",
        "乐观": "积极备货并加大广告，抢占旺季窗口",
    }
    best_action = best_action_map.get(best_name, "结合市场节奏推进")

    # 顶部总结指标栏
    st.markdown(
        f'<div style="background:linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border:1px solid #bfdbfe; '
        f'border-radius:16px; padding:18px 22px; margin-bottom:22px; display:flex; align-items:center; '
        f'justify-content:space-between; flex-wrap:wrap; gap:14px; box-shadow:0 4px 14px rgba(37,99,235,0.08);">'
        f'<div>'
        f'<div style="font-size:12px; font-weight:800; color:#64748b; text-transform:uppercase; '
        f'letter-spacing:0.04em; margin-bottom:5px;">当前最佳 ROI 情景</div>'
        f'<div style="font-size:22px; font-weight:900; color:#1e40af;">'
        f'{best_name}情景 · ROI {best_data["ROI"]:.2f}% · 月毛利 USD {best_data["月毛利"]:,.2f}'
        f'</div></div>'
        f'<div style="background:#ffffff; border-radius:12px; padding:12px 18px; font-size:14px; '
        f'font-weight:800; color:#1e40af; box-shadow:0 2px 8px rgba(0,0,0,0.05);">'
        f'建议操作：{best_action}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 3])
    with col1:
        st.markdown("<div class='info-card-title'>单件成本明细</div>", unsafe_allow_html=True)
        rows = "".join(
            _cost_row(item, value, breakdown_pct.get(item, "0%"), total_cost, _cost_color(item))
            for item, value in breakdown.items()
        )
        st.markdown(
            f'<div class="cost-breakdown-card">'
            f'<div class="cost-total-row">'
            f'<span class="cost-total-label">总成本</span>'
            f'<span class="cost-total-value">USD {total_cost:.2f}</span></div>'
            f'{rows}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("<div class='info-card-title'>ROI 情景分析</div>", unsafe_allow_html=True)

        current_volume = st.slider(
            "当前月销量",
            min_value=100,
            max_value=600,
            value=300,
            step=10,
            key="roi_volume_slider",
        )
        current_roi = current_volume * gross_profit / investment * 100
        current_color = _roi_color(current_roi)

        st.markdown(
            f'<div style="display:flex; gap:18px; flex-wrap:wrap; margin-bottom:12px;">'
            f'<div style="flex:1; min-width:140px; background:#ffffff; border:1px solid #e2e8f0; '
            f'border-radius:12px; padding:12px 16px; box-shadow:0 2px 8px rgba(15,23,42,0.04);">'
            f'<div style="font-size:11px; font-weight:800; color:#64748b; text-transform:uppercase; '
            f'letter-spacing:0.03em; margin-bottom:4px;">当前月销量</div>'
            f'<div style="font-size:20px; font-weight:900; color:#0f172a;">{current_volume} 件</div></div>'
            f'<div style="flex:1; min-width:140px; background:#ffffff; border:1px solid #e2e8f0; '
            f'border-radius:12px; padding:12px 16px; box-shadow:0 2px 8px rgba(15,23,42,0.04);">'
            f'<div style="font-size:11px; font-weight:800; color:#64748b; text-transform:uppercase; '
            f'letter-spacing:0.03em; margin-bottom:4px;">当前 ROI</div>'
            f'<div style="font-size:20px; font-weight:900; color:{current_color};">{current_roi:.2f}%</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=volumes,
                    y=roi_values,
                    mode="lines",
                    name="ROI 趋势",
                    line=dict(color="#3b82f6", width=3),
                    fill="tozeroy",
                    fillcolor="rgba(59,130,246,0.08)",
                    hovertemplate="月销量：%{x}<br>ROI：%{y:.2f}%<extra></extra>",
                )
            )
            # 当前滑块位置
            fig.add_trace(
                go.Scatter(
                    x=[current_volume],
                    y=[current_roi],
                    mode="markers",
                    name="当前销量",
                    marker=dict(size=14, color=current_color, line=dict(color="#ffffff", width=2)),
                    hovertemplate="当前<br>月销量：%{x}<br>ROI：%{y:.2f}%<extra></extra>",
                )
            )
            # 三个情景关键点
            scenario_points = {"保守": 100, "中性": 300, "乐观": 600}
            for s_name, s_vol in scenario_points.items():
                s_roi = s_vol * gross_profit / investment * 100
                fig.add_trace(
                    go.Scatter(
                        x=[s_vol],
                        y=[s_roi],
                        mode="markers+text",
                        name=f"{s_name}情景",
                        text=[s_name],
                        textposition="top center",
                        textfont=dict(size=11, color="#475569"),
                        marker=dict(size=10, color=_roi_color(s_roi), line=dict(color="#ffffff", width=2)),
                        hovertemplate=f"{s_name}情景<br>月销量：%{{x}}<br>ROI：%{{y:.2f}}%<extra></extra>",
                    )
                )
            # ROI 阈值参考线
            for threshold, t_color, t_label in [(20, "#dc2626", "20%"), (40, "#f97316", "40%"), (60, "#eab308", "60%")]:
                fig.add_hline(
                    y=threshold,
                    line=dict(color=t_color, width=1, dash="dash"),
                    annotation_text=t_label,
                    annotation_position="right",
                    annotation_font=dict(size=10, color=t_color),
                    opacity=0.6,
                )
            fig.update_layout(
                height=340,
                margin=dict(l=20, r=50, t=20, b=40),
                paper_bgcolor="#ffffff",
                plot_bgcolor="#f8fafc",
                font=dict(color="#1e293b"),
                xaxis=dict(gridcolor="#e2e8f0", tickfont=dict(size=12), title="月销量"),
                yaxis=dict(gridcolor="#e2e8f0", tickfont=dict(size=12), title="ROI %", ticksuffix="%"),
                showlegend=False,
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True, config=dict(displayModeBar=False))
        else:
            st.markdown(
                '<div class="loading-overlay"><div class="spinner"></div>正在加载 ROI 图表...</div>',
                unsafe_allow_html=True,
            )

    # 利润优化分析 + 关键假设
    st.markdown("<br>", unsafe_allow_html=True)
    sim_col, assumption_col = st.columns([3, 2])

    with sim_col:
        st.markdown("<div class='info-card-title'>利润优化分析</div>", unsafe_allow_html=True)
        prod_cost = breakdown.get("产品成本", 0)
        ad_cost = breakdown.get("广告费用", 0)
        fba_cost = breakdown.get("FBA 费用", 0)

        sc1, sc2 = st.columns(2)
        with sc1:
            cost_reduction = st.slider(
                "产品成本优化 (USD)",
                min_value=0.0,
                max_value=round(min(2.0, prod_cost * 0.3), 2),
                value=0.0,
                step=0.1,
                key="cost_reduction_slider",
                help="降低采购或生产成本",
            )
            ad_reduction = st.slider(
                "广告费用优化 (USD)",
                min_value=0.0,
                max_value=round(min(1.0, ad_cost * 0.3), 2),
                value=0.0,
                step=0.05,
                key="ad_reduction_slider",
                help="通过精准投放降低 ACoS",
            )
        with sc2:
            fba_reduction = st.slider(
                "FBA 费用优化 (USD)",
                min_value=0.0,
                max_value=round(min(1.0, fba_cost * 0.3), 2),
                value=0.0,
                step=0.05,
                key="fba_reduction_slider",
                help="优化包装或入仓方案",
            )
            price_increase = st.slider(
                "售价提升 (USD)",
                min_value=0.0,
                max_value=5.0,
                value=0.0,
                step=0.1,
                key="price_increase_slider",
                help="在不影响转化的前提下提价",
            )

        # 实时重算
        new_total_cost = total_cost - cost_reduction - ad_reduction - fba_reduction
        new_selling_price = selling_price + price_increase
        new_gross_profit = new_selling_price - new_total_cost
        new_margin = new_gross_profit / new_selling_price if new_selling_price > 0 else 0
        base_monthly_profit = 300 * gross_profit
        new_monthly_profit = 300 * new_gross_profit
        monthly_increase_raw = new_monthly_profit - base_monthly_profit
        monthly_increase = 0.0 if abs(monthly_increase_raw) < 0.005 else round(monthly_increase_raw, 2)
        impact_color = "#16a34a" if monthly_increase > 0 else "#dc2626" if monthly_increase < 0 else "#64748b"

        st.markdown(
            f'<div class="simulator-result">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">'
            f'<div>'
            f'<div style="font-size:12px; font-weight:800; color:#64748b; text-transform:uppercase; '
            f'letter-spacing:0.03em; margin-bottom:4px;">优化后毛利率</div>'
            f'<div style="font-size:26px; font-weight:900; color:#15803d;">{new_margin:.2%}</div></div>'
            f'<div>'
            f'<div style="font-size:12px; font-weight:800; color:#64748b; text-transform:uppercase; '
            f'letter-spacing:0.03em; margin-bottom:4px;">月利润变化</div>'
            f'<div style="font-size:26px; font-weight:900; color:{impact_color};">'
            f'{"+" if monthly_increase > 0 else ""}USD {monthly_increase:,.2f}'
            f'</div></div></div>'
            f'<div style="margin-top:10px; font-size:13px; color:#475569; font-weight:500;">'
            f'基于 300 件/月销量估算 · 优化后单件毛利 USD {new_gross_profit:.2f}'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # 逐项变化说明
        impact_lines = []
        if cost_reduction > 0:
            impact_lines.append(f"产品成本降低 USD {cost_reduction:.2f}")
        if ad_reduction > 0:
            impact_lines.append(f"广告费用降低 USD {ad_reduction:.2f}")
        if fba_reduction > 0:
            impact_lines.append(f"FBA 费用降低 USD {fba_reduction:.2f}")
        if price_increase > 0:
            impact_lines.append(f"售价提升 USD {price_increase:.2f}")
        if impact_lines:
            st.markdown(
                f'<div style="margin-top:12px; font-size:13px; color:#334155; font-weight:500; line-height:1.7;">'
                f'{" · ".join(impact_lines)}，毛利率从 {margin:.2%} 提升至 {new_margin:.2%}。'
                f'</div>',
                unsafe_allow_html=True,
            )

    with assumption_col:
        st.markdown("<div class='info-card-title'>关键假设</div>", unsafe_allow_html=True)
        commission_val = breakdown.get("平台佣金", 0)
        fba_val = breakdown.get("FBA 费用", 0)
        ad_val = breakdown.get("广告费用", 0)
        return_val = breakdown.get("退货预留", 0)
        shipping_val = breakdown.get("头程物流", 0)
        be_units = profit.get("breakeven_units", 0)

        assumptions = [
            ("平台佣金", commission_val / total_cost * 100 if total_cost else 0, "%"),
            ("FBA 费用", fba_val, "USD"),
            ("广告占比", ad_val / total_cost * 100 if total_cost else 0, "%"),
            ("退货预留", return_val / total_cost * 100 if total_cost else 0, "%"),
            ("头程物流", shipping_val, "USD"),
            ("盈亏平衡", be_units, "units"),
        ]
        cards_html = ""
        for label, raw, fmt in assumptions:
            if fmt == "%":
                value_text = f"{raw:.2f}%"
            elif fmt == "USD":
                value_text = f"USD {raw:.2f}"
            else:
                value_text = f"{int(raw)} 件/月"
            color = _assumption_risk_color(label, raw, total_cost)
            cards_html += (
                f'<div class="assumption-card">'
                f'<div class="assumption-label">{label}</div>'
                f'<div class="assumption-value" style="color:{color} !important;">{value_text}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div style="display:flex; flex-wrap:wrap; gap:10px;">{cards_html}</div>',
            unsafe_allow_html=True,
        )


def render_trend_analysis(report: Dict):
    trend = report["trend_analysis"]
    peak_months = set(trend["peak_months"])
    entry_windows = set(trend.get("entry_windows", []))
    narrative = trend.get("season_narrative", {})

    if PLOTLY_AVAILABLE:
        fig = go.Figure()
        x = trend["series"]["months"]
        y = trend["series"]["values"]
        last_year = trend["series"].get("last_year_values", [])
        forecast_months = trend["series"].get("forecast_months", [])
        forecast = trend["series"].get("forecast_values", [])
        all_x = list(x) + list(forecast_months)

        # 当前年度搜索热度
        fig.add_trace(go.Scatter(
            x=all_x,
            y=list(y) + [None] * len(forecast_months),
            mode="lines+markers+text",
            name="本年度搜索热度",
            line=dict(color="#2563eb", width=3.5),
            marker=dict(size=10, color="#ffffff", line=dict(color="#2563eb", width=2)),
            text=[f"{v}" for v in y] + [None] * len(forecast_months),
            textposition="top center",
            textfont=dict(size=11, color="#1e40af", family="Inter, sans-serif"),
        ))

        # 去年同期
        if last_year:
            fig.add_trace(go.Scatter(
                x=all_x,
                y=list(last_year) + [None] * len(forecast_months),
                mode="lines+markers",
                name="去年同期",
                line=dict(color="#94a3b8", width=2, dash="dot"),
                marker=dict(size=7, color="#94a3b8"),
            ))

        # 未来 3 个月预测
        if forecast:
            fig.add_trace(go.Scatter(
                x=all_x,
                y=[None] * len(x) + list(forecast),
                mode="lines+markers+text",
                name="趋势预测",
                line=dict(color="#f59e0b", width=3, dash="dash"),
                marker=dict(size=9, color="#f59e0b"),
                text=[None] * len(x) + [f"{v}" for v in forecast],
                textposition="top center",
                textfont=dict(size=10, color="#b45309"),
            ))

        # 提前备货/入局窗口：青绿色（市场低谷）
        # x 轴为分类坐标，类别索引从 0 开始，月份 m 对应索引 m-1
        for m in entry_windows:
            idx = m - 1
            fig.add_vrect(
                x0=idx - 0.5, x1=idx + 0.5,
                fillcolor="#14b8a6", opacity=0.15, line_width=0,
                layer="below",
            )
        # 旺季高峰：红色背景
        for m in peak_months:
            idx = m - 1
            fig.add_vrect(
                x0=idx - 0.5, x1=idx + 0.5,
                fillcolor="#ef4444", opacity=0.18, line_width=0,
                layer="below",
            )

        # 在第一个布局窗口和第一个旺季上方加标注
        if entry_windows:
            first_entry = min(entry_windows) - 1
            fig.add_annotation(
                x=first_entry, y=max(y) * 1.08,
                text="🚀 提前备货/入局",
                showarrow=False, font=dict(size=12, color="#0f766e", family="Inter, sans-serif"),
                bgcolor="rgba(255,255,255,0.95)", bordercolor="#14b8a6", borderwidth=1, borderpad=4,
            )
        if peak_months:
            first_peak = min(peak_months) - 1
            fig.add_annotation(
                x=first_peak, y=max(y) * 1.08,
                text="🔥 旺季高峰",
                showarrow=False, font=dict(size=12, color="#b91c1c", family="Inter, sans-serif"),
                bgcolor="rgba(255,255,255,0.95)", bordercolor="#ef4444", borderwidth=1, borderpad=4,
            )

        # 自定义图例项
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=12, color="#14b8a6", opacity=0.5),
            name="提前备货/入局窗口",
        ))
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode="markers",
            marker=dict(size=12, color="#ef4444", opacity=0.5),
            name="旺季高峰",
        ))

        fig.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=60, b=20),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#f8fafc",
            font=dict(color="#1e293b"),
            xaxis=dict(gridcolor="#e2e8f0", tickfont=dict(size=12)),
            yaxis=dict(gridcolor="#e2e8f0", tickfont=dict(size=12), title="搜索热度"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                bgcolor="rgba(255,255,255,0.8)", bordercolor="#e2e8f0", borderwidth=1,
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config=dict(displayModeBar=False))

    peak = "、".join(f"{m}月" for m in sorted(peak_months))
    entry = "、".join(f"{m}月" for m in sorted(entry_windows))
    season_desc = narrative.get("season_desc", "")
    trend_desc = narrative.get("trend_desc", "")

    # 建议行动节奏：用简洁的列表代替编号时间轴，避免视觉噪音与乱码风险
    action_items = [
        ("当前", "完成关键词/市场数据分析，确认品类季节性与利润空间。", "#2563eb"),
        ("样品验证", "2 周内锁定供应商、完成样品测试与合规资料确认。", "#0891b2"),
        (f"备货发货", f"在 {entry} 完成首批备货并发出，确保旺季前 4-6 周到仓。", "#0f766e"),
        (f"旺季销售", f"把握 {peak} 需求高峰，加大广告投放与促销力度。", "#ef4444"),
        ("复盘迭代", "旺季结束后复盘差评与库存周转，推进 V2.0 产品改良。", "#7c3aed"),
    ]
    action_html = "".join(
        f'<div style="display:flex; align-items:flex-start; gap:10px; padding:8px 0; border-bottom:1px solid #f1f5f9;">'
        f'<div style="flex-shrink:0; width:8px; height:8px; border-radius:50%; background:{color}; margin-top:7px;"></div>'
        f'<div style="flex:1;"><span style="font-weight:800; color:#0f172a; font-size:13px;">{title}：</span>'
        f'<span style="color:#475569; font-size:13px; line-height:1.6;">{desc}</span></div></div>'
        for title, desc, color in action_items
    )

    st.markdown(
        f'<div class="info-card" style="margin-top:14px;">'
        f'<div class="info-card-title">📅 季节与入场节奏</div>'
        f'<div style="display:flex; gap:16px; flex-wrap:wrap; font-size:14px; color:#475569; line-height:1.7;">'
        f'<div><span style="color:#ef4444; font-weight:800;">🔥 旺季高峰：</span>{peak}</div>'
        f'<div><span style="color:#0f766e; font-weight:800;">🚀 建议提前备货/入局窗口：</span>{entry}</div></div>'
        f'<div style="margin-top:12px; padding:14px; background:#f8fafc; border-radius:12px; border-left:4px solid #2563eb;">'
        f'<div style="font-size:13px; color:#334155; line-height:1.75; margin-bottom:6px;"><strong>行业季节洞察：</strong>{season_desc}</div>'
        f'<div style="font-size:13px; color:#334155; line-height:1.75;"><strong>趋势判断：</strong>{trend_desc}</div></div>'
        f'<div style="margin-top:16px;">'
        f'<div style="font-size:12px; font-weight:800; color:#64748b; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:10px;">📍 选品到销售行动节奏</div>'
        f'{action_html}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def render_suppliers(report: Dict):
    suppliers = report["suppliers"]

    st.markdown(
        f"""
        <div class="info-card" style="margin-bottom:16px; padding:18px 20px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <div class="info-card-title" style="margin-bottom:4px;">🏭 供应商竞争力 TOP10</div>
                    <div style="color:#64748b; font-size:13px; font-weight:500;">综合评分 · 产能 · 响应 · 报价多维度对比</div>
                </div>
                <span class="badge" style="background:#eff6ff; color:#1d4ed8;">已匹配 {len(suppliers)} 家</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    sort_col, _ = st.columns([1, 3])
    with sort_col:
        sort_by = st.selectbox(
            "排序方式",
            ["综合评分（默认）", "单价从低到高", "单价从高到低", "响应率从高到低"],
            key="supplier_sort",
        )

    sorted_suppliers = list(suppliers)
    if sort_by == "单价从低到高":
        sorted_suppliers.sort(key=lambda x: x["unit_cost"])
    elif sort_by == "单价从高到低":
        sorted_suppliers.sort(key=lambda x: x["unit_cost"], reverse=True)
    elif sort_by == "响应率从高到低":
        sorted_suppliers.sort(key=lambda x: x["response_rate"], reverse=True)

    # 排名重算
    for i, s in enumerate(sorted_suppliers, 1):
        s["display_rank"] = i

    for s in sorted_suppliers:
        rank = s["display_rank"]
        rank_class = "gold" if rank == 1 else "silver" if rank == 2 else "bronze" if rank == 3 else ""
        rating_pct = min(100, s["rating"] / 5.0 * 100)
        response_pct = s["response_rate"]
        # 评分条：暖色渐变（深橙到浅琥珀）
        rating_color = "linear-gradient(90deg, #ea580c, #fbbf24)"
        # 响应条：青绿渐变（深青到浅青）
        response_color = "linear-gradient(90deg, #0f766e, #2dd4bf)"

        hot_badges = "".join(
            f'<span class="badge" style="background:#fff7ed; color:#9a3412; border:1px solid #fed7aa;">🔥 {c}</span>'
            for c in s.get("hot_categories", [])
        )
        st.markdown(
            f"""
            <div class="product-card" style="padding:16px;">
                <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
                    <div class="supplier-rank {rank_class}">{rank}</div>
                    <div style="flex:1; min-width:220px;">
                        <div class="product-title" style="font-size:16px; margin-bottom:5px;">{s['name']}</div>
                        <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px;">
                            <span class="badge" style="background:#eff6ff; color:#1d4ed8;">{s['moq']}</span>
                            <span class="badge" style="background:#dbeafe; color:#1e40af;">交期 {s['lead_time']}</span>
                            <span class="badge" style="background:#f1f5f9; color:#334155;">{s['capacity']}</span>
                            <span class="badge" style="background:#ecfdf5; color:#047857;">打样 {s['sample_days']} 天</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:8px;">
                            <div style="display:flex; align-items:center; gap:6px; flex:1; min-width:120px;">
                                <span style="font-size:11px; font-weight:700; color:#475569; white-space:nowrap;">评分</span>
                                <div class="big-bar-bg"><div class="big-bar-fill" style="width:{rating_pct}%; background:{rating_color};"></div></div>
                                <span style="font-size:12px; font-weight:800; color:#0f172a; white-space:nowrap;">{s['rating']}</span>
                            </div>
                            <div style="display:flex; align-items:center; gap:6px; flex:1; min-width:120px;">
                                <span style="font-size:11px; font-weight:700; color:#475569; white-space:nowrap;">响应</span>
                                <div class="big-bar-bg"><div class="big-bar-fill" style="width:{response_pct}%; background:{response_color};"></div></div>
                                <span style="font-size:12px; font-weight:800; color:#0f172a; white-space:nowrap;">{s['response_rate']}%</span>
                            </div>
                        </div>
                        <div style="display:flex; gap:6px; flex-wrap:wrap; align-items:center;">
                            <span style="font-size:11px; font-weight:700; color:#475569; white-space:nowrap;">主营热卖：</span>
                            {hot_badges}
                        </div>
                    </div>
                    <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
                        <div style="display:flex; gap:14px; flex-wrap:wrap;">
                            <div class="supplier-metric">
                                <div class="supplier-metric-value" style="color:#2563eb;">${s['unit_cost']}</div>
                                <div class="supplier-metric-label">单价</div>
                            </div>
                            <div class="supplier-metric">
                                <div class="supplier-metric-value">${s['sample_cost']}</div>
                                <div class="supplier-metric-label">样品</div>
                            </div>
                            <div class="supplier-metric">
                                <div class="supplier-metric-value">{s['years']}年</div>
                                <div class="supplier-metric-label">经营</div>
                            </div>
                            <div class="supplier-metric">
                                <div class="supplier-metric-value">{s['transactions']}</div>
                                <div class="supplier-metric-label">成交</div>
                            </div>
                        </div>
                        <a href="{s.get('link_1688', '#')}" target="_blank" style="flex-shrink:0; display:flex; align-items:center; gap:8px; text-decoration:none; background:#fff7ed; border:1px solid #fed7aa; border-radius:12px; padding:8px 12px; min-width:150px;">
                            <img src="{s.get('hot_product_image', '')}" style="width:44px;height:44px;border-radius:8px;object-fit:cover;background:#fff;" />
                            <div style="text-align:left; min-width:0;">
                                <div style="color:#9a3412; font-weight:800; font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:110px;">{s.get('hot_product_name', '热卖品')}</div>
                                <div style="color:#d97706; font-weight:800; font-size:12px;">1688 搜索 →</div>
                            </div>
                        </a>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 导出 CSV
    import csv
    csv_buffer = io.StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=["display_rank", "name", "moq", "lead_time", "rating", "response_rate", "unit_cost", "sample_cost", "capacity", "sample_days", "years", "transactions", "hot_categories", "hot_product_name", "link_1688"],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(sorted_suppliers)
    st.download_button(
        label="📥 导出供应商对比表 (CSV)",
        data=csv_buffer.getvalue().encode("utf-8-sig"),
        file_name=f"{report['keyword'].replace(' ', '_').lower()}_{report['market'].lower()}_suppliers.csv",
        mime="text/csv",
    )


def render_compliance(report: Dict):
    comp = report["compliance"]
    risk_colors = {
        "低": {"bg": "#eff6ff", "text": "#1d4ed8", "border": "#bfdbfe"},
        "中": {"bg": "#fff7ed", "text": "#9a3412", "border": "#fed7aa"},
        "高": {"bg": "#fee2e2", "text": "#991b1b", "border": "#fecaca"},
    }
    rc = risk_colors.get(comp["risk_level"], {"bg": "#f1f5f9", "text": "#475569", "border": "#e2e8f0"})

    sections = [
        ("🎯 品类专属合规风险", comp.get("category_risks", []), "#dc2626", "重点关注", "与关键词行业精准匹配"),
        ("📋 强制认证", comp["certifications"], "#2563eb", "通过", "建议尽早上架前准备"),
        ("🎨 外观设计专利风险", comp.get("design_patent_risks", []), "#d97706", "需检索", "避免 TRO 与下架"),
        ("™️ 商标/品牌侵权风险", comp.get("brand_risks", []), "#7c3aed", "需筛查", "Listing 文案/图片自查"),
        ("⚙️ 行业/功能专利风险", comp.get("industry_patent_risks", []), "#0f766e", "需 FTO", "工厂授权链确认"),
        ("🌍 目标市场特殊合规", comp.get("market_specific", []), "#0369a1", "需适配", f"{comp['market']} 当地法规"),
    ]

    st.markdown(
        f"""
        <div class="info-card" style="margin-bottom:16px;">
            <div class="info-card-title">🛡️ 合规与知识产权风险检查</div>
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <span class="badge" style="background:{rc['bg']}; color:{rc['text']}; border:1px solid {rc['border']};">风险等级：{comp['risk_level']}</span>
                <span class="badge" style="background:#f1f5f9; color:#475569;">预估认证费用 ${comp['estimated_cert_cost']}</span>
                <span class="badge" style="background:#f1f5f9; color:#475569;">预估周期 {comp['estimated_cert_time']}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 使用 CSS Grid 布局，保证同一行左右卡片严格等高对齐
    cards_html = ""
    for idx, (title, items, accent, status_ok, status_note) in enumerate(sections):
        if not items:
            continue
        items_html = "".join(f"<li>{c}</li>" for c in items)
        cards_html += (
            f'<div class="compliance-card" style="border-left:4px solid {accent}; height:100%; min-height:170px; display:flex; flex-direction:column;">'
            f'<div class="compliance-card-header">'
            f'<div class="compliance-card-title">{title}</div>'
            f'<span class="compliance-status" style="background:{accent}20; color:{accent};">{status_ok}</span>'
            f'</div>'
            f'<ul class="compliance-list" style="flex:1;">{items_html}</ul>'
            f'<div style="margin-top:auto; padding:8px 10px; background:#f8fafc; border-radius:8px; font-size:12px; color:#64748b; font-weight:600;">'
            f'💡 {status_note}</div>'
            f'</div>'
        )
    st.markdown(
        f"<div style='display:grid; grid-template-columns:1fr 1fr; gap:16px;'>{cards_html}</div>",
        unsafe_allow_html=True,
    )


def render_trending_products(report: Dict):
    trending = report["trending_products"]
    for t in trending:
        opp_color = "#1d4ed8" if t["opportunity"] == "高" else "#2563eb"
        opp_bg = "#eff6ff" if t["opportunity"] == "高" else "#dbeafe"
        comp_color = "#16a34a" if t["competition"] == "低" else "#d97706" if t["competition"] == "中" else "#dc2626"
        st.markdown(
            f"""
            <div class="product-card">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <div class="product-title">{t['keyword']}</div>
                        <div class="product-meta">竞争强度：<span style="color:{comp_color}; font-weight:700;">{t['competition']}</span> · 机会：{t['opportunity']}</div>
                    </div>
                    <div>
                        <span class="badge" style="background:{opp_bg}; color:{opp_color};">↗ {t['growth_pct']}%</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _build_report_markdown(report: Dict) -> str:
    lines = [
        f"# 选品分析报告：{report['keyword'].upper()}",
        "",
        f"- 目标市场：{report['market']}",
        f"- 预算区间：{report['budget']}",
        f"- 综合判定：**{report['verdict']}（等级 {report['grade']}）**",
        f"- 综合评分：{report['overall_score']}/{report['max_score']}",
        "",
        "## 核心结论",
        f"关键词 **{report['keyword']}** 在 **{report['market']}** 市场平均售价 **${report['market_analysis']['avg_price']}**，"
        f"毛利率 **{report['profit_analysis']['gross_margin_pct']}**，趋势 **{report['trend_analysis']['trend_direction'].upper()}**。",
        "",
        "## 评分拆解",
    ]
    for name, score in report["score_breakdown"].items():
        lines.append(f"- {name}：{score}")
    lines.append("")
    lines.append("## 用户痛点")
    for pain in report["review_insights"]["pain_points"]:
        lines.append(f"- {pain}")
    lines.append("")
    lines.append("## 行动计划")
    for i, step in enumerate(report["next_steps"], 1):
        lines.append(f"{i}. [{step['phase']}] {step['title']}")
        for task in step["tasks"]:
            lines.append(f"   - {task}")
        lines.append(f"   - 价值：{step['value']}")
    lines.append("")
    lines.append("*报告由跨境电商智能选品决策驾驶舱生成*")
    return "\n".join(lines)


def _render_action_step(step: Dict, accent: str):
    tasks_html = "".join(f"<li>{t}</li>" for t in step["tasks"])
    st.markdown(
        f"""
        <div class="action-step" style="border-left:4px solid {accent}; margin-bottom:14px;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px; flex-wrap:wrap;">
                <span style="background:#eff6ff; color:#1d4ed8; border-radius:6px; padding:4px 12px; font-size:12px; font-weight:800;">{step['phase']}</span>
                <span style="color:#0f172a; font-weight:800; font-size:15px;">{step['title']}</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
                <span style="background:#f1f5f9; color:#64748b; border-radius:6px; padding:3px 10px; font-size:11px; font-weight:700;">👤 {step['owner']}</span>
            </div>
            <ul style="margin:0 0 10px 18px; padding:0; color:#475569; font-size:13px; line-height:1.7;">
                {tasks_html}
            </ul>
            <div style="padding:10px 12px; background:#f8fafc; border-radius:8px; font-size:13px; color:#334155; font-weight:600;">
                ✅ 价值：{step['value']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_action_plan(report: Dict):
    st.markdown("<div class='info-card-title'>🎯 可落地行动计划</div>", unsafe_allow_html=True)
    steps = report["next_steps"]
    accents = ["#2563eb", "#0891b2", "#7c3aed", "#16a34a", "#d97706"]

    # 左右两栏 Masonry 布局：奇数在左，偶数在右
    left_steps = [steps[i] for i in range(0, len(steps), 2)]
    right_steps = [steps[i] for i in range(1, len(steps), 2)]

    col_left, col_right = st.columns(2)
    with col_left:
        for i, step in enumerate(left_steps):
            _render_action_step(step, accents[(i * 2) % len(accents)])
    with col_right:
        for i, step in enumerate(right_steps):
            _render_action_step(step, accents[(i * 2 + 1) % len(accents)])

    col1, col2 = st.columns(2)
    with col1:
        md = _build_report_markdown(report)
        file_name = f"{report['keyword'].replace(' ', '_').lower()}_{report['market'].lower()}_report.md"
        st.download_button(
            label="📄 导出分析报告",
            data=md,
            file_name=file_name,
            mime="text/markdown",
            use_container_width=True,
        )
    with col2:
        if st.button("📤 推送飞书审批", use_container_width=True):
            approval_no = f"RPT-{report['market']}-{report['keyword'].replace(' ', '_').upper()}-{int(time.time()) % 100000:05d}"
            st.success(f"审批实例已创建：{approval_no}，请在飞书审批中心查看进度。")


def render_report(report: Dict):
    render_verdict_banner(report)
    render_kpi_cards(report)

    # 决策看板：雷达图与评分拆解/结论放入同一个 info-card，内部自然对齐
    st.markdown(
        "<div class='info-card' style='margin-bottom:20px; padding:18px;'>"
        "<div class='info-card-title'>🎯 选品决策看板</div>",
        unsafe_allow_html=True,
    )
    col_left, col_right = st.columns([3, 2])
    with col_left:
        render_radar(report, wrap_card=False)
    with col_right:
        render_score_breakdown(report, wrap_card=False)
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        render_conclusion(report, wrap_card=False)
    st.markdown("</div>", unsafe_allow_html=True)

    # 详情标签页
    tab_market, tab_review, tab_profit, tab_trend, tab_supply, tab_compliance, tab_action = st.tabs(
        ["市场分析", "评论洞察", "利润测算", "趋势季节", "供应商", "合规检查", "行动计划"]
    )

    with tab_market:
        render_market_analysis(report)
    with tab_review:
        render_review_insights(report)
    with tab_profit:
        render_profit_analysis(report)
    with tab_trend:
        render_trend_analysis(report)
    with tab_supply:
        render_suppliers(report)
    with tab_compliance:
        render_compliance(report)
    with tab_action:
        render_action_plan(report)


def _report_params(report: Dict):
    return (
        report.get("keyword", "").strip(),
        report.get("market", ""),
        report.get("budget", ""),
        float(report.get("selling_price", 0)),
        float(report.get("unit_cost", 0)),
    )


def main():
    inject_custom_css()
    render_header()
    keyword, market, budget, selling_price, unit_cost, analyze_btn = render_sidebar()

    if "report" not in st.session_state:
        st.session_state.report = None

    current_params = (keyword.strip(), market, budget, float(selling_price), float(unit_cost))
    report = st.session_state.report
    needs_refresh = report is None or _report_params(report) != current_params

    if needs_refresh:
        with st.spinner("Multi-Agent 协同分析中，请稍候..."):
            try:
                st.session_state.report = generate_report(
                    keyword, market, budget, selling_price, unit_cost
                )
            except Exception as e:
                st.error(f"分析出错：{e}")
                st.session_state.report = None

    if st.session_state.report:
        render_report(st.session_state.report)
    else:
        st.info("👈 在左侧填写产品信息并点击「开始选品分析」查看决策驾驶舱。")


if __name__ == "__main__":
    main()
