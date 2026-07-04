<template>
	<view class="settings-page">
		<view class="settings-section">
			<view class="section-header">
				<text class="section-title">服务器配置</text>
			</view>
			<view class="setting-item">
				<text class="item-label">服务器地址</text>
				<input
					class="item-input"
					v-model="config.serverUrl"
					placeholder="如：https://your-server.com"
				/>
			</view>
			<view class="setting-item center">
				<button class="btn-test" :loading="testing" @click="testConnection">测试连接</button>
			</view>
		</view>

		<view class="settings-section">
			<view class="section-header">
				<text class="section-title">缓存管理</text>
			</view>
			<view class="setting-item clickable" @click="clearCache">
				<text class="item-label">清除本地缓存</text>
				<text class="item-value">角色、会话等缓存数据</text>
				<text class="item-arrow">›</text>
			</view>
		</view>

		<view class="settings-section">
			<view class="section-header">
				<text class="section-title">隐私安全</text>
			</view>
			<view class="setting-item">
				<view class="item-label-wrap">
					<text class="item-label">隐私模式</text>
					<text class="item-hint">开启后消息列表将模糊显示</text>
				</view>
				<switch :checked="privacyMode" @change="togglePrivacy" color="#8AA4FF" />
			</view>
		</view>

		<view class="footer-actions">
			<button class="btn-save" @click="saveSettings">保存设置</button>
		</view>
	</view>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useAppStore } from '@/store/index.js';
import { getServerConfig, setServerConfig } from '@/utils/constants.js';
import { showError, showSuccess } from '@/utils/request.js';

const store = useAppStore();
const testing = ref(false);
const privacyMode = ref(false);

const config = reactive({
	serverUrl: ''
});

onMounted(() => {
	const saved = getServerConfig();
	config.serverUrl = saved.serverUrl;
	privacyMode.value = uni.getStorageSync('privacy_mode') || false;
});

const testConnection = async () => {
	if (!config.serverUrl.trim()) {
		showError('请输入服务器地址');
		return;
	}
	testing.value = true;
	store.setConfig(config.serverUrl.trim());
	try {
		const result = await store.checkHealth();
		if (result) {
			showSuccess('连接成功');
		} else {
			showError('连接失败，请检查服务器地址');
		}
	} catch (e) {
		showError('连接失败：' + (e.message || '网络错误'));
	} finally {
		testing.value = false;
	}
};

const saveSettings = () => {
	store.setConfig(config.serverUrl.trim());
	uni.setStorageSync('privacy_mode', privacyMode.value);
	showSuccess('设置已保存');
	setTimeout(() => uni.navigateBack(), 800);
};

const togglePrivacy = (e) => {
	privacyMode.value = e.detail.value;
};

const clearCache = () => {
	uni.showModal({
		title: '确认清除',
		content: '清除所有本地缓存数据？不会影响服务器数据。',
		success: (res) => {
			if (res.confirm) {
				uni.clearStorageSync();
				showSuccess('缓存已清除');
			}
		}
	});
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.settings-page {
	min-height: 100vh;
	background: $color-bg-page;
	padding: $spacing-md;
	padding-bottom: 140rpx;
}

.settings-section {
	background: #FFFFFF;
	margin-bottom: $spacing-md;
	border-radius: $radius-xl;
	padding: $spacing-xl;
	box-shadow: $shadow-card;
}

.section-header {
	margin-bottom: $spacing-lg;
}

.section-title {
	font-size: $font-size-body;
	color: $color-text-secondary;
	font-weight: $font-weight-medium;
}

.setting-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 20rpx 0;
	border-bottom: 1rpx solid $color-border;
}

.setting-item:last-child {
	border-bottom: none;
}

.setting-item.center {
	justify-content: center;
}

.setting-item.clickable:active {
	opacity: 0.7;
}

.item-label-wrap {
	display: flex;
	flex-direction: column;
	gap: 4rpx;
}

.item-label {
	font-size: $font-size-body;
	color: $color-text-body;
}

.item-hint {
	font-size: $font-size-aux;
	color: $color-text-secondary;
}

.item-input {
	flex: 1;
	font-size: $font-size-body;
	color: $color-text-body;
	text-align: right;
	margin-left: 20rpx;
}

.item-value {
	font-size: $font-size-body;
	color: $color-text-secondary;
	margin-left: 20rpx;
}

.item-arrow {
	font-size: 36rpx;
	color: $color-text-secondary;
	opacity: 0.5;
	margin-left: 12rpx;
}

.btn-test {
	width: 100%;
	background: $color-success;
	color: #FFFFFF;
	font-size: $font-size-body;
	border-radius: $radius-xxl;
	border: none;
	height: 72rpx;
	line-height: 72rpx;
}

.footer-actions {
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	padding: $spacing-md $spacing-xl;
	background: #FFFFFF;
	border-top: 1rpx solid $color-border;
	z-index: 100;
}

.btn-save {
	width: 100%;
	background: linear-gradient(135deg, $color-primary, $color-primary-dark);
	color: #FFFFFF;
	font-size: $font-size-title;
	font-weight: $font-weight-bold;
	border-radius: $radius-xxl;
	height: 88rpx;
	line-height: 88rpx;
	border: none;
	transition: transform $duration-fast $ease-default;
}

.btn-save:active {
	transform: scale(0.97);
}
</style>
