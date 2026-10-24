# 排错手册

> 现象 → 根因 → 处理。每条都是在真实部署中踩过的坑。

| # | 现象 | 根因 | 处理 |
|---|------|------|------|
| 1 | 管理后台**页面全白**，接口却能通 | 前端资源前缀与 Nginx 部署路径不一致：dist 引用 `/assets/...`，而 `proxy_pass` 只转发 `/cs/...` | `bash scripts/build_frontend.sh <目标> <实际的部署子路径>`；或改用根域名部署。用 `check_env.py` 前缀校验项确认 |
| 2 | 挂件出来了，但标题/欢迎语/配色是**默认文案** | 挂件拉不到 `/api/deploy/widget-config`（见下条） | 修好 API 路由后刷新；确认 `widget.js` 的 `apiPath()` 带了正确前缀 |
| 3 | 挂件配置拉不到，**同服务器还跑了别的项目** | 别的项目的 Nginx `location /api/ { proxy_pass ...; }` **抢占**了 smart-cs 的 `/api/*` | 给 smart-cs 精确匹配：`location = /api/deploy/widget-config { proxy_pass ...; }`，或统一走 `/cs/` 前缀命名空间 |
| 4 | 机器人**只会背规则话术**，回答很"傻" | `deploy/config.json` 没填 `llm.api_key`（或 provider 仍是 `offline`） | `python3 scripts/configure.py --target ... --api-key ... --provider api` 后重启；或在后台「⚙ 部署配置」填并应用 |
| 5 | `/api/health` 刚启动时返回**空响应** | 后端在 `initLLM()` 完成后才开始监听端口，初始化期间无响应 | 这是预期行为，等待 5–10 秒再探测；自动化脚本里加重试 |
| 6 | 数据"时有时无"，对话条数来回跳 | 同一份代码用**不同启动目录/不同 DB_PATH** 跑过，产生了两个独立数据库 | 统一 `DB_PATH`（推荐 PM2/ecosystem 或环境变量显式指定），确认只有一个真实库文件 |
| 7 | 写完数据重启后**丢失** | sql.js 是内存库 + 手动落盘；进程被强杀来不及 flush | 用 `pm2 restart`/正常退出；确认 `data/` 可写且有足够磁盘；重要操作前 `cp data/app.sqljs.db` 备份 |
| 8 | 启动报写入失败 | `data/` 目录不存在或无权限 | `mkdir -p data && chmod 755 data`；容器里检查 volume 挂载 |
| 9 | 端口被占用，起不来 | 旧进程或别的服务占用 | `lsof -i :3000` / `ss -ltnp | grep 3000`；`pm2 ls` 看是否已有实例 |
| 10 | 知识库检索**命中率低** | 全库向量没用同一个 embedding 模式生成（部分条目用旧模式） | 重建向量：确保 `embed_model` 一致后重新灌/更新条目；`npm run seed` 会按当前模式重建样例向量 |
| 11 | 登录管理后台失败 | 忘记密码或没跑 seed | 默认 `admin` / `admin123`；未 seed 则无管理员账号；可在「用户管理」改密 |
| 12 | 上传服务器后 `npm install` 卡住/失败 | 服务器 Node 版本过低（<22）或 registry 不通 | 确认 `node -v >= 22`；后端只有 5 个纯 JS 依赖，无需编译工具链 |
| 13 | 页面能开但**接口 401** | 除 `/api/health`、`/api/auth/login`、`/api/deploy/widget-config`、`/api/qa/public-chat` 外都需 Bearer token | 后台正常登录后自动携带；直接 curl 需 `-H "Authorization: Bearer <token>"` |
| 14 | 改了配置没生效 | 改完未重启，或改的是另一个实例的 config.json | `pm2 restart smart-cs`；确认改动文件就是运行实例的 `server/deploy/config.json` |
