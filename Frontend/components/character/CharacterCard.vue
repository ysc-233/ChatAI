<template>
	<view class="character-card" :class="{ selected: isSelected }" @click="onClick">
		<view class="card-avatar">
			<image
				class="avatar-img"
				:src="avatarUrl"
				mode="aspectFill"
			/>
		</view>
		<view class="card-info">
			<text class="card-name">{{ data.name }}</text>
			<text v-if="data.nickname" class="card-nickname">{{ data.nickname }}</text>
			<view v-if="data.age || data.gender" class="card-meta">
				<text v-if="data.age">{{ data.age }}</text>
				<text v-if="data.gender">{{ data.gender }}</text>
			</view>
			<text v-if="data.description" class="card-desc">{{ data.description }}</text>
			<text v-else-if="getShortDesc" class="card-desc">{{ getShortDesc }}</text>
		</view>
		<view v-if="isSelected" class="selected-mark">
			<text class="mark-icon">✓</text>
		</view>
	</view>
</template>

<script setup>
import { computed } from 'vue';
import { getServerConfig } from '@/utils/constants.js';

const props = defineProps({
	data: { type: Object, required: true },
	isSelected: { type: Boolean, default: false }
});

const emit = defineEmits(['click']);

const avatarUrl = computed(() => {
	if (props.data.avatar) {
		const { serverUrl } = getServerConfig();
		if (serverUrl && !props.data.avatar.startsWith('http')) {
			return serverUrl.replace(/\/$/, '') + props.data.avatar;
		}
		return props.data.avatar;
	}
	return '/static/images/default-avatar.png';
});

const getShortDesc = computed(() => {
	const p = props.data.personality;
	if (Array.isArray(p) && p.length > 0) {
		return p.slice(0, 3).join(' · ');
	}
	if (typeof p === 'string') {
		try {
			const arr = JSON.parse(p);
			if (Array.isArray(arr)) return arr.slice(0, 3).join(' · ');
		} catch (e) {}
	}
	return '';
});

const onClick = () => emit('click', props.data);
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.character-card {
	display: flex;
	align-items: center;
	background: #FFFFFF;
	border-radius: $radius-xl;
	padding: $spacing-lg;
	box-shadow: $shadow-card;
	position: relative;
	border: 2rpx solid transparent;
	transition: all $duration-normal $ease-default;
	box-sizing: border-box;
	width: 100%;
}

.character-card:active {
	transform: translateY(-2rpx);
	box-shadow: $shadow-card-hover;
}

.character-card.selected {
	border-color: $color-primary;
	background: $color-primary-light;
}

.card-avatar {
	position: relative;
	margin-right: $spacing-lg;
	flex-shrink: 0;
}

.avatar-img {
	width: 100rpx;
	height: 100rpx;
	border-radius: $radius-round;
	background: $color-bg-page;
	border: 2rpx solid $color-primary-light;
}

.card-info {
	flex: 1;
	min-width: 0;
}

.card-name {
	font-size: $font-size-title;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	display: block;
}

.card-nickname {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-top: 4rpx;
	display: block;
}

.card-meta {
	display: flex;
	gap: 12rpx;
	margin-top: 8rpx;
	font-size: $font-size-aux;
	color: $color-text-secondary;
}

.card-desc {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-top: 8rpx;
	display: block;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.selected-mark {
	width: 48rpx;
	height: 48rpx;
	background: $color-primary;
	border-radius: $radius-round;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-left: 16rpx;
	flex-shrink: 0;
}

.mark-icon {
	color: #fff;
	font-size: 28rpx;
}
</style>
