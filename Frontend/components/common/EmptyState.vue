<template>
	<view class="empty-state">
		<view class="empty-icon-wrap">
			<text class="empty-icon">😊</text>
		</view>
		<text class="empty-title">{{ title }}</text>
		<text class="empty-desc">{{ description }}</text>
		<button v-if="showButton" class="empty-btn" @click="onClick">{{ buttonText }}</button>
	</view>
</template>

<script setup>
const props = defineProps({
	title: { type: String, default: '暂无内容' },
	description: { type: String, default: '' },
	showButton: { type: Boolean, default: false },
	buttonText: { type: String, default: '去创建' }
});

const emit = defineEmits(['click']);

const onClick = () => emit('click');
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	padding: 120rpx 40rpx;
}

.empty-icon-wrap {
	width: 160rpx;
	height: 160rpx;
	border-radius: 50%;
	background: $color-primary-light;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-bottom: 32rpx;
	animation: breathe 3s ease-in-out infinite;
}

.empty-icon {
	font-size: 72rpx;
	line-height: 1;
}

@keyframes breathe {
	0%, 100% { transform: scale(1); }
	50% { transform: scale(1.08); }
}

.empty-title {
	font-size: $font-size-title;
	color: $color-text-title;
	font-weight: $font-weight-bold;
	margin-bottom: 16rpx;
}

.empty-desc {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	text-align: center;
	line-height: 1.5;
	max-width: 400rpx;
}

.empty-btn {
	margin-top: 48rpx;
	background: $color-primary;
	color: #FFFFFF;
	font-size: $font-size-body;
	padding: 18rpx 64rpx;
	border-radius: $radius-xxl;
	border: none;
	transition: transform $duration-fast $ease-default;
}

.empty-btn:active {
	transform: scale(0.96);
	opacity: 0.9;
}
</style>
