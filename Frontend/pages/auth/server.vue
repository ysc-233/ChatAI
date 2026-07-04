<template>
	<view class="server-page">
		<view class="server-card">
			<view class="server-header">
				<text class="server-title">服务器设置</text>
				<text class="server-desc">配置 ChatAPP 后端服务地址</text>
			</view>

			<view class="form-item">
				<text class="form-label">服务器地址</text>
				<input
					class="form-input"
					v-model="serverUrl"
					placeholder="http://192.168.1.100:8000"
					placeholder-class="input-placeholder"
				/>
			</view>

			<view class="form-hint">
				示例：http://127.0.0.1:8000 或你的局域网IP加端口
			</view>

			<button class="save-btn" @click="handleSave">
				保存并返回
			</button>
		</view>
	</view>
</template>

<script setup>
import { ref } from 'vue';
import { getServerConfig, setServerConfig } from '@/utils/constants.js';

const serverUrl = ref(getServerConfig().serverUrl || '');

const handleSave = () => {
	const url = serverUrl.value.trim();
	if (!url) {
		uni.showToast({ title: '请输入服务器地址', icon: 'none' });
		return;
	}
	setServerConfig(url);
	uni.showToast({ title: '已保存', icon: 'success' });
	setTimeout(() => {
		uni.navigateBack();
	}, 500);
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.server-page {
	display: flex;
	align-items: center;
	justify-content: center;
	min-height: 100vh;
	background: $color-bg-page;
	padding: 40rpx;
}

.server-card {
	width: 100%;
	max-width: 600rpx;
	background: #FFFFFF;
	border-radius: 32rpx;
	padding: 60rpx 48rpx 40rpx;
	box-shadow: 0 8rpx 40rpx rgba(0, 0, 0, 0.08);
}

.server-header {
	text-align: center;
	margin-bottom: 48rpx;
}

.server-title {
	font-size: 36rpx;
	font-weight: 700;
	color: $color-text-title;
	display: block;
}

.server-desc {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-top: 12rpx;
	display: block;
}

.form-item {
	margin-bottom: 24rpx;
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

.form-hint {
	font-size: $font-size-micro;
	color: $color-text-secondary;
	margin-bottom: 48rpx;
	padding: 0 8rpx;
}

.save-btn {
	width: 100%;
	height: 96rpx;
	background: linear-gradient(135deg, $color-primary, $color-primary-dark);
	color: #FFFFFF;
	border-radius: 48rpx;
	font-size: 32rpx;
	font-weight: 600;
	border: none;
	line-height: 96rpx;
	text-align: center;
}

.save-btn:active {
	opacity: 0.8;
}
</style>
