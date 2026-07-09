# ============================================================
# api/services/report_engine.py — 跨境电商智能选品数据引擎
#
# 从 frontend/app.py 提取的纯数据分析引擎，无 Streamlit/Plotly 依赖。
# 可在标准库环境下独立运行；requests/bs4 为可选依赖。
# ============================================================

import hashlib
import json
import math
import random
import urllib.parse
from dataclasses import dataclass
from typing import Dict, List, Optional

# 用于抓取真实 Amazon 产品 ASIN（可选依赖）
try:
    import requests
    from bs4 import BeautifulSoup

    SCRAPING_AVAILABLE = True
except ImportError:
    SCRAPING_AVAILABLE = False


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
    抓取失败或网络不可用时返回空列表，由调用方降级为示例数据+搜索链接。
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


if __name__ == "__main__":
    report = generate_report("cat toy", "US", "medium")
    summary = {
        "keyword": report["keyword"],
        "market": report["market"],
        "budget": report["budget"],
        "verdict": report["verdict"],
        "grade": report["grade"],
        "overall_score": report["overall_score"],
        "max_score": report["max_score"],
        "selling_price": report["selling_price"],
        "unit_cost": report["unit_cost"],
        "gross_margin_pct": report["profit_analysis"]["gross_margin_pct"],
        "competitors_count": len(report["market_analysis"]["competitors"]),
        "suppliers_count": len(report["suppliers"]),
        "peak_months": report["trend_analysis"]["peak_months"],
        "entry_windows": report["trend_analysis"]["entry_windows"],
        "trending_products_count": len(report["trending_products"]),
        "next_steps_count": len(report["next_steps"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
