<template>
	<view class="typing-indicator">
		<view class="indicator-bubble">
			<view class="dots">
				<view class="dot"></view>
				<view class="dot"></view>
				<view class="dot"></view>
			</view>
		</view>
	</view>
</template>

<script setup>
// 纯动画展示
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.typing-indicator {
	display: flex;
	padding: 12rpx 30rpx;
	animation: fadeInUp $duration-normal $ease-default;
}

@keyframes fadeInUp {
	from { opacity: 0; transform: translateY(8rpx); }
	to { opacity: 1; transform: translateY(0); }
}

.indicator-bubble {
	display: flex;
	align-items: center;
	background: #FFFFFF;
	padding: 24rpx 30rpx;
	border-radius: $radius-lg $radius-lg $radius-lg $radius-xs;
	box-shadow: $shadow-bubble-assistant;
}

.dots {
	display: flex;
	align-items: center;
	gap: 10rpx;
}

.dot {
	width: 16rpx;
	height: 16rpx;
	background: $color-primary;
	border-radius: $radius-round;
	animation: bounce 1.4s infinite ease-in-out both;
	opacity: 0.7;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
.dot:nth-child(3) { animation-delay: 0s; }

@keyframes bounce {
	0%, 80%, 100% {
		transform: scale(0.5);
		opacity: 0.3;
	}
	40% {
		transform: scale(1);
		opacity: 1;
	}
}
</style>
