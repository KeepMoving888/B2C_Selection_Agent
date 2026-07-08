# ============================================================
# scripts/setup_feishu.py — 飞书生态初始化
#
# 用途：
#   1. 创建/校验「行业选品报告」知识库（Wiki Space）
#   2. 在指定 Base 表中创建选品报告归档字段，并优化展示格式
#   3. 把 wiki_space_id 自动写回 .env
#
# 运行：
#   python scripts/setup_feishu.py
# ============================================================

import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from feishu.integration import FeishuConfig, FeishuIntegration


def update_env(key: str, value: str) -> None:
    """更新 .env 文件中的指定键。"""
    env_path = PROJECT_ROOT / ".env"
    content = env_path.read_text(encoding="utf-8")
    pattern = rf"^{re.escape(key)}=.*$"
    new_line = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
    else:
        content += f"\n{new_line}\n"
    env_path.write_text(content, encoding="utf-8")


def _is_placeholder(value: str) -> bool:
    return not value or value.startswith("your-") or "xxxxxxxx" in value


def main():
    config = FeishuConfig()
    feishu = FeishuIntegration(config)

    print("=" * 60)
    print("飞书生态初始化")
    print("=" * 60)

    # 0. 个人授权 token 检查
    print("\n[0/3] 检查个人授权 token ...")
    if config.user_access_token:
        print("   ✅ 已配置 FEISHU_USER_ACCESS_TOKEN，发布文档将以个人名义创建。")
    else:
        print("   ⚠️ 未配置 FEISHU_USER_ACCESS_TOKEN。")
        print("      文档将以应用机器人名义创建；如需以个人名义创建并直接编辑，请：")
        print("      1. 通过飞书 OAuth 授权获取 user_access_token（有效期约 2h）；")
        print("      2. 将其填入 .env 的 FEISHU_USER_ACCESS_TOKEN=u-xxxxxx；")
        print("      3. 重新运行发布脚本。")

    # 1. 创建/校验知识库
    print("\n[1/3] 创建/校验知识库 ...")
    wiki_space_id = config.wiki_space_id
    if not wiki_space_id or wiki_space_id.startswith("your-"):
        print("   正在创建知识库：行业选品报告库 ...")
        try:
            wiki_space_id = feishu.create_wiki_space(
                name="行业选品报告库",
                description="按行业归档 Multi-Agent 智能选品系统生成的选品报告，支持后续检索与复盘。",
            )
            if wiki_space_id:
                update_env("FEISHU_WIKI_SPACE_ID", wiki_space_id)
                print(f"   ✅ 知识库创建成功，space_id: {wiki_space_id}")
                print("      已自动写入 .env 的 FEISHU_WIKI_SPACE_ID")
            else:
                print("   ❌ 知识库创建失败，返回为空")
        except Exception as e:
            print(f"   ❌ 知识库创建失败: {e}")
            print("\n   解决步骤：")
            print("   1. 进入飞书开放平台 https://open.feishu.cn/app/")
            print("   2. 找到本应用，进入「权限管理」")
            print("   3. 开通 wiki:wiki / wiki:space 相关读写权限")
            print("   4. 重新发布应用并在企业管理后台「重新授权」")
            print("   5. 如需手动创建知识库，可将 space_token 写入 .env 的 FEISHU_WIKI_SPACE_ID")
            wiki_space_id = None
    else:
        print(f"   知识库已配置，space_token: {wiki_space_id}")
        try:
            numeric_space_id = feishu.get_wiki_space_id(wiki_space_id)
            if numeric_space_id:
                print(f"   ✅ 应用可访问该知识库（space_id: {numeric_space_id}）")
            else:
                print("   ⚠️ 应用无法通过 OpenAPI 读取该知识库列表，将尝试直接创建节点。")
                print("      若仍失败，文档会兜底到普通文档空间。请检查：")
                print("      - 权限管理是否勾选 wiki:wiki:read / wiki:space:read / wiki:space:write；")
                print("      - 企业管理后台是否已「重新授权」该应用；")
                print("      - 应用是否被添加为该知识库成员。")
        except Exception as e:
            print(f"   ⚠️ 校验知识库访问失败: {e}")
            print("      文档将尝试创建在普通文档空间作为兜底。")

    # 2. 确保 Base 字段
    print("\n[2/3] 检查并创建 Base 多维表字段 ...")
    try:
        field_map = feishu.ensure_base_fields(config.table_id)

        # 确保数字字段展示格式为业务友好格式
        format_configs = [
            ("预估毛利率", "number", {"formatter": "0.00%"}),
            ("综合评分", "number", {"formatter": "0.0"}),
            ("竞品均价 USD", "number", {"formatter": "0.00"}),
            ("目标月销售额 USD", "number", {"formatter": "0.00"}),
            ("最低 MOQ", "number", {"formatter": "0"}),
            ("供应商数量", "number", {"formatter": "0"}),
            ("盈亏平衡销量", "number", {"formatter": "0"}),
        ]
        for name, ftype, cfg in format_configs:
            if name in field_map:
                try:
                    feishu.update_base_field(
                        config.table_id,
                        field_map[name],
                        name,
                        ftype,
                        cfg,
                    )
                    print(f"   🎨 已更新 '{name}' 展示格式")
                except Exception as ue:
                    print(f"   ⚠️ 更新 '{name}' 展示格式失败: {ue}")

        # 重命名主列（第一列）为「报告编号」
        print("\n[3/3] 优化多维表主列与清理冗余字段 ...")
        fields_snapshot = feishu.list_base_fields(config.table_id)
        primary_field_id = None
        primary_field_name = None
        for f in fields_snapshot:
            if f.get("is_primary"):
                primary_field_id = f.get("field_id")
                primary_field_name = f.get("field_name")
                break

        # 若主列还不是「报告编号」，先删除可能存在的同名普通字段，再重命名主列
        if primary_field_id and primary_field_name != "报告编号":
            for f in fields_snapshot:
                if f.get("field_name") == "报告编号" and not f.get("is_primary"):
                    try:
                        feishu.delete_base_field(config.table_id, f.get("field_id"))
                        print("   🗑️  已删除与主列重名的普通字段「报告编号」")
                    except Exception as e:
                        print(f"   ⚠️ 删除重名字段失败: {e}")
                    break
            try:
                feishu.rename_base_field(config.table_id, primary_field_id, "报告编号", "text")
                print("   ✅ 已将 Base 主列（第一列）重命名为「报告编号」")
            except Exception as e:
                print(f"   ⚠️ 重命名主列失败: {e}")
        elif primary_field_id:
            print("   ✅ 主列已是「报告编号」")

        # 清理历史遗留的空字段（如旧版创建的 currency 字段）
        obsolete_names = {"文本", "竞品均价", "目标月销售额"}
        for f in feishu.list_base_fields(config.table_id):
            fname = f.get("field_name", "")
            fid = f.get("field_id")
            if fname in obsolete_names and fid:
                try:
                    feishu.delete_base_field(config.table_id, fid)
                    print(f"   🗑️  已删除冗余字段 '{fname}'")
                except Exception as e:
                    print(f"   ⚠️ 删除冗余字段 '{fname}' 失败: {e}")

        print(f"\n✅ 字段准备完成，共 {len(field_map)} 个业务字段。")
        for name, fid in field_map.items():
            print(f"   - {name}: {fid}")
    except Exception as e:
        print(f"❌ Base 字段初始化失败: {e}")
        print("\n   解决步骤：")
        print("   1. 进入飞书开放平台 https://open.feishu.cn/app/cli_aaac81afb0389cd5/auth")
        print("   2. 开通以下权限：")
        print("      - bitable:app 或 bitable:app:readonly")
        print("      - base:field:read / base:field:write")
        print("      - base:record:read / base:record:write")
        print("      - drive:file:write （上传 JSON 附件）")
        print("      - docx:document:write （创建文档）")
        print("      - wiki:space:write / wiki:wiki:write （创建知识库）")
        print("   3. 重新发布应用并授权")
        return

    print("\n" + "=" * 60)
    print("初始化完成，可运行：python scripts/publish_to_feishu.py <report.json>")
    print("=" * 60)


if __name__ == "__main__":
    main()
