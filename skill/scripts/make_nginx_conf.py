#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_nginx_conf.py —— 按「域名 + 部署子路径 + 后端端口」生成 Nginx 反向代理配置片段。

关键规则（坑）：
  location /cs/ { proxy_pass http://127.0.0.1:3000/; }
                                            ↑ 这个结尾斜杠会「剥离」/cs 前缀
  后端实际收到的请求是 /api/xxx、/assets/xxx，而不是 /cs/api/xxx。
  因此前端构建时的资源前缀必须与实际部署子路径一致，否则静态资源 404 → 页面空白。

用法：
  python scripts/make_nginx_conf.py --domain www.example.com --base-path /cs/ --port 3000
  python scripts/make_nginx_conf.py --domain kefu.example.com --base-path / --port 3000 --out /tmp/cs.conf
"""

from __future__ import annotations

import argparse
import sys

PROXY_HEADERS = """        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_read_timeout 300s;"""


def build_conf(domain: str, base_path: str, backend: str, port: int, listen: str) -> str:
    base_path = "/" if base_path in ("", "/") else "/" + base_path.strip("/") + "/"
    location = base_path if base_path != "/" else "/"
    upstream = f"http://{backend}:{port}/"

    return f"""# smart-cs 反向代理片段
# 域名：{domain}
# 部署子路径：{location}
# 后端：{upstream}
#
# ⚠️ proxy_pass 结尾的 / 会剥离 URL 前缀，必须保留；
#    前端 dist 的资源前缀与该子路径必须一致，否则静态资源 404（页面空白）。

server {{
    listen {listen};
    server_name {domain};

    client_max_body_size 20m;

    location {location} {{
        proxy_pass {upstream};
{PROXY_HEADERS}
    }}
}}
"""


def main() -> int:
    p = argparse.ArgumentParser(description="生成 smart-cs 的 Nginx 反向代理配置片段")
    p.add_argument("--domain", required=True, help="对外域名，如 www.example.com")
    p.add_argument("--base-path", default="/cs/", help="部署子路径，如 /cs/；根域名部署填 / 或留空")
    p.add_argument("--port", type=int, default=3000, help="后端监听端口，默认 3000")
    p.add_argument("--backend", default="127.0.0.1", help="后端地址，默认 127.0.0.1")
    p.add_argument("--listen", default="443 ssl", help="监听指令，默认 '443 ssl'；未配证书可改 '80'")
    p.add_argument("--out", help="写入指定文件；不传则打印到标准输出")
    args = p.parse_args()

    location = "/" if args.base_path in ("", "/") else "/" + args.base_path.strip("/") + "/"
    conf = build_conf(args.domain, args.base_path, args.backend, args.port, args.listen)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(conf)
        print(f"✅ 已写入 {args.out}")
    else:
        print(conf)

    # 部署要点提示
    print("-" * 60)
    print("部署要点：")
    print(f"  1) 管理后台访问地址：https://{args.domain}{'' if location == '/' else location}")
    print(f"  2) 网站挂件引入：<script src=\"https://{args.domain}"
          f"{'' if location == '/' else location}widget.js\"></script>")
    if location == "/":
        print("  3) 根域名部署：前端必须按根路径重新构建")
        print("     bash scripts/build_frontend.sh <目标目录> /")
    else:
        print(f"  3) 子路径部署：确保前端资源前缀也是 '{location}'")
        print(f"     bash scripts/build_frontend.sh <目标目录> {location}")
        print(f"     （或用预构建 dist，其默认前缀为 /cs/）")
    print("  4) 修改配置后：sudo nginx -t && sudo systemctl reload nginx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
