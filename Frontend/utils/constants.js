/**
 * 应用常量配置
 */

// 服务器配置（从本地存储读取，有默认值）
export const getServerConfig = () => {
	const serverUrl = uni.getStorageSync('server_url') || '';
	return { serverUrl };
};

export const setServerConfig = (serverUrl) => {
	uni.setStorageSync('server_url', serverUrl);
};

// 构建完整 API URL
export const buildUrl = (path) => {
	const { serverUrl } = getServerConfig();
	if (!serverUrl) return path;
	// 去除末尾斜杠
	let base = serverUrl.replace(/\/$/, '');
	// 自动补全协议（用户可能只输入 IP:Port）
	if (!/^https?:\/\//i.test(base)) {
		base = 'http://' + base;
	}
	// 路径确保以 / 开头
	const p = path.startsWith('/') ? path : '/' + path;
	return base + p;
};

// 构建 WebSocket URL
export const buildWsUrl = (sessionId) => {
	const { serverUrl } = getServerConfig();
	if (!serverUrl) return '';
	let wsBase = serverUrl.replace(/\/$/, '');
	// 自动补全协议
	if (!/^https?:\/\//i.test(wsBase)) {
		wsBase = 'http://' + wsBase;
	}
	wsBase = wsBase.replace(/^http/, 'ws');
	return `${wsBase}/ws/chat/${sessionId}`;
};

// ==================== Token 管理 ====================
export const getToken = () => {
	return uni.getStorageSync('access_token') || '';
};

export const getRefreshToken = () => {
	return uni.getStorageSync('refresh_token') || '';
};

export const setTokens = (accessToken, refreshToken) => {
	uni.setStorageSync('access_token', accessToken);
	uni.setStorageSync('refresh_token', refreshToken);
};

export const clearTokens = () => {
	uni.removeStorageSync('access_token');
	uni.removeStorageSync('refresh_token');
	uni.removeStorageSync('user_info');
	// 同时清除业务缓存
	uni.removeStorageSync(CACHE_KEYS.CHARACTERS);
	uni.removeStorageSync(CACHE_KEYS.PERSONAS);
	uni.removeStorageSync(CACHE_KEYS.SESSIONS);
};

export const isLoggedIn = () => {
	return !!getToken();
};

// 默认头像
export const DEFAULT_AVATAR = '/static/images/default-avatar.png';

// 缓存键
export const CACHE_KEYS = {
	CHARACTERS: 'cache_characters',
	PERSONAS: 'cache_personas',
	SESSIONS: 'cache_sessions',
	MESSAGES_PREFIX: 'cache_messages_',
	SETTINGS: 'app_settings'
};

// 错误码映射
export const ERROR_CODES = {
	40000: '请求参数错误',
	40001: '角色名称不能为空',
	40002: '角色背景故事不能为空',
	40003: '性格特征至少填写一项',
	40004: '切换角色会清空历史，请确认',
	40005: '头像文件类型不支持',
	40006: '头像文件超过 5MB',
	40007: '文件不是有效的图片',
	40008: '消息内容不能为空',
	40009: '消息内容超过 4000 字符',
	40100: '未认证：缺少有效令牌',
	40101: '令牌无效',
	40300: '禁止访问',
	40301: '系统角色不可修改',
	40302: '系统角色不可删除',
	40303: '默认用户角色不可修改名称',
	40304: '默认用户角色不可删除',
	40400: '资源不存在',
	40401: '对话角色不存在',
	40402: '用户角色不存在',
	40403: '会话不存在',
	40404: '消息不存在',
	40405: '角色状态未初始化',
	41300: '请求体过大',
	42200: '业务逻辑错误',
	50000: '服务器内部错误',
	50001: 'LLM API 调用失败',
	50002: 'LLM API 调用超时',
	50003: 'Embedding API 调用失败',
	50004: 'Qdrant 向量数据库错误',
	50005: 'Redis 连接错误',
	50006: '数据库操作错误',
	50007: '记忆抽取任务失败',
	50008: '角色状态更新失败'
};

// WebSocket 错误码
export const WS_ERROR_CODES = {
	auth_failed: '认证失败',
	invalid_session: '会话 ID 无效',
	session_closed: '会话已被关闭',
	rate_limited: '发送过于频繁，请稍后再试',
	llm_error: 'LLM 调用失败',
	llm_timeout: 'LLM 调用超时',
	content_filtered: '内容被安全过滤',
	server_error: '服务端内部错误',
	connection_closed: '连接被服务端关闭'
};

// 连接状态枚举
export const WS_STATUS = {
	DISCONNECTED: 'disconnected',
	CONNECTING: 'connecting',
	CONNECTED: 'connected',
	AUTHING: 'authing',
	READY: 'ready',
	RECONNECTING: 'reconnecting'
};

// 重连配置
export const RECONNECT_CONFIG = {
	maxRetries: 10,
	initialDelay: 1000,
	maxDelay: 30000,
	backoffMultiplier: 2
};

// 性别选项
export const GENDER_OPTIONS = [
	{ text: '男', value: '男' },
	{ text: '女', value: '女' },
	{ text: '其他', value: '其他' }
];

// 心情映射（用于图标）
export const MOOD_MAP = {
	'开心': { icon: '☀️', color: '#FF9500' },
	'平静': { icon: '🌤️', color: '#34C759' },
	'难过': { icon: '🌧️', color: '#8E8E93' },
	'生气': { icon: '⛈️', color: '#FF3B30' },
	'害羞': { icon: '💗', color: '#FF2D55' },
	'惊讶': { icon: '✨', color: '#5856D6' }
};

// 分页默认配置
export const PAGE_CONFIG = {
	defaultPage: 1,
	defaultPageSize: 20,
	maxPageSize: 100
};

// 消息相关
export const MESSAGE_CONFIG = {
	defaultLimit: 50,
	maxLimit: 100,
	scrollThreshold: 100 // 距离底部多少px时自动滚动
};

// 文件上传限制
export const UPLOAD_CONFIG = {
	maxAvatarSize: 5 * 1024 * 1024, // 5MB
	allowedImageTypes: ['image/jpeg', 'image/png', 'image/webp']
};

// 防抖时间
export const DEBOUNCE_DELAY = 500;

// 心跳间隔
export const HEARTBEAT_INTERVAL = 30000; // 30秒
export const HEARTBEAT_TIMEOUT = 60000; // 60秒无消息视为断开
