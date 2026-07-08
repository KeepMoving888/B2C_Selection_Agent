#!/usr/bin/env python3
"""
deploy/verify_model_integrity.py
==============================
校验 E:\models 中关键模型文件的完整性。

检查项：
  - model.safetensors.index.json 中引用的每个 shard 文件存在且非空
  - tokenizer / config 等关键元数据文件存在
  - 统计每个模型目录总大小

输出：
  - output/model_integrity/integrity_report.json
  - output/model_integrity/integrity_report.md
"""

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODELS = {
    "qwen/Qwen2.5-7B": Path("E:/models/qwen/Qwen2.5-7B"),
    "qwen/Qwen3.5-9B": Path("E:/models/qwen/Qwen3.5-9B"),
    "qwen2.5-7b-ecommerce-merged": Path("E:/models/qwen2.5-7b-ecommerce-merged"),
    "qwen2.5-7b-ecommerce-awq-v3": Path("E:/models/qwen2.5-7b-ecommerce-awq-v3"),
    "qwen2.5-7b-orpo-adapter": Path("E:/models/qwen2.5-7b-orpo-adapter"),
}

REQUIRED_FILES = ["config.json", "tokenizer_config.json", "tokenizer.json"]
ADAPTER_REQUIRED_FILES = ["adapter_config.json", "adapter_model.safetensors"]
OUTPUT_DIR = Path("output/model_integrity")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


EXPECTED_SIZE_GB = {
    "qwen/Qwen2.5-7B": 14.0,
    "qwen/Qwen3.5-9B": 17.5,
    "qwen2.5-7b-ecommerce-merged": 14.0,
    "qwen2.5-7b-ecommerce-awq-v3": 5.0,
    "qwen2.5-7b-orpo-adapter": 0.07,
}


def md5_file(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def check_model(name: str, model_dir: Path) -> dict:
    result = {
        "name": name,
        "path": str(model_dir),
        "exists": model_dir.exists(),
        "shards": [],
        "missing_shards": [],
        "empty_shards": [],
        "total_size_gb": 0.0,
        "expected_size_gb": EXPECTED_SIZE_GB.get(name),
        "size_status": "unknown",
        "required_files_missing": [],
        "integrity": True,
    }

    if not model_dir.exists():
        result["integrity"] = False
        return result

    # 关键元数据文件：adapter 与普通模型区分
    is_adapter = "adapter" in name.lower()
    files_to_check = ADAPTER_REQUIRED_FILES if is_adapter else REQUIRED_FILES
    for fname in files_to_check:
        fp = model_dir / fname
        if not fp.exists():
            result["required_files_missing"].append(fname)
            result["integrity"] = False

    # safetensors shards
    index_file = model_dir / "model.safetensors.index.json"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)
        weight_map = index.get("weight_map", {})
        seen = set()
        for _, shard_name in weight_map.items():
            if shard_name in seen:
                continue
            seen.add(shard_name)
            shard_path = model_dir / shard_name
            shard_ok = shard_path.exists() and shard_path.stat().st_size > 0
            size_mb = shard_path.stat().st_size / (1024 ** 2) if shard_path.exists() else 0
            result["shards"].append({
                "file": shard_name,
                "exists": shard_path.exists(),
                "size_mb": round(size_mb, 2),
            })
            if not shard_path.exists():
                result["missing_shards"].append(shard_name)
                result["integrity"] = False
            elif shard_path.stat().st_size == 0:
                result["empty_shards"].append(shard_name)
                result["integrity"] = False

    # single-file models (adapter)
    for single in ["adapter_model.safetensors", "model.safetensors", "pytorch_model.bin"]:
        fp = model_dir / single
        if fp.exists():
            result["shards"].append({
                "file": single,
                "exists": True,
                "size_mb": round(fp.stat().st_size / (1024 ** 2), 2),
            })

    total_bytes = sum(
        (model_dir / s["file"]).stat().st_size
        for s in result["shards"] if (model_dir / s["file"]).exists()
    )
    result["total_size_gb"] = round(total_bytes / (1024 ** 3), 2)

    # 大小校验：与期望值偏差超过 30% 视为异常
    expected = EXPECTED_SIZE_GB.get(name)
    if expected and expected > 0:
        ratio = result["total_size_gb"] / expected
        if 0.7 <= ratio <= 1.3:
            result["size_status"] = "normal"
        else:
            result["size_status"] = f"abnormal (expected ~{expected} GB, got {result['total_size_gb']} GB)"
            result["integrity"] = False
    return result


def generate_report(results: list[dict]):
    # JSON
    json_path = OUTPUT_DIR / "integrity_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Markdown
    md_path = OUTPUT_DIR / "integrity_report.md"
    lines = [
        "# E:\\models 模型完整性校验报告",
        "",
        "| 模型 | 路径 | 总大小(GB) | 期望大小(GB) | 大小状态 | 元数据文件 | Shard 文件 | 完整性 |",
        "|------|------|-----------|-------------|---------|-----------|-----------|--------|",
    ]
    for r in results:
        meta_ok = "完整" if not r["required_files_missing"] else f"缺失 {', '.join(r['required_files_missing'])}"
        shard_ok = "完整" if not r["missing_shards"] and not r["empty_shards"] else "不完整"
        size_status = r["size_status"] if r["size_status"] != "unknown" else "-"
        lines.append(
            f"| {r['name']} | {r['path']} | {r['total_size_gb']} | {r['expected_size_gb'] or '-'} | {size_status} | {meta_ok} | {shard_ok} | "
            f"{'通过' if r['integrity'] else '未通过'} |"
        )

    lines.extend([
        "",
        "## 详细 Shard 列表",
        "",
    ])
    for r in results:
        lines.append(f"### {r['name']}")
        for s in r["shards"]:
            lines.append(f"- {s['file']}: {s['size_mb']} MB, exists={s['exists']}")
        if r["missing_shards"]:
            lines.append(f"- 缺失: {', '.join(r['missing_shards'])}")
        if r["empty_shards"]:
            lines.append(f"- 空文件: {', '.join(r['empty_shards'])}")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Chart: model sizes
    names = [r["name"] for r in results]
    sizes = [r["total_size_gb"] for r in results]
    colors = ["#22c55e" if r["integrity"] else "#ef4444" for r in results]

    plt.figure(figsize=(10, 6))
    bars = plt.barh(names, sizes, color=colors)
    for bar, val in zip(bars, sizes):
        plt.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                 f"{val:.2f} GB", va="center", fontsize=10)
    plt.xlabel("Size (GB)", fontsize=12)
    plt.title("E:\\models 模型大小与完整性", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_model_size_integrity.png", dpi=150)
    plt.close()

    print(f"[Verify] Report saved: {json_path}, {md_path}, {OUTPUT_DIR / '01_model_size_integrity.png'}")


def main():
    results = []
    for name, model_dir in MODELS.items():
        print(f"[Verify] Checking {name} ...", flush=True)
        results.append(check_model(name, model_dir))

    all_ok = all(r["integrity"] for r in results)
    print(f"[Verify] All models integrity: {'PASS' if all_ok else 'FAIL'}", flush=True)
    generate_report(results)


if __name__ == "__main__":
    main()
