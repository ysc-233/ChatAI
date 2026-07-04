import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { getServerConfig, setServerConfig, CACHE_KEYS, WS_STATUS } from '@/utils/constants.js';
import http, { showError, showSuccess } from '@/utils/request.js';
import { getWebSocket } from '@/utils/websocket.js';

// ==================== App Store ====================
export const useAppStore = defineStore('app', () => {
	// State
	const serverUrl = ref(getServerConfig().serverUrl);
	const isLoading = ref(false);
	const errorMessage = ref('');
	const isConfigured = computed(() => !!serverUrl.value);

	// Actions
	const setConfig = (url) => {
		serverUrl.value = url;
		setServerConfig(url);
	};

	const setLoading = (loading) => { isLoading.value = loading; };
	const setError = (msg) => { errorMessage.value = msg; };
	const clearError = () => { errorMessage.value = ''; };

	// 检查服务器连接
	const checkHealth = async () => {
		try {
			const res = await http.get('/api/health');
			return res.data;
		} catch (err) {
			showError(err, '服务器连接失败');
			return null;
		}
	};

	return {
		serverUrl, isLoading, errorMessage, isConfigured,
		setConfig, setLoading, setError, clearError, checkHealth
	};
});

// ==================== Character Store ====================
export const useCharacterStore = defineStore('character', () => {
	const characters = ref([]);
	const currentCharacter = ref(null);
	const isLoading = ref(false);

	const getCachedCharacters = () => {
		try {
			const cached = uni.getStorageSync(CACHE_KEYS.CHARACTERS);
			return cached ? JSON.parse(cached) : [];
		} catch (e) { return []; }
	};

	// 初始化时加载缓存
	characters.value = getCachedCharacters();

	const cacheCharacters = () => {
		uni.setStorageSync(CACHE_KEYS.CHARACTERS, JSON.stringify(characters.value));
	};

	const fetchCharacters = async (params = {}) => {
		isLoading.value = true;
		try {
			const res = await http.get('/api/characters', params);
			characters.value = res.data.items || [];
			cacheCharacters();
			return characters.value;
		} catch (err) {
			showError(err);
			return characters.value;
		} finally {
			isLoading.value = false;
		}
	};

	const getCharacter = async (id) => {
		try {
			const res = await http.get(`/api/characters/${id}`);
			currentCharacter.value = res.data;
			return res.data;
		} catch (err) {
			showError(err);
			return null;
		}
	};

	const createCharacter = async (data) => {
		try {
			const res = await http.post('/api/characters', data);
			showSuccess('角色创建成功');
			await fetchCharacters();
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const updateCharacter = async (id, data) => {
		try {
			const res = await http.put(`/api/characters/${id}`, data);
			showSuccess('角色更新成功');
			await fetchCharacters();
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const deleteCharacter = async (id) => {
		try {
			await http.delete(`/api/characters/${id}`);
			showSuccess('角色已删除');
			characters.value = characters.value.filter(c => c.id !== id);
			cacheCharacters();
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const setDefaultCharacter = async (id) => {
		try {
			await http.put(`/api/characters/${id}/default`);
			characters.value.forEach(c => c.is_default = (c.id === id ? 1 : 0));
			cacheCharacters();
			showSuccess('已设为默认角色');
		} catch (err) {
			showError(err);
		}
	};

	const getDefaultCharacter = async () => {
		try {
			const res = await http.get('/api/characters/default');
			return res.data;
		} catch (err) {
			showError(err);
			return null;
		}
	};

	const uploadAvatar = async (id, filePath) => {
		try {
			const res = await http.upload(`/api/characters/${id}/avatar`, filePath);
			showSuccess('头像上传成功');
			await fetchCharacters();
			// 同步更新聊天页的角色头像
			const sessionStore = useSessionStore();
			if (sessionStore.activeSession?.character?.id === id) {
				sessionStore.activeSession.character.avatar = res.data.avatar_url;
			}
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const clearMemories = async (id) => {
		try {
			const res = await http.post(`/api/characters/${id}/clear-memories`);
			showSuccess(`已清除 ${res.data.deleted_count || 0} 条长期记忆`);
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	return {
		characters, currentCharacter, isLoading,
		fetchCharacters, getCharacter, createCharacter, updateCharacter,
		deleteCharacter, setDefaultCharacter, getDefaultCharacter, uploadAvatar,
		clearMemories
	};
});

// ==================== Persona Store ====================
export const usePersonaStore = defineStore('persona', () => {
	const personas = ref([]);
	const currentPersona = ref(null);
	const isLoading = ref(false);

	const getCachedPersonas = () => {
		try {
			const cached = uni.getStorageSync(CACHE_KEYS.PERSONAS);
			return cached ? JSON.parse(cached) : [];
		} catch (e) { return []; }
	};

	personas.value = getCachedPersonas();

	const cachePersonas = () => {
		uni.setStorageSync(CACHE_KEYS.PERSONAS, JSON.stringify(personas.value));
	};

	const fetchPersonas = async (params = {}) => {
		isLoading.value = true;
		try {
			const res = await http.get('/api/personas', params);
			personas.value = res.data.items || [];
			cachePersonas();
			return personas.value;
		} catch (err) {
			showError(err);
			return personas.value;
		} finally {
			isLoading.value = false;
		}
	};

	const getDefaultPersona = async () => {
		try {
			const res = await http.get('/api/personas/default');
			currentPersona.value = res.data;
			return res.data;
		} catch (err) {
			showError(err);
			return null;
		}
	};

	const getPersona = async (id) => {
		try {
			const res = await http.get(`/api/personas/${id}`);
			currentPersona.value = res.data;
			return res.data;
		} catch (err) {
			showError(err);
			return null;
		}
	};

	const createPersona = async (data) => {
		try {
			const res = await http.post('/api/personas', data);
			showSuccess('人格创建成功');
			await fetchPersonas();
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const updatePersona = async (id, data) => {
		try {
			const res = await http.put(`/api/personas/${id}`, data);
			showSuccess('资料更新成功');
			await fetchPersonas();
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const deletePersona = async (id) => {
		try {
			await http.delete(`/api/personas/${id}`);
			showSuccess('人格已删除');
			personas.value = personas.value.filter(p => p.id !== id);
			cachePersonas();
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const setDefaultPersona = async (id) => {
		try {
			await http.put(`/api/personas/${id}/default`);
			personas.value.forEach(p => p.is_default = (p.id === id ? 1 : 0));
			cachePersonas();
			showSuccess('已设为默认人格');
		} catch (err) {
			showError(err);
		}
	};

	const uploadAvatar = async (id, filePath) => {
		try {
			const res = await http.upload(`/api/personas/${id}/avatar`, filePath);
			showSuccess('头像上传成功');
			await fetchPersonas();
			// 同步更新聊天页的用户头像
			const sessionStore = useSessionStore();
			if (sessionStore.activeSession?.user_persona?.id === id) {
				sessionStore.activeSession.user_persona.avatar = res.data.avatar_url;
			}
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	return {
		personas, currentPersona, isLoading,
		fetchPersonas, getDefaultPersona, getPersona, createPersona, updatePersona,
		deletePersona, setDefaultPersona, uploadAvatar
	};
});

// ==================== Session Store ====================
export const useSessionStore = defineStore('session', () => {
	const sessions = ref([]);
	const activeSession = ref(null);
	const isLoading = ref(false);

	const getCachedSessions = () => {
		try {
			const cached = uni.getStorageSync(CACHE_KEYS.SESSIONS);
			return cached ? JSON.parse(cached) : [];
		} catch (e) { return []; }
	};

	sessions.value = getCachedSessions();

	const cacheSessions = () => {
		uni.setStorageSync(CACHE_KEYS.SESSIONS, JSON.stringify(sessions.value));
	};

	const fetchSessions = async (params = {}) => {
		isLoading.value = true;
		try {
			const res = await http.get('/api/sessions', {
				include_character: 1,
				include_persona: 1,
				include_last_message: 1,
				...params
			});
			sessions.value = res.data.items || [];
			cacheSessions();
			return sessions.value;
		} catch (err) {
			showError(err);
			return sessions.value;
		} finally {
			isLoading.value = false;
		}
	};

	const getOrCreateSession = async (characterId) => {
		try {
			const res = await http.get(`/api/sessions/by_character/${characterId}`);
			return res.data;
		} catch (err) {
			showError(err);
			return null;
		}
	};

	const getSession = async (id) => {
		try {
			const res = await http.get(`/api/sessions/${id}`);
			return res.data;
		} catch (err) {
			showError(err);
			return null;
		}
	};

	const createSession = async (data) => {
		try {
			const res = await http.post('/api/sessions', data);
			showSuccess('会话创建成功');
			await fetchSessions();
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const updateSession = async (id, data) => {
		try {
			const res = await http.put(`/api/sessions/${id}`, data);
			showSuccess('会话更新成功');
			await fetchSessions();
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const deleteSession = async (id) => {
		try {
			await http.delete(`/api/sessions/${id}`);
			showSuccess('会话已删除');
			sessions.value = sessions.value.filter(s => s.id !== id);
			if (activeSession.value?.id === id) {
				activeSession.value = null;
				// 清理当前聊天消息，避免残留历史记录
				const chatStore = useChatStore();
				chatStore.clearMessages();
				chatStore.disconnect(); // 断开 WebSocket，避免残留连接
			}
			cacheSessions();
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	const activateSession = async (id) => {
		try {
			await http.put(`/api/sessions/${id}/activate`);
			// 重新获取完整会话信息（包含 character 和 user_persona）
			const res = await http.get(`/api/sessions/${id}`);
			activeSession.value = res.data;
			await fetchSessions();
			return res.data;
		} catch (err) {
			showError(err);
			return null;
		}
	};

	const getActiveSession = async () => {
		try {
			const res = await http.get('/api/sessions/active');
			if (res.data) {
				activeSession.value = res.data;
			}
			return res.data;
		} catch (err) {
			showError(err);
			return null;
		}
	};

	const clearSessionMessages = async (id) => {
		try {
			const res = await http.post(`/api/sessions/${id}/clear`);
			showSuccess('历史消息已清空');
			return res.data;
		} catch (err) {
			showError(err);
			throw err;
		}
	};

	return {
		sessions, activeSession, isLoading,
		fetchSessions, getOrCreateSession, getSession, createSession, updateSession,
		deleteSession, activateSession, getActiveSession, clearSessionMessages
	};
});

// ==================== Chat Store ====================
export const useChatStore = defineStore('chat', () => {
	const messages = ref([]);
	const isConnected = ref(false);
	const isTyping = ref(false);
	const wsStatus = ref(WS_STATUS.DISCONNECTED);
	const hasMoreMessages = ref(true);
	const characterState = ref(null);
	const isLoadingMessages = ref(false);
	const searchStatus = ref(null);  // { status: 'searching'|'done'|'empty', query?, count? }
	const ws = getWebSocket();

	// WebSocket 状态文本
	const wsStatusText = computed(() => {
		const map = {
			[WS_STATUS.DISCONNECTED]: '已断开',
			[WS_STATUS.CONNECTING]: '连接中...',
			[WS_STATUS.CONNECTED]: '已连接',
			[WS_STATUS.AUTHING]: '认证中...',
			[WS_STATUS.READY]: '就绪',
			[WS_STATUS.RECONNECTING]: '重连中...'
		};
		return map[wsStatus.value] || wsStatus.value;
	});

	// 监听 WebSocket 状态变化
	let unsubscribes = [];

	const setupWebSocketListeners = (sessionId) => {
		// 清理旧监听：先调用旧的取消订阅函数，再清空 ws 上所有残留监听（双保险）
		unsubscribes.forEach(fn => fn());
		unsubscribes = [];
		ws.clearAllListeners();

		unsubscribes.push(ws.on('statusChange', (status) => {
			wsStatus.value = status;
			isConnected.value = (status === WS_STATUS.READY);
		}));

		unsubscribes.push(ws.on('connect', () => {
			isConnected.value = true;
		}));

		unsubscribes.push(ws.on('disconnect', () => {
			isConnected.value = false;
		}));

		// LLM 正在生成响应
		unsubscribes.push(ws.on('typing', (msg) => {
			isTyping.value = true;
			// 创建占位消息
			const msgId = msg.message_id;
			const existing = messages.value.find(m => m.id === msgId);
			if (!existing) {
				messages.value.push({
					id: msgId,
					role: 'assistant',
					content: '',
					isDone: false,
					created_at: new Date().toISOString()
				});
			}
		}));

		// 完整消息一次性到达
		unsubscribes.push(ws.on('message', (msg) => {
			isTyping.value = false;
			const msgId = msg.message_id;
			const existing = messages.value.find(m => m.id === msgId);
			if (existing) {
				existing.content = msg.content;
				existing.isDone = true;
			} else {
				messages.value.push({
					id: msgId,
					role: msg.role || 'assistant',
					content: msg.content,
					isDone: true,
					created_at: new Date().toISOString()
				});
			}
		}));

		unsubscribes.push(ws.on('error', (msg) => {
			isTyping.value = false;
			showError(msg.error || 'WebSocket 错误');
		}));

		unsubscribes.push(ws.on('state_update', (data) => {
			characterState.value = data;
		}));

		// Search status events
		unsubscribes.push(ws.on('search_status', (data) => {
			searchStatus.value = data;
		}));

		// Affection update events
		unsubscribes.push(ws.on('affection_update', (data) => {
			// Update character state if we have one
			if (characterState.value) {
				characterState.value.affection = data.new_value;
			}
			// Show notification
			const direction = data.delta > 0 ? '↑' : '↓';
			const emoji = data.delta > 0 ? '💚' : '💔';
			uni.showToast({
				title: `好感度 ${direction}${Math.abs(data.delta)}  ${data.reason || ''}`,
				icon: 'none',
				duration: 2500
			});
		}));
	};

	const connect = (sessionId) => {
		setupWebSocketListeners(sessionId);
		ws.connect(sessionId);
	};

	const disconnect = () => {
		ws.close();
		unsubscribes.forEach(fn => fn());
		unsubscribes = [];
		ws.clearAllListeners();
	};

	const sendMessage = (content) => {
		if (!ws.isReady()) {
			showError('WebSocket 未连接，请稍后重试');
			return false;
		}
		ws.sendChat(content);
		return true;
	};

	const stopGeneration = () => {
		ws.sendStop();
		isTyping.value = false;
	};

	const regenerateMessage = (content, messageId) => {
		if (!ws.isReady()) return false;
		ws.sendChat(content, messageId);
		return true;
	};

	const fetchMessages = async (sessionId, params = {}) => {
		isLoadingMessages.value = true;
		try {
			const res = await http.get('/api/messages', {
				session_id: sessionId,
				limit: 50,
				...params
			});
			const items = res.data.items || [];
			if (params.before_id) {
				// 向上翻页：prepend
				messages.value = [...items, ...messages.value];
			} else {
				messages.value = items;
			}
			hasMoreMessages.value = res.data.has_more !== false;
			return items;
		} catch (err) {
			showError(err);
			return [];
		} finally {
			isLoadingMessages.value = false;
		}
	};

	const getCharacterState = async (sessionId) => {
		try {
			const res = await http.get(`/api/sessions/${sessionId}/state`);
			characterState.value = res.data;
			return res.data;
		} catch (err) {
			console.log('Character state not found:', err.message);
			characterState.value = null;
			return null;
		}
	};

	const clearMessages = () => {
		messages.value = [];
		hasMoreMessages.value = true;
	};

	const addLocalMessage = (role, content) => {
		messages.value.push({
			id: `local_${Date.now()}`,
			role,
			content,
			isDone: true,
			created_at: new Date().toISOString()
		});
	};

	return {
		messages, isConnected, isTyping, wsStatus, hasMoreMessages,
		characterState, isLoadingMessages, searchStatus, wsStatusText,
		connect, disconnect, sendMessage, stopGeneration, regenerateMessage,
		fetchMessages, getCharacterState, clearMessages, addLocalMessage
	};
});

// ==================== 统一导出 ====================
export { useUserStore } from './user.js';

const stores = {
	useAppStore,
	useCharacterStore,
	usePersonaStore,
	useSessionStore,
	useChatStore
};

stores.install = () => {
	// Pinia stores 无需 install，已自动注册
};

export default stores;
