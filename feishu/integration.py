# ============================================================
# feishu/integration.py — 飞书生态闭环集成
#
# 完整闭环链路：
#   飞书消息触发 → Agent 分析 → 中间结果写入 Base
#   → 飞书审批 → 通过后生成 Docx 报告 → 归档知识库 → 消息通知
#
# 认证方式：通过 tenant_access_token (bot 身份) 调用 OpenAPI。
# app_id 和 app_secret 从环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET 读取。
# 文档写入需将应用添加为飞书文档的协作者。
# ============================================================

from __future__ import annotations

import json
import mimetypes
import time
import os
import urllib.request
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FeishuConfig:
    """飞书应用配置"""
    app_id: str = ""
    app_secret: str = ""
    base_token: str = ""
    table_id: str = ""
    wiki_space_id: str = ""
    approval_code: str = ""
    report_folder_token: str = ""
    user_open_id: str = ""
    user_member_type: str = "openid"  # openid | email | userid
    user_access_token: str = ""  # 个人授权 token，用于以个人名义创建文档

    def __post_init__(self):
        self.app_id = self.app_id or os.environ.get("FEISHU_APP_ID", "")
        self.app_secret = self.app_secret or os.environ.get("FEISHU_APP_SECRET", "")
        self.base_token = self.base_token or os.environ.get("FEISHU_BASE_TOKEN", "")
        self.table_id = self.table_id or os.environ.get("FEISHU_TABLE_ID", "")
        self.wiki_space_id = self.wiki_space_id or os.environ.get("FEISHU_WIKI_SPACE_ID", "")
        self.user_open_id = self.user_open_id or os.environ.get("FEISHU_USER_OPEN_ID", "")
        self.user_member_type = self.user_member_type or os.environ.get("FEISHU_USER_MEMBER_TYPE", "openid")
        self.user_access_token = self.user_access_token or os.environ.get("FEISHU_USER_ACCESS_TOKEN", "")


class FeishuIntegration:
    """
    飞书生态集成层。

    设计价值：
    1. 将选品能力嵌入飞书工作流，用户无需离开飞书平台
    2. 中间产物可追溯：Base 中记录每个 Agent 的分析结果
    3. 审批流保证质量：报告必须通过审批才能发布
    4. 知识沉淀可复用：历史选品报告自动归入知识库供后续检索

    实现方式：
    通过 tenant_access_token 调用飞书 OpenAPI，
    支持 docx、base、wiki、im 等模块。
    """

    AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal"
    DOCX_URL = "https://open.feishu.cn/open-apis/docx/v1/documents"

    def __init__(self, config: FeishuConfig = None):
        self.config = config or FeishuConfig()
        self._token: Optional[str] = None
        self._token_expiry: float = 0

    # ── 认证 ────────────────────────────────────────────

    def _get_token(self) -> str:
        """获取或刷新 tenant_access_token（有效期 2h）"""
        if self._token and time.time() < self._token_expiry:
            return self._token
        data = json.dumps({
            "app_id": self.config.app_id,
            "app_secret": self.config.app_secret,
        }).encode()
        req = urllib.request.Request(self.AUTH_URL, data=data,
                                     headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        self._token = resp["tenant_access_token"]
        self._token_expiry = time.time() + resp.get("expire", 7200) - 300
        return self._token

    def _api(self, method: str, path: str, body: Dict = None,
             extra_headers: Dict = None,
             user_token: bool = False,
             allow_fallback: bool = True) -> Dict:
        """调用飞书 OpenAPI。user_token=True 时使用个人 access_token。
        若个人 token 失效且 allow_fallback=True，则自动回退到 tenant_access_token。
        """
        url = f"https://open.feishu.cn/open-apis{path}"
        data = json.dumps(body, ensure_ascii=False).encode() if body else None
        use_user = user_token and bool(self.config.user_access_token)
        tokens = []
        if use_user:
            tokens.append(("user", self.config.user_access_token))
        tokens.append(("tenant", self._get_token()))

        last_error = None
        for token_type, token in tokens:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            if extra_headers:
                headers.update(extra_headers)
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                return json.loads(urllib.request.urlopen(req, timeout=30).read())
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8", errors="ignore")
                last_error = RuntimeError(f"Feishu API error {e.code}: {error_body}")
                # 个人 token 过期/无效，且允许回退时，继续尝试 tenant token
                if token_type == "user" and allow_fallback:
                    if "99991677" in error_body or "99991663" in error_body:
                        print("[WARN] FEISHU_USER_ACCESS_TOKEN 已过期或无效，回退到应用 token 创建文档。")
                        continue
                raise last_error
        raise last_error

    # ── 文档操作 ────────────────────────────────────────

    def create_doc(self, title: str, content_blocks: List[Dict],
                   wiki_space_id: Optional[str] = None,
                   use_user_token: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """创建文档并写入结构化块。返回 (文档 URL, 文档 token)。

        use_user_token=True 时使用 FEISHU_USER_ACCESS_TOKEN，文档将以个人名义创建。
        """
        user_token = use_user_token and bool(self.config.user_access_token)
        # 若以个人身份创建，遇到 401 时不回退到应用 token，避免文档跑到 bot 名下
        allow_fallback = not user_token

        wiki_token = None
        doc_id = None

        if wiki_space_id:
            # 创建节点需要数字 space_id；若传入 space_token 则先转换
            space_id = wiki_space_id
            if not str(space_id).isdigit():
                space_id = self.get_wiki_space_id(space_token=space_id)

            # 即便列表接口为空，仍尝试用用户配置的原始值创建一次节点
            # （某些企业租户下列表与写权限分离，直接写可能成功）
            candidates = [space_id, wiki_space_id] if not space_id else [space_id]
            wiki_err = None
            for sid in candidates:
                if not sid:
                    continue
                try:
                    resp = self._api("POST", f"/wiki/v2/spaces/{sid}/nodes", {
                        "node_type": "origin",
                        "obj_type": "docx",
                        "title": title,
                    }, user_token=user_token, allow_fallback=allow_fallback)
                    doc_id = resp["data"]["node"]["obj_token"]
                    wiki_token = resp["data"]["node"]["node_token"]
                    break
                except RuntimeError as e:
                    wiki_err = e
                    # 仅当权限/参数错误时继续尝试下一个候选；其它错误直接抛
                    if not ("400" in str(e) or "403" in str(e) or "99991663" in str(e)):
                        raise

            if not doc_id:
                print("[WARN] 无法在知识库中创建文档节点，将兜底到普通文档空间。")
                print("      排查建议（已开通 wiki 权限但仍失败时）：")
                print("      1. 飞书开放平台「权限管理」中确认已勾选：")
                print("         - wiki:wiki:read / wiki:wiki（读取知识库列表）")
                print("         - wiki:space:read / wiki:space（读取空间）")
                print("         - wiki:space:write / wiki:wiki:write（创建节点）")
                print("      2. 在企业管理后台「应用管理」对该应用点击「重新授权」；")
                print("      3. 将应用添加为该知识库成员（知识库设置-成员管理-添加应用）；")
                print("      4. 开通权限后 tenant_access_token 缓存约 2h，可重启或等待缓存过期。")
                if wiki_err:
                    print(f"      最后错误：{wiki_err}")
                resp = self._api("POST", "/docx/v1/documents", {"title": title},
                                 user_token=user_token, allow_fallback=allow_fallback)
                doc_id = resp["data"]["document"]["document_id"]
        else:
            resp = self._api("POST", "/docx/v1/documents", {"title": title},
                             user_token=user_token, allow_fallback=allow_fallback)
            doc_id = resp["data"]["document"]["document_id"]

        for batch in self._chunk(content_blocks, 50):
            self._api("POST", f"/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
                      {"children": batch}, user_token=user_token, allow_fallback=allow_fallback)

        if wiki_token:
            return f"https://my.feishu.cn/wiki/{wiki_token}", doc_id
        return f"https://my.feishu.cn/docx/{doc_id}", doc_id

    def append_text(self, doc_token: str, text: str) -> bool:
        """向文档追加文本块"""
        self._api("POST",
                  f"/docx/v1/documents/{doc_token}/blocks/{doc_token}/children",
                  {"children": [{"block_type": 2, "text": {
                      "elements": [{"text_run": {"content": text}}],
                      "style": {}}}]}
                  )
        return True

    def transfer_doc_owner(self, doc_token: str, member_id: str,
                           member_type: str = "openid",
                           remove_old_owner: bool = False) -> bool:
        """转移云文档所有者到指定用户/邮箱/userid。"""
        self._api("POST",
                  f"/drive/v1/permissions/{doc_token}/members/transfer_owner?type=docx",
                  {
                      "member_type": member_type,
                      "member_id": member_id,
                      "remove_old_owner": remove_old_owner,
                  })
        return True

    def add_doc_member(self, doc_token: str, member_id: str,
                       member_type: str = "openid", perm: str = "edit") -> bool:
        """为云文档添加协作者（view/edit/full_access）。"""
        self._api("POST",
                  f"/drive/v1/permissions/{doc_token}/members?type=docx",
                  {
                      "member_type": member_type,
                      "member_id": member_id,
                      "perm": perm,
                  })
        return True

    # ── 知识库 ──────────────────────────────────────────

    def create_wiki_space(self, name: str, description: str = "") -> Optional[str]:
        """创建知识库，返回 space_id。"""
        try:
            resp = self._api("POST", "/wiki/v2/spaces", {
                "name": name,
                "description": description,
            })
            return resp.get("data", {}).get("space", {}).get("space_id")
        except RuntimeError as e:
            if "99991663" in str(e):
                raise RuntimeError(
                    "创建知识库失败：应用的 tenant_access_token 没有 wiki 写权限。\n"
                    "请在飞书开放平台「权限管理」中确认已勾选 wiki:space:write / wiki:wiki:write，"
                    "并重新发布应用、在企业管理后台「重新授权」该应用后重试。"
                ) from e
            raise

    def get_wiki_space_id(self, space_token: str = "") -> Optional[str]:
        """通过 space_token 获取数字 space_id（创建节点需要）。"""
        resp = self._api("GET", "/wiki/v2/spaces")
        items = resp.get("data", {}).get("items", [])
        if not items:
            print("[DEBUG] /wiki/v2/spaces 返回知识库列表为空。排查建议：")
            print("        1. 确认应用已开通 wiki:space:read / wiki:wiki:read 权限；")
            print("        2. 在企业管理后台「应用管理」里重新授权该应用；")
            print("        3. 若是手动创建的知识库，需将应用添加为知识库成员（管理员-成员管理-添加应用）。")
            return None
        matched = None
        for space in items:
            if space.get("space_token") == space_token or str(space.get("space_id")) == str(space_token):
                matched = space.get("space_id")
                break
        if not matched:
            names = [f"{s.get('name')}({s.get('space_token')})" for s in items[:5]]
            print(f"[DEBUG] 未找到知识库 {space_token}。应用可见知识库：{', '.join(names)}")
        return matched

    # ── Base 多维表 ─────────────────────────────────────

    BASE_FIELD_TYPES = {
        "text": 1,
        "number": 2,
        "single_select": 3,
        "multi_select": 4,
        "date": 5,
        "checkbox": 7,
        "attachment": 17,
        "url": 15,
        "currency": 22,
        "auto_number": 1001,
    }

    # 推荐字段配置（用于选品报告归档）
    DEFAULT_BASE_FIELDS = [
        {"field_name": "报告编号", "type": "text"},
        {"field_name": "关键词", "type": "text"},
        {"field_name": "行业", "type": "single_select", "property": {
            "options": [
                {"name": "pet", "color": 1}, {"name": "3c", "color": 2},
                {"name": "home", "color": 3}, {"name": "sports", "color": 4},
                {"name": "beauty", "color": 5}, {"name": "baby", "color": 6},
            ]
        }},
        {"field_name": "目标市场", "type": "single_select", "property": {
            "options": [{"name": "US", "color": 1}, {"name": "EU", "color": 2}, {"name": "JP", "color": 3}]
        }},
        {"field_name": "目标平台", "type": "single_select", "property": {
            "options": [{"name": "amazon", "color": 1}]
        }},
        {"field_name": "综合评分", "type": "number", "property": {"formatter": "0.0"}},
        {"field_name": "决策结论", "type": "single_select", "property": {
            "options": [
                {"name": "推荐进入", "color": 1},
                {"name": "可以考虑", "color": 3},
                {"name": "谨慎进入", "color": 0},
            ]
        }},
        {"field_name": "竞品均价 USD", "type": "number", "property": {"formatter": "0.00"}},
        {"field_name": "预估毛利率", "type": "number", "property": {"formatter": "0.00%"}},
        {"field_name": "最低 MOQ", "type": "number", "property": {"formatter": "0"}},
        {"field_name": "供应商数量", "type": "number", "property": {"formatter": "0"}},
        {"field_name": "TOP10 供应商", "type": "text"},
        {"field_name": "合规风险", "type": "single_select", "property": {
            "options": [{"name": "low", "color": 1}, {"name": "low_to_medium", "color": 3}, {"name": "medium", "color": 0}]
        }},
        {"field_name": "趋势方向", "type": "single_select", "property": {
            "options": [{"name": "rising", "color": 1}, {"name": "stable", "color": 3}, {"name": "falling", "color": 0}]
        }},
        {"field_name": "目标月销售额 USD", "type": "number", "property": {"formatter": "0.00"}},
        {"field_name": "盈亏平衡销量", "type": "number", "property": {"formatter": "0"}},
        {"field_name": "数据来源", "type": "multi_select", "property": {
            "options": [
                {"name": "mock", "color": 0}, {"name": "rainforest", "color": 2},
                {"name": "google_trends", "color": 4}, {"name": "real", "color": 1},
            ]
        }},
        {"field_name": "报告文档", "type": "url"},
        {"field_name": "JSON 附件", "type": "attachment"},
        {"field_name": "报告日期", "type": "text"},
        {"field_name": "行动计划", "type": "text"},
        {"field_name": "数据质量备注", "type": "text"},
    ]

    def list_base_fields(self, table_id: Optional[str] = None) -> List[Dict]:
        """列出 Base 表已有字段。"""
        app_token = self.config.base_token
        table_id = table_id or self.config.table_id
        resp = self._api("GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields")
        return resp.get("data", {}).get("items", [])

    def create_base_field(self, table_id: str, field_name: str,
                          field_type: str, property: Optional[Dict] = None) -> Optional[str]:
        """创建 Base 字段，返回 field_id。"""
        app_token = self.config.base_token
        body = {
            "field_name": field_name,
            "type": self.BASE_FIELD_TYPES[field_type],
        }
        if property:
            body["property"] = property
        try:
            resp = self._api("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields", body)
            return resp.get("data", {}).get("field", {}).get("field_id")
        except RuntimeError as e:
            raise RuntimeError(f"创建字段 '{field_name}' 失败: {e}") from e

    def update_base_field(self, table_id: str, field_id: str, field_name: str,
                          field_type: str, property: Optional[Dict] = None) -> bool:
        """更新 Base 字段属性（全量更新）。"""
        app_token = self.config.base_token
        body = {
            "field_name": field_name,
            "type": self.BASE_FIELD_TYPES[field_type],
        }
        if property:
            body["property"] = property
        try:
            self._api("PUT", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}", body)
            return True
        except RuntimeError as e:
            raise RuntimeError(f"更新字段 '{field_name}' 失败: {e}") from e

    def rename_base_field(self, table_id: str, field_id: str, new_name: str,
                          field_type: str = "text", property: Optional[Dict] = None) -> bool:
        """重命名/转换 Base 字段（常用于把默认主列「文本」改为「报告编号」）。"""
        return self.update_base_field(table_id, field_id, new_name, field_type, property)

    def delete_base_field(self, table_id: str, field_id: str) -> bool:
        """删除 Base 字段（需 base:field:write 权限）。"""
        app_token = self.config.base_token
        try:
            self._api("DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}")
            return True
        except RuntimeError as e:
            raise RuntimeError(f"删除字段失败: {e}") from e

    def ensure_base_fields(self, table_id: Optional[str] = None,
                           fields: Optional[List[Dict]] = None) -> Dict[str, str]:
        """确保推荐字段全部存在，返回 field_name -> field_id 映射。"""
        table_id = table_id or self.config.table_id
        existing = {f["field_name"]: f["field_id"] for f in self.list_base_fields(table_id)}
        mapping = {}
        for cfg in (fields or self.DEFAULT_BASE_FIELDS):
            name = cfg["field_name"]
            if name in existing:
                mapping[name] = existing[name]
            else:
                fid = self.create_base_field(table_id, name, cfg["type"], cfg.get("property"))
                mapping[name] = fid
        return mapping

    def upload_file(self, file_path: str, parent_node: Optional[str] = None) -> str:
        """上传文件到飞书 Drive / Base，返回 file_token。"""
        boundary = uuid.uuid4().hex
        file_name = Path(file_path).name
        file_size = Path(file_path).stat().st_size
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        # 未指定 parent_node 时，默认挂到 Base（附件字段）下
        parent_node = parent_node or self.config.base_token
        parent_type = "bitable_file"

        with open(file_path, "rb") as f:
            file_content = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file_name"\r\n\r\n'
            f"{file_name}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="parent_type"\r\n\r\n'
            f"{parent_type}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="parent_node"\r\n\r\n'
            f"{parent_node}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="size"\r\n\r\n'
            f"{file_size}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode() + file_content + f"\r\n--{boundary}--\r\n".encode()

        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all",
            data=body, headers=headers, method="POST",
        )
        try:
            resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Upload media error {e.code}: {error_body}") from e
        return resp["data"]["file_token"]

    def create_base_record(self, fields: Dict, table_id: Optional[str] = None) -> Optional[str]:
        """创建 Base 记录，返回 record_id。"""
        app_token = self.config.base_token
        table_id = table_id or self.config.table_id
        # Feishu 新版记录接口要求 path 为 /tables/{table_id}/records
        resp = self._api("POST", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
                         {"fields": fields})
        record_id = resp.get("data", {}).get("record", {}).get("record_id")
        if not record_id:
            print(f"[DEBUG] create_base_record response: {json.dumps(resp, ensure_ascii=False)[:500]}")
        return record_id

    # ── 选品报告（新版：简洁商务版）────────────────────────

    def create_selection_report(self, summary: Dict) -> Optional[str]:
        """将选品分析结果写入飞书文档（兼容旧版）。"""
        blocks = []
        for key, label in [("market", "市场分析"), ("supply", "供应链"),
                            ("compliance", "合规"), ("profit", "利润")]:
            blocks.append(self._heading_block(f"{label}", level=2))
            value = summary.get(key, {})
            blocks.append(self._text_block(json.dumps(value, ensure_ascii=False, indent=2)))

        title = f"选品报告 - {summary.get('product', 'Unknown')} - {time.strftime('%Y-%m-%d')}"
        url, _ = self.create_doc(title, blocks)
        return url

    def create_selection_report_v2(self, report: Dict,
                                   wiki_space_id: Optional[str] = None,
                                   use_user_token: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """生成商务版选品报告文档，返回 (文档 URL, 文档 token)。

        排版对标飞书云文档原生格式：
          一级标题「一、xxx」
          二级标题「1. xxx」
          三级标题「(1) xxx」
          四级标题「① xxx」
          表格用全角空格对齐模拟（当前租户 block_type=4 表格报 invalid param）
          引用块用左侧竖条 ▎ + 浅色背景模拟
        """
        summary = report.get("executive_summary", {})
        scores = report.get("dimension_scores", {})
        details = report.get("detailed_analysis", {})
        market = details.get("market", {})
        supply = details.get("supply", {})
        compliance = details.get("compliance", {})
        profit = details.get("profit", {})
        trend = details.get("trend", {})

        keyword = summary.get("product_keyword", "Unknown")
        title = f"选品报告 - {keyword} - {datetime.now().strftime('%Y-%m-%d')}"
        blocks: List[Dict] = []

        def _fmt(v: Any, default: str = "N/A") -> str:
            return str(v) if v is not None else default

        def h1(text: str):
            # 一级标题：带彩色背景条，突出章节分隔
            blocks.append(self._banner_heading_block(text, level=1, bg_color=5))

        def h2(text: str):
            # 二级标题：下划线 + 主题色，层次明显
            blocks.append(self._sub_title_block(text))

        def h3(text: str):
            blocks.append(self._heading_block(text, level=3, color=6))

        def h4(text: str):
            blocks.append(self._heading_block(text, level=4, color=7))

        def para(text: str, bold: bool = False, italic: bool = False,
                 color: Optional[int] = None, bg_color: Optional[int] = None):
            blocks.append(self._text_block(text, bold=bold, italic=italic,
                                           color=color, bg_color=bg_color))

        def bullet(text: str, indent: int = 0, bold: bool = False,
                   color: Optional[int] = None):
            blocks.append({
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": text, "bold": bold,
                                               "text_color": color}}],
                    "style": {"list": {"type": "bullet", "indent_level": indent}},
                },
            })

        def ordered(text: str, indent: int = 0):
            blocks.append({
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": text}}],
                    "style": {"list": {"type": "ordered", "indent_level": indent}},
                },
            })

        def quote(text: str):
            blocks.append(self._quote_block(text))

        def table_row(cells: List[str], widths: List[int], header: bool = False,
                      bg: Optional[int] = None):
            blocks.append(self._table_row_block(cells, widths=widths,
                                                 header=header, bg_color=bg))

        def empty():
            blocks.append(self._empty_block())

        overall_score = summary.get('overall_score', 0)
        max_score = summary.get('max_score', 100)
        verdict = _fmt(summary.get('verdict'))

        # ── 封面元信息 ──
        empty()
        para(f"关键词：{keyword}    目标市场：{summary.get('target_market', 'US')}    "
             f"目标平台：{summary.get('target_platform', 'amazon')}")
        para(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", italic=True, color=7)
        empty()

        # 决策结论
        score_pct = overall_score / max_score if max_score else 0
        score_color = 4 if score_pct >= 0.7 else 3 if score_pct >= 0.5 else 1
        verdict_emoji = "✓" if score_pct >= 0.7 else "~" if score_pct >= 0.5 else "!"
        blocks.append(self._verdict_block(
            verdict, overall_score, max_score, score_color, verdict_emoji))
        empty()

        # ── 一、执行摘要 ──
        h1("一、执行摘要")
        h2("1. 核心指标")
        widths = [12, 20, 16]
        table_row(["指标", "数值", "说明"], widths, header=True, bg=5)
        table_row(["综合评分", f"{overall_score}/{max_score}", "满分 100"], widths)
        table_row(["竞品均价", f"${market.get('avg_price', 0):.2f}", "Amazon 平均售价"], widths)
        table_row(["预估毛利率", _fmt(profit.get('gross_margin')), "扣除主要成本后"], widths)
        table_row(["最低 MOQ", f"{_fmt(supply.get('min_moq'))} pcs", "供应商起订量"], widths)
        table_row(["供应商数量", _fmt(supply.get('supplier_count', 0)), "可替代来源数"], widths)
        table_row(["合规风险", _fmt(compliance.get('overall_risk')), "综合合规评估"], widths)
        table_row(["趋势方向", _fmt(trend.get('trend_direction')), "Google Trends 判断"], widths)
        h3("(1) 关键发现")
        for finding in summary.get("key_findings", []):
            bullet(_fmt(finding), indent=0)
        quote("以上为核心结论摘要，详细分析见后续章节。")

        # ── 二、市场机会 ──
        h1("二、市场机会")
        para(f"关键词「{keyword}」在 Amazon 上找到 {market.get('top_products_count', 0)} 个去重竞品，"
             f"平均售价 ${market.get('avg_price', 0):.2f}，平均评论 {market.get('avg_reviews', 0)}，"
             f"最低 BSR {market.get('min_bsr', 'N/A')}。", italic=True)
        h2("1. 竞争格局")
        table_row(["维度", "数值", "解读"], widths, header=True, bg=5)
        table_row(["去重竞品数", f"{market.get('top_products_count', 0)}", "头部样本"], widths)
        table_row(["平均评论", f"{market.get('avg_reviews', 0)}", "反映市场成熟度"], widths)
        table_row(["最低 BSR", f"{market.get('min_bsr', 'N/A')}", "最好排名"], widths)
        h2("2. 核心用户痛点")
        pain_points = market.get("top_pain_points", [])
        if pain_points:
            for pt in pain_points[:5]:
                bullet(_fmt(pt), indent=0, color=1)
                bullet("建议在产品设计阶段针对性优化。", indent=1, color=7)
        else:
            bullet("暂无明确痛点，建议进一步调研评论与问答区。")
        h3("(1) 市场特征")
        bullet(f"季节相关性：{_fmt(market.get('seasonal_relevance', 'all_year'))}")
        bullet(f"关键词机会：{_fmt(market.get('keyword_opportunity_analysis'))}")
        bullet(f"数据质量：{_fmt(market.get('data_quality_notes', market.get('data_quality')))}")

        # ── 三、供应链方案 ──
        h1("三、供应链方案")
        h2("1. 供应能力")
        table_row(["指标", "数值", "备注"], widths, header=True, bg=5)
        table_row(["供应商数量", _fmt(supply.get('supplier_count', 0)), "1688/Alibaba"], widths)
        table_row(["平均采购价", f"${supply.get('avg_unit_cost_usd', 0):.2f}", "FOB 单价"], widths)
        table_row(["推荐物流", _fmt(supply.get('recommended_shipping', 'sea_freight')), "成本最优"], widths)
        table_row(["头程运费", f"${supply.get('shipping_per_unit', 0):.2f}/unit", "到仓"], widths)
        table_row(["交货周期", f"{_fmt(supply.get('lead_time_days_range'))}", "生产+运输"], widths)
        h2("2. TOP3 供应商")
        top_suppliers = supply.get("top_suppliers", [])[:3]
        if top_suppliers:
            for idx, s in enumerate(top_suppliers, 1):
                certs = ", ".join(s.get("certifications", [])[:2]) or "-"
                bullet(f"供应商 {idx}：{_fmt(s.get('name'))}", bold=True)
                bullet(f"地区：{_fmt(s.get('location'))}", indent=1)
                bullet(f"MOQ：{_fmt(s.get('moq'))} pcs，单价：${s.get('unit_price_usd', 0):.2f}", indent=1)
                bullet(f"认证：{certs}，评分：{_fmt(s.get('rating'))}", indent=1)
        else:
            bullet("暂无供应商数据。")

        # ── 四、合规与风险 ──
        h1("四、合规与风险")
        risk_level = compliance.get('overall_risk', 'medium')
        risk_color = 1 if risk_level in ('medium', 'high') else 4 if risk_level == 'low' else 3
        para(f"综合合规风险：{risk_level}", bold=True, color=risk_color)
        h2("1. 主要风险因素")
        risk_factors = compliance.get("risk_factors", [])
        if risk_factors:
            for rf in risk_factors:
                bullet(_fmt(rf), color=1)
        else:
            bullet("未发现显著风险因素。", color=4)
        h2("2. 关税与认证")
        tariff = compliance.get("import_tariff", {})
        table_row(["项目", "详情", "备注"], widths, header=True, bg=5)
        table_row(["HS Code", _fmt(tariff.get('hs_code')), "参考编码"], widths)
        table_row(["关税率", f"{tariff.get('duty_rate_pct', 0)}%", "可能变动"], widths)
        table_row(["单件关税", f"${tariff.get('estimated_duty_per_unit', 0):.2f}", "按申报价"], widths)
        quote("关税、FBA 费率和平台佣金可能变动，建议定期重新测算。")

        # ── 五、利润测算 ──
        h1("五、利润测算")
        h2("1. 盈利指标")
        table_row(["指标", "数值", "说明"], widths, header=True, bg=5)
        table_row(["建议售价", f"${profit.get('selling_price', 0):.2f}", "Amazon 售价"], widths)
        table_row(["单件总成本", f"${profit.get('total_cost_per_unit', 0):.2f}", "含物流/佣金/广告"], widths)
        table_row(["单件毛利", f"${profit.get('gross_profit_per_unit', 0):.2f}", "毛利额"], widths)
        table_row(["毛利率", _fmt(profit.get('gross_margin')), "毛利率"], widths)
        table_row(["盈亏平衡销量", f"{_fmt(profit.get('breakeven_units'))} 件/月", "月销门槛"], widths)
        h2("2. 单件成本拆解")
        breakdown = profit.get("cost_breakdown", {})
        if breakdown:
            for k, v in breakdown.items():
                bullet(f"{k}：${v:.2f}", bold=True)
        h2("3. ROI 三档情景")
        roi = profit.get("roi_scenarios", {})
        if roi:
            scene_meta = [
                ("conservative", "保守", 1),
                ("neutral", "中性", 3),
                ("optimistic", "乐观", 4),
            ]
            for scene, label, color in scene_meta:
                r = roi.get(scene, {})
                bullet(f"{label}情景：月销量 {_fmt(r.get('monthly_sales'))}，"
                       f"月营收 ${r.get('monthly_revenue', 0):.2f}，"
                       f"月利润 ${r.get('monthly_profit', 0):.2f}", bold=True, color=color)
                bullet(f"ROI {r.get('roi_pct', 0):.1f}%，回本周期 {r.get('payback_months', 0)} 个月",
                       indent=1)

        # ── 六、趋势判断 ──
        h1("六、趋势判断")
        h2("1. 趋势指标")
        table_row(["指标", "数值", "解读"], widths, header=True, bg=5)
        confidence = trend.get("confidence", 0)
        table_row(["趋势方向", _fmt(trend.get('trend_direction')), "Google Trends"], widths)
        table_row(["置信度", f"{confidence:.0%}" if isinstance(confidence, (int, float)) else _fmt(confidence),
                   "模型置信度"], widths)
        table_row(["生命周期", _fmt(trend.get('lifecycle_stage')), "产品阶段"], widths)
        table_row(["热度分", _fmt(trend.get('buzz_score')), "搜索热度"], widths)
        h3("(1) 上升查询词")
        rising = trend.get("rising_queries", [])
        if rising:
            for q in rising[:5]:
                ordered(_fmt(q))

        # ── 七、可执行行动计划 ──
        h1("七、可执行行动计划")
        para("按优先级排序，建议 30 天内启动：", italic=True)
        for idx, action in enumerate(report.get("action_recommendations", []), 1):
            ordered(f"{_fmt(action)}")

        # ── 八、风险提示与数据来源 ──
        h1("八、风险提示与数据来源")
        h2("1. 风险提示")
        for warning in report.get("risk_warnings", []):
            bullet(_fmt(warning), color=1)
        h2("2. 数据来源")
        for src, desc in report.get("data_sources", {}).items():
            bullet(f"{src}：{desc}")

        return self.create_doc(title, blocks, wiki_space_id=wiki_space_id, use_user_token=use_user_token)

    def publish_selection_report(self, report: Dict, json_path: Optional[str] = None,
                                 table_id: Optional[str] = None,
                                 wiki_space_id: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        一键发布选品报告：
        1. 生成飞书商务版文档（可归档到知识库）
        2. 将核心指标写入 Base 多维表
        3. 上传 JSON 报告作为附件
        4. 将文档所有者转移给指定用户（如已配置）
        返回 {"doc_url": ..., "record_id": ..., "record_url": ...}
        """
        table_id = table_id or self.config.table_id
        wiki_space_id = wiki_space_id or self.config.wiki_space_id
        if not wiki_space_id or str(wiki_space_id).startswith("your-"):
            wiki_space_id = None

        # 1. 创建文档（若配置个人 user_access_token，则以个人名义创建）
        use_user_token = bool(self.config.user_access_token)
        if use_user_token:
            print("[INFO] 检测到 FEISHU_USER_ACCESS_TOKEN，文档将以个人名义创建。")
        doc_url, doc_token = self.create_selection_report_v2(
            report, wiki_space_id=wiki_space_id, use_user_token=use_user_token)

        # 2. 若未使用个人 token，则尝试转移所有者或添加协作者
        user_id = self.config.user_open_id
        is_placeholder = not user_id or "your-" in user_id or "xxxxxxxx" in user_id
        if doc_token and user_id and not is_placeholder and not use_user_token:
            try:
                self.transfer_doc_owner(doc_token, user_id, self.config.user_member_type)
                print(f"[INFO] 文档所有者已转移至 {self.config.user_member_type}:{user_id}")
            except Exception as e:
                print(f"[WARN] 转移文档所有者失败，尝试添加可编辑协作者: {e}")
                try:
                    self.add_doc_member(doc_token, user_id,
                                        self.config.user_member_type, "edit")
                    print(f"[INFO] 已添加协作者 {self.config.user_member_type}:{user_id}（可编辑）")
                except Exception as e2:
                    print(f"[WARN] 添加协作者也失败: {e2}")

        # 3. 确保字段存在
        field_map = self.ensure_base_fields(table_id)

        # 4. 获取主列（第一列）真实字段名及其 field_id；若主列名不是「报告编号」则重命名
        fields_snapshot = self.list_base_fields(table_id)
        primary_field_name = None
        primary_field_id = None
        for f in fields_snapshot:
            if f.get("is_primary"):
                primary_field_name = f.get("field_name")
                primary_field_id = f.get("field_id")
                break
        if primary_field_id and primary_field_name != "报告编号":
            # 先删除可能存在的同名普通字段，避免重命名冲突
            for f in fields_snapshot:
                if f.get("field_name") == "报告编号" and not f.get("is_primary"):
                    try:
                        self.delete_base_field(table_id, f.get("field_id"))
                        print("[INFO] 已删除与主列重名的普通字段「报告编号」")
                    except Exception as e:
                        print(f"[WARN] 删除重名字段失败: {e}")
                    break
            try:
                self.rename_base_field(table_id, primary_field_id, "报告编号", "text")
                primary_field_name = "报告编号"
                print("[INFO] 已将 Base 主列（第一列）重命名为「报告编号」")
            except Exception as e:
                print(f"[WARN] 重命名主列失败，将使用原主列名 '{primary_field_name}' 填充: {e}")
        if primary_field_name and primary_field_id:
            field_map[primary_field_name] = primary_field_id

        # 5. 提取核心指标
        summary = report.get("executive_summary", {})
        scores = report.get("dimension_scores", {})
        details = report.get("detailed_analysis", {})
        market = details.get("market", {})
        supply = details.get("supply", {})
        compliance = details.get("compliance", {})
        profit = details.get("profit", {})
        trend = details.get("trend", {})

        # 毛利率统一转为 0-1 之间的小数，配合 number + 0.00% formatter 显示为百分比
        margin_raw = profit.get("gross_margin", "0%")
        margin = 0.0
        try:
            margin_str = str(margin_raw).replace("%", "").strip()
            margin_val = float(margin_str)
            if margin_val > 1:
                margin = margin_val / 100.0
            else:
                margin = margin_val
        except Exception:
            margin = 0.0

        optimistic_revenue = profit.get("roi_scenarios", {}).get("optimistic", {}).get("monthly_revenue", 0)

        # 构造 fields 字典（field_name -> value）
        fields: Dict[str, Any] = {}

        def set_text(name: str, text: str):
            if field_map.get(name):
                fields[name] = str(text)

        def set_url(name: str, url: str):
            if field_map.get(name):
                fields[name] = {"link": str(url), "text": "查看报告"}

        def set_number(name: str, num: float):
            if field_map.get(name):
                try:
                    fields[name] = float(num)
                except Exception:
                    fields[name] = 0

        def set_select(name: str, option: str):
            if field_map.get(name) and option:
                fields[name] = str(option)

        def set_multi_select(name: str, options: List[str]):
            if field_map.get(name) and options:
                fields[name] = [str(o) for o in options]

        def set_date(name: str, date_str: str):
            if field_map.get(name):
                fields[name] = str(date_str)

        def set_attachment(name: str, file_token: str):
            if field_map.get(name) and file_token:
                fields[name] = [{"file_token": file_token}]

        report_no = f"RPT{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 填充第一列（主列）：使用真实字段名，这样 Base 的第一列不再为空
        if primary_field_name and field_map.get(primary_field_name):
            fields[primary_field_name] = report_no
            print(f"[INFO] 已填充主列字段 '{primary_field_name}': {report_no}")

        set_text("报告编号", report_no)
        set_text("关键词", summary.get("product_keyword", ""))
        set_select("行业", summary.get("industry", ""))
        set_select("目标市场", summary.get("target_market", "US"))
        set_select("目标平台", summary.get("target_platform", "amazon"))
        set_number("综合评分", summary.get("overall_score", 0))
        set_select("决策结论", summary.get("verdict", ""))
        set_number("竞品均价 USD", market.get("avg_price", 0))
        set_number("预估毛利率", margin)
        set_number("最低 MOQ", supply.get("min_moq", 0))
        set_number("供应商数量", supply.get("supplier_count", 0))
        top10_names = [s.get("name", "") for s in supply.get("top_suppliers", [])[:10] if s.get("name")]
        set_text("TOP10 供应商", "\n".join(top10_names) if top10_names else "-")
        set_select("合规风险", compliance.get("overall_risk", ""))
        set_select("趋势方向", trend.get("trend_direction", ""))
        set_number("目标月销售额 USD", optimistic_revenue)
        set_number("盈亏平衡销量", profit.get("breakeven_units", 0))
        sources = [k for k in report.get("data_sources", {}).keys()]
        if not sources:
            sources = ["mock"]
        set_multi_select("数据来源", sources)
        set_url("报告文档", doc_url or "")
        set_date("报告日期", datetime.now().strftime("%Y-%m-%d"))
        set_text("行动计划", "；".join(report.get("action_recommendations", [])))
        quality_notes = []
        for src in report.get("data_sources", {}).values():
            if "MOCK" in str(src) or "mock" in str(src):
                quality_notes.append("含示例数据")
        set_text("数据质量备注", ", ".join(quality_notes) or "请复核真实 API")

        # 6. 上传 JSON 附件
        if json_path and field_map.get("JSON 附件") and Path(json_path).exists():
            try:
                file_token = self.upload_file(json_path)
                set_attachment("JSON 附件", file_token)
            except Exception as e:
                print(f"[WARN] JSON 附件上传失败: {e}")

        # 7. 创建记录
        record_id = self.create_base_record(fields, table_id)
        record_url = f"https://my.feishu.cn/base/{self.config.base_token}?table={table_id}"

        return {
            "doc_url": doc_url,
            "record_id": record_id,
            "record_url": record_url,
        }

    # ── Block 渲染辅助 ──────────────────────────────────

    @staticmethod
    def _text_block(text: str, bold: bool = False, color: Optional[int] = None,
                    bg_color: Optional[int] = None, italic: bool = False,
                    underline: bool = False) -> Dict:
        """文本块，支持颜色、背景色、斜体、下划线。"""
        run = {"content": text}
        if bold:
            run["bold"] = True
        if italic:
            run["italic"] = True
        if underline:
            run["underline"] = True
        if color is not None:
            run["text_color"] = color
        if bg_color is not None:
            run["background_color"] = bg_color
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": run}],
                "style": {},
            },
        }

    @staticmethod
    def _multi_text_block(runs: List[Dict]) -> Dict:
        """多段样式文本块；runs 为 text_run 字典列表。"""
        return {
            "block_type": 2,
            "text": {"elements": [{"text_run": r} for r in runs], "style": {}},
        }

    @staticmethod
    def _heading_block(text: str, level: int = 2, icon: str = "",
                       color: Optional[int] = None) -> Dict:
        """飞书标题块：使用 text block + heading_level style。
        参考图层级：一级「一、」，二级「1. 」，三级「(1)」，四级「①」。
        """
        content = f"{icon} {text}" if icon else text
        run = {"content": content, "bold": True}
        if color is not None:
            run["text_color"] = color
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": run}],
                "style": {"heading_level": level},
            },
        }

    @staticmethod
    def _bullet_block(text: str, bold_label: bool = False, icon: str = "•",
                      color: Optional[int] = None) -> Dict:
        """无序列表项；icon 可替换为 emoji 等符号。"""
        prefix = f"{icon} " if icon else ""
        full = prefix + text
        if bold_label and "：" in text:
            label, value = text.split("：", 1)
            elements = [
                {"text_run": {"content": f"{prefix}{label}：", "bold": True}},
                {"text_run": {"content": value, "text_color": color} if color is not None else {"content": value}},
            ]
        else:
            run = {"content": full}
            if color is not None:
                run["text_color"] = color
            elements = [{"text_run": run}]
        return {
            "block_type": 2,
            "text": {
                "elements": elements,
                "style": {"list": {"type": "bullet", "indent_level": 0}},
            },
        }

    @staticmethod
    def _numbered_block(text: str, bold: bool = False, icon: str = "") -> Dict:
        content = f"{icon} {text}" if icon else text
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": content, "bold": bold}}],
                "style": {"list": {"type": "ordered", "indent_level": 0}},
            },
        }

    @staticmethod
    def _divider_block() -> Dict:
        """分隔线：当前租户 block_type=14 报 invalid param，用空段落替代。"""
        return {
            "block_type": 2,
            "text": {"elements": [{"text_run": {"content": " "}}], "style": {}},
        }

    @staticmethod
    def _empty_block() -> Dict:
        """空段落，用于增加呼吸感。"""
        return {
            "block_type": 2,
            "text": {"elements": [{"text_run": {"content": " "}}], "style": {}},
        }

    @staticmethod
    def _callout_block(text: str, bold: bool = True, bg_color: int = 2,
                       text_color: int = 0) -> Dict:
        """高亮提示块：用背景色 + 加粗模拟 Callout。"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {
                    "content": text,
                    "bold": bold,
                    "background_color": bg_color,
                    "text_color": text_color,
                }}],
                "style": {},
            },
        }

    @staticmethod
    def _quote_block(text: str, bold: bool = False, bg_color: int = 3,
                     text_color: int = 7) -> Dict:
        """引用块：左侧竖条 + 浅色背景（模拟飞书引用样式）。"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {
                    "content": f"▎ {text}",
                    "bold": bold,
                    "background_color": bg_color,
                    "text_color": text_color,
                }}],
                "style": {},
            },
        }

    @staticmethod
    def _table_row_block(cells: List[str], widths: List[int] = None,
                         header: bool = False, bg_color: Optional[int] = None) -> Dict:
        """模拟表格行：用全角空格/Tab 对齐列（当前租户 block_type=4 表格不可用）。"""
        widths = widths or [12, 20, 16]
        # 全角空格占位，使列大致对齐
        def pad(s: str, width: int):
            # 中文字符按 2 个宽度计算，英文字符按 1 个宽度
            actual = 0
            for ch in s:
                actual += 2 if '\u4e00' <= ch <= '\u9fff' else 1
            pad_len = max(0, width - actual)
            return s + "　" * (pad_len // 2) + " " * (pad_len % 2)

        parts = []
        for i, cell in enumerate(cells):
            if i < len(widths):
                parts.append(pad(str(cell), widths[i]))
            else:
                parts.append(str(cell))
        content = "　".join(parts)
        run = {"content": content, "bold": header}
        if bg_color is not None:
            run["background_color"] = bg_color
        return {
            "block_type": 2,
            "text": {"elements": [{"text_run": run}], "style": {}},
        }

    @staticmethod
    def _table_block(rows: List[List[str]],
                     header: bool = True,
                     column_widths: Optional[List[int]] = None) -> Dict:
        """rows[0] 为表头，后续为数据行。"""
        row_size = len(rows)
        column_size = len(rows[0]) if rows else 0
        cells: List[List[Dict]] = []
        for ridx, row in enumerate(rows):
            cell_row: List[Dict] = []
            for cell in row:
                cell_row.append({
                    "block_type": 5,
                    "table_cell": {
                        "children": [{
                            "block_type": 2,
                            "text": {
                                "elements": [{
                                    "text_run": {
                                        "content": str(cell),
                                        "bold": header and ridx == 0,
                                    }
                                }],
                                "style": {},
                            },
                        }],
                    },
                })
            cells.append(cell_row)
        widths = column_widths or [180] * column_size
        return {
            "block_type": 4,
            "table": {
                "table_position": {
                    "row_size": row_size,
                    "column_size": column_size,
                    "merge_type": 0,
                },
                "cells": cells,
                "property": {
                    "row_size": row_size,
                    "column_size": column_size,
                    "header_column": False,
                    "header_row": header,
                    "column_widths": widths,
                },
            },
        }

    def _kpi_table(self, items: List[List[str]],
                   column_widths: Optional[List[int]] = None) -> Dict:
        """两列 KPI 展示表。"""
        rows = [["指标", "数值"]]
        rows.extend(items)
        return self._table_block(rows, column_widths=column_widths)

    @staticmethod
    def _cover_title_block(text: str) -> Dict:
        """封面大标题：深色背景 + 白色加粗字。"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {
                    "content": f"  {text}  ",
                    "bold": True,
                    "background_color": 7,
                    "text_color": 0,
                }}],
                "style": {"heading_level": 1},
            },
        }

    @staticmethod
    def _section_title_block(text: str, bg_color: int = 5) -> Dict:
        """章节大标题：彩色背景条 + 加粗。"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {
                    "content": f"  {text}  ",
                    "bold": True,
                    "background_color": bg_color,
                    "text_color": 0,
                }}],
                "style": {"heading_level": 2},
            },
        }

    @staticmethod
    def _sub_title_block(text: str) -> Dict:
        """小节标题：下划线 + 加粗，突出层级。"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {
                    "content": text,
                    "bold": True,
                    "underline": True,
                    "text_color": 5,
                }}],
                "style": {"heading_level": 2},
            },
        }

    @staticmethod
    def _banner_heading_block(text: str, level: int = 1, bg_color: int = 5) -> Dict:
        """章节标题：彩色背景条 + 加粗白字，形成清晰的一级分隔。"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {
                    "content": f"  {text}  ",
                    "bold": True,
                    "background_color": bg_color,
                    "text_color": 0,
                }}],
                "style": {"heading_level": level},
            },
        }

    @staticmethod
    def _kpi_row_block(label: str, value: str, icon: str = "▸",
                       bg_color: int = 5) -> Dict:
        """单行 KPI 卡片：图标 + 彩色背景标签 + 值。"""
        return {
            "block_type": 2,
            "text": {
                "elements": [
                    {"text_run": {
                        "content": f" {icon} ",
                        "background_color": bg_color,
                    }},
                    {"text_run": {
                        "content": f" {label} ",
                        "bold": True,
                        "background_color": bg_color,
                        "text_color": 0,
                    }},
                    {"text_run": {"content": "  "}},
                    {"text_run": {
                        "content": str(value),
                        "bold": True,
                        "text_color": 7,
                    }},
                ],
                "style": {},
            },
        }

    @staticmethod
    def _verdict_block(verdict: str, score: float, max_score: float,
                       color: int, emoji: str) -> Dict:
        """决策结论大卡片。"""
        return {
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {
                    "content": f"  {emoji} 决策结论：{verdict}  （综合评分 {score}/{max_score}）  ",
                    "bold": True,
                    "background_color": color,
                    "text_color": 0,
                }}],
                "style": {},
            },
        }

    # ── 辅助 ────────────────────────────────────────────

    @staticmethod
    def _chunk(lst: List, n: int):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
