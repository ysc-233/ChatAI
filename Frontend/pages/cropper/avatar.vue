<template>
	<view class="cropper-page" @touchmove.stop.prevent>
		<!-- 导航栏 -->
		<view class="cropper-nav" :style="{ paddingTop: statusBarHeight + 'px' }">
			<text class="nav-back" @click="goBack">←</text>
			<text class="nav-title">裁剪头像</text>
			<text class="nav-placeholder"></text>
		</view>

		<!-- 裁剪区域 -->
		<view class="cropper-area">
			<qf-image-cropper
				v-if="imageSrc"
				ref="cropperRef"
				:src="imageSrc"
				:width="cropSize"
				:height="cropSize"
				:radius="cropRadius"
				:choosable="false"
				:fileType="fileType"
				:showAngle="true"
				:showGrid="true"
				:showBorder="true"
				:checkRange="true"
				:bounce="true"
				:rotatable="true"
				:gpu="true"
				@crop="onCrop"
			/>
			<view v-else class="no-image">
				<text class="no-image-text">未选择图片</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref } from 'vue';
import { onLoad } from '@dcloudio/uni-app';

const statusBarHeight = ref(0);
const imageSrc = ref('');
const cropType = ref('circle');
const cropSize = ref(300);
const cropRadius = ref(0);
const fileType = ref('png');
const cropEventId = ref('');
const cropperRef = ref(null);

onLoad((options) => {
	const sysInfo = uni.getSystemInfoSync();
	statusBarHeight.value = sysInfo.statusBarHeight || 0;
	cropSize.value = sysInfo.windowWidth;

	const src = options?.src;
	cropType.value = options?.type || 'circle';
	cropEventId.value = options?.eventId || '';
	if (src) {
		imageSrc.value = decodeURIComponent(src);
		cropRadius.value = cropType.value === 'circle' ? cropSize.value / 2 : 0;
	}
});

const onCrop = (e) => {
	const eventName = cropEventId.value || 'avatarCropComplete';
	uni.$emit(eventName, {
		eventId: cropEventId.value,
		filePath: e.tempFilePath
	});
	uni.navigateBack();
};

const goBack = () => {
	uni.navigateBack();
};
</script>

<style lang="scss">
@import '@/common/styles/theme.scss';

.cropper-page {
	display: flex;
	flex-direction: column;
	height: 100vh;
	background: #000;
	overflow: hidden;
	touch-action: none;
}

.cropper-nav {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 20rpx 30rpx;
	background: #000;
	color: #fff;
	z-index: 100;
}

.nav-back {
	font-size: 40rpx;
	padding: 10rpx;
}

.nav-title {
	font-size: 32rpx;
	font-weight: 600;
}

.nav-placeholder {
	width: 60rpx;
}

.cropper-area {
	flex: 1;
	position: relative;
	overflow: hidden;
}

.no-image {
	position: absolute;
	top: 50%;
	left: 50%;
	transform: translate(-50%, -50%);
	color: $color-text-secondary;
	font-size: 30rpx;
}
</style>
