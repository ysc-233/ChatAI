<template>
	<view class="auth-page">
		<view class="auth-card">
			<!-- 右上角设置齿轮 -->
			<view class="settings-toggle" @click="goServer">
				<text class="settings-icon">⚙</text>
			</view>

			<!-- Logo -->
			<view class="auth-logo">
				<image class="logo-img" src="/static/logo.png" mode="aspectFit" />
				<text class="logo-name">创建账号</text>
				<text class="logo-subtitle">加入 ChatAPP，开始你的对话</text>
			</view>

			<!-- 表单 -->
			<view class="auth-form">
				<view class="form-item">
					<text class="form-label">用户名</text>
					<input
						class="form-input"
						v-model="username"
						placeholder="3-50位字母、数字或下划线"
						placeholder-class="input-placeholder"
						maxlength="50"
					/>
				</view>
				<view class="form-item">
					<text class="form-label">昵称（可选）</text>
					<input
						class="form-input"
						v-model="nickname"
						placeholder="用于显示的昵称"
						placeholder-class="input-placeholder"
						maxlength="50"
					/>
				</view>
				<view class="form-item">
					<text class="form-label">密码</text>
					<view class="password-wrap">
						<input
							class="form-input"
							v-model="password"
							:password="!showPassword"
							placeholder="至少8位密码"
							placeholder-class="input-placeholder"
							maxlength="128"
						/>
						<text class="password-toggle" @click="showPassword = !showPassword">
							{{ showPassword ? '👁' : '👁‍🗨' }}
						</text>
					</view>
				</view>
				<view class="form-item">
					<text class="form-label">确认密码</text>
					<input
						class="form-input"
						v-model="confirmPassword"
						password
						placeholder="再次输入密码"
						placeholder-class="input-placeholder"
						maxlength="128"
					/>
				</view>

				<button
					class="auth-btn"
					:class="{ 'auth-btn--loading': isLoading }"
					:disabled="isLoading"
					@click="handleRegister"
				>
					{{ isLoading ? '注册中...' : '注册' }}
				</button>
			</view>

			<!-- 底部链接 -->
			<view class="auth-footer">
				<text class="footer-text">已有账号？</text>
				<text class="footer-link" @click="goLogin">去登录</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref } from 'vue';
import { setTokens, getServerConfig, buildUrl } from '@/utils/constants.js';

const username = ref('');
const nickname = ref('');
const password = ref('');
const confirmPassword = ref('');
const showPassword = ref(false);
const isLoading = ref(false);

const goServer = () => {
	uni.navigateTo({ url: '/pages/auth/server' });
};

const handleRegister = async () => {
	const { serverUrl } = getServerConfig();
	if (!serverUrl) {
		uni.showToast({ title: '请点击右上角⚙设置服务器地址', icon: 'none' });
		return;
	}
	if (!username.value.trim()) {
		uni.showToast({ title: '请输入用户名', icon: 'none' });
		return;
	}
	if (!/^[a-zA-Z0-9_]{3,50}$/.test(username.value.trim())) {
		uni.showToast({ title: '用户名格式：3-50位字母、数字或下划线', icon: 'none' });
		return;
	}
	if (!password.value || password.value.length < 8) {
		uni.showToast({ title: '密码至少8位', icon: 'none' });
		return;
	}
	if (password.value !== confirmPassword.value) {
		uni.showToast({ title: '两次密码不一致', icon: 'none' });
		return;
	}

	isLoading.value = true;
	try {
		const res = await new Promise((resolve, reject) => {
			uni.request({
				url: buildUrl('/api/auth/register'),
				method: 'POST',
				header: { 'Content-Type': 'application/json' },
				data: {
					username: username.value.trim(),
					password: password.value,
					nickname: nickname.value.trim() || undefined
				},
				success: (res) => {
					if (res.statusCode === 200 && res.data && res.data.code === 0) {
						resolve(res.data);
					} else {
						const msg = (res.data && res.data.detail && res.data.detail.message) || (res.data && res.data.message) || '注册失败';
						reject(new Error(msg));
					}
				},
				fail: (err) => {
					reject(new Error(err.errMsg || '网络请求失败'));
				}
			});
		});

		setTokens(res.data.access_token, res.data.refresh_token);

		uni.showToast({ title: '注册成功', icon: 'success' });

		setTimeout(() => {
			uni.switchTab({ url: '/pages/message/list' });
		}, 500);
	} catch (err) {
		uni.showToast({ title: err.message || '注册失败', icon: 'none' });
	} finally {
		isLoading.value = false;
	}
};

const goLogin = () => {
	uni.redirectTo({ url: '/pages/auth/login' });
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.auth-page {
	display: flex;
	align-items: center;
	justify-content: center;
	min-height: 100vh;
	background: linear-gradient(135deg, #E8EFFF 0%, #F7F8FA 50%, #E8EFFF 100%);
	padding: 40rpx;
}

.auth-card {
	width: 100%;
	max-width: 600rpx;
	background: #FFFFFF;
	border-radius: 32rpx;
	padding: 60rpx 48rpx 40rpx;
	box-shadow: 0 8rpx 40rpx rgba(0, 0, 0, 0.08);
	position: relative;
}

.settings-toggle {
	position: absolute;
	top: 24rpx;
	right: 24rpx;
	width: 64rpx;
	height: 64rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 2;
}

.settings-icon {
	font-size: 40rpx;
	color: $color-text-secondary;
	opacity: 0.5;
}

.auth-logo {
	display: flex;
	flex-direction: column;
	align-items: center;
	margin-bottom: 60rpx;
}

.logo-img {
	width: 120rpx;
	height: 120rpx;
	border-radius: 28rpx;
	margin-bottom: 24rpx;
}

.logo-name {
	font-size: 40rpx;
	font-weight: 700;
	color: $color-primary;
}

.logo-subtitle {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-top: 12rpx;
}

.auth-form {
	margin-bottom: 40rpx;
}

.form-item {
	margin-bottom: 32rpx;
}

.form-label {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-bottom: 12rpx;
	display: block;
}

.form-input {
	width: 100%;
	height: 88rpx;
	background: $color-bg-page;
	border-radius: 16rpx;
	padding: 0 24rpx;
	font-size: $font-size-body;
	color: $color-text-body;
	box-sizing: border-box;
	border: 2rpx solid transparent;
	transition: border-color $duration-normal $ease-default;
}

.form-input:focus {
	border-color: $color-primary;
}

.input-placeholder {
	color: $color-text-secondary;
	opacity: 0.5;
}

.password-wrap {
	position: relative;
}

.password-toggle {
	position: absolute;
	right: 24rpx;
	top: 50%;
	transform: translateY(-50%);
	font-size: 36rpx;
	z-index: 1;
}

.auth-btn {
	width: 100%;
	height: 96rpx;
	background: linear-gradient(135deg, $color-primary, $color-primary-dark);
	color: #FFFFFF;
	border-radius: 48rpx;
	font-size: 32rpx;
	font-weight: 600;
	border: none;
	margin-top: 48rpx;
	line-height: 96rpx;
	text-align: center;
	transition: opacity $duration-normal $ease-default;
}

.auth-btn:active {
	opacity: 0.8;
}

.auth-btn--loading {
	opacity: 0.7;
}

.auth-footer {
	display: flex;
	justify-content: center;
	align-items: center;
	gap: 8rpx;
}

.footer-text {
	font-size: $font-size-aux;
	color: $color-text-secondary;
}

.footer-link {
	font-size: $font-size-aux;
	color: $color-primary;
	font-weight: 600;
}
</style>
