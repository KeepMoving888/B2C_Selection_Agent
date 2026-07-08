#!/usr/bin/env python3
"""
微调数据集质量检查脚本

运行：python finetune/check_dataset.py

输出：
  - 样本总数 / 字段完整性
  - prompt / chosen / rejected 长度分布
  - 重复 prompt 数量
  - 偏好对质量信号（长度比、内容差异）
  - 每个产品类别的分布
  - 是否能满足 ORPO 高质量微调要求
"""

import json
import re
import statistics
from collections import Counter
from pathlib import Path


def _percentile(arr, p):
    """无需 numpy 的百分位实现。"""
    if not arr:
        return 0.0
    s = sorted(arr)
    k = (len(s) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    return s[f] + (s[c] - s[f]) * (k - f)


def load_orpo_dataset(path: Path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"[WARN] JSON parse error: {e}")
    return records


def token_len_approx(text: str) -> int:
    """粗略中文字符 + 英文单词 token 估算"""
    cn = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[a-zA-Z0-9]+", text))
    return int(cn + en * 1.3)


def extract_product_name(query: str) -> str:
    """从产品查询中提取产品名（简化）"""
    # 匹配「产品「xxx」」或「分析xxx的市场」
    for pattern in [r"产品「(.+?)」", r"分析(.+?)的市场", r"分析(.+?)在"]:
        m = re.search(pattern, query)
        if m:
            return m.group(1).strip()
    return "unknown"


def main():
    data_file = Path(__file__).resolve().parent / "data" / "orpo_chosen_rejected.jsonl"
    if not data_file.exists():
        print(f"[ERROR] Dataset not found: {data_file}")
        return

    records = load_orpo_dataset(data_file)
    total = len(records)
    print(f"[Dataset] Loaded {total} records from {data_file}\n")

    # 字段完整性
    valid = 0
    missing_fields = []
    for i, r in enumerate(records):
        fields_ok = all(k in r and r[k] for k in ("prompt", "chosen", "rejected"))
        if fields_ok:
            valid += 1
        else:
            missing_fields.append(i)
    print(f"字段完整性: {valid}/{total} ({valid/total*100:.1f}%)")
    if missing_fields:
        print(f"  缺失字段样本索引: {missing_fields[:10]}...")

    # 长度统计
    prompt_lens = [token_len_approx(r["prompt"]) for r in records]
    chosen_lens = [token_len_approx(r["chosen"]) for r in records]
    rejected_lens = [token_len_approx(r["rejected"]) for r in records]

    def stats(arr):
        return {
            "mean": round(statistics.mean(arr), 1),
            "median": round(statistics.median(arr), 1),
            "min": min(arr),
            "max": max(arr),
            "p95": round(_percentile(arr, 95), 1),
            "p99": round(_percentile(arr, 99), 1),
        }

    print("\n长度统计（近似 token 数）:")
    print(f"  prompt:    {stats(prompt_lens)}")
    print(f"  chosen:    {stats(chosen_lens)}")
    print(f"  rejected:  {stats(rejected_lens)}")

    # chosen 比 rejected 长多少
    longer_chosen = sum(1 for c, r in zip(chosen_lens, rejected_lens) if c > r)
    print(f"\nchosen 长度 > rejected 的样本: {longer_chosen}/{total} ({longer_chosen/total*100:.1f}%)")

    # 重复 prompt（ORPO 中同一 prompt 可对应不同 chosen/rejected，因此也统计完整 triple 重复）
    queries = [r["prompt"] for r in records]
    dup_counts = Counter(queries)
    duplicates = {q: c for q, c in dup_counts.items() if c > 1}
    unique_triples = Counter(
        (r["prompt"], r["chosen"], r["rejected"]) for r in records
    )
    exact_dup_triples = {t: c for t, c in unique_triples.items() if c > 1}
    print(f"\n重复 prompt 数量: {len(duplicates)} 个，涉及 {sum(duplicates.values())} 条样本")
    print(f"完全重复的 (prompt, chosen, rejected) 数量: {len(exact_dup_triples)} 组")

    # 产品分布
    products = [extract_product_name(q) for q in queries]
    product_counts = Counter(products)
    print(f"\n产品类别分布（Top 10）:")
    for name, count in product_counts.most_common(10):
        print(f"  {name}: {count}")

    # 质量判断
    print("\n质量评估:")
    if total >= 1500:
        print("  ✅ 样本量 >= 1500，满足 ORPO 高质量微调需求")
    elif total >= 500:
        print("  ⚠️ 样本量 >= 500 但 < 1500，可训练但建议补充至 1500-2000 条")
    else:
        print(f"  ⚠️ 样本量 {total} < 500，建议补充至 1500-2000 条")

    if statistics.median(prompt_lens) <= 50:
        print("  ⚠️ prompt 中位数过短，可能缺乏任务描述")
    else:
        print("  ✅ prompt 长度合理")

    if longer_chosen / total >= 0.7:
        print("  ✅ chosen 普遍比 rejected 长，偏好信号明确")
    else:
        print("  ⚠️ chosen/rejected 长度差异不够明显，偏好信号可能不足")

    if len(exact_dup_triples) > total * 0.05:
        print(f"  ⚠️ 完全重复样本占比 > 5%，训练时可能过拟合")
    else:
        print("  ✅ 完全重复率可控（同一 prompt 对应不同 chosen/rejected 是正常 ORPO 格式）")

    print("\n结论:")
    if total >= 1500 and valid == total and longer_chosen / total >= 0.7 and len(exact_dup_triples) <= total * 0.05:
        print("  数据集满足高质量 ORPO 微调要求，可以开始训练。")
    else:
        print("  数据集存在改进空间，建议先修复上述问题再训练。")


if __name__ == "__main__":
    main()
