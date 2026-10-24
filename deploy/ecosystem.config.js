import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// PM2 单进程配置：与贵司官网一致的零停机发布方式。
// cwd 指向 current 软链（release.sh 在发版时切换），数据落在 releases 之外的 data/ 持久化。
export default {
  apps: [{
    name: 'smart-cs-v2',
    cwd: path.join(__dirname, 'current'),        // 当前发布版本（软链）
    script: 'server/index.js',
    instances: 1,                                // 单进程
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    env: {
      NODE_ENV: 'production',
      PORT: 3200,
      // 数据库持久化在 releases 目录之外，发版不丢数据（与 db.js 默认 app.sqljs.db 一致）
      DB_PATH: path.join(__dirname, 'data', 'app.sqljs.db'),
      // 前端构建产物路径
      WEB_DIST: path.join(__dirname, 'current', 'web', 'dist')
    }
  }]
};
