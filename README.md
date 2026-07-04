# ChatAI

一个基于大语言模型的多角色 AI 聊天应用，支持自定义角色、长期记忆和跨端部署。

## 功能特性

- **多角色对话** — 创建和管理多个 AI 角色，每个角色拥有独立的性格、背景和对话风格
- **长期记忆** — 基于向量数据库（Qdrant）的语义记忆系统，AI 可以记住对话上下文
- **跨端支持** — 基于 uni-app 构建，一套代码编译到微信小程序、H5、iOS、Android 等多平台
- **用户系统** — 完整的注册、登录、JWT 鉴权流程
- **角色设计器** — 可视化编辑角色名称、描述、性格等属性
- **个人身份（Persona）** — 用户可自定义在对话中扮演的身份
- **消息管理** — 会话列表、消息历史、下拉刷新
- **搜索增强** — 集成搜索服务，为对话提供实时信息补充
- **头像裁剪** — 内置图片裁剪功能

## 技术栈

### 前端
| 技术 | 说明 |
|------|------|
| Vue.js | 前端框架 |
| uni-app | 跨端开发框架 |
| Vuex / Pinia | 状态管理 |
| uni-ui | UI 组件库 |

### 后端
| 技术 | 说明 |
|------|------|
| FastAPI | 异步 Web 框架 |
| SQLAlchemy (async) | 异步 ORM |
| SQLite (aiosqlite) | 关系型数据库 |
| Qdrant | 向量数据库，用于语义记忆存储与检索 |
| Redis | 缓存与后台任务队列 |
| PyJWT + bcrypt | 认证与密码加密 |
| httpx | 异步 HTTP 客户端（调用 LLM API） |

### 基础设施
| 技术 | 说明 |
|------|------|
| Docker Compose | 一键部署全部服务 |
| Nginx | 反向代理 |

## 项目结构

```
ChatAI/
├── Backend/
│   ├── app/
│   │   ├── api/            # API 路由（auth, characters, messages, sessions, personas ...）
│   │   ├── core/           # 核心模块（auth, logging, exceptions）
│   │   ├── db/             # 数据库模型与初始化
│   │   ├── services/       # 业务服务
│   │   │   ├── llm_adapter.py          # LLM API 适配
│   │   │   ├── embedding_adapter.py    # 向量嵌入适配
│   │   │   ├── memory_engine.py        # 记忆引擎
│   │   │   ├── context_engine.py       # 上下文管理
│   │   │   ├── vector_store.py         # Qdrant 向量存储
│   │   │   ├── search_service.py       # 搜索服务
│   │   │   └── character_service.py    # 角色业务逻辑
│   │   ├── workers/        # 后台任务（memory_tasks）
│   │   ├── config.py       # 配置管理
│   │   └── main.py         # 应用入口
│   ├── docker-compose.yml  # 服务编排
│   ├── Dockerfile
│   ├── nginx.conf
│   └── requirements.txt
├── Frontend/
│   ├── pages/
│   │   ├── auth/           # 登录、注册、服务器设置
│   │   ├── message/        # 消息列表
│   │   ├── chat/           # 聊天页面
│   │   ├── characters/     # 角色列表、设计、详情
│   │   ├── personas/       # 身份设计
│   │   ├── profile/        # 个人中心
│   │   ├── settings/       # 设置、关于
│   │   └── cropper/        # 头像裁剪
│   ├── components/         # 公共组件（MessageBubble, ChatInput, CharacterCard ...）
│   ├── pages.json          # 页面路由配置
│   └── main.js             # 前端入口
└── README.md
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 16+
- Docker & Docker Compose（推荐）

### 方式一：Docker Compose 部署（推荐）

```bash
cd Backend

# 复制并编辑环境变量
cp .env.example .env
# 编辑 .env 填入你的 LLM API Key 等配置

# 一键启动所有服务
docker-compose up -d
```

服务启动后：
- 前端页面：`http://localhost`（Nginx）
- 后端 API：`http://localhost:8000/api`
- Qdrant 控制台：`http://localhost:6333/dashboard`

### 方式二：本地开发

**后端：**

```bash
cd Backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入配置

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**前端：**

```bash
cd Frontend

# 安装依赖
npm install

# 运行到 H5
npm run dev:h5

# 运行到微信小程序
npm run dev:mp-weixin
```

## 配置说明

在 `Backend/.env` 中配置以下环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_URL` | LLM API 地址 | — |
| `LLM_API_KEY` | LLM API 密钥 | — |
| `LLM_MODEL` | 使用的模型名称 | — |
| `EMBEDDING_API_URL` | 嵌入模型 API 地址 | — |
| `EMBEDDING_API_KEY` | 嵌入模型 API 密钥 | — |
| `QDRANT_HOST` | Qdrant 服务地址 | `localhost` |
| `QDRANT_PORT` | Qdrant 服务端口 | `6333` |
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:6379` |
| `JWT_SECRET` | JWT 签名密钥 | — |
| `DATABASE_URL` | 数据库连接 URL | `sqlite+aiosqlite:///./data/chat.db` |

## API 接口

| 模块 | 路径 | 说明 |
|------|------|------|
| 认证 | `/api/auth` | 注册、登录、Token 管理 |
| 角色 | `/api/characters` | 角色的增删改查 |
| 消息 | `/api/messages` | 消息发送与历史查询 |
| 会话 | `/api/sessions` | 会话管理 |
| 身份 | `/api/personas` | 用户身份管理 |
| 健康检查 | `/api/health` | 服务状态检查 |
| 日志 | `/api/logs` | 日志管理 |

## 架构概览

```
┌─────────────┐     HTTP      ┌──────────────┐
│   Frontend   │ ───────────▶ │    Nginx      │
│  (uni-app)   │              │  (Reverse     │
└─────────────┘              │   Proxy)      │
                              └──────┬───────┘
                                     │
                              ┌──────▼───────┐
                              │   FastAPI     │
                              │   Backend     │
                              └──┬───┬───┬───┘
                                 │   │   │
                    ┌────────────┘   │   └────────────┐
                    ▼                ▼                 ▼
             ┌──────────┐   ┌──────────────┐   ┌──────────┐
             │  SQLite   │   │   Qdrant     │   │  Redis   │
             │ (对话/用户)│   │ (向量记忆)    │   │ (缓存)   │
             └──────────┘   └──────────────┘   └──────────┘
                                     │
                              ┌──────▼───────┐
                              │  LLM API     │
                              │ (大语言模型)   │
                              └──────────────┘
```

## License

MIT
