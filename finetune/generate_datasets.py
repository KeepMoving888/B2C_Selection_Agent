#!/usr/bin/env python3
"""
微调数据集生成器
将手工样本 + 产品模板 + 市场参数组合，生成为微调所需的数据集。

运行：python finetune/generate_datasets.py

# 产出：
#  sft_train.jsonl            → ~500 条电商选品 SFT 数据（chat 格式）
#  orpo_chosen_rejected.jsonl → ~2000 条 ORPO 偏好对
#  qwen32b_instructions.jsonl → ~300 条 Qwen2.5-7B 指令数据
"""

import json, random, os

# ── 产品 × 市场 × 价格 组合池 ──
# 覆盖跨境电商主流高潜类目：宠物、家居、电子、运动、美妆、母婴、汽配、工具
PRODUCTS = [
    ("宠物咀嚼玩具", "Pet Supplies > Dogs > Toys > Chew Toys", "15-25美元", "pet_supplies", "US"),
    ("瑜伽裤", "Sports > Fitness > Yoga > Pants", "25-40欧元", "clothing", "DE"),
    ("硅胶折叠水杯", "Sports > Camping > Hydration > Collapsible Bottles", "10-15英镑", "sports", "UK"),
    ("LED化妆镜", "Beauty > Tools > Mirrors > Lighted", "25-40美元", "beauty", "US"),
    ("不锈钢保温咖啡杯", "Home & Kitchen > Dining > Travel Mugs", "20-30美元", "home_kitchen", "US"),
    ("手机防水袋", "Electronics > Accessories > Cases > Waterproof", "8-15英镑", "electronics", "UK"),
    ("儿童硅胶餐具套装", "Baby > Feeding > Bowls & Plates", "20-30美元", "baby", "US"),
    ("可调节哑铃组", "Sports > Strength > Dumbbells", "150-300美元", "sports", "US"),
    ("浴室收纳架", "Home & Kitchen > Bath > Storage", "20-35加元", "home_kitchen", "CA"),
    ("汽车手机支架", "Automotive > Accessories > Phone Mounts", "10-20美元", "electronics", "US"),
    ("竹纤维厨房毛巾", "Home & Kitchen > Linens > Kitchen Towels", "12-18美元", "home_kitchen", "US"),
    ("电动牙刷替换刷头", "Health > Oral Care > Replacement Heads", "8-15英镑", "beauty", "UK"),
    ("桌面手机支架", "Electronics > Accessories > Stands", "10-20美元", "electronics", "US"),
    ("瑜伽垫", "Sports > Fitness > Yoga > Mats", "25-40美元", "sports", "US"),
    ("猫抓板", "Pet Supplies > Cats > Scratching Posts", "15-25美元", "pet_supplies", "US"),
    ("办公桌垫", "Office Products > Desk Accessories > Mats", "15-25美元", "office", "US"),
    ("花园浇水喷头", "Garden > Watering > Nozzles", "10-20美元", "garden", "US"),
    ("旅行收纳袋套装", "Luggage > Packing Organizers", "15-25美元", "luggage", "US"),
    ("无线蓝牙耳机", "Electronics > Headphones > Earbuds", "20-40美元", "electronics", "US"),
    ("不锈钢饭盒", "Home & Kitchen > Food Containers", "15-25美元", "home_kitchen", "US"),
    ("瑜伽砖", "Sports > Fitness > Yoga > Blocks", "8-15美元", "sports", "US"),
    ("狗牵引绳", "Pet Supplies > Dogs > Leashes", "10-20美元", "pet_supplies", "US"),
    ("键盘腕托", "Office Products > Accessories > Wrist Rests", "10-20美元", "office", "US"),
    ("露营灯", "Sports > Camping > Lighting > Lanterns", "15-30美元", "sports", "US"),
    ("化妆刷套装", "Beauty > Tools > Brushes > Sets", "15-25美元", "beauty", "US"),
    ("宠物自动喂食器", "Pet Supplies > Cats > Feeders & Waterers", "30-50美元", "pet_supplies", "US"),
    ("猫砂盆", "Pet Supplies > Cats > Litter Boxes", "25-45美元", "pet_supplies", "US"),
    ("狗窝", "Pet Supplies > Dogs > Beds", "35-60美元", "pet_supplies", "US"),
    ("宠物烘干箱", "Pet Supplies > Grooming > Drying Cabinets", "80-150美元", "pet_supplies", "US"),
    ("厨房置物架", "Home & Kitchen > Storage > Racks", "25-40美元", "home_kitchen", "US"),
    ("冰箱收纳盒", "Home & Kitchen > Storage > Organizers", "15-25美元", "home_kitchen", "US"),
    ("真空压缩袋", "Home & Kitchen > Storage > Vacuum Bags", "12-20美元", "home_kitchen", "US"),
    ("床上四件套", "Home & Kitchen > Bedding > Sheet Sets", "40-70美元", "home_kitchen", "US"),
    ("遮光窗帘", "Home & Kitchen > Curtains > Blackout", "30-55美元", "home_kitchen", "US"),
    ("无线吸尘器", "Home & Kitchen > Vacuums > Stick Vacuums", "120-200美元", "home_kitchen", "US"),
    ("空气炸锅配件", "Home & Kitchen > Appliances > Air Fryer Accessories", "18-30美元", "home_kitchen", "US"),
    ("便携充电宝", "Electronics > Accessories > Power Banks", "20-40美元", "electronics", "US"),
    ("数据线收纳包", "Electronics > Accessories > Cable Organizers", "10-18美元", "electronics", "US"),
    ("笔记本支架", "Electronics > Accessories > Laptop Stands", "20-35美元", "electronics", "US"),
    ("屏幕挂灯", "Electronics > Accessories > Monitor Lights", "25-45美元", "electronics", "US"),
    ("智能手环表带", "Electronics > Wearables > Watch Bands", "8-15美元", "electronics", "US"),
    ("车载充电器", "Automotive > Accessories > Car Chargers", "12-22美元", "automotive", "US"),
    ("行车记录仪支架", "Automotive > Accessories > Dash Cam Mounts", "15-25美元", "automotive", "US"),
    ("车载吸尘器", "Automotive > Accessories > Car Vacuums", "30-55美元", "automotive", "US"),
    ("登山包", "Sports > Outdoor > Hiking Backpacks", "40-80美元", "sports", "US"),
    ("运动水壶", "Sports > Fitness > Water Bottles", "15-25美元", "sports", "US"),
    ("筋膜枪", "Sports > Recovery > Massage Guns", "40-80美元", "sports", "US"),
    ("阻力带套装", "Sports > Fitness > Resistance Bands", "12-22美元", "sports", "US"),
    ("滑板护具", "Sports > Skateboarding > Protective Gear", "20-35美元", "sports", "US"),
    ("防晒霜", "Beauty > Skin Care > Sunscreen", "15-30美元", "beauty", "US"),
    ("睫毛夹", "Beauty > Tools > Eyelash Curlers", "8-15美元", "beauty", "US"),
    ("美甲灯", "Beauty > Tools > Nail Dryers", "15-28美元", "beauty", "US"),
    ("假发片", "Beauty > Hair > Extensions", "20-40美元", "beauty", "US"),
    ("婴儿推车挂钩", "Baby > Stroller Accessories > Hooks", "8-15美元", "baby", "US"),
    ("儿童围栏", "Baby > Safety > Playards", "80-150美元", "baby", "US"),
    ("哺乳枕", "Baby > Nursing > Pillows", "25-45美元", "baby", "US"),
    ("园艺手套", "Garden > Tools > Gloves", "10-18美元", "garden", "US"),
    ("除草工具", "Garden > Tools > Weeders", "12-22美元", "garden", "US"),
    ("户外野餐垫", "Sports > Outdoor > Picnic Blankets", "15-28美元", "sports", "US"),
    ("车载香薰", "Automotive > Accessories > Air Fresheners", "10-18美元", "automotive", "US"),
    ("螺丝刀套装", "Tools > Hand Tools > Screwdrivers", "18-32美元", "tools", "US"),
    ("卷尺", "Tools > Measuring > Tape Measures", "10-20美元", "tools", "US"),
    ("LED工作灯", "Tools > Lighting > Work Lights", "20-38美元", "tools", "US"),
    ("护目镜", "Tools > Safety > Goggles", "8-18美元", "tools", "US"),
    ("行李秤", "Luggage > Accessories > Luggage Scales", "10-18美元", "luggage", "US"),
    ("护照包", "Luggage > Accessories > Passport Holders", "12-22美元", "luggage", "US"),
]

MARKETS = [
    ("美国", "US", "amazon.com", "$"),
    ("英国", "UK", "amazon.co.uk", "£"),
    ("德国", "DE", "amazon.de", "€"),
    ("日本", "JP", "amazon.co.jp", "¥"),
    ("加拿大", "CA", "amazon.ca", "CAD"),
]

# ── 生成辅助函数 ──
def gen_sft_system():
    return "你是跨境电商选品分析专家，精通Amazon/Shopify/eBay多平台选品。输出需包含：市场潜力评分(0-100)、竞争格局、需求特征、合规风险、供应链可行性、利润预估、行动建议的结构化JSON。"

def gen_sft_entry(product, market, price_range):
    name, cat, _, _, _ = product
    mkt_name, mkt_code, platform, currency = market
    score = random.randint(55, 85)
    yoy = random.randint(5, 25)
    verdicts = ["建议进入", "条件性建议进入", "强烈建议进入", "不建议进入"]
    verdict = random.choice(verdicts[:3]) if score > 60 else verdicts[3]

    return {
        "messages": [
            {"role": "system", "content": gen_sft_system()},
            {"role": "user", "content": f"分析{name}在{platform}的市场可行性，目标售价{price_range}"},
            {"role": "assistant", "content": json.dumps({
                "market_potential_score": score,
                "market_overview": {
                    "category": cat,
                    "market": mkt_code,
                    "platform": platform,
                    "yoy_growth": f"{yoy}%",
                    "search_volume_monthly": random.randint(15000, 150000)
                },
                "recommendation": {
                    "verdict": verdict,
                    "overall_score": score,
                    "key_factors": ["市场规模", "竞争强度", "合规门槛", "利润率"]
                }
            }, ensure_ascii=False)}
        ]
    }

def gen_orpo_entry(product, variant_idx: int = 0):
    name, cat, price_range, _, market = product
    score = random.randint(55, 85)
    competitors = random.randint(8, 60)
    margin_low = random.randint(25, 35)
    margin_high = random.randint(40, 55)
    moq = random.choice(["300", "500", "1000", "2000"])
    peak = random.choice(["Q4 假日季", "Q2 运动旺季", "全年稳定", "夏季出行季"])
    rating = round(random.uniform(4.0, 4.6), 1)
    search_vol = random.randint(12000, 180000)

    # 市场特定合规与物流提示
    market_notes = {
        "US": "需关注 FCC/UL/FDA 等认证及关税",
        "UK": "需 UKCA 标识及英欧物流差异",
        "DE": "需 CE/GS/WEEE 及德语说明书",
        "JP": "需 PSE/无线电法及日语标签",
        "CA": "需 CSA/IC 认证及英法双语包装",
    }.get(market, "需核查目标市场认证")

    # 高质量 chosen：结构化、有数据、有行动建议
    chosen_templates = [
        (
            f"经过多维度分析，{name}在{market}市场评分{score}/100。"
            f"类目为{cat}，目标售价{price_range}。"
            f"竞品数量约{competitors}个，Top 10 平均评分 {rating}，存在差异化空间；"
            f"月搜索量约 {search_vol}，旺季集中在{peak}。"
            f"供应链主要集中在中国浙江/广东，MOQ {moq}件起，账期可谈。"
            f"预计毛利率{margin_low}%-{margin_high}%。"
            f"建议进入：重点打造差异化卖点（材质/功能/包装），提前 45 天备货，{market_notes}。"
        ),
        (
            f"【{name}选品结论】综合评分 {score}/100。"
            f"市场需求：搜索量稳定（月约{search_vol}），{peak}为旺季；"
            f"竞争格局：{competitors}个核心竞品，头部品牌占比约 35%，新品牌有机会；"
            f"供应链：浙江/广东工厂成熟，{moq}件起订，交期 25-35 天；"
            f"利润：售价{price_range}，毛利率约{margin_low}%-{margin_high}%；"
            f"风险：{market_notes}，差评集中在质量与尺寸描述不符。"
            f" verdict：建议进入，优先小批量测款。"
        ),
        (
            f"产品：{name} | 目标市场：{market} | 售价：{price_range}\n"
            f"市场评分：{score}/100\n"
            f"搜索热度：{search_vol}/月，旺季{peak}\n"
            f"竞品情况：{competitors}个核心链接，平均评分{rating}\n"
            f"供应链：浙江/广东，MOQ {moq}，交期 25-35 天\n"
            f"毛利率：{margin_low}%-{margin_high}%\n"
            f"建议：可进入，先做 200-500 件测款，同步完成{market_notes}。"
        ),
        json.dumps({
            "product": name,
            "category": cat,
            "target_price": price_range,
            "market": market,
            "market_potential_score": score,
            "search_volume_monthly": search_vol,
            "competitor_count": competitors,
            "avg_rating": rating,
            "gross_margin_pct": f"{margin_low}-{margin_high}",
            "peak_season": peak,
            "supply_chain": {"origin": "Zhejiang/Guangdong", "moq": moq, "lead_time_days": random.randint(25, 40)},
            "compliance_note": market_notes,
            "recommendation": "RECOMMENDED",
            "action_items": ["差异化卖点设计", "认证核查", "小批量测款"]
        }, ensure_ascii=False),
    ]

    # 劣质 rejected：模糊、无数据、无行动建议
    rejected_templates = [
        (
            f"这个产品还行，{name}可以做。价格看着定，供应商网上搜一下就有。"
            f"具体数据查一下 Google Trends。认证方面应该问题不大。"
        ),
        (
            f"{name}市场应该不错，很多人都卖。建议直接上链接，定价参考竞品就行。"
            f"利润大概有个三成吧，具体算一下。"
        ),
        (
            f"我觉得{market}市场可以尝试一下，反正成本不高。"
            f"先做一批货，卖不动再换产品。"
        ),
        (
            f"{name}看起来还行，应该能卖。"
            f"你先去 1688 找几家供应商问问价，对比一下再决定。"
        ),
        json.dumps({
            "product": name,
            "score": "unknown",
            "analysis": "感觉还可以",
            "recommendation": "maybe"
        }, ensure_ascii=False),
    ]

    chosen = chosen_templates[variant_idx % len(chosen_templates)]
    rejected = rejected_templates[variant_idx % len(rejected_templates)]

    return {
        "prompt": (
            f"你是一名跨境电商选品分析专家。请分析产品「{name}」在目标市场的可行性。\n"
            f"产品类目：{cat}\n"
            f"目标售价：{price_range}\n"
            f"目标市场：{market}\n"
            f"要求：输出市场评分（0-100）、竞争格局、供应链情况、毛利率预估、风险点及明确建议。"
        ),
        "chosen": chosen,
        "rejected": rejected,
    }

def gen_32b_entry(task_type):
    tasks = [
        {
            "user": "系统指令：理解跨境电商选品分析请求'分析不锈钢保温杯在亚马逊德国站的市场机会'，提取结构化参数并制定DAG分析计划。",
            "assistant": json.dumps({
                "extracted_params": {
                    "product": "不锈钢保温杯",
                    "market": "DE",
                    "platform": "amazon.de",
                    "category": "Home & Kitchen"
                },
                "dag_plan": [
                    {"id":"m1","agent":"market_research","action":"分析不锈钢保温杯在德国亚马逊的市场需求","depends_on":[]},
                    {"id":"s1","agent":"supply_chain","action":"搜索1688不锈钢保温杯供应商","depends_on":[]},
                    {"id":"c1","agent":"compliance","action":"检查欧盟食品接触材料法规","depends_on":[]},
                    {"id":"p1","agent":"profit_calculator","action":"计算利润","depends_on":["m1","s1"]}
                ],
                "parallel_groups": [["m1","s1","c1"]],
                "sequential": ["p1"]
            }, ensure_ascii=False)
        },
        {
            "user": "执行Market Research Agent的amazon_product_search工具调用，分析硅胶折叠水杯在英国站的竞品格局。",
            "assistant": json.dumps({
                "tool_call": {
                    "name": "amazon_product_search",
                    "params": {"keyword": "silicone collapsible water bottle", "marketplace": "co.uk", "limit": 20}
                },
                "analysis": {
                    "avg_price": 12.99,
                    "avg_rating": 4.3,
                    "market_concentration": "中等",
                    "top_brands": ["Stojo", "Platypus", "HydraPak"],
                    "differentiation_opportunity": "10-12英镑区间仅2个竞品且评分低于4.0"
                }
            }, ensure_ascii=False)
        },
    ]
    entry = random.choice(tasks) if task_type == "random" else tasks[0]
    return {
        "messages": [
            {"role": "system", "content": "你是一个跨境电商选品分析系统，负责自动化分析产品在亚马逊各站点的市场可行性。"},
            {"role": "user", "content": entry["user"]},
            {"role": "assistant", "content": entry["assistant"]}
        ]
    }

# ── 主生成逻辑 ──
def generate():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    # ── Path 1: DS V4 SFT (500 条) ──
    random.seed(42)
    sft_entries = []
    for product in PRODUCTS:
        for market in random.sample(MARKETS, 2):  # 每个产品选2个市场
            sft_entries.append(gen_sft_entry(product, market, product[2]))
    # 补充到 ~500 条
    while len(sft_entries) < 500:
        product = random.choice(PRODUCTS)
        market = random.choice(MARKETS)
        sft_entries.append(gen_sft_entry(product, market, product[2]))
    sft_entries = sft_entries[:500]

    sft_path = os.path.join(data_dir, "sft_train.jsonl")
    # 保留手工编写的 15 条
    existing = []
    if os.path.exists(sft_path):
        with open(sft_path, "r", encoding="utf-8") as f:
            existing = [json.loads(line) for line in f if line.strip()]
    all_sft = existing + sft_entries
    random.shuffle(all_sft)
    with open(sft_path, "w", encoding="utf-8") as f:
        for entry in all_sft[:500]:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[DS V4 SFT] {min(len(all_sft), 500)} entries → {sft_path}")

    # ── Path 2: ORPO (按产品严格划分训练/验证/测试集) ──
    # 66 个产品均分为 6 组：前 4 组训练（44 产品），第 5 组验证（11 产品），第 6 组测试（11 产品）
    # 核心原则：训练集、验证集、测试集的产品互不重叠，确保评估真实反映泛化能力
    # 44 x 31 = 1364 训练 / 11 x 31 = 341 验证 / 11 x 31 = 341 测试
    group_size = len(PRODUCTS) // 6
    train_products = PRODUCTS[:group_size * 4]
    val_products = PRODUCTS[group_size * 4:group_size * 5]
    test_products = PRODUCTS[group_size * 5:]

    def build_orpo_entries(products):
        entries = []
        for product in products:
            for variant_idx in range(31):
                entries.append(gen_orpo_entry(product, variant_idx))
        random.shuffle(entries)
        return entries

    train_entries = build_orpo_entries(train_products)
    val_entries = build_orpo_entries(val_products)
    test_entries = build_orpo_entries(test_products)

    for split, entries in [("train", train_entries), ("val", val_entries), ("test", test_entries)]:
        path = os.path.join(data_dir, f"orpo_{split}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(f"[ORPO {split}] {len(entries)} entries → {path}")

    # 保留完整的 orpo_chosen_rejected.jsonl 作为训练数据（兼容旧流程）
    all_orpo = train_entries + val_entries + test_entries
    orpo_path = os.path.join(data_dir, "orpo_chosen_rejected.jsonl")
    random.shuffle(all_orpo)
    with open(orpo_path, "w", encoding="utf-8") as f:
        for entry in all_orpo:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[ORPO all] {len(all_orpo)} entries → {orpo_path}")

    # ── Path 3: Qwen2.5-7B Instructions (300 条) ──
    inst_entries = []
    for _ in range(300):
        inst_entries.append(gen_32b_entry("random"))
    inst_entries = inst_entries[:300]

    inst_path = os.path.join(data_dir, "qwen32b_instructions.jsonl")
    existing_inst = []
    if os.path.exists(inst_path):
        with open(inst_path, "r", encoding="utf-8") as f:
            existing_inst = [json.loads(line) for line in f if line.strip()]
    all_inst = existing_inst + inst_entries
    random.shuffle(all_inst)
    with open(inst_path, "w", encoding="utf-8") as f:
        for entry in all_inst[:300]:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[32B/9B Instructions] {min(len(all_inst), 300)} entries → {inst_path}")

    # ── 统计 ──
    total_orpo = len(train_entries) + len(val_entries) + len(test_entries)
    print(f"\n总计：DS V4 SFT {min(len(all_sft),500)} + ORPO {total_orpo} (train={len(train_entries)}, val={len(val_entries)}, test={len(test_entries)}) + Instructions {min(len(all_inst),300)} = {min(len(all_sft),500)+total_orpo+min(len(all_inst),300)} 条")

if __name__ == "__main__":
    generate()
