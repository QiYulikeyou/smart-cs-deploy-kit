#!/usr/bin/env bash
# build_frontend.sh —— 按「部署子路径」重新构建 smart-cs 前端。
#
# 为什么需要：前端资源前缀必须与实际部署路径一致，否则 Nginx 反代后静态资源 404 → 页面空白。
#   VITE_BASE     → 静态资源前缀  (如 /cs/)
#   VITE_API_BASE → 接口调用前缀  (如 /cs)
#
# 用法：
#   bash scripts/build_frontend.sh <目标目录>            # 默认 /cs/ 子路径（挂现有官网）
#   bash scripts/build_frontend.sh <目标目录> /cs/       # 显式指定子路径
#   bash scripts/build_frontend.sh <目标目录> /          # 根域名部署（如 kefu.example.com）
set -e

TARGET="$1"
BASE="${2:-/cs/}"

if [ -z "$TARGET" ]; then
  echo "用法: bash scripts/build_frontend.sh <目标目录> [部署子路径]"
  echo "  <部署子路径> 例如 /cs/（子路径部署）或 /（根域名部署），默认 /cs/"
  exit 1
fi

WEB="$TARGET/web"
if [ ! -d "$WEB" ]; then
  echo "❌ 找不到前端目录: $WEB"
  exit 1
fi

# 归一化：/cs/ -> /cs/ 与 /cs ； / 或空 -> 根部署
if [ "$BASE" = "/" ] || [ -z "$BASE" ]; then
  VITE_BASE=""
  VITE_API_BASE=""
else
  BP="$(echo "$BASE" | sed 's#^/##; s#/$##')"
  VITE_BASE="/$BP/"
  VITE_API_BASE="/$BP"
fi

echo ">> 目标目录     : $WEB"
echo ">> 资源前缀     : ${VITE_BASE:-（根路径）}"
echo ">> 接口前缀     : ${VITE_API_BASE:-（根路径）}"

cd "$WEB"
echo ">> 安装前端依赖"
npm install --no-audit --no-fund

echo ">> 构建前端"
VITE_BASE="$VITE_BASE" VITE_API_BASE="$VITE_API_BASE" npm run build

echo
echo "✅ 构建完成。dist/index.html 的资源引用："
grep -oE '(src|href)="[^"]*"' dist/index.html || true
