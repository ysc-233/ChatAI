/**
 * WebSocket 连接管理器
 * 封装连接、认证、心跳、重连、消息收发
 */

import { buildWsUrl, WS_STATUS, RECONNECT_CONFIG, HEARTBEAT_INTERVAL, HEARTBEAT_TIMEOUT, getToken } from './constants.js';

class ChatWebSocket {
	constructor() {
		this.socket = null;
		this.sessionId = null;
		this.status = WS_STATUS.DISCONNECTED;
		this.listeners = new Map();
		this.reconnectTimer = null;
		this.reconnectCount = 0;
		this.heartbeatTimer = null;
		this.lastPingTime = 0;
		this.lastMessageTime = Date.now();
		this.messageQueue = []; // 待发送消息队列（未连接时缓存）
		this.currentTaskId = 0; // 用于生成唯一ID
		this.intentionalClose = false; // 标记是否为主动关闭（防止 onClose 触发自动重连）
	}

	/**
	 * 注册事件监听器
	 */
	on(event, handler) {
		if (!this.listeners.has(event)) {
			this.listeners.set(event, []);
		}
		this.listeners.get(event).push(handler);
		
		// 返回取消订阅函数
		return () => {
			const handlers = this.listeners.get(event);
			if (handlers) {
				const index = handlers.indexOf(handler);
				if (index > -1) handlers.splice(index, 1);
			}
		};
	}

	/**
	 * 清除所有事件监听器（用于重新连接前确保没有残留监听）
	 */
	clearAllListeners() {
		this.listeners.clear();
	}

	/**
	 * 触发事件
	 */
	emit(event, data) {
		const handlers = this.listeners.get(event);
		if (handlers) {
			handlers.forEach(handler => {
				try {
					handler(data);
				} catch (err) {
					console.error(`WebSocket event handler error [${event}]:`, err);
				}
			});
		}
	}

	/**
	 * 建立连接
	 */
	connect(sessionId) {
		// 如果 sessionId 变化，先关闭旧连接
		if (this.sessionId && this.sessionId !== sessionId) {
			console.log(`[WebSocket] Session changed: ${this.sessionId} -> ${sessionId}, closing old connection`);
			this._closeSocket();
		}

		// 如果正在连接/已连接/已就绪，直接返回
		if (this.status === WS_STATUS.CONNECTING || this.status === WS_STATUS.CONNECTED || this.status === WS_STATUS.READY) {
			console.log('WebSocket already connected or connecting');
			return;
		}

		// 如果正在重连中，取消待定的重连定时器，由本次主动连接接管
		if (this.status === WS_STATUS.RECONNECTING && this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}

		this.sessionId = sessionId;
		this.status = WS_STATUS.CONNECTING;
		this.intentionalClose = false; // 新连接重置标记
		this.emit('statusChange', this.status);

		const wsUrl = buildWsUrl(sessionId);
		if (!wsUrl) {
			this.status = WS_STATUS.DISCONNECTED;
			this.emit('error', { message: '服务器地址未配置' });
			return;
		}

		console.log(`[WebSocket] Connecting to ${wsUrl}`);

		this.socket = uni.connectSocket({
			url: wsUrl,
			complete: () => {}
		});

		this.socket.onOpen(() => {
			console.log('[WebSocket] Connected');
			this.status = WS_STATUS.CONNECTED;
			this.reconnectCount = 0;
			this.lastMessageTime = Date.now();
			this.emit('statusChange', this.status);
			this.emit('connect', {});

			// 发送认证消息
			this._authenticate();
		});

		this.socket.onMessage((res) => {
			this._handleMessage(res.data);
		});

		this.socket.onClose((res) => {
			console.log('[WebSocket] Closed', res.code, res.reason);
			this._cleanup();
			this.socket = null;
			this.status = WS_STATUS.DISCONNECTED;
			this.emit('statusChange', this.status);
			this.emit('disconnect', { code: res.code, reason: res.reason });
			
			// 仅在非主动关闭时尝试重连
			if (!this.intentionalClose) {
				this._scheduleReconnect();
			}
		});

		this.socket.onError((err) => {
			console.error('[WebSocket] Error', err);
			this.emit('error', { message: err.errMsg || 'WebSocket 连接错误' });
		});
	}

	/**
	 * 发送认证消息
	 */
	_authenticate() {
		const token = getToken();
		if (!token) {
			console.warn('[WebSocket] No token configured');
			this.status = WS_STATUS.READY;
			this.emit('statusChange', this.status);
			this._flushMessageQueue();
			return;
		}

		this.status = WS_STATUS.AUTHING;
		this.emit('statusChange', this.status);
		this._send({ type: 'auth', token });
	}

	/**
	 * 处理收到的消息
	 */
	_handleMessage(data) {
		this.lastMessageTime = Date.now();
		
		let message;
		try {
			message = JSON.parse(data);
		} catch (e) {
			console.error('[WebSocket] Invalid JSON:', data);
			return;
		}

		console.log('[WebSocket] Received:', message.type);

		switch (message.type) {
			case 'auth_success':
				this.status = WS_STATUS.READY;
				this.emit('statusChange', this.status);
				this.emit('ready', message);
				this._startHeartbeat();
				this._flushMessageQueue();
				break;

			case 'typing':
				this.emit('typing', message);
				break;

			case 'message':
				this.emit('message', message);
				break;

			case 'delta':
			case 'done':
				// Deprecated: streaming mode removed, should not receive these
				break;

			case 'error':
				// 认证失败时关闭连接
				if (message.code === 'auth_failed') {
					this.status = WS_STATUS.DISCONNECTED;
					this.emit('statusChange', this.status);
					this.close();
				}
				this.emit('error', message);
				break;

			case 'ping':
				this.emit('ping', message);
				break;

			case 'state_update':
				this.emit('state_update', message.data);
				break;

			default:
				console.log('[WebSocket] Unknown message type:', message.type);
		}
	}

	/**
	 * 发送消息（内部）
	 */
	_send(data) {
		if (!this.socket) return false;
		
		try {
			this.socket.send({
				data: JSON.stringify(data)
			});
			return true;
		} catch (err) {
			console.error('[WebSocket] Send failed:', err);
			return false;
		}
	}

	/**
	 * 发送聊天消息
	 */
	sendChat(content, messageId = null) {
		// Build local ISO 8601 timestamp with timezone offset
		const now = new Date();
		const tzOffset = -now.getTimezoneOffset();
		const tzSign = tzOffset >= 0 ? '+' : '-';
		const tzHours = String(Math.floor(Math.abs(tzOffset) / 60)).padStart(2, '0');
		const tzMinutes = String(Math.abs(tzOffset) % 60).padStart(2, '0');
		const client_time = now.getFullYear() + '-' +
			String(now.getMonth() + 1).padStart(2, '0') + '-' +
			String(now.getDate()).padStart(2, '0') + 'T' +
			String(now.getHours()).padStart(2, '0') + ':' +
			String(now.getMinutes()).padStart(2, '0') + ':' +
			String(now.getSeconds()).padStart(2, '0') +
			tzSign + tzHours + ':' + tzMinutes;

		const data = {
			type: 'chat',
			content,
			message_id: messageId,
			stop: false,
			client_time
		};

		if (this.status === WS_STATUS.READY) {
			this._send(data);
		} else {
			this.messageQueue.push(data);
			console.log('[WebSocket] Message queued, status:', this.status);
		}
	}

	/**
	 * 请求停止生成
	 */
	sendStop() {
		if (this.status === WS_STATUS.READY) {
			this._send({
				type: 'chat',
				content: '',
				message_id: null,
				stop: true
			});
		}
	}

	/**
	 * 刷新消息队列（连接就绪后发送）
	 */
	_flushMessageQueue() {
		while (this.messageQueue.length > 0) {
			const data = this.messageQueue.shift();
			this._send(data);
		}
	}

	/**
	 * 启动心跳检测
	 */
	_startHeartbeat() {
		this._stopHeartbeat();
		
		this.heartbeatTimer = setInterval(() => {
			const elapsed = Date.now() - this.lastMessageTime;
			if (elapsed > HEARTBEAT_TIMEOUT) {
				console.log('[WebSocket] Heartbeat timeout, reconnecting...');
				this.close();
				this._scheduleReconnect();
			}
		}, HEARTBEAT_INTERVAL);
	}

	/**
	 * 停止心跳
	 */
	_stopHeartbeat() {
		if (this.heartbeatTimer) {
			clearInterval(this.heartbeatTimer);
			this.heartbeatTimer = null;
		}
	}

	/**
	 * 安排重连
	 */
	_scheduleReconnect() {
		if (this.reconnectTimer) return;
		if (this.reconnectCount >= RECONNECT_CONFIG.maxRetries) {
			this.emit('error', { message: '连接已断开，超过最大重连次数，请检查网络或刷新页面' });
			return;
		}

		const delay = Math.min(
			RECONNECT_CONFIG.initialDelay * Math.pow(RECONNECT_CONFIG.backoffMultiplier, this.reconnectCount),
			RECONNECT_CONFIG.maxDelay
		);

		this.reconnectCount++;
		this.status = WS_STATUS.RECONNECTING;
		this.emit('statusChange', this.status);
		
		console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectCount}/${RECONNECT_CONFIG.maxRetries})`);
		this.emit('reconnecting', { attempt: this.reconnectCount, delay });

		this.reconnectTimer = setTimeout(() => {
			this.reconnectTimer = null;
			if (this.sessionId) {
				this.connect(this.sessionId);
			}
		}, delay);
	}

	/**
	 * 清理资源（内部使用，不关闭 socket）
	 */
	_cleanup() {
		this._stopHeartbeat();
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
	}

	/**
	 * 主动关闭连接
	 */
	close() {
		this.intentionalClose = true; // 标记为主动关闭，阻止 onClose 自动重连
		this._closeSocket();
		this.status = WS_STATUS.DISCONNECTED;
		this.emit('statusChange', this.status);
	}

	/**
	 * 关闭底层 socket 并清理资源
	 */
	_closeSocket() {
		this._stopHeartbeat();
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		if (this.socket) {
			try {
				this.socket.close();
			} catch (e) {
				// ignore
			}
			this.socket = null;
		}
	}

	/**
	 * 获取当前状态
	 */
	getStatus() {
		return this.status;
	}

	/**
	 * 是否已就绪（可发送消息）
	 */
	isReady() {
		return this.status === WS_STATUS.READY;
	}

	/**
	 * 销毁实例
	 */
	destroy() {
		this.close();
		this.listeners.clear();
		this.messageQueue = [];
	}
}

// 单例实例
let instance = null;

export const getWebSocket = () => {
	if (!instance) {
		instance = new ChatWebSocket();
	}
	return instance;
};

export const createWebSocket = () => {
	if (instance) {
		instance.destroy();
	}
	instance = new ChatWebSocket();
	return instance;
};

export default ChatWebSocket;
