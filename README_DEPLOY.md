# Ombre Memory Gateway 部署与改造说明书

> 目标：在一台 VPS 上重新部署一个独立目录的新项目，参考 Ombre-Brain 原版与 PDF 二改版，构建一个“主动召回型记忆网关”。
>
> 本文件用于避免后续对话压缩后遗漏关键需求、架构决策和部署步骤。

---

## 0. 项目定位

本项目不是简单复刻 Ombre-Brain，也不是完全替换成普通 RAG。

目标是做一个：

```text
Ombre Memory Gateway
= Ombre-Brain 情绪记忆机制
+ 主模型前置自动召回
+ Anthropic-compatible 网关
+ OpenAI-compatible 网关
+ 可选自定义 /chat 接口
+ MCP 工具保留
+ 后续可扩展日记/知识库管理层
```

核心需求：

1. 保留 Ombre-Brain 的记忆工作原理：
   - 情感坐标 valence / arousal；
   - importance 重要度；
   - activation_count 激活次数；
   - 遗忘曲线衰减；
   - pinned / resolved / archived 等状态；
   - 关键词 + 向量混合检索；
   - 主动浮现 breath；
   - hold / grow / trace / dream / pulse 等 MCP 工具。

2. 新增“前置自动召回网关”：
   - 主模型不主动调用工具时，也能自动获得相关记忆；
   - 用户消息进入主模型前，网关自动调用 Ombre 的召回逻辑；
   - 召回结果注入 system/context；
   - 再转发给真实主模型。

3. 优先支持 Anthropic-compatible 接口：
   - `POST /v1/messages`

4. 同时搭建 OpenAI-compatible 接口：
   - `POST /v1/chat/completions`

5. 保留调试与自定义接口：
   - `POST /api/auto-recall`：只看自动召回结果，不调用主模型；
   - `POST /chat`：自定义聊天接口，方便自家前端传 room、character、memory debug 等高级参数。

6. VPS 上已有旧项目，但本次部署新建独立目录，不依赖旧目录，不覆盖旧项目。

---

## 1. 总体架构

### 1.1 原始 Ombre-Brain 形态

```text
Claude / 客户端
   ↓ MCP 工具调用
Ombre-Brain
   ↓
Markdown 记忆桶 / Obsidian / SQLite embedding cache
```

问题：

```text
如果主模型不调用 breath，记忆不会被召回。
```

### 1.2 改造后的网关形态

```text
客户端 / 前端 / Claude-compatible Client / OpenAI-compatible Client
   ↓
Ombre Memory Gateway
   ├─ 解析请求
   ├─ 自动构造 recall query
   ├─ 调用 Ombre-Brain 内部 breath 逻辑
   ├─ 召回相关记忆
   ├─ 注入 system/context
   ├─ 转发给真实主模型 API
   ↓
真实模型 Anthropic / OpenAI / DeepSeek / Gemini / OpenAI-compatible Provider
   ↓
返回响应
```

### 1.3 MCP 工具仍然保留

自动召回不删除工具。

分工：

```text
网关自动召回：每轮默认执行，保证主模型不用主动调用工具也能“记得”。

MCP 工具：用于主模型主动精查、写入、修改、做梦、自省、系统状态查看。
```

---

## 2. 参考来源

### 2.1 Ombre-Brain 原版

仓库：

```text
https://github.com/P0luz/Ombre-Brain
```

核心特性：

- Markdown 记忆桶；
- YAML frontmatter 元数据；
- Russell valence/arousal 情感坐标；
- importance；
- activation_count；
- pinned / resolved / digested；
- dynamic / permanent / feel / archived 类型；
- 关键词模糊检索 + embedding 语义检索；
- 改进版艾宾浩斯遗忘曲线；
- breath / hold / grow / trace / pulse / dream MCP 工具；
- Dashboard；
- Obsidian 原生兼容。

### 2.2 PDF 二改版参考点

PDF 名称：`记忆模块-搭建说明书7647561460159909134.pdf`

值得借鉴的设计：

1. 结构化记忆与日记/知识库分层：

```text
memories：短条结构化记忆，带情绪坐标和重要度；
knowledge_documents：日记/知识库原文；
knowledge_chunks：长文档切块 + embedding。
```

2. 两种召回范式：

```text
结构化记忆：主动浮现，按重要度 × 激活次数 × 时间衰减 × 情感强度打分；
日记/知识库：向量语义检索。
```

3. 每轮被动自动检索注入上下文：

```text
聊天中模型可用工具主动检索；
同时系统每轮自动检索并注入上下文。
```

4. per-room / per-character 隔离。

5. pinned 记忆独立成段，不挤占普通召回名额。

6. 低分记忆软归档，可恢复。

7. 日记原文与抽取记忆通过 source 字段双向关联：

```text
source = old-diary:<文件名>
```

8. 日记重抽使用非破坏性审阅合并流程：

```text
重抽预览 → 新旧语义配对 → 人工逐条选择 → 确认后事务落库
```

---

## 3. 第一阶段范围

第一阶段不要一次做太大。

### 3.1 第一阶段必须完成

1. 新建独立部署目录。
2. 部署 Ombre-Brain 最新原版代码作为基础。
3. 保留原 MCP 工具。
4. 新增自动召回模块：
   - `auto_recall.py`
   - 从 messages 中构造 recall query；
   - 调用原 breath 检索逻辑；
   - 格式化 memory context。
5. 新增 Anthropic-compatible 网关：
   - `POST /v1/messages`
   - 支持非流式；
   - 尽量支持流式，若第一版复杂，可先非流式跑通。
6. 新增 OpenAI-compatible 网关：
   - `POST /v1/chat/completions`
   - 支持非流式；
   - 流式可第二步完善。
7. 新增调试接口：
   - `POST /api/auto-recall`
8. 新增简单自定义聊天接口：
   - `POST /chat`
9. 使用环境变量配置主模型、功能模型、记忆召回参数。
10. 写 Docker Compose 部署方式。

### 3.2 第一阶段暂不强制完成

1. PostgreSQL + pgvector 迁移。
2. 日记/知识库完整管理后台。
3. 日记重抽审阅 UI。
4. 多角色复杂权限系统。
5. 高级可视化记忆网络。

这些作为第二阶段或第三阶段。

---

## 4. 目录规划

VPS 上建议新建目录：

```bash
/opt/ombre-memory-gateway
```

或用户目录：

```bash
~/ombre-memory-gateway
```

推荐目录结构：

```text
ombre-memory-gateway/
  app/
    server.py
    bucket_manager.py
    decay_engine.py
    dehydrator.py
    embedding_engine.py
    utils.py
    auto_recall.py
    memory_injector.py
    llm_clients.py
    gateway_config.py
    gateway_models.py
    import_memory.py
    dashboard.html
    ...原 Ombre-Brain 文件
  buckets/
    dynamic/
    permanent/
    feel/
    archived/
  data/
    dehydration_cache.db
    embeddings.db 或原项目使用的 SQLite 文件
  logs/
  config.yaml
  config.example.yaml
  .env
  docker-compose.yml
  Dockerfile
  README_DEPLOY.md
```

若直接基于原仓库结构，也可以保持原结构，只新增文件。

---

## 5. 关键接口设计

### 5.1 `POST /api/auto-recall`

用途：调试自动召回，不调用主模型。

请求示例：

```json
{
  "room": "default",
  "character_id": "default",
  "messages": [
    {"role": "user", "content": "我今天有点累"}
  ],
  "max_memories": 8,
  "max_tokens": 3000,
  "include_pinned": true,
  "include_related": true,
  "debug": true
}
```

响应示例：

```json
{
  "query": "用户最新消息：我今天有点累",
  "memory_context": "[长期记忆召回]\n...\n[/长期记忆召回]",
  "memories": [
    {
      "id": "abc123",
      "name": "近期睡眠问题",
      "content": "...",
      "score": 0.82,
      "importance": 8,
      "valence": 0.35,
      "arousal": 0.7,
      "source": "ombre"
    }
  ],
  "debug": {
    "strategy": "pinned + related + breath(query)",
    "token_estimate": 1200
  }
}
```

### 5.2 `POST /v1/messages` Anthropic-compatible

请求示例：

```json
{
  "model": "claude-3-5-sonnet-latest",
  "system": "你是一个助手。",
  "messages": [
    {"role": "user", "content": "我今天有点累"}
  ],
  "max_tokens": 2048,
  "temperature": 0.8,
  "stream": false
}
```

网关处理：

```text
1. 读取 system 与 messages；
2. 构造 recall query；
3. 自动召回记忆；
4. 将 memory_context 追加到 system；
5. 转发到真实 Anthropic API；
6. 返回 Anthropic 格式响应。
```

记忆注入方式：

```text
原 system

[长期记忆召回]
以下记忆由系统自动召回，可能与当前对话相关。请自然参考，不要机械复述；如果明显无关，可以忽略。

1. ...
2. ...
[/长期记忆召回]
```

### 5.3 `POST /v1/chat/completions` OpenAI-compatible

请求示例：

```json
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "system", "content": "你是一个助手。"},
    {"role": "user", "content": "我今天有点累"}
  ],
  "temperature": 0.8,
  "stream": false
}
```

网关处理：

```text
1. 读取 messages；
2. 找到 system message；
3. 构造 recall query；
4. 自动召回记忆；
5. 插入或追加 system memory_context；
6. 转发到真实 OpenAI-compatible API；
7. 返回 OpenAI-compatible 格式响应。
```

### 5.4 `POST /chat` 自定义接口

用途：自家前端高级调用。

请求示例：

```json
{
  "room": "default",
  "user_id": "default-user",
  "character_id": "default-character",
  "provider": "anthropic",
  "model": "claude-3-5-sonnet-latest",
  "system": "你是一个助手。",
  "messages": [
    {"role": "user", "content": "我今天有点累"}
  ],
  "memory": {
    "enabled": true,
    "include_pinned": true,
    "include_related": true,
    "max_memories": 8,
    "max_tokens": 3000,
    "debug": false
  },
  "stream": false,
  "temperature": 0.8,
  "max_tokens": 2048
}
```

后端职责：

```text
1. 接收前端请求；
2. 识别 room / user / character；
3. 自动召回对应空间的记忆；
4. 注入 system；
5. 按 provider 调用真实模型；
6. 返回统一响应；
7. 可选返回 memory debug。
```

---

## 6. 自动召回策略

### 6.1 recall query 构造

不要只使用最新一句用户消息。

推荐使用：

```text
最近 N 轮对话 + 最新用户消息
```

环境变量：

```env
OMBRE_AUTO_RECALL_RECENT_TURNS=6
```

query 格式示例：

```text
以下是最近对话片段，用于检索长期记忆：
user: ...
assistant: ...
user: 我今天有点累
```

### 6.2 召回来源

第一阶段：

```text
1. pinned 核心记忆；
2. breath(query=...) 相关记忆；
3. breath() 可选主动浮现。
```

后续阶段：

```text
4. 日记/知识库 chunks 向量检索。
```

### 6.3 pinned 独立成段

pinned 不应与普通记忆争抢名额。

注入格式：

```text
[核心记忆]
- ...

[本轮相关记忆]
- ...
```

### 6.4 token 预算

环境变量：

```env
OMBRE_AUTO_RECALL_MAX_TOKENS=3000
OMBRE_AUTO_RECALL_MAX_MEMORIES=8
OMBRE_AUTO_RECALL_PINNED_LIMIT=5
```

若超出预算：

```text
优先保留 pinned；
再保留高分相关记忆；
低分记忆截断或丢弃。
```

### 6.5 注入提示词

推荐固定模板：

```text
[长期记忆召回]
以下记忆由系统自动召回，可能与当前对话相关。请自然参考，不要机械复述；如果某条明显无关，请忽略。不要向用户暴露内部检索过程，除非用户主动询问。

[核心记忆]
1. ...

[本轮相关记忆]
1. ...
[/长期记忆召回]
```

---

## 7. 配置与环境变量

### 7.1 基础配置

`.env` 示例：

```env
# 服务
OMBRE_HOST=0.0.0.0
OMBRE_PORT=8000
OMBRE_TRANSPORT=streamable-http
OMBRE_BUCKETS_DIR=/data/buckets

# Dashboard，可选
OMBRE_DASHBOARD_PASSWORD=change-me

# 原 Ombre 功能模型 API Key
# 用于脱水、自动打标、embedding 等。部署时再询问用户具体供应商。
OMBRE_API_KEY=
OMBRE_BASE_URL=
```

### 7.2 网关开关

```env
OMBRE_GATEWAY_ENABLED=true
OMBRE_AUTO_RECALL_ENABLED=true
OMBRE_AUTO_RECALL_RECENT_TURNS=6
OMBRE_AUTO_RECALL_MAX_MEMORIES=8
OMBRE_AUTO_RECALL_MAX_TOKENS=3000
OMBRE_AUTO_RECALL_PINNED_LIMIT=5
OMBRE_AUTO_RECALL_INCLUDE_PINNED=true
OMBRE_AUTO_RECALL_INCLUDE_RELATED=true
OMBRE_AUTO_RECALL_INCLUDE_FLOATING=false
OMBRE_AUTO_RECALL_DEBUG=false
```

### 7.3 主模型配置

部署时需要向用户询问：

```text
主模型 provider 是什么？
- anthropic
- openai
- openai_compatible
- deepseek
- gemini
- ollama
```

环境变量示例：

#### Anthropic 主模型

```env
OMBRE_MAIN_MODEL_PROVIDER=anthropic
OMBRE_MAIN_MODEL_BASE_URL=https://api.anthropic.com
OMBRE_MAIN_MODEL_API_KEY=你的_anthropic_key
OMBRE_MAIN_MODEL_NAME=claude-3-5-sonnet-latest
OMBRE_MAIN_MODEL_VERSION=2023-06-01
```

#### OpenAI 主模型

```env
OMBRE_MAIN_MODEL_PROVIDER=openai
OMBRE_MAIN_MODEL_BASE_URL=https://api.openai.com
OMBRE_MAIN_MODEL_API_KEY=你的_openai_key
OMBRE_MAIN_MODEL_NAME=gpt-4o-mini
```

#### DeepSeek / OpenAI-compatible 主模型

```env
OMBRE_MAIN_MODEL_PROVIDER=openai_compatible
OMBRE_MAIN_MODEL_BASE_URL=https://api.deepseek.com
OMBRE_MAIN_MODEL_API_KEY=你的_deepseek_key
OMBRE_MAIN_MODEL_NAME=deepseek-chat
```

#### Ollama 主模型

```env
OMBRE_MAIN_MODEL_PROVIDER=openai_compatible
OMBRE_MAIN_MODEL_BASE_URL=http://host.docker.internal:11434/v1
OMBRE_MAIN_MODEL_API_KEY=ollama
OMBRE_MAIN_MODEL_NAME=llama3.1
```

### 7.4 功能性模型配置

部署时再询问用户。

功能性模型包括：

1. 记忆脱水/压缩模型；
2. 记忆自动打标模型；
3. 日记抽取模型；
4. embedding 模型。

建议配置：

```env
# 脱水/打标/抽取
OMBRE_FUNCTION_MODEL_PROVIDER=openai_compatible
OMBRE_FUNCTION_MODEL_BASE_URL=
OMBRE_FUNCTION_MODEL_API_KEY=
OMBRE_FUNCTION_MODEL_NAME=

# embedding
OMBRE_EMBEDDING_PROVIDER=openai_compatible
OMBRE_EMBEDDING_BASE_URL=
OMBRE_EMBEDDING_API_KEY=
OMBRE_EMBEDDING_MODEL=
OMBRE_EMBEDDING_DIMENSIONS=1536
```

若沿用 Ombre 原版 Gemini：

```env
OMBRE_API_KEY=你的_google_ai_studio_key
OMBRE_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
OMBRE_EMBEDDING_MODEL=gemini-embedding-001
OMBRE_EMBEDDING_DIMENSIONS=3072
```

若参考 PDF 二改版：

```env
OMBRE_EMBEDDING_MODEL=text-embedding-3-small
OMBRE_EMBEDDING_DIMENSIONS=1536
```

---

## 8. Docker Compose 部署草案

### 8.1 `docker-compose.yml`

```yaml
services:
  ombre-memory-gateway:
    build: .
    container_name: ombre-memory-gateway
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "18001:8000"
    volumes:
      - ./buckets:/data/buckets
      - ./data:/data/appdata
      - ./logs:/app/logs
      - ./config.yaml:/app/config.yaml:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
```

### 8.2 Dockerfile 草案

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["python", "server.py"]
```

---

## 9. VPS 部署步骤

### 9.1 登录 VPS

```bash
ssh root@你的服务器IP
```

或普通用户：

```bash
ssh your_user@你的服务器IP
```

### 9.2 安装基础依赖

Ubuntu/Debian：

```bash
sudo apt update
sudo apt install -y git curl vim ufw ca-certificates
```

安装 Docker：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable docker
sudo systemctl start docker
```

安装 compose 插件通常 Docker 官方脚本会一起处理。检查：

```bash
docker --version
docker compose version
```

### 9.3 新建独立目录

```bash
sudo mkdir -p /opt/ombre-memory-gateway
sudo chown -R $USER:$USER /opt/ombre-memory-gateway
cd /opt/ombre-memory-gateway
```

### 9.4 拉取原版代码

优先 GitHub：

```bash
git clone https://github.com/P0luz/Ombre-Brain.git app
```

如果 GitHub 不稳定：

```bash
git clone https://git.p0lar1s.uk/P0lar1s/Ombre_Brain.git app
```

进入目录：

```bash
cd /opt/ombre-memory-gateway/app
```

### 9.5 新建数据目录

```bash
cd /opt/ombre-memory-gateway
mkdir -p buckets data logs
```

### 9.6 配置 `.env`

```bash
cd /opt/ombre-memory-gateway/app
cp config.example.yaml config.yaml || true
nano .env
```

填入基础内容，模型相关部署时再问用户。

### 9.7 加入网关改造代码

需要新增或修改：

```text
auto_recall.py
memory_injector.py
llm_clients.py
gateway_config.py
gateway_models.py
server.py
requirements.txt
config.example.yaml
ENV_VARS.md
```

如果改造后 Docker Compose 放在项目根目录，则也需要：

```text
Dockerfile
docker-compose.yml
```

### 9.8 启动

```bash
cd /opt/ombre-memory-gateway/app
docker compose up -d --build
```

若 compose 文件放在 `/opt/ombre-memory-gateway` 根目录：

```bash
cd /opt/ombre-memory-gateway
docker compose up -d --build
```

### 9.9 查看日志

```bash
docker logs -f ombre-memory-gateway
```

### 9.10 健康检查

```bash
curl http://127.0.0.1:18001/health
```

期望：

```json
{"status":"ok", ...}
```

---

## 10. 接口测试命令

### 10.1 auto-recall 测试

```bash
curl -X POST http://127.0.0.1:18001/api/auto-recall \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "我今天有点累"}
    ],
    "max_memories": 8,
    "max_tokens": 3000,
    "debug": true
  }'
```

### 10.2 Anthropic-compatible 测试

```bash
curl -X POST http://127.0.0.1:18001/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: gateway-local-test" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-latest",
    "system": "你是一个助手。",
    "messages": [
      {"role": "user", "content": "我今天有点累"}
    ],
    "max_tokens": 512,
    "stream": false
  }'
```

注意：`x-api-key` 对客户端来说可以是网关 token；网关内部使用 `.env` 中真实主模型 API key。

### 10.3 OpenAI-compatible 测试

```bash
curl -X POST http://127.0.0.1:18001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer gateway-local-test" \
  -d '{
    "model": "deepseek-chat",
    "messages": [
      {"role": "system", "content": "你是一个助手。"},
      {"role": "user", "content": "我今天有点累"}
    ],
    "temperature": 0.8,
    "stream": false
  }'
```

### 10.4 自定义 `/chat` 测试

```bash
curl -X POST http://127.0.0.1:18001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "anthropic",
    "model": "claude-3-5-sonnet-latest",
    "system": "你是一个助手。",
    "messages": [
      {"role": "user", "content": "我今天有点累"}
    ],
    "memory": {
      "enabled": true,
      "debug": true
    },
    "stream": false,
    "max_tokens": 512
  }'
```

---

## 11. 反向代理与 HTTPS

如果需要公网访问，建议用 Nginx/Caddy 反代。

### 11.1 Caddy 推荐配置

域名示例：

```text
memory.example.com
```

Caddyfile：

```caddy
memory.example.com {
    reverse_proxy 127.0.0.1:18001
}
```

Caddy 会自动申请 HTTPS。

### 11.2 Nginx 示例

```nginx
server {
    listen 80;
    server_name memory.example.com;

    location / {
        proxy_pass http://127.0.0.1:18001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

如需流式 SSE，要确保关闭缓冲：

```nginx
proxy_buffering off;
proxy_cache off;
```

---

## 12. 安全要求

### 12.1 不要裸奔公网

如果暴露到公网，至少需要一种鉴权：

```text
1. 网关 API token；
2. Basic Auth；
3. 反代层访问控制；
4. VPN / Tailscale / Cloudflare Access。
```

### 12.2 建议新增网关访问 token

环境变量：

```env
OMBRE_GATEWAY_AUTH_TOKEN=一个长随机字符串
```

OpenAI-compatible：

```http
Authorization: Bearer <token>
```

Anthropic-compatible：

```http
x-api-key: <token>
```

### 12.3 日志脱敏

日志不要输出完整记忆内容和完整用户消息。

只记录：

```text
request_id
provider
model
message_count
query_length
recalled_count
latency_ms
error_type
```

不要记录：

```text
完整聊天正文
完整记忆正文
API key
Authorization header
```

---

## 13. 后续数据库化路线

第一阶段沿用 Ombre 原 Markdown 桶。

第二阶段可以引入 PostgreSQL + pgvector，参考 PDF 二改版。

### 13.1 结构化记忆表

```sql
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  content TEXT NOT NULL,
  name TEXT,
  tags TEXT[],
  domain TEXT,
  valence DOUBLE PRECISION,
  arousal DOUBLE PRECISION,
  importance INTEGER,
  is_pinned BOOLEAN DEFAULT FALSE,
  is_resolved BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  source TEXT,
  author TEXT,
  room TEXT DEFAULT 'default',
  character_id TEXT DEFAULT 'default',
  activation_count DOUBLE PRECISION DEFAULT 0,
  created_at TIMESTAMP DEFAULT now(),
  last_activated_at TIMESTAMP
);
```

### 13.2 知识文档表

```sql
CREATE TABLE knowledge_documents (
  id TEXT PRIMARY KEY,
  source_name TEXT,
  original_content TEXT,
  file_type TEXT,
  room TEXT DEFAULT 'default',
  character_id TEXT DEFAULT 'default',
  created_at TIMESTAMP DEFAULT now()
);
```

### 13.3 知识切块表

```sql
CREATE TABLE knowledge_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT REFERENCES knowledge_documents(id) ON DELETE CASCADE,
  source_name TEXT,
  chunk_index INTEGER,
  content TEXT,
  embedding vector(1536),
  room TEXT DEFAULT 'default',
  character_id TEXT DEFAULT 'default',
  created_at TIMESTAMP DEFAULT now()
);
```

注意：embedding 维度要跟实际模型一致。

---

## 14. 需要在部署时询问用户的信息

部署前必须确认：

### 14.1 VPS 信息

```text
1. 操作系统：Ubuntu/Debian/CentOS？
2. 是否已有 Docker 和 docker compose？
3. 是否有域名？
4. 是否需要公网访问？
5. 是否使用 Caddy/Nginx/Cloudflare Tunnel？
```

### 14.2 主模型信息

```text
1. 主模型 provider：Anthropic / OpenAI / DeepSeek / Gemini / OpenAI-compatible / Ollama？
2. 主模型 API key？
3. 主模型 base_url？
4. 主模型名称？
5. 是否需要流式输出？
```

### 14.3 功能模型信息

```text
1. 记忆脱水/压缩用哪个模型？
2. 记忆自动打标用哪个模型？
3. embedding 用哪个模型？
4. 日记抽取用哪个模型？
5. 是否希望功能模型和主模型分开？
```

### 14.4 记忆配置

```text
1. 是否挂载 Obsidian Vault？
2. 记忆桶目录放哪里？
3. 是否迁移旧 Ombre-Brain 记忆？
4. 是否启用 room / character 隔离？
5. 初始 token 预算多少？
```

### 14.5 安全配置

```text
1. 网关是否公网暴露？
2. 使用什么鉴权 token？
3. Dashboard 是否启用密码？
4. 是否限制 IP？
```

---

## 15. 推荐第一版默认选择

如果用户没有特殊要求，推荐：

```text
部署方式：Docker Compose
项目目录：/opt/ombre-memory-gateway
外部端口：18001
存储方式：沿用 Ombre Markdown buckets
主入口：/v1/messages Anthropic-compatible
附加入口：/v1/chat/completions OpenAI-compatible
调试入口：/api/auto-recall
自定义入口：/chat 简单版
自动召回：开启
recent_turns：6
max_memories：8
max_tokens：3000
pinned_limit：5
公网访问：先不暴露，或用 Caddy + token
```

---

## 16. 开发实现顺序

### Step 1：确认原版可运行

```text
先确保原 Ombre-Brain health、MCP、Dashboard 正常。
```

### Step 2：抽出自动召回模块

新增：

```text
auto_recall.py
```

实现：

```python
build_recall_query(messages, recent_turns)
recall_memories(query, options)
format_memory_context(memories)
```

### Step 3：实现记忆注入模块

新增：

```text
memory_injector.py
```

实现：

```python
inject_into_anthropic(system, memory_context)
inject_into_openai(messages, memory_context)
```

### Step 4：实现模型转发模块

新增：

```text
llm_clients.py
```

实现：

```python
call_anthropic(payload)
call_openai_compatible(payload)
```

第一版先支持非流式。

### Step 5：注册接口

修改：

```text
server.py
```

新增路由：

```text
POST /api/auto-recall
POST /v1/messages
POST /v1/chat/completions
POST /chat
```

### Step 6：测试 auto-recall

先不要调用主模型，确认记忆召回结果合理。

### Step 7：测试 Anthropic-compatible

确认请求能被网关接收、注入记忆、转发、返回。

### Step 8：测试 OpenAI-compatible

确认通用客户端可以接入。

### Step 9：补流式输出

SSE 流式转发较容易出坑，建议非流式稳定后再做。

---

## 17. 非目标与注意事项

1. 第一版不要重构所有 Ombre 内部逻辑。
2. 第一版不要强行上 PostgreSQL。
3. 第一版不要把写入记忆也完全自动化，否则容易存垃圾记忆。
4. 自动召回可以默认开启，但自动写入建议仍由主模型工具或人工控制。
5. 记忆注入不要过长，避免污染主模型上下文。
6. 召回内容必须标注“可能相关，可忽略”，降低错误召回影响。
7. 外部 API key 不写入日志。
8. 旧项目暂时不动，后续确认后再迁移旧记忆。

---

## 18. 最终目标图

```text
                        ┌───────────────────────┐
                        │  Client / Frontend      │
                        │  Claude-style / OpenAI  │
                        └───────────┬───────────┘
                                    ↓
                        ┌───────────────────────┐
                        │ Ombre Memory Gateway   │
                        │                       │
                        │ /v1/messages           │
                        │ /v1/chat/completions   │
                        │ /chat                  │
                        │ /api/auto-recall       │
                        └───────────┬───────────┘
                                    ↓
              ┌─────────────────────┼─────────────────────┐
              ↓                     ↓                     ↓
     ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
     │ Auto Recall     │    │ Memory Inject  │    │ LLM Proxy       │
     │ breath/query    │    │ system/context │    │ Anthropic/OpenAI │
     └───────┬────────┘    └────────────────┘    └───────┬────────┘
             ↓                                             ↓
     ┌────────────────────┐                       ┌────────────────────┐
     │ Ombre Core          │                       │ Main Model API      │
     │ buckets/decay/embed │                       │ Claude/DeepSeek/etc │
     └────────────────────┘                       └────────────────────┘
```

---

## 21. 当前开发路线确认

更新时间：2026-06-05 09:02

用户已确认按路线 A 开始：

```text
路线 A：直接基于 Ombre-Brain 原项目改造。
```

开发策略：

```text
1. 在本地工作区拉取/准备 Ombre-Brain 最新代码；
2. 阅读 server.py / bucket_manager.py / embedding_engine.py 等核心文件；
3. 找到 breath 的内部实现；
4. 新增自动召回模块；
5. 新增 Anthropic-compatible /v1/messages；
6. 新增 OpenAI-compatible /v1/chat/completions；
7. 新增 /api/auto-recall；
8. 第一版先做非流式 + mock 模型模式；
9. 本地跑通后再上 VPS；
10. VPS 端口需避开旧版 Ombre-Brain。
```

端口提醒：

```text
用户 VPS 上旧版 Ombre-Brain 可能已经占用 8000。
新项目容器内部仍可使用 8000，但宿主机映射端口必须更换。
推荐宿主机端口：18002 或 18081。
```

推荐 Docker 映射：

```yaml
ports:
  - "18002:8000"
```

Cloudflare Tunnel 目标相应改为：

```text
http://127.0.0.1:18002
```
## 22. 本地 mock 测试结果

更新时间：2026-06-05 09:28

本地工作区已完成第一轮 mock 链路测试。

测试服务地址：

```text
http://127.0.0.1:18080
```

启动方式：

```bash
cd ombre-brain-gateway
. .venv/bin/activate
OMBRE_TRANSPORT=streamable-http \
OMBRE_PORT=18080 \
OMBRE_GATEWAY_MOCK_LLM=true \
OMBRE_BUCKETS_DIR=/.../ombre-brain-gateway/buckets \
python server.py
```

已测通接口：

```text
GET  /health                    OK
POST /api/auto-recall           OK
POST /v1/messages               OK，Anthropic-compatible mock 响应
POST /v1/chat/completions       OK，OpenAI-compatible mock 响应
POST /chat                      OK，自定义 chat mock 响应
```

创建了一条本地测试记忆桶：

```text
bucket_id: 349c7a4297af
name: 疲惫与回答偏好测试记忆
content: 用户最近提到自己容易疲惫、睡眠不足。回答时应更直接、少空泛安慰，先关心休息和负担。
tags: 疲惫 / 睡眠 / 偏好 / 直接
importance: 8
domain: 健康 / 偏好
valence: 0.35
arousal: 0.65
```

验证结果：

当用户输入：

```text
我今天有点疲惫，睡眠不足
```

`/api/auto-recall` 成功召回并生成：

```text
[长期记忆召回]
...
=== 本轮相关记忆 ===
[bucket_id:349c7a4297af] 📌 记忆桶: 疲惫与回答偏好测试记忆 [主题:健康, 偏好] [情感:V0.3/A0.7]
用户最近提到自己容易疲惫、睡眠不足。回答时应更直接、少空泛安慰，先关心休息和负担。
[/长期记忆召回]
```

`/v1/messages` 与 `/v1/chat/completions` 均返回 mock 响应，并在 debug 字段中显示：

```json
"used": true
```

说明：

```text
客户端请求 → 网关自动召回 → 记忆注入 → LLM mock 转发响应
```

链路已经跑通。

当前发现的小问题：

```text
当用户只说“我今天有点累”时，在没有 embedding API 的情况下，关键词模糊检索不一定能命中“疲惫/睡眠不足”记忆。
这是因为本地 mock 阶段未配置 embedding，语义检索不可用，只能依靠关键词/fuzzy。
部署功能模型与 embedding 后，这类同义语义召回会明显改善。
```

后续可优化：

```text
1. 配置真实 embedding 模型；
2. 自动召回无结果时，可选调用 breath() 浮现模式兜底；
3. 或增加关键词扩展/同义词扩展，但第一优先级仍是 embedding。
```

## 23. 当前发布顺序确认

更新时间：2026-06-05 11:47

用户确认发布顺序：

```text
1. 先生成干净部署压缩包；
2. 上传 VPS 并用 MOCK 模式测试通过；
3. VPS 测试通过后，再推到 GitHub；
4. 功能模型、向量模型、脱水压缩/打标模型，等 VPS mock 测试与 GitHub 推送两步完成后再最终确定。
```

当前压缩包应排除：

```text
.git
.venv
__pycache__
buckets
.env
*.pyc
*.pyo
```

第一轮 VPS 只验证：

```text
/health
/api/auto-recall
/v1/messages mock
/v1/chat/completions mock
/chat mock
```

暂不要求验证：

```text
真实 Anthropic 转发
embedding 语义召回
hold 自动打标
grow 日记拆分
长记忆脱水压缩
```

## 24. Dashboard 配置面板计划

更新时间：2026-06-05 13:00

用户确认：后续网关需要提供 Dashboard 配置面板，用于修改主模型、功能模型、embedding 与自动召回参数。

当前状态：

```text
尚未实现。
当前模型配置仍通过 VPS 上的 .env / config.yaml 修改。
```

采用方案：

```text
方案 A：Dashboard 读取并写入 .env / config.yaml。
保存后提示用户重启 Docker 容器生效。
```

暂不采用：

```text
方案 B：配置存 SQLite / JSON 并运行时动态热加载。
原因：改动更大，后续产品化再做。
```

第一版配置面板应支持编辑：

```text
1. 主模型配置
   - OMBRE_GATEWAY_MOCK_LLM
   - OMBRE_MAIN_MODEL_PROVIDER
   - OMBRE_MAIN_MODEL_BASE_URL
   - OMBRE_MAIN_MODEL_API_KEY
   - OMBRE_MAIN_MODEL_NAME
   - OMBRE_MAIN_MODEL_VERSION

2. 功能模型配置
   - OMBRE_API_KEY
   - OMBRE_BASE_URL
   - OMBRE_DEHYDRATION_MODEL
   - 后续如原项目支持独立 analysis/tagging model，也应加入

3. Embedding 配置
   - OMBRE_EMBEDDING_API_KEY
   - OMBRE_EMBEDDING_BASE_URL
   - OMBRE_EMBEDDING_MODEL
   - OMBRE_EMBEDDING_DIMENSIONS / 维度配置，如项目需要

4. 自动召回配置
   - OMBRE_AUTO_RECALL_ENABLED
   - OMBRE_AUTO_RECALL_RECENT_TURNS
   - OMBRE_AUTO_RECALL_MAX_MEMORIES
   - OMBRE_AUTO_RECALL_MAX_TOKENS
   - OMBRE_AUTO_RECALL_INCLUDE_PINNED
   - OMBRE_AUTO_RECALL_INCLUDE_RELATED
   - OMBRE_AUTO_RECALL_INCLUDE_FLOATING
   - OMBRE_GATEWAY_DEBUG

5. 安全配置
   - OMBRE_GATEWAY_AUTH_TOKEN
```

安全要求：

```text
1. API Key / Token 不应在 Dashboard 明文回显。
2. 页面只显示掩码，例如 sk-****abcd。
3. 用户留空时表示不修改原值。
4. 只有输入新值时才覆盖 .env。
5. 保存前后不要把密钥写入日志。
```

保存后的提示：

```bash
cd /opt/ombre-memory-gateway/app
docker compose -f docker-compose.gateway.yml restart
```

实现优先级：

```text
1. 先做读取 .env 并展示当前配置；
2. 再做保存 .env；
3. 再接入 Dashboard 页面入口；
4. 再补 config.yaml 里原 Ombre 功能模型相关字段；
5. 最后再考虑无需重启的动态配置方案。
```

下一阶段在配置真实模型前，建议先实现这个 Dashboard 设置页，避免每次 SSH 手改 .env。

UI 风格要求：

```text
用户要求新增配置页面必须保持 Ombre-Brain 原版 Dashboard UI 风格一致。
```

已确认原版 Dashboard 是单文件 `dashboard.html`，整体风格包括：

```text
1. 暖色羊皮纸/奶油色背景：#FDFCF0、#EDE4D3、#E2D1B3；
2. 半透明 glass surface：var(--surface)；
3. 柔和拟物阴影：shadow-light / shadow-dark-subtle；
4. Cormorant Garamond 标题字体 + Inter 正文字体；
5. 圆角配置卡片 `.config-section`；
6. 表单行 `.config-row`；
7. tab 导航 `.tabs` / `.tab`；
8. 主按钮 `.btn-primary`，次按钮 `.btn-secondary`；
9. 文案语气保持原版简洁、安静、偏诗性但不花哨。
```

实现时不要另起一套 UI 框架，不要引入 React/Vue，也不要做现代 SaaS 风格的大改。应复用原版 Dashboard 已有 CSS class：

```text
.config-section
.config-row
.btn-primary
.btn-secondary
.tabs
.tab
content view
```

建议新增 tab：

```text
Gateway
```

或在现有 `配置` tab 里新增 `Gateway / 主模型 / 自动召回` 分组。优先考虑不破坏原版结构。

## 25. Dashboard 配置页合并方向

更新时间：2026-06-05 13:27

用户本地预览后反馈：原版 Dashboard 的 `配置` 页面其实已经可以手动更换功能模型，包括脱水 / 打标 API 与 Embedding 的一部分配置。因此，新增 `网关` 页面不应长期重复承载所有功能模型配置。

当前临时实现：

```text
新增独立 tab：网关
包含：主模型、功能模型、Embedding、自动召回、安全 token、mock 开关。
```

后续合并方向：

```text
1. 保留原版 `配置` 页面作为功能模型 / Embedding 设置入口；
2. 将 `网关` 页面重点收敛为：
   - 主模型配置；
   - Anthropic / OpenAI-compatible 转发配置；
   - 自动召回配置；
   - 网关鉴权 token；
   - mock 开关；
3. 或者最终把 `配置` 与 `网关` 合并成一个统一设置页，避免重复配置项；
4. 合并时需要保持原版 Dashboard UI 风格一致；
5. 合并前，当前独立 `网关` tab 可作为过渡版本，用于验证主模型与自动召回配置写入 `.env` 的逻辑。
```

需要避免的问题：

```text
1. 不要让用户在两个页面看到两套功能模型配置而困惑；
2. 不要让 config.yaml 与 .env 中的同类字段产生优先级混乱；
3. API Key 留空不修改、掩码显示、不写日志的安全规则仍然保留。
```

下一步建议：

```text
先完成当前 `网关` tab 的保存/读取验证；
VPS 与 GitHub 同步前，可暂时保留独立页面；
后续正式配置模型前，再决定是否将功能模型字段从 `网关` tab 移除，只保留主模型和自动召回。
```

