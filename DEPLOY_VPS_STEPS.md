# VPS 部署步骤：Ombre Memory Gateway

> 本文件是实际部署操作清单。项目设计说明见 `README_DEPLOY.md`。

---

## 0. 当前约定

```text
VPS 系统：Ubuntu
部署目录：/opt/ombre-memory-gateway
项目代码目录：/opt/ombre-memory-gateway/app
宿主机端口：18002
容器内部端口：8000
主模型：Anthropic
第一轮部署：建议先 MOCK 模式跑通，再切真实 Anthropic
公网访问：Cloudflare Tunnel 指向 http://127.0.0.1:18002
```

端口说明：旧版 Ombre-Brain 可能占用 8000 或 18001，所以新项目默认使用宿主机端口 `18002`。

---

## 1. 登录 VPS

```bash
ssh root@你的服务器IP
```

如果用普通用户：

```bash
ssh your_user@你的服务器IP
```

---

## 2. 检查 Docker

```bash
docker --version
docker compose version
```

如果没有 Docker，安装：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo systemctl enable docker
sudo systemctl start docker
```

如果当前用户没有 docker 权限，可以临时用 `sudo docker ...`，或者加入 docker 组：

```bash
sudo usermod -aG docker $USER
```

然后重新登录 SSH。

---

## 3. 新建独立部署目录

```bash
sudo mkdir -p /opt/ombre-memory-gateway
sudo chown -R $USER:$USER /opt/ombre-memory-gateway
cd /opt/ombre-memory-gateway
```

---

## 4. 上传/同步代码

### 方案 A：如果后续我们把改造代码推到 Git 仓库

```bash
git clone <你的仓库地址> app
cd app
```

### 方案 B：从本地工作区打包上传

本地打包时，不要包含：

```text
.venv
__pycache__
buckets
.env
*.pyc
```

VPS 上解压：

```bash
cd /opt/ombre-memory-gateway
mkdir -p app
tar -xzf ombre-memory-gateway.tar.gz -C app --strip-components=1
cd app
```

---

## 5. 准备配置文件

进入项目目录：

```bash
cd /opt/ombre-memory-gateway/app
```

复制环境变量示例：

```bash
cp .env.gateway.example .env
```

如果没有 `config.yaml`：

```bash
cp config.example.yaml config.yaml
```

编辑 `.env`：

```bash
nano .env
```

第一轮建议先 MOCK 跑通：

```env
OMBRE_TRANSPORT=streamable-http
OMBRE_PORT=8000
OMBRE_HOST_PORT=18002

OMBRE_GATEWAY_ENABLED=true
OMBRE_GATEWAY_MOCK_LLM=true
OMBRE_GATEWAY_AUTH_TOKEN=先填一个长随机字符串

OMBRE_AUTO_RECALL_ENABLED=true
OMBRE_AUTO_RECALL_RECENT_TURNS=6
OMBRE_AUTO_RECALL_MAX_MEMORIES=8
OMBRE_AUTO_RECALL_MAX_TOKENS=3000
OMBRE_AUTO_RECALL_INCLUDE_RELATED=true
OMBRE_AUTO_RECALL_INCLUDE_FLOATING=false

OMBRE_MAIN_MODEL_PROVIDER=anthropic
OMBRE_MAIN_MODEL_BASE_URL=https://api.anthropic.com
OMBRE_MAIN_MODEL_API_KEY=
OMBRE_MAIN_MODEL_NAME=claude-3-5-sonnet-latest
OMBRE_MAIN_MODEL_VERSION=2023-06-01

# 功能模型：部署时再确认
OMBRE_API_KEY=
OMBRE_BASE_URL=
```

生成随机 token 可用：

```bash
openssl rand -hex 32
```

---

## 6. 启动 Docker Compose

使用 gateway 专用 compose 文件：

```bash
cd /opt/ombre-memory-gateway/app
docker compose -f docker-compose.gateway.yml up -d --build
```

查看日志：

```bash
docker logs -f ombre-memory-gateway
```

---

## 7. 本机健康检查

在 VPS 上执行：

```bash
curl http://127.0.0.1:18002/health
```

期望看到类似：

```json
{
  "status": "ok",
  "gateway": "enabled",
  "gateway_mock_llm": true
}
```

---

## 8. 测试自动召回接口

如果设置了 `OMBRE_GATEWAY_AUTH_TOKEN`，需要带 token。

```bash
TOKEN="你的网关token"

curl -sS -X POST http://127.0.0.1:18002/api/auto-recall \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "我今天有点累"}
    ],
    "debug": true
  }'
```

新库为空时，`memory_context` 为空是正常的。

---

## 9. 测试 Anthropic-compatible 网关

```bash
TOKEN="你的网关token"

curl -sS -X POST http://127.0.0.1:18002/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $TOKEN" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-3-5-sonnet-latest",
    "system": "你是一个助手。",
    "messages": [
      {"role": "user", "content": "我今天有点累"}
    ],
    "max_tokens": 256,
    "stream": false,
    "debug": true
  }'
```

MOCK 模式下应返回：

```text
[MOCK] 网关已收到 Anthropic-compatible 请求，并完成记忆自动召回与注入。
```

---

## 10. 测试 OpenAI-compatible 网关

```bash
TOKEN="你的网关token"

curl -sS -X POST http://127.0.0.1:18002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "model": "gpt-mock",
    "messages": [
      {"role": "system", "content": "你是一个助手。"},
      {"role": "user", "content": "我今天有点累"}
    ],
    "stream": false,
    "debug": true
  }'
```

---

## 11. 切换到真实 Anthropic

确认 mock 链路跑通后，编辑 `.env`：

```bash
nano /opt/ombre-memory-gateway/app/.env
```

修改：

```env
OMBRE_GATEWAY_MOCK_LLM=false
OMBRE_MAIN_MODEL_PROVIDER=anthropic
OMBRE_MAIN_MODEL_BASE_URL=https://api.anthropic.com
OMBRE_MAIN_MODEL_API_KEY=你的真实AnthropicKey
OMBRE_MAIN_MODEL_NAME=claude-3-5-sonnet-latest
OMBRE_MAIN_MODEL_VERSION=2023-06-01
```

重启：

```bash
cd /opt/ombre-memory-gateway/app
docker compose -f docker-compose.gateway.yml up -d --build
```

再测 `/v1/messages`。

---

## 12. 功能模型 / Embedding 配置

这一步部署时需要再问用户。

功能模型影响：

```text
hold：自动打标 valence/arousal/importance/tags/name
长记忆 dehydrate：脱水压缩
embedding：语义检索，“累” 能召回 “疲惫/睡眠不足”
grow/import：日记抽取
```

如果暂时没有功能模型：

```text
已有短记忆仍可被关键词/fuzzy 召回；
但 hold/grow/长内容脱水/embedding 语义召回会受限。
```

待确认项：

```text
1. 功能模型 provider
2. 功能模型 base_url
3. 功能模型 api_key
4. 功能模型 model name
5. embedding 模型和维度
```

---

## 13. Cloudflare Tunnel 接入

用户通常使用 Cloudflare Tunnel。

Tunnel 目标服务填：

```text
http://127.0.0.1:18002
```

结构：

```text
公网域名
  ↓ Cloudflare Tunnel
VPS 127.0.0.1:18002
  ↓ Docker 映射
容器 8000
  ↓
Ombre Memory Gateway
```

接入后测试：

```bash
curl https://你的域名/health
```

如果公网使用，必须设置：

```env
OMBRE_GATEWAY_AUTH_TOKEN=长随机字符串
```

---

## 14. 客户端接入方式

### Anthropic-compatible

Base URL：

```text
https://你的域名
```

Endpoint：

```text
/v1/messages
```

Header：

```text
x-api-key: 你的网关token
anthropic-version: 2023-06-01
```

注意：客户端传入的 key 是网关 token，不是真实 Anthropic key。真实 Anthropic key 只放 VPS `.env`。

### OpenAI-compatible

Base URL：

```text
https://你的域名/v1
```

Endpoint：

```text
/chat/completions
```

Header：

```text
Authorization: Bearer 你的网关token
```

---

## 15. 常用维护命令

查看容器：

```bash
docker ps
```

查看日志：

```bash
docker logs -f ombre-memory-gateway
```

重启：

```bash
cd /opt/ombre-memory-gateway/app
docker compose -f docker-compose.gateway.yml restart
```

停止：

```bash
cd /opt/ombre-memory-gateway/app
docker compose -f docker-compose.gateway.yml down
```

更新后重建：

```bash
cd /opt/ombre-memory-gateway/app
docker compose -f docker-compose.gateway.yml up -d --build
```

备份记忆桶：

```bash
tar -czf ombre-buckets-backup-$(date +%F).tar.gz /opt/ombre-memory-gateway/app/buckets
```

---

## 16. 整理完后的下一步

1. 确认代码包同步方式：
   - 推到 Git 仓库；或
   - 打 tar 包上传 VPS；或
   - 直接在 VPS 上 clone 原仓库后应用补丁。

2. 登录 VPS，检查 Docker。

3. 在 `/opt/ombre-memory-gateway` 新建独立目录。

4. 上传代码并按本文件启动 MOCK 模式。

5. 测通：

```text
/health
/api/auto-recall
/v1/messages
/v1/chat/completions
```

6. 向用户索取真实 Anthropic 信息：

```text
Anthropic Base URL
Anthropic API Key
模型名
```

7. 关闭 mock，测试真实 Anthropic 转发。

8. 再询问并配置功能模型与 embedding。

9. 接 Cloudflare Tunnel。

10. 客户端接入公网域名。
