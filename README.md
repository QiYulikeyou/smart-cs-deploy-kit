# smart-cs-deploy-kit · 智能客服一键部署（v1.0.0）

把 `alexchang2025/smart-cs-deploy` **v1.0.0** 的 Skill 本体、脱敏配置模板、Nginx 片段、嵌入片段与实测记录打包成一个可直接使用的部署套件。

- **目标仓库**：`QiYulikeyou/smart-cs-deploy-kit`
- **目标分支**：`main`
- **公开落地页**：https://qiyulikeyou.github.io/smart-cs-deploy-kit/
- **上游来源**：https://github.com/alexchang2025/smart-cs-deploy/releases/tag/v1.0.0 （`smart-cs-deploy.zip`，400,908 字节，包内 `SKILL.md` 版本 `1.0.0`）

> 上游仓库 `main` 分支的 `SKILL.md` 已是 `1.0.1`，比 v1.0.0 更新。本套件严格锁定 **v1.0.0**（按需求指定版本安装）。

---

## 1. 目录结构

```
smart-cs-deploy-kit/
├── index.html                     # 公开落地页（GitHub Pages 入口）
├── README.md                      # 本文件
├── skill/                         # Skill 本体（v1.0.0，可整目录拷进 ~/.workbuddy-ai/skills/）
│   ├── SKILL.md
│   ├── assets/smart-cs-src.zip    # 脱敏源码模板（111 文件）
│   ├── references/                # deployment / config-schema / troubleshooting
│   └── scripts/                   # configure.py / make_nginx_conf.py / check_env.py / build_frontend.sh
├── deploy/
│   ├── config.example.json        # 部署配置模板（密钥已清空）
│   ├── nginx-cs.conf              # Nginx 反代片段（/cs/ 子路径）
│   └── ecosystem.config.js        # PM2 进程配置
└── embed/
    └── snippet.html               # 挂到任意网站的访客挂件片段
```

---

## 2. 依赖

| 依赖 | 版本要求 | 用途 | 本机实测 |
|---|---|---|---|
| Node.js | **>= 22** | 后端运行时（`package.json` 的 `engines`） | 22.22.2 ✅ |
| Python | 3.x | 仅跑 skill 的辅助脚本 | 3.13.14 ✅ |
| Nginx | 任意稳定版 | 生产反代（子路径 / 独立域名） | 未装（本地直连 Node 验证） |
| PM2 | 可选 | 进程守护（Docker 方式不需要） | 未装 |
| LLM API Key | **必需**（否则只有规则应答） | 语义问答 + 向量 | 未提供 → 本次跑 `offline` |

后端只有 5 个纯 JS 依赖，**无需编译工具链**：

```
fastify  @fastify/cors  @fastify/static  node-cron  sql.js
```

---

## 3. 环境变量

优先级：**环境变量 > `deploy/config.json` > 内置默认**。

| 变量 | 默认 | 说明 |
|---|---|---|
| `PORT` | `3000` | 后端监听端口 |
| `DB_PATH` | `data/app.sqljs.db` | sql.js 单文件数据库路径，**备份即复制文件** |
| `WEB_DIST` | `web/dist` | 管理后台构建产物目录 |
| `AUTH_SECRET` | 内置默认值 | JWT 签名密钥，**生产必须设置**，否则启动会告警 |
| `AUTH_TOKEN_TTL` | 内置 | 登录令牌有效期 |
| `LLM_PROVIDER` | `offline` | `api` / `ollama` / `offline` |
| `LLM_API_KEY` | 空 | 云端大模型密钥 |
| `LLM_API_BASE` | `https://apihub.agnes-ai.com/v1` | 云端 API 基址 |
| `LLM_MODEL` | `agnes-2.5-flash` | 对话模型 |
| `EMBED_MODEL` / `EMBED_API_BASE` / `EMBED_API_KEY` | 同 LLM | 向量模型（可与对话模型分开） |
| `OLLAMA_HOST` / `OLLAMA_LLM_MODEL` / `OLLAMA_EMBED_MODEL` | — | 本地 Ollama 模式 |

---

## 4. 配置项（`deploy/config.json`）

**一个实例一份配置，换一份 config 就是另一个客户的客服。**
模板见 `deploy/config.example.json`。⚠️ 该文件**含密钥**，已被 `.gitignore` 忽略，**禁止提交到公开仓库**。

| 分组 | 关键字段 | 说明 |
|---|---|---|
| `tenant` | `name`（必填）、`brand`、`english`、`website`、`phone`、`email`、`positioning`、`business[]`、`advantages[]`、`scopeNote` | 决定机器人「代表谁说话」；`scopeNote` 是业务边界话术，避免乱承诺 |
| `widget` | `title`、`greeting`、`placeholder`、`powered`、`accentFrom`/`accentTo`、`siteToken`、`presetQuestions[]` | 访客挂件的外观与文案 |
| `llm` | `provider`、`base`、`model`、`embed_model`、`api_key` | `offline` 可启动演示但只有规则应答 |
| `knowledge` | `kb_source`（`local`/`ima`/`feishu`）、`ima_api_key`、`ima_kb_id` | 知识库来源 |

生成/更新配置（幂等，密钥在预览中脱敏）：

```bash
python skill/scripts/configure.py --target ./smart-cs \
  --name "你的公司全称" --brand "简称" --website "https://example.com" \
  --provider api --api-key "sk-..." --model "agnes-2.5-flash"
```

---

## 5. 部署步骤

### 5.1 本地跑通（最快验证，无需 Nginx）

```bash
unzip skill/assets/smart-cs-src.zip -d . && mv smart-cs my-cs && cd my-cs
npm install                      # 5 个依赖，约 15 秒
node server/seed.js              # ⚠️ 必须在服务停止时执行，见「已知问题 2」
PORT=3100 node server/index.js
```

> 自带 `web/dist` 是按 `/cs/` 构建的。**直接访问根路径会白屏**（资源 404）。
> 根路径部署必须先重构建：`bash skill/scripts/build_frontend.sh ./my-cs /`

### 5.2 子路径部署（推荐，挂现有官网 `/cs/`）

```bash
bash skill/scripts/build_frontend.sh ./my-cs /cs/
python skill/scripts/make_nginx_conf.py --domain www.example.com --base-path /cs/ --port 3000 \
  --out /etc/nginx/conf.d/smart-cs.conf
sudo nginx -t && sudo systemctl reload nginx
pm2 start deploy/ecosystem.config.js && pm2 save
```

### 5.3 独立域名部署

```bash
bash skill/scripts/build_frontend.sh ./my-cs /
python skill/scripts/make_nginx_conf.py --domain kefu.example.com --base-path / --port 3000
```

### 5.4 嵌入到任意网站

见 `embed/snippet.html`，核心就一行：

```html
<script src="https://你的域名/cs/widget.js" data-site-token=""></script>
```

---

## 6. 验收清单

| 检查项 | 命令 | 期望 |
|---|---|---|
| 健康检查 | `curl -s localhost:3000/api/health` | `{"ok":true,...}`；**首次启动需等 5–10 秒** |
| 挂件配置 | `curl -s localhost:3000/api/deploy/widget-config` | 返回 `title`/`greeting`，**不含任何密钥** |
| 登录 | `POST /api/auth/login {"username":"admin","password":"admin123"}` | 返回 `token` |
| 鉴权接口 | `curl -H "Authorization: Bearer <token>" /api/knowledge` | 200（无 token 应 401） |
| 访客问答 | `POST /api/qa/public-chat {"message":"..."}` | 返回 `reply` |
| 管理后台 | 浏览器打开 `/` 或 `/cs/` | 登录页正常渲染，无白屏 |

---

## 7. 已知问题与解法（本次实测）

### 1）前端资源前缀不匹配 → 白屏

自带 `dist` 引用 `/cs/assets/...`。直连 Node 根路径时 `/cs/assets/*` 落到 SPA 兜底，返回 `text/html`，
浏览器报 `Failed to load module script: ... MIME type of "text/html"`。

**解法**：要么按 `/cs/` 反代（`proxy_pass` 结尾保留 `/` 以剥离前缀），要么 `build_frontend.sh <dir> /` 重构建。
本次采用后者，重构建耗时 959ms。

### 2）`seed` 必须在服务停止时执行

sql.js 是**内存库**，服务运行期间每次写操作都会把内存状态 flush 回文件。
服务在跑时执行 `node server/seed.js`，种子数据会被服务下一次写操作**覆盖**（表现为「seed 成功但登录一直失败、用户表为空」）。

**解法**：停服务 → `node server/seed.js` → 起服务。本次实测按此顺序后 `admin/admin123` 登录成功。

### 3）Windows Git Bash 会把 `/cs/` 转成 Windows 路径

`--base-path /cs/` 在 Git Bash 下被 MSYS 转成 `D:/.../PortableGit/cs/`，生成的 Nginx 配置直接作废。

**解法**：`MSYS_NO_PATHCONV=1`，且脚本路径改用 Windows 形式（`C:/...`）。

### 4）GitHub Pages 不能托管这个后端

Fastify 需要常驻 Node 进程 + 可写数据库文件。Pages 是纯静态托管，**只能放落地页和文档，跑不了服务**。
要「所有人公开访问可交互的客服」，必须有能跑 Node 的宿主（自有 VPS / Railway / Render / Fly 等）。

---

## 8. 安全说明

- `skill/` 下 4 个脚本已逐个审阅：无外联请求、无 `rmtree`、不读取 `~/.ssh`、不写系统目录。
  `check_env.py` 仅执行 `node --version` 并删除自己创建的探针文件。
- `deploy/config.example.json` 中所有密钥字段已清空。
- 源码模板上游声明已脱敏（无 node_modules / 无数据库 / 无真实密钥）。
- 上游仓库**无 LICENSE 文件**，商用前请自行与作者确认授权。
