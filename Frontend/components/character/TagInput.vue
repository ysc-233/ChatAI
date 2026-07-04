<template>
	<view class="tag-input">
		<view class="tag-list">
			<view v-for="(tag, index) in modelValue" :key="index" class="tag-item">
				<text class="tag-text">{{ tag }}</text>
				<text class="tag-close" @click="removeTag(index)">×</text>
			</view>
			<input
				v-if="inputVisible"
				ref="inputRef"
				v-model="inputValue"
				class="tag-input-field"
				:placeholder="placeholder"
				@confirm="handleConfirm"
				@blur="handleBlur"
				focus
				confirm-type="done"
			/>
			<view v-else class="tag-add" @click="showInput">
				<text class="tag-add-icon">+</text>
				<text>{{ placeholder }}</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, nextTick } from 'vue';

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	placeholder: { type: String, default: '添加标签' },
	maxTags: { type: Number, default: 20 }
});

const emit = defineEmits(['update:modelValue']);

const inputVisible = ref(false);
const inputValue = ref('');
const inputRef = ref(null);

const showInput = () => {
	if (props.modelValue.length >= props.maxTags) {
		uni.showToast({ title: `最多${props.maxTags}个标签`, icon: 'none' });
		return;
	}
	inputVisible.value = true;
	nextTick(() => {});
};

const handleConfirm = () => {
	const val = inputValue.value.trim();
	if (!val) {
		inputVisible.value = false;
		return;
	}

	if (props.modelValue.includes(val)) {
		uni.showToast({ title: '标签已存在', icon: 'none' });
		inputValue.value = '';
		return;
	}

	const newTags = [...props.modelValue, val];
	emit('update:modelValue', newTags);
	inputValue.value = '';
	inputVisible.value = false;
};

const handleBlur = () => {
	if (inputValue.value.trim()) {
		handleConfirm();
	} else {
		inputVisible.value = false;
	}
};

const removeTag = (index) => {
	const newTags = [...props.modelValue];
	newTags.splice(index, 1);
	emit('update:modelValue', newTags);
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.tag-input {
	width: 100%;
}

.tag-list {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 16rpx;
	padding: 20rpx 0;
}

.tag-item {
	display: flex;
	align-items: center;
	background: $color-primary-light;
	color: $color-primary-dark;
	padding: 12rpx 24rpx;
	border-radius: 32rpx;
	font-size: $font-size-aux;
}

.tag-text {
	margin-right: 12rpx;
}

.tag-close {
	font-size: $font-size-body;
	color: $color-primary-dark;
	padding: 0 4rpx;
}

.tag-add {
	display: flex;
	align-items: center;
	background: $color-border;
	color: $color-text-secondary;
	padding: 12rpx 24rpx;
	border-radius: 32rpx;
	font-size: $font-size-aux;
}

.tag-add-icon {
	font-size: $font-size-body;
	margin-right: 8rpx;
}

.tag-input-field {
	min-width: 160rpx;
	background: $color-bg-page;
	border-radius: $radius-xs;
	padding: 12rpx 20rpx;
	font-size: $font-size-aux;
	color: $color-text-body;
}
</style>
