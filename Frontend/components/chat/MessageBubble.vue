<template>
	<view class="message-bubble" :class="[roleClass, { 'has-avatar': isAssistant }]">
		<!-- AI 头像（仅助手，显示在左侧） -->
		<image
			v-if="isAssistant"
			class="msg-avatar"
			:src="avatarUrl"
			mode="aspectFill"
		/>

		<view class="bubble-wrapper">
			<!-- 消息内容 -->
			<view class="bubble-content" @longpress="onLongPress">
				<text class="msg-text" user-select>{{ message.content }}</text>
				<text v-if="!isDone && isAssistant" class="cursor">|</text>
			</view>

			<!-- 底部信息栏 -->
			<view class="bubble-footer">
				<text class="msg-time">{{ formatTime }}</text>
				<text v-if="message.token_count" class="msg-token">{{ message.token_count }} tokens</text>
			</view>
		</view>

		<!-- 用户头像（显示在右侧） -->
		<image
			v-if="isUser && props.userAvatar"
			class="msg-avatar user-avatar"
			:src="userAvatarUrl"
			mode="aspectFill"
		/>
		<view v-else-if="isUser" class="msg-avatar user-avatar user-default-avatar">
			<text class="default-avatar-text">我</text>
		</view>
	</view>
</template>

<script setup>
import { computed } from 'vue';
import { getServerConfig } from '@/utils/constants.js';

const props = defineProps({
	message: { type: Object, required: true },
	characterAvatar: { type: String, default: '' },
	userAvatar: { type: String, default: '' }
});

const emit = defineEmits(['longpress']);

const isUser = computed(() => props.message.role === 'user');
const isAssistant = computed(() => props.message.role === 'assistant');
const roleClass = computed(() => isUser.value ? 'user' : 'assistant');
const isDone = computed(() => props.message.isDone !== false);

const parseDate = (dateStr) => {
  if (!dateStr) return null;
  if (/[Z+\-]\d{2}:\d{2}$/.test(dateStr) || dateStr.endsWith('Z')) {
    return new Date(dateStr);
  }
  return new Date(dateStr + 'Z');
};

const resolveAvatar = (avatar) => {
	if (!avatar) return '/static/images/default-avatar.png';
	if (avatar.startsWith('http') || avatar.startsWith('/static/')) return avatar;
	const { serverUrl } = getServerConfig();
	if (serverUrl) return serverUrl.replace(/\/$/, '') + avatar;
	return avatar;
};

const avatarUrl = computed(() => resolveAvatar(props.characterAvatar));
const userAvatarUrl = computed(() => resolveAvatar(props.userAvatar));

const formatTime = computed(() => {
	if (!props.message.created_at) return '';
	let date = parseDate(props.message.created_at);
	if (!date || isNaN(date.getTime())) {
		date = new Date(props.message.created_at);
		if (isNaN(date.getTime())) return '';
	}
	const now = new Date();
	const isToday = date.toDateString() === now.toDateString();

	const hours = String(date.getHours()).padStart(2, '0');
	const minutes = String(date.getMinutes()).padStart(2, '0');

	if (isToday) {
		return `${hours}:${minutes}`;
	}
	return `${date.getMonth() + 1}/${date.getDate()} ${hours}:${minutes}`;
});

const onLongPress = () => {
	emit('longpress', props.message);
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.message-bubble {
	display: flex;
	align-items: flex-start;
	padding: 12rpx 24rpx;
	gap: 16rpx;
	animation: msgFadeIn $duration-slow $ease-default;
}

@keyframes msgFadeIn {
	from { opacity: 0; transform: translateY(16rpx); }
	to { opacity: 1; transform: translateY(0); }
}

/* 用户消息：右对齐 */
.message-bubble.user {
	flex-direction: row;
	justify-content: flex-end;
}

.msg-avatar {
	width: 72rpx;
	height: 72rpx;
	border-radius: $radius-round;
	flex-shrink: 0;
	background: $color-bg-page;
}

.user-avatar {
	background: $color-primary-light;
}

.user-default-avatar {
	display: flex;
	align-items: center;
	justify-content: center;
	background: $color-success;
}

.default-avatar-text {
	font-size: 28rpx;
	font-weight: $font-weight-bold;
	color: #FFFFFF;
}

.bubble-wrapper {
	max-width: 72%;
}

.bubble-content {
	padding: 20rpx 24rpx;
	border-radius: $radius-lg;
	font-size: $font-size-body;
	line-height: $line-height-bubble;
	word-break: break-word;
	position: relative;
}

.user .bubble-content {
	background: linear-gradient(135deg, $color-primary, $color-primary-dark);
	color: #FFFFFF;
	border-radius: $radius-lg $radius-lg $radius-xs $radius-lg;
	box-shadow: $shadow-bubble-user;
}

.assistant .bubble-content {
	background: #FFFFFF;
	color: $color-text-body;
	border-radius: $radius-lg $radius-lg $radius-lg $radius-xs;
	box-shadow: $shadow-bubble-assistant;
}

.msg-text {
	white-space: pre-wrap;
}

.cursor {
	display: inline-block;
	color: $color-primary;
	animation: blink 1s infinite;
	margin-left: 4rpx;
	font-weight: $font-weight-bold;
}

@keyframes blink {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.2; }
}

.bubble-footer {
	display: flex;
	align-items: center;
	gap: 16rpx;
	margin-top: 8rpx;
	padding: 0 8rpx;
}

.msg-time {
	font-size: $font-size-micro;
	color: $color-text-secondary;
}

.msg-token {
	font-size: 18rpx;
	color: $color-text-secondary;
	opacity: 0.5;
}

.user .bubble-footer {
	justify-content: flex-end;
}
</style>
