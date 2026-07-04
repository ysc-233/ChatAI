<template>
	<view class="chat-input-bar">
		<view class="input-wrapper">
			<textarea
				class="input-field"
				v-model="text"
				:placeholder="placeholder"
				placeholder-class="input-placeholder"
				:maxlength="4000"
				:auto-height="true"
				confirm-type="send"
				@confirm="send"
				:disable-default-padding="true"
				:cursor-spacing="20"
				:show-confirm-bar="false"
				:hold-keyboard="false"
			/>
		</view>
		<view class="action-buttons">
			<button
				v-if="isTyping"
				class="btn-stop"
				@click="stop"
			>
				<text class="btn-icon-stop">■</text>
			</button>
			<button
				v-else
				class="btn-send"
				:disabled="!canSend || disabled"
				@click="send"
			>
				<text class="btn-icon-send">✈</text>
			</button>
		</view>
	</view>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
	isTyping: { type: Boolean, default: false },
	disabled: { type: Boolean, default: false },
	placeholder: { type: String, default: '想说点什么...' }
});

const emit = defineEmits(['send', 'stop']);

const text = ref('');
const lastSendTime = ref(0);

const canSend = computed(() => text.value.trim().length > 0);

const send = () => {
	const content = text.value.trim();
	if (!content || props.disabled) return;

	// 防抖 500ms
	const now = Date.now();
	if (now - lastSendTime.value < 500) return;
	lastSendTime.value = now;

	emit('send', content);
	text.value = '';
};

const stop = () => {
	emit('stop');
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.chat-input-bar {
	display: flex;
	align-items: flex-end;
	padding: 16rpx 20rpx;
	background: #FFFFFF;
	border-top: 1rpx solid $color-border;
	gap: 12rpx;
}

.input-wrapper {
	flex: 1;
	background: $color-bg-page;
	border-radius: $radius-xxl;
	padding: 14rpx 24rpx;
	min-height: 72rpx;
	max-height: 240rpx;
	display: flex;
	align-items: center;
}

.input-field {
	width: 100%;
	font-size: $font-size-body;
	color: $color-text-body;
	line-height: 1.4;
	min-height: 40rpx;
	max-height: 200rpx;
	background: transparent;
	padding: 4rpx 0;
}

.input-placeholder {
	color: $color-text-secondary;
	line-height: 1.4;
}

.action-buttons {
	flex-shrink: 0;
}

.btn-send, .btn-stop {
	width: 76rpx;
	height: 76rpx;
	border-radius: $radius-round;
	display: flex;
	align-items: center;
	justify-content: center;
	border: none;
	padding: 0;
	margin: 0;
	transition: transform $duration-fast $ease-default;
}

.btn-send:active, .btn-stop:active {
	transform: scale(0.9);
}

.btn-send {
	background: $color-primary;
	box-shadow: 0 4rpx 12rpx rgba(138, 164, 255, 0.3);
}

.btn-send[disabled] {
	background: #C8CCD6;
	box-shadow: none;
	opacity: 0.7;
}

.btn-stop {
	background: $color-danger;
	box-shadow: 0 4rpx 12rpx rgba(255, 59, 48, 0.3);
}

.btn-icon-send {
	font-size: 30rpx;
	color: #FFFFFF;
	transform: rotate(0deg);
}

.btn-icon-stop {
	font-size: 24rpx;
	color: #FFFFFF;
}
</style>
