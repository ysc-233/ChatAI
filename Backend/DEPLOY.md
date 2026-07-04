# AI Chat Companion - 后端部署文档

> 版本: v1.0
> 适用后端: Python 3.11 + FastAPI + SQLite + Qdrant + Redis
> 文档路径: `Backend/DEPLOY.md`

---

## 一、环境要求

### 1.1 最低系统要求

| 资源 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 1核 | 2核及以上 |
| 内存 | 1GB | 2GB及以上 |
| 磁盘 | 5GB 可用空间 | 20GB SSD |
| 网络 | 公网IP或内网可达 | 固定公网IP + 域名 |
| OS | Linux (Ubuntu 22.04/Debian 12/CentOS 8) | Ubuntu 22.04 LTS |

### 1.2 必需软件环境

| 软件 | 版本要求 | 用途 |
|------|---------|------|
| Python | 3.11+ | 后端运行时 |
| pip | 23.0+ | Python 包管理 |
| Docker | 24.0+ | 容器化部署（推荐） |
| Docker Compose | v2.20+ | 多容器编排 |
| Git | 2.30+ | 代码拉取 |

### 1.3 外部依赖（可选但强烈建议）

| 服务 | 用途 | 说明 |
|------|------|------|
| 大语言模型 API | 聊天生成 | OpenAI API / 兼容格式 |
| Embedding API | 文本向量化 | 用于长期记忆检索 |
| Qdrant | 向量数据库 | Docker 内已包含 |
| Redis | 任务队列 / 缓存 | Docker 内已包含 |

> **注意**: 如果不配置 LLM API，系统仍可启动，但聊天功能会返回占位文本。

---

## 二、项目目录结构

部署前请确认 `Backend/` 目录包含以下文件:

```
Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 全局配置
│   ├── api/
│   │   ├── __init__.py
│   │   ├── characters.py       # 对话角色 API
│   │   ├── personas.py         # 用户角色 API
│   │   ├── sessions.py         # 会话管理 API
│   │   ├── messages.py         # 消息历史 API
│   │   ├── ws.py               # WebSocket 聊天
│   │   ├── health.py           # 健康检查
│   │   └── logs.py             # 日志查询 API (新增)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── context_engine.py   # 上下文引擎
│   │   ├── llm_adapter.py      # LLM 调用适配器
│   │   ├── embedding_adapter.py # Embedding 适配器
│   │   ├── memory_engine.py    # 记忆引擎
│   │   ├── character_service.py # 角色状态服务
│   │   └── log_service.py      # 日志服务 (新增)
│   ├── workers/
│   │   ├── __init__.py
│   │   └── memory_tasks.py     # arq 后台任务
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py         # 数据库连接与初始化
│   │   └── models.py           # SQLAlchemy 模型
│   └── core/
│       ├── __init__.py
│       ├── security.py         # API Key 认证
│       ├── exceptions.py       # 自定义异常
│       └── logging.py           # 系统日志模块 (新增)
├── data/                        # 数据持久化目录
│   ├── avatars/
│   │   ├── characters/          # 对话角色头像
│   │   └── personas/           # 用户角色头像
│   └── logs/                    # 日志文件 (自动生成)
├── requirements.txt             # Python 依赖
├── Dockerfile                   # Docker 镜像构建
├── docker-compose.yml           # Docker Compose 编排
├── nginx.conf                   # Nginx 反向代理配置
└── .env.example                 # 环境变量模板
```

---

## 三、部署方式一：Docker Compose 部署（推荐生产环境）

### 步骤 1: 准备服务器

确保服务器已安装 Docker 和 Docker Compose:

```bash
# 检查 Docker 版本
docker --version
# 期望输出: Docker version 24.x.x 或更高

# 检查 Docker Compose 版本
docker compose version
# 期望输出: Docker Compose version v2.x.x 或更高
```

如果未安装，参考以下命令安装（Ubuntu 22.04）:

```bash
# 更新包索引
sudo apt-get update

# 安装依赖
sudo apt-get install -y ca-certificates curl gnupg

# 添加 Docker 官方 GPG 密钥
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 添加 Docker 软件源
echo   "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu   "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" |   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 验证安装
sudo docker run hello-world

# 将当前用户加入 docker 组（避免每次使用 sudo）
sudo usermod -aG docker $USER
# 退出并重新登录生效
```

### 步骤 2: 上传项目代码

将 `Backend/` 目录上传到服务器，例如 `/opt/ai-chat-app/Backend`:

```bash
# 创建项目目录
sudo mkdir -p /opt/ai-chat-app
sudo chown $USER:$USER /opt/ai-chat-app

# 方式 A: 使用 scp 从本地上传
scp -r Backend/ root@your-server-ip:/opt/ai-chat-app/

# 方式 B: 使用 git 克隆
cd /opt/ai-chat-app
git clone https://your-repo.git .

# 进入后端目录
cd /opt/ai-chat-app/Backend
```

### 步骤 3: 创建环境变量文件

从模板复制并修改 `.env`:

```bash
cp .env.example .env
```

编辑 `.env`，至少修改以下关键配置:

```bash
# === 安全（必须修改）===
API_KEY=your-very-secret-api-key-at-least-32-chars

# === LLM API（必须配置，否则无法聊天）===
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL_NAME=gpt-4o-mini

# === Embedding API（如需长期记忆功能）===
EMBEDDING_API_URL=https://api.openai.com/v1/embeddings
EMBEDDING_API_KEY=sk-your-openai-api-key
EMBEDDING_MODEL=text-embedding-3-small

# === 文件路径（Docker 内保持默认即可）===
DATABASE_URL=sqlite+aiosqlite:///data/chat.db
LOG_FILE_PATH=data/logs/app.log
```

> **安全警告**: `API_KEY` 是前端访问后端的唯一凭证，必须设置为高强度随机字符串，且不可泄露。

### 步骤 4: 创建数据目录并设置权限

```bash
# 创建持久化目录
mkdir -p data/avatars/characters data/avatars/personas data/logs data/qdrant_storage

# 设置权限（Docker 容器内非 root 用户需要访问）
chmod -R 755 data/
```

### 步骤 5: 启动服务

```bash
# 构建并启动所有服务（后台运行）
docker compose up -d --build

# 查看启动日志（前 50 行）
docker compose logs -f --tail=50 backend
```

首次启动时会:
1. 构建 FastAPI 后端 Docker 镜像
2. 拉取 Qdrant、Redis、Nginx 镜像
3. 创建 SQLite 数据库表并插入默认数据（小雨角色 + 默认用户）
4. 启动所有服务

### 步骤 6: 验证部署

```bash
# 1. 检查所有容器是否正常运行
docker compose ps
# 期望看到: backend, qdrant, redis, nginx 均为 Up 状态

# 2. 测试健康检查接口
curl http://localhost:8000/api/health
# 期望返回 JSON，database 状态为 "connected"

# 3. 测试 API Key 认证（替换为你的 API_KEY）
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/characters
# 期望返回角色列表，包含"小雨"

# 4. 查看后端日志
docker compose logs -f backend
```

### 步骤 7: 配置 Nginx / HTTPS（生产环境必须）

如果使用 Nginx 容器（已在 docker-compose.yml 中配置），默认监听 80 端口。

如需 HTTPS，请准备 SSL 证书并修改 `nginx.conf`:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    # 其他配置保持不变...
}
```

然后在 `docker-compose.yml` 的 nginx 服务中挂载证书目录:

```yaml
volumes:
  - ./nginx.conf:/etc/nginx/nginx.conf:ro
  - ./data/avatars:/usr/share/nginx/avatars:ro
  - ./ssl:/etc/nginx/ssl:ro  # 新增 SSL 证书挂载
```

重启 Nginx:

```bash
docker compose restart nginx
```

---

## 四、部署方式二：本地 Python 直接运行（推荐开发环境）

### 步骤 1: 安装 Python 3.11

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# macOS (使用 Homebrew)
brew install python@3.11

# 验证版本
python3.11 --version
# 期望: Python 3.11.x
```

### 步骤 2: 创建虚拟环境

```bash
cd /path/to/ChatAPP/Backend

# 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 验证 (命令行前缀应显示 venv)
```

### 步骤 3: 安装依赖

```bash
# 确保在虚拟环境中
pip install --upgrade pip

# 安装 requirements
pip install -r requirements.txt

# 验证 FastAPI 安装
python -c "import fastapi; print(fastapi.__version__)"
```

### 步骤 4: 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，设置开发环境配置:

```bash
APP_ENV=development
API_KEY=dev-api-key

# 开发环境可暂时不配置 LLM，使用占位回复
# LLM_API_URL=...
# LLM_API_KEY=...

# 数据库使用本地路径
DATABASE_URL=sqlite+aiosqlite:///data/chat.db
```

### 步骤 5: 创建数据目录

```bash
mkdir -p data/avatars/characters data/avatars/personas data/logs
```

### 步骤 6: 启动服务

```bash
# 方式 A: 使用 uvicorn（推荐开发）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 方式 B: 使用 python -m（不热重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后会看到:
- `Starting AI-Chat-Companion in development mode`
- `Database tables initialized`
- Uvicorn 监听地址

### 步骤 7: 验证

```bash
# 健康检查
curl http://localhost:8000/api/health

# 获取角色列表（携带 API Key）
curl -H "X-API-Key: dev-api-key" http://localhost:8000/api/characters

# 查看自动生成的 API 文档（浏览器打开）
http://localhost:8000/docs
```

---

## 五、log 模块使用说明

本项目新增的 **log 模块** 支持以下功能:

### 5.1 自动记录的日志类型

系统会自动记录以下日志到 `system_logs` 表和日志文件:

| 日志类型 | 来源 | 说明 |
|----------|------|------|
| API 请求 | 中间件 | 每个 HTTP 请求的方法、路径、状态码、耗时、客户端 IP |
| WebSocket 事件 | ws.py | 连接、断开、认证成功/失败 |
| LLM 调用 | llm_adapter.py | 模型名称、token 数、耗时、成功/失败 |
| 数据库操作 | database.py | 表初始化、数据插入 |
| 安全事件 | security.py | 认证失败、非法访问 |
| 系统启动 | lifespan | 服务启动/关闭事件 |

### 5.2 查询日志 API

```bash
# 获取所有日志（分页）
curl -H "X-API-Key: your-key" "http://localhost:8000/api/logs?page=1&page_size=20"

# 按级别筛选 ERROR
curl -H "X-API-Key: your-key" "http://localhost:8000/api/logs?level=ERROR"

# 按分类和时间段筛选
curl -H "X-API-Key: your-key" "http://localhost:8000/api/logs?category=api&start_time=2024-06-20T00:00:00Z"

# 搜索关键词
curl -H "X-API-Key: your-key" "http://localhost:8000/api/logs?keyword=timeout"

# 获取日志统计（最近 7 天）
curl -H "X-API-Key: your-key" "http://localhost:8000/api/logs/statistics?days=7"

# 获取支持的日志级别和分类
curl -H "X-API-Key: your-key" "http://localhost:8000/api/logs/levels"

# 手动写入日志
curl -X POST -H "X-API-Key: your-key" -H "Content-Type: application/json"   http://localhost:8000/api/logs   -d '{"level":"INFO","category":"system","message":"Manual log entry","details":{"action":"test"}}'

# 清理 30 天前的日志
curl -X DELETE -H "X-API-Key: your-key" "http://localhost:8000/api/logs/cleanup?retention_days=30"
```

### 5.3 日志文件位置

| 部署方式 | 日志路径 |
|----------|---------|
| Docker | `./data/logs/app.log` (宿主机) 或容器内 `/app/data/logs/app.log` |
| 本地 | `./data/logs/app.log` |
| SQLite | `system_logs` 表 |

### 5.4 日志表结构

```sql
CREATE TABLE system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL CHECK(level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    category TEXT NOT NULL,           -- system, api, websocket, llm, memory, database, security
    message TEXT NOT NULL,
    details TEXT,                     -- JSON 格式额外信息
    source TEXT,                      -- 来源代码位置
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 六、配置文件详解

### 6.1 .env 核心配置项

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `APP_NAME` | 否 | AI-Chat-Companion | 应用名称 |
| `APP_ENV` | 否 | development | 环境：development/production |
| `API_KEY` | **是** | - | 访问 API 的密钥，必须修改！ |
| `SERVER_HOST` | 否 | 0.0.0.0 | 监听地址 |
| `SERVER_PORT` | 否 | 8000 | 监听端口 |
| `DATABASE_URL` | 否 | sqlite+aiosqlite:///data/chat.db | 数据库连接 |
| `LLM_API_URL` | 建议 | - | 大模型 API 地址 |
| `LLM_API_KEY` | 建议 | - | 大模型 API 密钥 |
| `LLM_MODEL_NAME` | 否 | gpt-4o-mini | 主模型 |
| `EMBEDDING_API_URL` | 建议 | - | Embedding API 地址 |
| `EMBEDDING_API_KEY` | 建议 | - | Embedding API 密钥 |
| `QDRANT_HOST` | 否 | qdrant | Qdrant 主机名 |
| `QDRANT_PORT` | 否 | 6333 | Qdrant 端口 |
| `REDIS_URL` | 否 | redis://redis:6379 | Redis 连接串 |
| `LOG_LEVEL` | 否 | INFO | 日志级别 |
| `LOG_RETENTION_DAYS` | 否 | 30 | 日志保留天数 |
| `LOG_TO_DB` | 否 | true | 是否写入数据库 |
| `LOG_TO_FILE` | 否 | true | 是否写入文件 |

---

## 七、常用运维命令

### 7.1 Docker 环境

```bash
# 查看所有容器状态
docker compose ps

# 查看后端实时日志
docker compose logs -f backend

# 查看 Qdrant 日志
docker compose logs -f qdrant

# 重启单个服务
docker compose restart backend

# 重建并启动（修改代码后）
docker compose up -d --build backend

# 停止所有服务
docker compose down

# 停止并删除数据卷（危险！会清空数据）
docker compose down -v

# 进入后端容器执行命令
docker compose exec backend sh

# 查看数据库文件（宿主机）
ls -la data/chat.db

# 备份数据库
cp data/chat.db data/chat.db.backup.$(date +%Y%m%d)
```

### 7.2 本地环境

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 查看 SQLite 数据库
sqlite3 data/chat.db ".tables"
sqlite3 data/chat.db "SELECT * FROM characters;"

# 查看日志文件
tail -f data/logs/app.log

# 更新依赖
pip install -r requirements.txt
```

---

## 八、常见问题排查

### Q1: 启动时报 `ModuleNotFoundError`

**原因**: Python 依赖未安装完整。

**解决**:
```bash
pip install -r requirements.txt
```

### Q2: Docker 启动后 `backend` 一直重启

**原因**: 可能是 `.env` 中 `API_KEY` 为空，或权限问题。

**解决**:
```bash
# 检查日志
docker compose logs backend

# 检查 .env 是否存在且包含 API_KEY
cat .env | grep API_KEY

# 检查数据目录权限
ls -la data/
```

### Q3: 前端无法连接 WebSocket

**原因**: Nginx 未正确配置 WebSocket 升级，或防火墙阻挡。

**解决**:
1. 确认 `nginx.conf` 中 `/ws/` 位置的 `proxy_set_header Upgrade` 和 `Connection` 配置
2. 检查防火墙:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 8000/tcp  # 开发调试时
   ```

### Q4: 聊天时返回 "未配置 LLM API"

**原因**: `.env` 中未设置 `LLM_API_URL` 和 `LLM_API_KEY`。

**解决**: 编辑 `.env` 配置正确的 LLM API，然后重启服务。

### Q5: SQLite 数据库被锁定

**原因**: 多进程/线程同时写入 SQLite。

**解决**: Docker 部署时使用单 worker（已默认），本地开发时避免多开。

### Q6: 日志没有写入数据库

**原因**: `LOG_TO_DB=false` 或数据库表未创建。

**解决**:
```bash
# 检查配置
grep LOG_TO_DB .env

# 检查表是否存在
sqlite3 data/chat.db ".schema system_logs"
```

---

## 九、安全建议

1. **修改默认 API_KEY**: 生产环境必须设置高强度随机字符串，最小 32 位。
2. **HTTPS**: 生产环境必须启用 HTTPS，配置 SSL 证书。
3. **防火墙**: 仅开放 80/443 端口，8000 端口仅允许内网访问。
4. **定期备份**: 定时备份 `data/chat.db` 和 `data/avatars/` 目录。
5. **日志清理**: 设置 cron 任务定期调用 `/api/logs/cleanup` 或清理日志文件。

---

## 十、部署检查清单

部署完成后，请确认以下项目:

- [ ] Docker 和 Docker Compose 已安装且版本符合要求
- [ ] 项目代码已上传到服务器正确位置
- [ ] `.env` 文件已创建且 `API_KEY` 已修改
- [ ] `LLM_API_URL` 和 `LLM_API_KEY` 已配置（如需聊天功能）
- [ ] 数据目录已创建且权限正确
- [ ] `docker compose up -d` 成功启动无报错
- [ ] 健康检查 `/api/health` 返回 `database: connected`
- [ ] `/api/characters` 返回默认角色 "小雨"
- [ ] `/api/logs` 返回日志列表（log 模块正常工作）
- [ ] WebSocket `/ws/chat/{session_id}` 可以连接
- [ ] Nginx 正确代理静态文件 `/avatars/`
- [ ] （可选）HTTPS 证书已配置

---

> 如有问题，请查看日志文件 `data/logs/app.log` 或接口文档 `doc/接口文档.md`。
