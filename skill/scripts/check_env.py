#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_env.py —— 部署前/部署后的环境自检，把「上线后才发现的坑」提前拦住。

重点检查（都是真踩过的坑）：
  1. 前端 dist 的资源前缀 vs 实际部署子路径是否一致 —— 不一致必然白屏。
  2. Node 版本是否 >= 22。
  3. 数据目录是否可写（首次启动要落库）。
  4. 目标端口是否被占用 / 服务是否已在监听。
  5. 是否填了 LLM api_key（没填只有规则应答，且无法生成向量）。

用法：
  python scripts/check_env.py --target /home/ubuntu/smart-cs --base-path /cs/ --port 3000
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys

GREEN, YELLOW, RED, RESET = "✅", "⚠️ ", "❌", ""


def report(level: str, item: str, detail: str) -> None:
    icon = {"PASS": GREEN, "WARN": YELLOW, "FAIL": RED}[level]
    print(f"{icon} {item:<22} {detail}")


def check_target(target: str) -> bool:
    if not os.path.isdir(target):
        report("FAIL", "目标目录", f"不存在：{target}")
        return False
    report("PASS", "目标目录", os.path.abspath(target))
    return True


def check_files(target: str) -> None:
    entry = os.path.join(target, "server", "index.js")
    report("PASS" if os.path.isfile(entry) else "FAIL", "后端入口", entry)
    dist_index = os.path.join(target, "web", "dist", "index.html")
    report("PASS" if os.path.isfile(dist_index) else "WARN", "前端产物 dist", dist_index)


def check_dist_prefix(target: str, base_path: str) -> None:
    """dist 资源前缀必须与部署子路径一致，否则静态资源 404 → 白屏。"""
    dist_index = os.path.join(target, "web", "dist", "index.html")
    if not os.path.isfile(dist_index):
        report("WARN", "前端前缀校验", "dist/index.html 不存在，跳过（需先构建前端）")
        return
    with open(dist_index, "r", encoding="utf-8") as fh:
        html = fh.read()
    refs = re.findall(r'(?:src|href)="([^"]+)"', html)
    asset = next((r for r in refs if r.startswith("/")), None)
    if asset is None:
        report("WARN", "前端前缀校验", "dist 中未找到绝对路径资源引用")
        return
    if asset.startswith("http") or not asset.startswith("/"):
        report("WARN", "前端前缀校验", f"首个资源为 {asset}，非同域绝对路径")
        return
    want = "/" if base_path in ("", "/") else "/" + base_path.strip("/") + "/"
    if want == "/":
        # 根域名部署：dist 必须直接引用 /assets/...，多出任何子路径段都会 404 白屏
        first_seg = asset.lstrip("/").split("/")[0]
        ok = first_seg == "assets"
        expect = "/assets/...（根路径）"
    else:
        ok = asset.startswith(want)
        expect = want
    if ok:
        report("PASS", "前端前缀校验", f"资源 {asset} 与部署形态一致：{expect}")
    else:
        report("FAIL", "前端前缀校验", f"资源前缀 {asset} ≠ 部署形态 {expect} → 必然白屏")
        print(f"     修复：bash scripts/build_frontend.sh {target} {want}")


def check_node() -> None:
    node = shutil.which("node")
    if not node:
        report("WARN", "Node 运行时", "PATH 中未找到 node（若在服务器部署，请登录服务器再自检）")
        return
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=15)
        ver = out.stdout.strip()
        major = int(re.sub(r"[^0-9]", "", ver.split(".")[0]) or 0)
        if major >= 22:
            report("PASS", "Node 运行时", f"{ver} ({node})")
        else:
            report("WARN", "Node 运行时", f"{ver} 低于要求 22，建议升级")
    except Exception as exc:  # noqa: BLE001
        report("WARN", "Node 运行时", f"无法读取版本：{exc}")


def check_data_writable(target: str) -> None:
    data_dir = os.path.join(target, "data")
    try:
        os.makedirs(data_dir, exist_ok=True)
        probe = os.path.join(data_dir, ".write-probe")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        report("PASS", "数据目录可写", data_dir)
    except Exception as exc:  # noqa: BLE001
        report("FAIL", "数据目录可写", f"{data_dir} 不可写（{exc}）→ 首次启动落库会失败")


def check_port(port: int, host: str = "127.0.0.1") -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.5)
    try:
        if sock.connect_ex((host, port)) == 0:
            report("PASS", f"端口 {port}", f"已在监听（服务应已启动）")
        else:
            report("WARN", f"端口 {port}", "未监听（服务未启动，或被防火墙/容器隔离）")
    finally:
        sock.close()


def check_config(target: str) -> None:
    cfg_path = os.path.join(target, "server", "deploy", "config.json")
    if not os.path.isfile(cfg_path):
        report("WARN", "部署配置", f"不存在：{cfg_path}（用 configure.py 生成）")
        return
    import json

    try:
        with open(cfg_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception as exc:  # noqa: BLE001
        report("FAIL", "部署配置", f"JSON 解析失败：{exc}")
        return

    llm = cfg.get("llm", {})
    provider = llm.get("provider")
    has_key = bool(llm.get("api_key"))
    if provider == "api" and not has_key:
        report("FAIL", "大模型密钥", "provider=api 但 api_key 为空 → 只会规则应答")
    elif provider == "offline":
        report("WARN", "大模型密钥", "provider=offline（离线规则模式），想启用智能问答请填 api_key")
    else:
        report("PASS", "大模型密钥", f"provider={provider}，api_key 已配置")

    tenant = cfg.get("tenant", {})
    if not tenant.get("name"):
        report("WARN", "企业档案", "tenant.name 未填，机器人不知道代表哪家公司")
    else:
        report("PASS", "企业档案", tenant.get("name", ""))


def main() -> int:
    p = argparse.ArgumentParser(description="smart-cs 部署环境自检")
    p.add_argument("--target", required=True, help="目标 smart-cs 项目目录")
    p.add_argument("--base-path", default="/cs/", help="部署子路径，根域名部署填 /")
    p.add_argument("--port", type=int, default=3000, help="后端端口")
    args = p.parse_args()

    print("=" * 64)
    print(f"smart-cs 部署自检 —— target={os.path.abspath(args.target)} base={args.base_path} port={args.port}")
    print("=" * 64)
    if check_target(args.target):
        check_files(args.target)
        check_dist_prefix(args.target, args.base_path)
        check_node()
        check_data_writable(args.target)
        check_port(args.port)
        check_config(args.target)
    print("=" * 64)
    print("说明：WARN 不阻断部署，FAIL 必须修复后再上线。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
