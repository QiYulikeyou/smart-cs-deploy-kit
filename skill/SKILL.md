---
name: smart-cs-deploy
version: 1.0.0
display_name: 智能客服一键部署
display_name_en: Smart CS Deploy
description_zh: "把一套完整的 AI 智能客服系统（Fastify 后端 + Vue 3 管理后台 + sql.js 存储 + 网站访客挂件 + 全量质检/知识库/派单）部署到任意网站或服务器上，支持挂到现有官网子路径（如 /cs/）或独立域名，一次交付包含管理后台、访客对话与「访客问答一键转知识库」闭环。当用户说「给网站部署智能客服」「给客户网站加个 AI 客服」「部署 smart-cs」「在 xxx.com 上挂一个在线客服」「帮我把客服系统装到服务器上」等需求时使用。自带脱敏源码模板、配置生成脚本、Nginx 配置生成器、部署自检脚本与前端重构建脚本，换台机器/换个客户也能直接跑。"
description_en: "Deploy a complete AI customer-service system (Fastify backend + Vue 3 admin + sql.js storage + website visitor chat widget + full QA/knowledge-base/dispatch) onto any website or server, either under an existing site subpath (e.g. /cs/) or a standalone domain. Trigger phrases include 'deploy AI customer service to our website', 'add a chat widget to a client site', 'deploy smart-cs'. Ships with a sanitized source template, config generator, Nginx config generator, deployment self-check and frontend rebuild scripts, so it works out of the box on any new machine or client."
agent_created: true
description: "把一套完整的 AI 智能客服系统（Fastify 后端 + Vue 3 管理后台 + sql.js 存储 + 网站访客挂件 + 全量质检/知识库/派单）部署到任意网站或服务器上，支持挂到现有官网子路径（如 /cs/）或独立域名，一次交付包含管理后台、访客对话与「访客问答一键转知识库」闭环。当用户说「给网站部署智能客服」「给客户网站加个 AI 客服」「部署 smart-cs」「在 xxx.com 上挂一个在线客服」「帮我把客服系统装到服务器上」等需求时使用。自带脱敏源码模板、配置生成脚本、Nginx 配置生成器、部署自检脚本与前端重构建脚本，换台机器/换个客户也能直接跑。"
---

<!-- 开放平台必填字段：version / display_name / display_name_en / description_zh / description_en -->

# 智能客服系统部署（smart-cs）

## Overview

把一套可立即对外服务的 AI 智能客服装到目标环境：包含**网站访客挂件**（访客直接对话）、
**管理后台**（坐席对话/知识库/话术/质检/派单/用户管理）、**零停机发布**能力。
同一份代码换一个 `deploy/config.json` 就是一个新客户的客服实例。

自带 `assets/smart-cs-src.zip` 完整源码模板（**已脱敏：无 node_modules、无数据库、无密钥**；解压得 `smart-cs/` 目录），
配合 `scripts/` 下的配置生成、Nginx 生成、环境自检、前端重构建脚本，实现"少手改、多自动化"的部署。

## 什么时候用

- "给我们的官网加个智能客服 / AI 客服"
- "帮我在 xxx.com 上部署一个在线客服（挂 /cs/）"
- "把这个客服系统装到客户服务器"
- "部署 smart-cs / 给客户复制一套客服实例"
- "客服页面白屏了 / 挂件配置拉不到" —— 也用本 skill 的排错手册定位

## 前置条件

- **源码模板**：本 skill 自带（`assets/smart-cs-src.zip`），无需从别处拷贝。
- **Node.js >= 22**（后端只用 5 个纯 JS 依赖：fastify / @fastify/cors / @fastify/static / node-cron / sql.js，**无需编译工具链**）。
- **python3**（仅运行本 skill 的辅助脚本；Windows 可用 WorkBuddy 托管 python）。
- 目标 Linux 服务器需 **Nginx + PM2**（Docker 方式则不需要 PM2）。
- LLM：**必须**有一个可用的 API Key（默认走 agnes 接入点），否则机器人只有规则应答。

## 关键原理：三个必踩的坑（动手前先读）

1. **前缀必须一致，否则白屏**
   Nginx 的 `location /cs/ { proxy_pass http://127.0.0.1:3000/; }` 中，`proxy_pass` **结尾的斜杠会剥离 `/cs` 前缀**，
   后端收到的实际是 `/api/xxx`、`/assets/xxx`。所以前端构建时的资源前缀（`VITE_BASE`）和接口前缀（`VITE_API_BASE`）
   必须与部署路径一致。自带 dist 按 `/cs/` 构建；**根域名部署必须重新构建**。

2. **`/api/*` 容易被同服务器的其他项目抢走**
   若同一台服务器还跑了别的应用且配了 `location /api/`，smart-cs 的公开接口（尤其挂件配置
   `/api/deploy/widget-config`）会被抢占，导致挂件退回默认文案。推荐整体走 `/cs/` 命名空间，
   或为该接口加精确匹配 `location = /api/deploy/widget-config`。

3. **首次启动有初始化窗口**
   后端在 `initLLM()` 完成后才开始监听端口，所以刚启动时 `/api/health` 会短暂无响应（约 5–10 秒），
   健康检查要重试，不要误判为失败。

## 标准工作流

### 1. 确认部署形态
向用户确认：域名是什么？是挂现有官网子路径（推荐 `/cs/`）还是独立根域名？据此决定是否需要重构建前端。

### 2. 部署源码到目标环境
```bash
# 解压自带源码包（得 smart-cs/ 目录）
unzip <skill>/assets/smart-cs-src.zip -d /目标路径/ && mv /目标路径/smart-cs /目标路径/my-cs
# 远程： scp <skill>/assets/smart-cs-src.zip user@server:/tmp/ && ssh user@server "unzip -o /tmp/smart-cs-src.zip -d /home/ubuntu/"
```

### 3. 生成部署配置（企业信息 + LLM 密钥）
```bash
python3 <skill>/scripts/configure.py --target /目标路径/my-cs \
    --api-key "<密钥>" --name "某某科技有限公司" --brand "某某" \
    --website https://example.com --phone 400-000-0000 --email hi@example.com \
    --preset-questions "你们主要做哪些业务?;怎么联系你们?"
```
先 `--dry-run` 预览；列表参数用**分号**分隔；密钥写入文件、预览自动脱敏。

### 4. 按需重建前端
仅在**根域名部署**或子路径不是 `/cs/` 时需要：
```bash
bash <skill>/scripts/build_frontend.sh /目标路径/my-cs /      # 根域名
bash <skill>/scripts/build_frontend.sh /目标路径/my-cs /kefu/ # 自定义子路径
```

### 5. 安装依赖并初始化
```bash
cd /目标路径/my-cs && npm install && npm run seed
```
`npm run seed` 创建默认管理员 **admin / admin123**（首次务必改密）。

### 6. 生成 Nginx 配置并生效
```bash
python3 <skill>/scripts/make_nginx_conf.py --domain www.example.com --base-path /cs/ --port 3000 --out /tmp/cs.conf
sudo cp /tmp/cs.conf /etc/nginx/conf.d/smart-cs.conf && sudo nginx -t && sudo systemctl reload nginx
```

### 7. 启动 + 自检 + 真实入口验收
```bash
pm2 start server/index.js --name smart-cs --cwd /目标路径/my-cs && pm2 save
python3 <skill>/scripts/check_env.py --target /目标路径/my-cs --base-path /cs/ --port 3000
curl -s https://域名/cs/api/health      # 期望 {"ok":true}（首次需等 5–10 秒）
```
最后把 `<script src="https://域名/cs/widget.js"></script>` 提供给客户嵌入官网。

> 生产环境推荐用内置的 `release.sh` 零停机发布（自动构建 → `releases/<版本>` → `current` 软链 → `pm2 reload`），
> 该方式下端口为 **3200**、进程名 `smart-cs-v2`。详见 `references/deployment.md`。

## 脚本清单

| 脚本 | 用途 | 典型调用 |
|------|------|---------|
| `scripts/configure.py` | 幂等生成/更新 `deploy/config.json`（密钥脱敏预览） | `--target ... --api-key ... --name ...` |
| `scripts/make_nginx_conf.py` | 按域名+子路径+端口生成 Nginx 反代配置 | `--domain ... --base-path /cs/ --port 3000` |
| `scripts/check_env.py` | 部署自检（**重点校验前端前缀 vs 部署路径是否一致**） | `--target ... --base-path ... --port ...` |
| `scripts/build_frontend.sh` | 按部署路径重构建前端，解决子路径/根路径错配 | `bash ... <目标目录> /cs/` |

## 资源清单

| 资源 | 说明 |
|------|------|
| `assets/smart-cs-src.zip` | 完整源码模板（后端 + 前端源码 + 预构建 dist），已脱敏；单文件 zip 形式随包分发（平台限制两级目录），使用前先解压 |
| `references/deployment.md` | 完整部署流程（三种方式、验收清单、升级回滚） |
| `references/config-schema.md` | `deploy/config.json` 全字段说明与优先级 |
| `references/troubleshooting.md` | 14 条真实排错表（白屏、配置丢失、API 被抢、数据跳动…） |

只在需要完整命令细节时读取 references，避免占用上下文。

## 安全红线

- **绝不**把 `deploy/config.json`（含密钥）提交到任何仓库或分享出去；多人协作时各自填自己的 key。
- 交付前检查源码 zip 是否被误写入了真实密钥 —— 模板必须保持空白（改模板改 `assets/smart-cs-src.zip`，解压→改→重压）。
- 提醒客户**首次登录立即修改默认密码** `admin/admin123`。
- 数据库是单文件 `data/app.sqljs.db`：升级/清库前先 `cp` 备份，可秒级回滚。
