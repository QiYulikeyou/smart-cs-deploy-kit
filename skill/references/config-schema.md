# 部署配置说明（deploy/config.json）

`server/deploy/config.json` 是**一套实例一份**的部署配置：同一份代码，换一个 config 就是另一个客户的客服。

## 配置优先级

```
环境变量  >  deploy/config.json  >  内置空白默认
```

- 运行时exposed环境变量：`PORT`、`DB_PATH`、`WEB_DIST`。
- LLM / 知识库相关字段也可由环境变量覆盖（见 `server/deployConfig.js`）。
- 管理后台「⚙ 部署配置」页面保存后写入该文件，点「应用生效」即时生效（部分字段需重启才完全生效）。
- 该文件**含密钥**，已被项目 `.gitignore` 忽略，**禁止提交到任何公开仓库**。

## 字段总览

### tenant —— 企业档案（决定机器人"代表谁说话"）

| 字段 | 说明 |
|------|------|
| `name` | 公司全称（**必填**，否则机器人不知道代表哪家公司） |
| `brand` | 品牌简称 |
| `english` | 英文名 |
| `website` | 官网地址 |
| `phone` / `email` | 联系方式，机器人引导人工时会用 |
| `founded` | 成立年份文案 |
| `positioning` | 一句话公司定位 |
| `business[]` | 业务板块列表 |
| `advantages[]` | 核心优势列表 |
| `scopeNote` | 业务边界话术：客户问到范围外能力时如何引导（避免乱承诺） |
| `updated` | 更新日期标记 |

### widget —— 访客端挂件外观与文案

| 字段 | 说明 |
|------|------|
| `title` | 挂件标题，如「在线客服」 |
| `greeting` | 欢迎语（支持 `\n` 换行） |
| `placeholder` | 输入框占位文案 |
| `powered` | 底部署名 |
| `accentFrom` / `accentTo` | 主题渐变色（hex） |
| `siteToken` | 站点标识（多站点区分用，可留空） |
| `presetQuestions[]` | 预置问题，访客点击即问 |

### llm —— 大模型引擎

| 字段 | 说明 |
|------|------|
| `provider` | `api`（云端）/ `ollama`（本地）/ `offline`（离线规则） |
| `base` | API 基址，默认 `https://apihub.agnes-ai.com/v1` |
| `model` | 对话模型，默认 `agnes-2.5-flash` |
| `embed_model` | 向量模型，通常与对话模型同款 |
| `api_key` | API 密钥（**留文件里，不要提交仓库**） |

> `provider=offline` 时系统仍能启动演示，但只有规则应答、无语义向量；要真正智能必须填 `api_key` 并用 `api`。

### knowledge —— 知识库来源

| 字段 | 说明 |
|------|------|
| `kb_source` | `local`（本系统知识库）/ `ima`（腾讯 ima）/ `feishu`（飞书） |
| `ima_client_id` / `ima_api_key` / `ima_kb_id` | ima 凭据三件套 |
| `feishu_app_id` / `feishu_app_secret` / `feishu_space_ids` | 飞书应用凭据与知识空间 ID（多个用逗号分隔） |
| `feishu_sync.cron` | 同步周期表达式，默认 `0 3 * * *`（每天凌晨 3 点） |
| `feishu_sync.keyword` | 只同步含该关键词的文档，默认「常见问题」 |

## 最小可用配置示例

```json
{
  "tenant": { "name": "某某科技有限公司", "brand": "某某", "phone": "400-000-0000" },
  "widget": { "title": "在线客服", "presetQuestions": ["你们做什么业务？"] },
  "llm": {
    "provider": "api",
    "base": "https://apihub.agnes-ai.com/v1",
    "model": "agnes-2.5-flash",
    "embed_model": "agnes-2.5-flash",
    "api_key": "这里填客户提供的密钥"
  },
  "knowledge": { "kb_source": "local" }
}
```

用 `scripts/configure.py` 生成可避免手误；完整空白模板见源码包 `smart-cs-src.zip` 内 `smart-cs/server/deploy/config.json`。
