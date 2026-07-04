<template>
	<view class="avatar-uploader" @click="chooseImage">
		<image
			class="avatar-img"
			:src="displayUrl"
			mode="aspectFill"
		/>
		<view v-if="hasImage && showDelete" class="delete-btn" @click.stop="onDelete">
			<text>×</text>
		</view>
	</view>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, getCurrentInstance, watch } from 'vue';
import { getServerConfig, UPLOAD_CONFIG } from '@/utils/constants.js';

const props = defineProps({
	src: { type: String, default: '' },
	showDelete: { type: Boolean, default: true }
});

const emit = defineEmits(['upload', 'delete']);
const hasImage = computed(() => !!props.src);

// 缓存破坏参数：当 src 变化时更新，强制 image 组件重新加载
const cacheBuster = ref(Date.now());
watch(() => props.src, () => {
	cacheBuster.value = Date.now();
});

// 暴露 refresh() 方法供父组件强制调用（解决 src 相同时不触发更新的问题）
const refresh = () => {
	cacheBuster.value = Date.now();
};
defineExpose({ refresh });

// 生成唯一事件名，防止跨页面全局事件泄漏
const instanceId = ref(`avatarCrop_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`);

const displayUrl = computed(() => {
	if (!props.src) return '/static/images/default-avatar.png';
	let url = props.src;
	if (url.startsWith('http') || url.startsWith('/static/')) {
		// 远程 URL 添加缓存破坏参数
		if (url.startsWith('http')) {
			const sep = url.includes('?') ? '&' : '?';
			url = `${url}${sep}_t=${cacheBuster.value}`;
		}
		return url;
	}
	const { serverUrl } = getServerConfig();
	if (serverUrl) {
		url = serverUrl.replace(/\/$/, '') + url;
		const sep = url.includes('?') ? '&' : '?';
		url = `${url}${sep}_t=${cacheBuster.value}`;
	}
	return url;
});

const onCropComplete = (data) => {
	if (data.eventId !== instanceId.value) return;  // 只响应自己的事件
	emit('upload', data.filePath);
};

onMounted(() => {
	uni.$on(instanceId.value, onCropComplete);
});

onUnmounted(() => {
	uni.$off(instanceId.value, onCropComplete);
});

const chooseImage = () => {
	uni.chooseImage({
		count: 1,
		sizeType: ['compressed'],
		sourceType: ['album', 'camera'],
		success: (res) => {
			const tempFilePath = res.tempFilePaths[0];
			
			// 检查文件大小
			uni.getFileInfo({
				filePath: tempFilePath,
				success: (fileInfo) => {
					if (fileInfo.size > UPLOAD_CONFIG.maxAvatarSize) {
						uni.showToast({ title: '图片超过5MB限制', icon: 'none' });
						return;
					}
					uni.navigateTo({
						url: `/pages/cropper/avatar?src=${encodeURIComponent(tempFilePath)}&type=circle&eventId=${instanceId.value}`
					});
				},
				fail: () => {
					uni.navigateTo({
						url: `/pages/cropper/avatar?src=${encodeURIComponent(tempFilePath)}&type=circle&eventId=${instanceId.value}`
					});
				}
			});
		},
		fail: (err) => {
			console.log('选择图片取消或失败', err);
		}
	});
};

const onDelete = () => {
	uni.showModal({
		title: '确认删除',
		content: '确定要删除头像吗？',
		success: (res) => {
			if (res.confirm) {
				emit('delete');
			}
		}
	});
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.avatar-uploader {
	position: relative;
	width: 160rpx;
	height: 160rpx;
	border-radius: 50%;
	overflow: hidden;
	cursor: pointer;
}

.avatar-img {
	width: 100%;
	height: 100%;
	object-fit: cover;
	background: $color-bg-page;
}

.delete-btn {
	position: absolute;
	top: 0;
	right: 0;
	width: 48rpx;
	height: 48rpx;
	background: $color-danger;
	color: #fff;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 32rpx;
	z-index: 10;
}
</style>
