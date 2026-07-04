# AI 聊天伴侣 App - 前端开发计划

## 一、项目现状分析

当前 Frontend 目录是一个 **uni-app Hello 模板工程**，包含大量示例页面（内置组件、API、模版、扩展组件等），与我们的 AI 聊天应用需求无关。

**决策：完全替换 pages.json 和所有业务页面，保留 uni_modules 和公共样式资源。**

## 二、目标架构

基于设计文档和接口文档，前端需要实现以下功能模块：

### 2.1 页面结构

| 页面 | 路由 | 说明 |
|------|------|------|
| 聊天页 | `pages/chat/chat` | 主页面，消息列表+输入框+状态栏 |
| 对话角色列表 | `pages/characters/list` | 展示所有AI角色，支持新建/编辑/删除 |
| 对话角色设计 | `pages/characters/design` | 创建/编辑AI角色表单 |
| 对话角色详情 | `pages/characters/detail` | 查看角色完整信息 |
| 用户角色列表 | `pages/personas/list` | 展示所有用户角色 |
| 用户角色设计 | `pages/personas/design` | 创建/编辑用户角色 |
| 会话创建 | `pages/session/create` | 选择角色组合创建新会话 |
| 会话列表 | `pages/session/list` | 管理所有会话（新增） |
| 设置 | `pages/settings/settings` | API配置、服务器地址等 |

### 2.2 TabBar 导航

```
┌──────────┬──────────┬──────────┐
│  💬 聊天  │  🎭 角色  │  👤 我的  │
└──────────┴──────────┴──────────┘
```

- **聊天**：`pages/chat/chat`
- **角色**：`pages/characters/list`（对话角色管理）
- **我的**：`pages/personas/list`（用户角色 + 设置入口）

### 2.3 目录结构

```
Frontend/
├── pages/
│   ├── chat/
│   │   └── chat.vue                    # 主聊天页
│   ├── characters/
│   │   ├── list.vue                    # 对话角色列表
│   │   ├── design.vue                  # 角色设计/编辑
│   │   └── detail.vue                  # 角色详情
│   ├── personas/
│   │   ├── list.vue                    # 用户角色列表
│   │   └── design.vue                  # 用户角色设计
│   ├── session/
│   │   ├── list.vue                    # 会话列表（管理）
│   │   └── create.vue                  # 创建会话
│   └── settings/
│       └── settings.vue                # 应用设置
├── components/
│   ├── chat/
│   │   ├── MessageBubble.vue           # 消息气泡组件
│   │   ├── ChatInput.vue               # 聊天输入栏
│   │   ├── ChatHeader.vue              # 聊天顶部栏（角色状态）
│   │   └── TypingIndicator.vue         # 正在输入指示器
│   ├── character/
│   │   ├── CharacterCard.vue           # 角色卡片（横向滚动）
│   │   ├── AvatarUploader.vue          # 头像上传组件
│   │   └── TagInput.vue                # 标签输入组件
│   └── common/
│       ├── FormField.vue               # 通用表单字段
│       └── EmptyState.vue              # 空状态占位
├── utils/
│   ├── request.js                      # HTTP请求封装（REST API）
│   ├── websocket.js                    # WebSocket封装
│   └── constants.js                    # 常量定义（API地址、错误码等）
├── store/
│   └── index.js                        # Pinia Store（会话状态、角色状态、消息状态）
├── pages.json                          # 页面路由配置
└── App.vue / main.js                   # 应用入口（适度修改）
```

## 三、开发阶段（Phase 划分）

### Phase 1: 基础设施 ✅ 优先完成

1. **重写 `pages.json`**：配置新的页面路由和 TabBar
2. **创建 `utils/constants.js`**：定义后端地址、API Key、错误码映射
3. **创建 `utils/request.js`**：封装 uni.request，统一处理认证、错误码、Token
4. **创建 `utils/websocket.js`**：WebSocket 连接管理类（连接、认证、心跳、重连、状态机）
5. **创建 `store/index.js`**：Pinia Store 定义（使用 Vue3 + Pinia，已有依赖）
   - `useChatStore`：当前会话、消息列表、连接状态、发送中状态
   - `useCharacterStore`：对话角色列表、当前角色缓存
   - `usePersonaStore`：用户角色列表、当前用户角色缓存
   - `useSessionStore`：会话列表、当前活跃会话
   - `useAppStore`：全局配置（API地址、API Key、加载状态）

### Phase 2: 公共组件

1. **`components/common/FormField.vue`**：通用表单字段（支持 text/textarea/tag-input/key-value/slider/radio）
2. **`components/character/AvatarUploader.vue`**：头像上传/预览/删除（调用 uni.chooseImage + uni.uploadFile）
3. **`components/character/CharacterCard.vue`**：角色卡片（头像、名称、简介、选中状态）
4. **`components/character/TagInput.vue`**：标签输入（用于性格特征、禁忌话题等数组字段）
5. **`components/chat/MessageBubble.vue`**：消息气泡（用户/助手区分样式、时间戳、重新生成按钮）
6. **`components/chat/ChatInput.vue`**：聊天输入栏（文本输入、发送按钮、停止按钮、扩展功能预留）
7. **`components/chat/ChatHeader.vue`**：聊天顶部栏（角色头像、名称、心情、好感度进度条）
8. **`components/chat/TypingIndicator.vue`**：正在输入动画

### Phase 3: 角色管理页面

1. **`pages/characters/list.vue`**：
   - 网格展示所有对话角色
   - 每个角色卡片：头像、名称、昵称、默认标记
   - 点击 → 详情页 / 长按 → 编辑/删除/设为默认
   - 底部浮动按钮：新建角色
   - 调用 API：`GET /api/characters`, `DELETE /api/characters/{id}`, `PUT /api/characters/{id}/default`

2. **`pages/characters/design.vue`**：
   - 完整的角色设计表单（对应技术方案中的字段）
   - 分段：基础信息 / 核心设定 / 示例对话 / 世界观 / 初始状态
   - 示例对话支持动态添加/删除
   - 保存时调用 `POST /api/characters` 或 `PUT /api/characters/{id}`
   - 头像上传调用 `POST /api/characters/{id}/avatar`

3. **`pages/characters/detail.vue`**：
   - 展示角色完整信息（只读）
   - 提供编辑按钮、删除按钮、设为默认按钮
   - 快速开始对话按钮（直接创建会话并跳转聊天页）

4. **`pages/personas/list.vue`**：
   - 类似角色列表，但展示用户角色
   - 调用 `GET /api/personas`
   - 包含设置入口

5. **`pages/personas/design.vue`**：
   - 用户角色表单（字段较少：名称、简介、背景、性格、说话风格）
   - 调用 `POST /api/personas` 或 `PUT /api/personas/{id}`
   - 头像上传调用 `POST /api/personas/{id}/avatar`

### Phase 4: 会话与聊天页面

1. **`pages/session/list.vue`**：
   - 展示所有会话列表
   - 每个会话：名称、角色头像、消息数量、更新时间
   - 点击切换会话 → 激活并跳转到聊天页
   - 滑动删除会话、清空消息
   - 调用 API：`GET /api/sessions`, `PUT /api/sessions/{id}/activate`, `DELETE /api/sessions/{id}`, `POST /api/sessions/{id}/clear`

2. **`pages/session/create.vue`**：
   - 横向滚动选择用户角色（可选默认）
   - 横向滚动选择对话角色
   - 会话名称输入（可选）
   - 创建后自动激活并跳转聊天页
   - 调用 `POST /api/sessions` → `PUT /api/sessions/{id}/activate`

3. **`pages/chat/chat.vue`**（核心页面）：
   - 顶部：ChatHeader（角色信息 + 状态 + 会话切换按钮）
   - 中部：消息列表（scroll-view，向上滚动加载历史）
   - 首次加载调用 `GET /api/messages?session_id={id}&limit=50`
   - 向上翻页调用 `GET /api/messages?session_id={id}&before_id={firstId}&limit=50`
   - 底部：ChatInput
   - 建立 WebSocket 连接 `wss://{server}/ws/chat/{session_id}`
   - 发送消息流程：输入 → 本地显示 → WS发送 → 等待 delta → 逐字追加 → done → 更新状态
   - 重新生成：长按消息 → 选择重新生成 → WS发送带 message_id
   - 接收 state_update → 更新顶部状态栏

### Phase 5: 设置页面

1. **`pages/settings/settings.vue`**：
   - 服务器地址配置（保存到本地存储）
   - API Key 配置（保存到本地存储）
   - 清除本地缓存按钮
   - 关于信息

## 四、接口映射汇总

### REST API 封装函数

```javascript
// 角色管理
getCharacters(params)           // GET /api/characters
getCharacter(id)                // GET /api/characters/{id}
createCharacter(data)           // POST /api/characters
updateCharacter(id, data)       // PUT /api/characters/{id}
deleteCharacter(id)             // DELETE /api/characters/{id}
setDefaultCharacter(id)         // PUT /api/characters/{id}/default
getDefaultCharacter()           // GET /api/characters/default
uploadCharacterAvatar(id, file) // POST /api/characters/{id}/avatar

// 用户角色管理
getPersonas(params)             // GET /api/personas
getPersona(id)                  // GET /api/personas/{id}
createPersona(data)             // POST /api/personas
updatePersona(id, data)         // PUT /api/personas/{id}
deletePersona(id)               // DELETE /api/personas/{id}
setDefaultPersona(id)           // PUT /api/personas/{id}/default
getDefaultPersona()             // GET /api/personas/default
uploadPersonaAvatar(id, file)   // POST /api/personas/{id}/avatar

// 会话管理
getSessions(params)             // GET /api/sessions
getSession(id)                  // GET /api/sessions/{id}
createSession(data)             // POST /api/sessions
updateSession(id, data)         // PUT /api/sessions/{id}
deleteSession(id)               // DELETE /api/sessions/{id}
activateSession(id)             // PUT /api/sessions/{id}/activate
getActiveSession()              // GET /api/sessions/active
clearSessionMessages(id)        // POST /api/sessions/{id}/clear

// 消息管理
getMessages(sessionId, params)  // GET /api/messages?session_id={id}

// 角色状态
getCharacterState(sessionId)    // GET /api/sessions/{session_id}/state

// 健康检查
getHealth()                     // GET /api/health
```

### WebSocket 协议封装

```javascript
// 连接
ws.connect(sessionId, apiKey)

// 发送
ws.sendChat(content, messageId = null)
ws.sendStop()
ws.sendAuth(apiKey)

// 事件监听
ws.on('delta', handler)         // 流式内容
ws.on('done', handler)          // 完成
ws.on('error', handler)         // 错误
ws.on('state_update', handler)  // 状态更新
ws.on('ping', handler)          // 心跳
ws.on('connect', handler)       // 连接成功
ws.on('disconnect', handler)    // 断开连接
ws.on('reconnecting', handler)  // 正在重连
```

## 五、数据流与状态管理

### Store 状态设计（Pinia）

```javascript
// useAppStore
{
  serverUrl: '',      // 从本地存储读取，默认 ''
  apiKey: '',         // 从本地存储读取
  isLoading: false,
  errorMessage: ''
}

// useSessionStore
{
  sessions: [],       // 会话列表
  activeSession: null, // 当前活跃会话（含展开的 character/persona）
  isLoading: false
}

// useChatStore
{
  messages: [],      // 当前会话的消息列表（倒序或正序？正序渲染）
  isConnected: false,  // WS连接状态
  isTyping: false,    // 是否正在生成回复
  wsStatus: 'disconnected', // disconnected/connecting/connected/authing/ready/reconnecting
  hasMoreMessages: true,  // 是否还有更多历史消息
  currentDelta: ''     // 当前正在流式接收的内容（用于实时渲染）
}

// useCharacterStore
{
  characters: [],      // 对话角色列表
  currentCharacter: null // 当前查看/编辑的角色
}

// usePersonaStore
{
  personas: [],        // 用户角色列表
  currentPersona: null // 当前查看/编辑的用户角色
}
```

## 六、关键实现细节

### 6.1 消息列表滚动加载

- 首次进入聊天页：加载最新 50 条，滚动到底部
- 向上滚动到顶部：触发加载更早消息（before_id=列表第一条的id）
- 新消息到达：如果是自己发送的或最新回复，自动滚动到底部
- 加载历史消息时保持滚动位置（使用 scroll-view 的 scroll-into-view 或 scroll-top）

### 6.2 WebSocket 重连机制

```
指数退避重连：
- 第1次：1秒后
- 第2次：2秒后
- 第3次：4秒后
- ...最大30秒
- 超过10次后提示用户手动刷新
```

### 6.3 输入防抖

- 发送按钮点击后 500ms 内不可再次点击
- 发送后立即清空输入框，显示"发送中"状态
- 收到 done/error 后恢复输入框

### 6.4 头像 URL 处理

- 后端返回相对路径 `/avatars/characters/1.png`
- 前端拼接完整 URL：`${serverUrl}${avatarPath}`
- 未上传头像时显示默认占位图

### 6.5 本地缓存策略

- 角色列表：缓存到 `uni.setStorage`，启动时先显示缓存，再刷新
- 会话列表：同上
- 服务器地址和 API Key：持久化到本地存储

## 七、开发顺序与依赖关系

```
Phase 1 (基础设施)
  │
  ├─→ utils/constants.js
  ├─→ utils/request.js
  ├─→ utils/websocket.js
  ├─→ store/index.js (Pinia stores)
  └─→ pages.json (路由配置)
       │
Phase 2 (公共组件)
  │
  ├─→ components/common/FormField.vue
  ├─→ components/character/AvatarUploader.vue
  ├─→ components/character/CharacterCard.vue
  ├─→ components/character/TagInput.vue
  ├─→ components/chat/MessageBubble.vue
  ├─→ components/chat/ChatInput.vue
  ├─→ components/chat/ChatHeader.vue
  └─→ components/chat/TypingIndicator.vue
       │
Phase 3 (角色管理)
  │
  ├─→ pages/characters/list.vue
  ├─→ pages/characters/design.vue
  ├─→ pages/characters/detail.vue
  ├─→ pages/personas/list.vue
  └─→ pages/personas/design.vue
       │
Phase 4 (会话与聊天)
  │
  ├─→ pages/session/list.vue
  ├─→ pages/session/create.vue
  └─→ pages/chat/chat.vue  (核心，依赖所有其他模块)
       │
Phase 5 (设置与收尾)
  │
  └─→ pages/settings/settings.vue
  └─→ App.vue 修改 (启动时加载配置)
  └─→ 测试与验证
```

## 八、UI 设计规范（基于 uni-ui + 自定义）

### 8.1 颜色系统

```scss
$primary: #007AFF;        // 主色调（蓝色）
$primary-light: #E6F2FF;  // 主色调浅色背景
$success: #34C759;        // 成功/在线状态
$warning: #FF9500;        // 警告
$danger: #FF3B30;         // 删除/错误
$bg-page: #F5F5F5;        // 页面背景
$bg-card: #FFFFFF;        // 卡片背景
$text-primary: #333333;   // 主文字
$text-secondary: #666666; // 次要文字
$text-tertiary: #999999;  // 辅助文字
$border: #E5E5E5;         // 边框
```

### 8.2 聊天页布局

```
┌────────────────────────────┐
│  [头像] 角色名  [心情]      │  ← ChatHeader (高度 100rpx)
│  好感度 ████████░░ 80/100  │
├────────────────────────────┤
│                            │
│    你好呀小雨              │  ← 用户消息 (右侧，蓝色气泡)
│                            │
│ 嗨～今天过得怎么样呢？    │  ← 助手消息 (左侧，白色气泡+头像)
│                            │
│  ... 消息列表 scroll-view  │
│                            │
│  [正在输入...]             │  ← TypingIndicator
├────────────────────────────┤
│  [输入框.............] [发送] │ ← ChatInput (高度自适应)
└────────────────────────────┘
```

### 8.3 角色卡片布局

```
┌────────────────────────────┐
│  ┌────┐  角色名称          │
│  │ 👧 │  昵称 · 17岁 · 女  │  ← CharacterCard
│  └────┘  温柔、傲娇...      │
└────────────────────────────┘
```

## 九、风险与注意事项

1. **uni-app 平台兼容性**：WebSocket 在 H5/App/小程序中的 API 略有差异，使用 uni.connectSocket 统一封装。
2. **大段文本渲染**：消息内容可能很长，使用 scroll-view 而非 view 列表，避免性能问题。
3. **WebSocket 消息顺序**：delta 消息必须按顺序追加，不能乱序处理。
4. **图片上传**：uni-app 的 `uni.chooseImage` 和 `uni.uploadFile` 在各平台表现一致，但返回路径格式不同，需要处理临时路径。
5. **VUE3 与 Pinia**：项目已引入 Pinia，Store 使用 Composition API 风格。
6. **NVUE 问题**：本项目不使用 nvue，所有页面使用 vue。

## 十、完成检查清单

- [ ] pages.json 重写完成，TabBar 配置正确
- [ ] utils/request.js 封装所有 REST API
- [ ] utils/websocket.js 完成状态机和重连逻辑
- [ ] store/index.js 所有 Pinia stores 定义完整
- [ ] 所有公共组件实现完成
- [ ] 所有页面实现完成
- [ ] 聊天页面流式输出正常
- [ ] 角色创建/编辑/删除正常
- [ ] 会话创建/切换/删除正常
- [ ] 头像上传/显示正常
- [ ] 本地缓存和配置持久化正常
