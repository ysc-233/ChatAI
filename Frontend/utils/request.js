/**
 * HTTP 请求封装
 * 统一处理：基础URL拼接、JWT认证、错误码处理、加载状态
 */

import { buildUrl, ERROR_CODES, getToken, getRefreshToken, setTokens, clearTokens } from './constants.js';

// 并发刷新互斥锁
let _isRefreshing = false;
let _refreshPromise = null;

// 请求拦截器
const request = (options) => {
	return new Promise((resolve, reject) => {
		const token = getToken();
		
		// 默认配置
		const defaultOptions = {
			timeout: 30000,
			header: {
				'Content-Type': 'application/json'
			}
		};
		
		// 合并配置
		const config = { ...defaultOptions, ...options };
		
		// JWT 认证
		if (token) {
			config.header['Authorization'] = `Bearer ${token}`;
		}
		
		// 构建完整URL
		if (config.url && !config.url.startsWith('http')) {
			config.url = buildUrl(config.url);
		}
		
		uni.request({
			...config,
			success: (res) => {
				const { statusCode, data } = res;
				
				// 401 处理：Token 过期 → 尝试刷新 → 失败则跳转登录
				if (statusCode === 401 && token) {
					if (!_isRefreshing) {
						_isRefreshing = true;
						_refreshPromise = _refreshAccessToken();
					}
					_refreshPromise.then(() => {
						_isRefreshing = false;
						_refreshPromise = null;
						// 重试原请求
						request(options).then(resolve).catch(reject);
					}).catch(() => {
						_isRefreshing = false;
						_refreshPromise = null;
						clearTokens();
						uni.reLaunch({ url: '/pages/auth/login' });
						reject(new Error('登录已过期，请重新登录'));
					});
					return;
				}
				
				// HTTP 层错误
				if (statusCode >= 400) {
					let errMsg = `HTTP ${statusCode}`;
					if (data && data.detail && data.detail.message) {
						errMsg = data.detail.message;
					} else if (data && data.message) {
						errMsg = data.message;
					} else if (statusCode === 401) {
						errMsg = '未认证：请重新登录';
					} else if (statusCode === 413) {
						errMsg = '请求体过大';
					} else if (statusCode === 500) {
						errMsg = '服务器内部错误';
					}
					
					reject(new Error(errMsg));
					return;
				}
				
				// 业务层错误（code !== 0）
				if (data && data.code !== undefined && data.code !== 0) {
					const errorCode = data.code;
					const errorMessage = data.message || ERROR_CODES[errorCode] || `未知错误 (${errorCode})`;
					const error = new Error(errorMessage);
					error.code = errorCode;
					error.data = data.data;
					reject(error);
					return;
				}
				
				// 成功
				resolve(data);
			},
			fail: (err) => {
				reject(new Error(err.errMsg || '网络请求失败'));
			}
		});
	});
};

// Token 刷新
const _refreshAccessToken = async () => {
	const refreshToken = getRefreshToken();
	if (!refreshToken) throw new Error('No refresh token');
	
	return new Promise((resolve, reject) => {
		uni.request({
			url: buildUrl('/api/auth/refresh'),
			method: 'POST',
			header: { 'Authorization': `Bearer ${refreshToken}` },
			success: (res) => {
				if (res.statusCode === 200 && res.data && res.data.code === 0) {
					setTokens(res.data.data.access_token, res.data.data.refresh_token);
					resolve();
				} else {
					reject(new Error('Token refresh failed'));
				}
			},
			fail: (err) => {
				reject(new Error(err.errMsg || 'Token refresh failed'));
			}
		});
	});
};

// HTTP 方法封装
export const http = {
	get(url, params = {}) {
		// 将 params 转换为 query string
		const query = Object.entries(params)
			.filter(([_, v]) => v !== undefined && v !== null)
			.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
			.join('&');
		
		const fullUrl = query ? `${url}?${query}` : url;
		return request({ url: fullUrl, method: 'GET' });
	},
	
	post(url, data = {}) {
		return request({ url, method: 'POST', data });
	},
	
	put(url, data = {}) {
		return request({ url, method: 'PUT', data });
	},
	
	delete(url, data = {}) {
		return request({ url, method: 'DELETE', data });
	},
	
	// 文件上传
	upload(url, filePath, name = 'file', formData = {}) {
		return new Promise((resolve, reject) => {
			const token = getToken();
			const fullUrl = buildUrl(url);
			
			const header = {};
			if (token) {
				header['Authorization'] = `Bearer ${token}`;
			}
			
			uni.uploadFile({
				url: fullUrl,
				filePath,
				name,
				formData,
				header,
				timeout: 60000,
				success: (res) => {
					let data;
					try {
						data = JSON.parse(res.data);
					} catch (e) {
						// 部分后端返回的原始数据不是 JSON，但 HTTP 成功时直接当作数据返回
						if (res.statusCode >= 200 && res.statusCode < 300) {
							resolve({ code: 0, data: res.data || null });
							return;
						}
						reject(new Error('解析响应数据失败'));
						return;
					}
					
					if (data.code !== undefined && data.code !== 0) {
						const errorCode = data.code;
						const errorMessage = data.message || ERROR_CODES[errorCode] || `未知错误 (${errorCode})`;
						const error = new Error(errorMessage);
						error.code = errorCode;
						reject(error);
						return;
					}
					
					resolve(data);
				},
				fail: (err) => {
					reject(new Error(err.errMsg || '文件上传失败'));
				}
			});
		});
	}
};

// 显示错误提示
export const showError = (err, title = '出错了') => {
	const message = err.message || err || '未知错误';
	uni.showToast({
		title: message,
		icon: 'none',
		duration: 3000
	});
	console.error(`[${title}]`, err);
};

// 显示成功提示
export const showSuccess = (message) => {
	uni.showToast({
		title: message,
		icon: 'success',
		duration: 2000
	});
};

// 加载状态封装
export const withLoading = async (fn, title = '加载中...') => {
	uni.showLoading({ title, mask: true });
	try {
		const result = await fn();
		return result;
	} catch (err) {
		showError(err);
		throw err;
	} finally {
		uni.hideLoading();
	}
};

export default http;
