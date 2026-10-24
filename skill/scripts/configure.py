#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
configure.py —— 生成 / 更新某个 smart-cs 实例的部署配置（server/deploy/config.json）。

原则：
- 幂等：已存在配置时只覆盖显式传入的字段，未传的保持原值。
- 安全：密钥只写入文件，预览输出一律脱敏（首尾各 4 位）。
- 零依赖：仅用 Python 标准库。

用法示例：
  python scripts/configure.py --target /home/ubuntu/smart-cs \
      --api-key sk-xxxx --name "某某科技有限公司" --brand "某某" \
      --website https://example.com --phone 400-000-0000 --email hi@example.com \
      --preset-questions "你们主要做哪些业务?;怎么联系你们?"

  # 仅生成不涉及大模型（离线规则应答）的配置
  python scripts/configure.py --target ./my-cs --provider offline --name "某某科技"

列表类参数用「分号」分隔：--business / --advantages / --preset-questions。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(SKILL_ROOT, "assets", "smart-cs", "server", "deploy", "config.json")

# agnes 公共接入点的默认值（换别的厂商时用 --base / --model 覆盖）
DEFAULT_API_BASE = "https://apihub.agnes-ai.com/v1"
DEFAULT_MODEL = "agnes-2.5-flash"


def mask(value: Optional[str]) -> str:
    """密钥脱敏预览：短串原样，长串保留首尾各 4 位。"""
    if not value:
        return "(空)"
    return value if len(value) <= 8 else f"{value[:4]}***{value[-4:]}"


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def split_list(raw: Optional[str]) -> Optional[List[str]]:
    """把 'a;b;c' 解析成列表；None 表示「未传入」，保持原值。"""
    if raw is None:
        return None
    items = [seg.strip() for seg in raw.replace("；", ";").split(";") if seg.strip()]
    return items


def set_if(cfg: Dict[str, Any], section: str, key: str, value: Any) -> bool:
    """仅当 value 不为 None 时写入；返回是否发生变更。"""
    if value is None:
        return False
    cfg.setdefault(section, {})[key] = value
    return True


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="生成/更新 smart-cs 的 deploy/config.json（幂等、无依赖、密钥脱敏预览）"
    )
    p.add_argument("--target", required=True, help="目标 smart-cs 项目目录")

    g1 = p.add_argument_group("企业档案")
    g1.add_argument("--name", help="公司全称")
    g1.add_argument("--brand", help="品牌简称")
    g1.add_argument("--english", help="英文名")
    g1.add_argument("--website", help="官网地址")
    g1.add_argument("--phone", help="联系电话")
    g1.add_argument("--email", help="联系邮箱")
    g1.add_argument("--founded", help="成立年份文案")
    g1.add_argument("--positioning", help="一句话公司定位")
    g1.add_argument("--business", help="业务板块，分号分隔")
    g1.add_argument("--advantages", help="核心优势，分号分隔")
    g1.add_argument("--scope-note", help="业务边界话术（超出范围时如何引导）")

    g2 = p.add_argument_group("访客挂件")
    g2.add_argument("--widget-title", help="挂件标题，如「在线客服」")
    g2.add_argument("--greeting", help="欢迎语")
    g2.add_argument("--placeholder", help="输入框占位文案")
    g2.add_argument("--powered", help="底部署名")
    g2.add_argument("--accent-from", help="主题渐变起色（hex）")
    g2.add_argument("--accent-to", help="主题渐变止色（hex）")
    g2.add_argument("--preset-questions", help="预置问题，分号分隔")

    g3 = p.add_argument_group("大模型引擎")
    g3.add_argument("--provider", choices=["api", "ollama", "offline"], help="引擎模式")
    g3.add_argument("--api-key", help="LLM API Key（写入文件，预览脱敏）")
    g3.add_argument("--base", help="LLM API base URL")
    g3.add_argument("--model", help="对话模型名")
    g3.add_argument("--embed-model", help="向量(embedding)模型名")

    g4 = p.add_argument_group("知识库来源")
    g4.add_argument("--kb-source", choices=["local", "ima", "feishu"], help="知识库来源")
    g4.add_argument("--ima-client-id")
    g4.add_argument("--ima-api-key")
    g4.add_argument("--ima-kb-id")
    g4.add_argument("--feishu-app-id")
    g4.add_argument("--feishu-app-secret")
    g4.add_argument("--feishu-space-ids", help="飞书知识空间 ID，多个用逗号分隔")

    p.add_argument("--dry-run", action="store_true", help="只打印结果，不写盘")
    return p


def main() -> int:
    args = build_parser().parse_args()

    target_cfg = os.path.join(args.target, "server", "deploy", "config.json")
    if os.path.exists(target_cfg):
        try:
            cfg = load_json(target_cfg)
            origin = f"已有配置 {target_cfg}"
        except Exception as exc:  # noqa: BLE001
            print(f"❌ 目标配置无法解析：{target_cfg} ({exc})")
            return 1
    elif os.path.exists(BASELINE):
        cfg = load_json(BASELINE)
        origin = f"skill 自带空白模板 {BASELINE}"
    else:
        print(f"❌ 找不到基线配置模板：{BASELINE}")
        return 1

    changed: List[str] = []

    # ---- 企业档案 ----
    tenant_fields = [
        ("name", args.name), ("brand", args.brand), ("english", args.english),
        ("website", args.website), ("phone", args.phone), ("email", args.email),
        ("founded", args.founded), ("positioning", args.positioning),
        ("scopeNote", args.scope_note),
    ]
    for key, val in tenant_fields:
        if set_if(cfg, "tenant", key, val):
            changed.append(f"tenant.{key}")
    for key, raw in (("business", args.business), ("advantages", args.advantages)):
        parsed = split_list(raw)
        if parsed is not None:
            set_if(cfg, "tenant", key, parsed)
            changed.append(f"tenant.{key}")

    # ---- 挂件 ----
    for key, val in [
        ("title", args.widget_title), ("greeting", args.greeting),
        ("placeholder", args.placeholder), ("powered", args.powered),
        ("accentFrom", args.accent_from), ("accentTo", args.accent_to),
    ]:
        if val is not None and set_if(cfg, "widget", key, val):
            changed.append(f"widget.{key}")
    parsed = split_list(args.preset_questions)
    if parsed is not None:
        set_if(cfg, "widget", "presetQuestions", parsed)
        changed.append("widget.presetQuestions")

    # ---- 大模型 ----
    # 未显式指定 provider 时，若给了 api_key / model / base，自动切到 api，
    # 避免「填了密钥却仍是 offline」这种最常见的配置陷阱。
    inferred_provider = args.provider
    if inferred_provider is None and (args.api_key or args.model or args.base):
        inferred_provider = "api"
    provider = inferred_provider or cfg.get("llm", {}).get("provider")
    base = args.base or (DEFAULT_API_BASE if provider == "api" else None)
    model = args.model or (DEFAULT_MODEL if provider == "api" else None)
    embed = args.embed_model or (model if provider == "api" else None)
    for key, val in [
        ("provider", inferred_provider), ("base", base), ("model", model),
        ("embed_model", embed), ("api_key", args.api_key),
    ]:
        # provider=offline 时不要写入 api 的默认值
        if provider == "offline" and key in ("base", "model", "embed_model"):
            continue
        if val is not None and set_if(cfg, "llm", key, val):
            changed.append(f"llm.{key}")

    # ---- 知识库 ----
    for key, val in [
        ("kb_source", args.kb_source), ("ima_client_id", args.ima_client_id),
        ("ima_api_key", args.ima_api_key), ("ima_kb_id", args.ima_kb_id),
        ("feishu_app_id", args.feishu_app_id), ("feishu_app_secret", args.feishu_app_secret),
        ("feishu_space_ids", args.feishu_space_ids),
    ]:
        if val is not None and set_if(cfg, "knowledge", key, val):
            changed.append(f"knowledge.{key}")

    # ---- 输出预览 ----
    llm = cfg.get("llm", {})
    kb = cfg.get("knowledge", {})
    tenant = cfg.get("tenant", {})
    widget = cfg.get("widget", {})

    print("=" * 60)
    print(f"目标实例：{os.path.abspath(args.target)}")
    print(f"配置来源：{origin}")
    print(f"变更字段：{', '.join(changed) if changed else '（无）'}")
    print("-" * 60)
    print(f"  企业：  {tenant.get('name', '(未填)')} / 品牌 {tenant.get('brand', '(未填)')}")
    print(f"  联系：  {tenant.get('phone', '(未填)')} · {tenant.get('email', '(未填)')}")
    print(f"  挂件：  {widget.get('title', '(未填)')}，预置问题 {len(widget.get('presetQuestions', []))} 条")
    print(f"  模型：  provider={llm.get('provider')}  model={llm.get('model', '(未填)')}")
    print(f"         base={llm.get('base', '(未填)')}")
    print(f"         api_key={mask(llm.get('api_key'))}")
    print(f"  知识库：kb_source={kb.get('kb_source')}")
    print("=" * 60)

    # ---- 一致性提醒 ----
    warnings: List[str] = []
    if llm.get("provider") == "api" and not llm.get("api_key"):
        warnings.append("provider=api 但未填 api_key，机器人只会规则应答，且无法算语义向量")
    if kb.get("kb_source") == "ima" and not (kb.get("ima_api_key") and kb.get("ima_kb_id")):
        warnings.append("kb_source=ima 但 ima_api_key / ima_kb_id 不完整，知识检索会退化")
    if kb.get("kb_source") == "feishu" and not (kb.get("feishu_app_id") and kb.get("feishu_app_secret")):
        warnings.append("kb_source=feishu 但飞书凭据不完整，同步任务会失败")
    if not tenant.get("name"):
        warnings.append("tenant.name 未填，机器人不知道自己代表哪家公司")
    for msg in warnings:
        print(f"⚠️  {msg}")

    if args.dry_run:
        print("\n--dry-run：未写盘。")
        return 0

    save_json(target_cfg, cfg)
    print(f"\n✅ 已写入 {target_cfg}")
    print("提醒：deploy/config.json 含密钥，已被项目 .gitignore 忽略，请勿提交到公开仓库。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
