# 部署流程参考（详细版）

> 本文件是 SKILL.md 中工作流的展开：给出每一步的确切命令、可选分支与验收点。
> 只有在需要完整命令细节时才加载本文件。

## 0. 物料准备：把源码放到目标环境

本 skill 自带**脱敏源码模板**，是一个 zip 包：`assets/smart-cs-src.zip`（解压后得到 `smart-cs/` 目录）：

```
smart-cs/
├── package.json            # 后端依赖（仅 5 个标准包）
├── ecosystem.config.js     # PM2 零停机配置（端口 3200）
├── release.sh              # 零停机发布脚本
├── Dockerfile / docker-compose.yml
├── server/                 # 后端源码（含 deploy/config.json 空白模板）
└── web/                    # 前端源码 + 预构建 dist（默认 /cs/ 前缀）
```

`smart-cs-src.zip` **不含** `node_modules`、`data/*.db`，也不含任何真实密钥，可直接分发。

> 说明：WorkBuddy 开放平台要求 skill 包只支持两级目录（根目录/二级目录/文件），
> 因此源码以单文件 zip 形式随包分发，使用前先解压。

解压方式：

```bash
# 本地/本机部署
unzip <skill>/assets/smart-cs-src.zip -d /目标路径/
mv /目标路径/smart-cs /目标路径/my-cs

# 远程服务器（先上传再解压）
scp <skill>/assets/smart-cs-src.zip user@server:/tmp/
ssh user@server "unzip -o /tmp/smart-cs-src.zip -d /home/ubuntu/ && mv /home/ubuntu/smart-cs /home/ubuntu/my-cs"
```

## 1. 先决定部署形态（决定后面所有步骤）

| 形态 | 适用场景 | 前端需要重构建吗 | Nginx location |
|------|---------|----------------|---------------|
| **子路径 `/cs/`** | 挂到已有官网（推荐） | 不需要（自带 dist 已按 `/cs/` 构建） | `location /cs/ { proxy_pass http://127.0.0.1:PORT/; }` |
| **根域名** | 独立域名/子域如 `kefu.example.com` | **需要**（见第 3 步） | `location / { proxy_pass http://127.0.0.1:PORT/; }` |

> ⚠️ Nginx 的 `proxy_pass ...;` **结尾斜杠会剥离前缀**：`/cs/api/health` 到后端实际是 `/api/health`。
> 因此前端资源/接口前缀必须与部署路径一致，否则浏览器请求 `/assets/...` 落到根 location → 404 → **页面空白**。

## 2. 生成部署配置（密钥/企业信息）

```bash
python3 scripts/configure.py --target /目标路径/my-cs \
    --api-key "<客户提供的 API Key>" \
    --name "某某科技有限公司" --brand "某某" \
    --website https://example.com --phone 400-000-0000 --email hi@example.com \
    --preset-questions "你们主要做哪些业务?;怎么联系你们?"
```

- 幂等：只覆盖显式传入的字段。
- `--dry-run` 先预览再写盘。
- 列表参数用**分号**分隔。
- 也可以在管理后台「⚙ 部署配置」页面图形化填写并「应用生效」，无需改文件。

## 3. 按需重建前端（仅根域名部署必须）

```bash
# 根域名部署
bash scripts/build_frontend.sh /目标路径/my-cs /

# 换成别的子路径（例如 /kefu/）
bash scripts/build_frontend.sh /目标路径/my-cs /kefu/
```

构建后确认 `my-cs/web/dist/index.html` 的资源前缀与目标路径一致。

## 4. 安装依赖并初始化

```bash
cd /目标路径/my-cs
npm install                 # 仅 5 个后端依赖，纯 JS 无编译
npm run seed                # 建库 + 默认管理员 admin/admin123
```

`npm run seed` 会等待 sql.js 加载并建表，同时写入样例数据（工单 + 知识条目），便于立即体验检索与质检。
不需要样例数据时可不执行 seed——**首次启动会自动建空库**，但要登录管理后台就必须有 admin 账号（由 seed 创建）。

## 5. 启动服务

### 方式 A：直接启动（最简单）

```bash
# 前台验证
node server/index.js        # 默认端口 3000

# 生产守护
pm2 start server/index.js --name smart-cs --cwd /目标路径/my-cs
pm2 save
```

环境变量可覆盖：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `3000` | 监听端口 |
| `DB_PATH` | `<项目>/data/app.sqljs.db` | 数据库文件 |
| `WEB_DIST` | `<项目>/web/dist` | 前端产物目录 |

### 方式 B：零停机发布（推荐用于生产）

`release.sh` 会自动构建前端 → 复制到 `releases/<时间戳>` → 切换 `current` 软链 → `pm2 reload`：

```bash
cd /目标路径/my-cs
bash release.sh              # 或 bash release.sh v1.0.1
```

该方式下 `ecosystem.config.js` 生效：进程名 `smart-cs-v2`、**端口 3200**、`cwd` 指向 `current` 软链，
数据库落在 `releases` 之外的 `data/`，发版不丢数据。Nginx 需反代到 **3200**。

### 方式 C：Docker

```bash
cd /目标路径/my-cs
docker-compose up -d --build
```

默认端口 3000，数据持久化在 `./data`。

## 6. 配置 Nginx 反代

```bash
# 子路径部署
python3 scripts/make_nginx_conf.py --domain www.example.com --base-path /cs/ --port 3000 --out /tmp/cs.conf

# 根域名部署
python3 scripts/make_nginx_conf.py --domain kefu.example.com --base-path / --port 3000 --out /tmp/cs.conf
```

落地：

```bash
sudo cp /tmp/cs.conf /etc/nginx/conf.d/smart-cs.conf
sudo nginx -t && sudo systemctl reload nginx
```

## 7. 验收清单

```bash
python3 scripts/check_env.py --target /目标路径/my-cs --base-path /cs/ --port 3000
```

再加三项真实入口验证：

```bash
curl -s https://域名/cs/api/health                 # 期望 {"ok":true}
curl -s -o /dev/null -w '%{http_code}\n' https://域名/cs/   # 期望 200（页面）
curl -s -o /dev/null -w '%{http_code}\n' https://域名/cs/assets/$(ls my-cs/web/dist/assets | head -1)
                                                   # 期望 200（静态资源可达，排白屏）
```

> 首次启动时后端会先 `initLLM()` 再监听端口，**health 接口需要等 5–10 秒**才有响应。

## 8. 把挂件嵌入客户网站

```html
<script src="https://域名/cs/widget.js"></script>
```

`widget.js` 启动时会拉取免登录接口 `/api/deploy/widget-config` 获取标题、欢迎语、配色与预置问题，
因此**不要**把它当静态文件单独 CDN 托管而不带 `/cs` 前缀，否则拿不到定制配置（会退回默认文案）。

## 9. 升级与回滚

- **方式 A**：替换 `server/`、`web/dist` 后 `pm2 restart smart-cs`。升级前备份旧代码与 `data/*.db`。
- **方式 B**：`bash release.sh` 自动切换软链；回滚把 `current` 指回上一个 `releases/<版本>` 并 `pm2 reload`。
- 数据库是单文件 `data/app.sqljs.db`，**升级前先 `cp` 一份**即可秒级回滚数据。
