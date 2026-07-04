<template>
  <view class="chat-header" :style="headerStyle">
    <view class="header-main">
      <image
        class="header-avatar"
        :src="avatarUrl"
        mode="aspectFill"
        @click="onAvatarClick"
      />
      <view class="header-info">
        <text class="header-name">{{ characterName }}</text>
        <text v-if="isTyping" class="typing-status">
          <text class="typing-dot">●</text> 正在输入...
        </text>
        <view class="header-state" v-else-if="state">
          <text class="state-mood">{{ moodIcon }} {{ state.mood }}</text>
          <view class="affection-bar">
            <view class="affection-track">
              <view class="affection-fill" :style="{ width: affectionPercent + '%' }"></view>
            </view>
            <text class="affection-text">好感 {{ state.affection || 50 }}</text>
          </view>
        </view>
      </view>
    </view>
    <view class="header-actions">
      <text class="action-icon" @click="onSettings">⚙</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue';
import { getServerConfig, MOOD_MAP } from '@/utils/constants.js';

const props = defineProps({
	characterName: { type: String, default: 'AI 角色' },
	characterAvatar: { type: String, default: '' },
	state: { type: Object, default: null },
	isConnected: { type: Boolean, default: false },
	isTyping: { type: Boolean, default: false }
});

const emit = defineEmits(['settings', 'avatarClick']);

const headerStyle = computed(() => '');

const avatarUrl = computed(() => {
	if (!props.characterAvatar) return '/static/images/default-avatar.png';
	if (props.characterAvatar.startsWith('http') || props.characterAvatar.startsWith('/static/')) return props.characterAvatar;
	const { serverUrl } = getServerConfig();
	if (serverUrl) return serverUrl.replace(/\/$/, '') + props.characterAvatar;
	return props.characterAvatar;
});

const moodIcon = computed(() => {
	if (!props.state?.mood) return '';
	return MOOD_MAP[props.state.mood]?.icon || '';
});

const affectionPercent = computed(() => {
	return Math.max(0, Math.min(100, props.state?.affection || 50));
});

const onSettings = () => emit('settings');
const onAvatarClick = () => emit('avatarClick');
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.chat-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16rpx 24rpx;
	background: #FFFFFF;
	border-bottom: 1rpx solid $color-border;
	position: relative;
}

.header-main {
	display: flex;
	align-items: center;
	flex: 1;
	min-width: 0;
}

.header-avatar {
	width: 72rpx;
	height: 72rpx;
	border-radius: $radius-round;
	margin-right: 16rpx;
	background: $color-bg-page;
	flex-shrink: 0;
	border: 2rpx solid $color-primary-light;
}

.header-info {
	flex: 1;
	min-width: 0;
}

.header-name {
	font-size: $font-size-title;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	display: block;
}

.typing-status {
	font-size: $font-size-aux;
	color: $color-primary-dark;
	margin-top: 4rpx;
	display: flex;
	align-items: center;
	gap: 6rpx;
}

.typing-dot {
	font-size: 14rpx;
	animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.3; }
}

.header-state {
	display: flex;
	align-items: center;
	gap: 16rpx;
	margin-top: 6rpx;
}

.state-mood {
	font-size: $font-size-aux;
	color: $color-text-secondary;
}

.affection-bar {
	display: flex;
	align-items: center;
	gap: 8rpx;
	flex: 1;
}

.affection-track {
	width: 100rpx;
	height: 10rpx;
	background: $color-border;
	border-radius: 5rpx;
	overflow: hidden;
}

.affection-fill {
	height: 100%;
	background: linear-gradient(90deg, $color-danger, $color-warning, $color-success);
	border-radius: 5rpx;
	transition: width $duration-slow $ease-default;
}

.affection-text {
	font-size: $font-size-micro;
	color: $color-text-secondary;
	white-space: nowrap;
}

.header-actions {
	display: flex;
	gap: 20rpx;
	margin-left: 16rpx;
}

.action-icon {
	font-size: 36rpx;
	color: $color-text-secondary;
	padding: 8rpx;
	transition: transform $duration-fast $ease-default;
}

.action-icon:active {
	transform: scale(0.9);
}
</style>
