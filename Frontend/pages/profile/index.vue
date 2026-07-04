<template>
	<view class="profile-page">
		<!-- 顶部用户信息 -->
		<view class="profile-header">
			<AvatarUploader
				ref="avatarUploaderRef"
				:src="persona?.avatar"
				:show-delete="false"
				@upload="onAvatarUpload"
			/>
			<text class="profile-name">{{ persona?.name || '用户' }}</text>
			<text class="profile-desc">{{ persona?.description || '暂无简介' }}</text>
		</view>

		<!-- 功能菜单 -->
		<view class="menu-group">
			<view class="menu-item" @click="goEdit">
				<text class="menu-icon">✏</text>
				<text class="menu-text">编辑资料</text>
				<text class="menu-arrow">›</text>
			</view>
		</view>
		<view class="menu-group">
			<view class="menu-item" @click="goSettings">
				<text class="menu-icon">⚙</text>
				<text class="menu-text">应用设置</text>
				<text class="menu-arrow">›</text>
			</view>
			<view class="menu-item" @click="goAbout">
				<text class="menu-icon">ℹ</text>
				<text class="menu-text">关于应用</text>
				<text class="menu-arrow">›</text>
			</view>
		</view>

		<view class="menu-group">
			<view class="menu-item logout-item" @click="handleLogout">
				<text class="menu-icon">⎋</text>
				<text class="menu-text logout-text">退出登录</text>
				<text class="menu-arrow">›</text>
			</view>
		</view>

		<!-- 品牌标语 -->
		<view class="footer-brand">
			<text class="brand-text">安心对话，温暖陪伴</text>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { usePersonaStore, useUserStore } from '@/store/index.js';
import AvatarUploader from '@/components/character/AvatarUploader.vue';

const personaStore = usePersonaStore();
const userStore = useUserStore();
const persona = ref(null);
const avatarUploaderRef = ref(null);
const currentUser = ref(null);

onMounted(() => {
	loadPersona();
	loadUser();
});

onShow(() => {
	loadPersona();
	loadUser();
});

const loadUser = async () => {
	const data = await userStore.fetchUser();
	if (data) {
		currentUser.value = data;
	}
};

const loadPersona = async () => {
	const data = await personaStore.getDefaultPersona();
	if (data) {
		persona.value = data;
	}
};

const onAvatarUpload = async (filePath) => {
	if (!persona.value?.id) return;
	try {
		const res = await personaStore.uploadAvatar(persona.value.id, filePath);
		if (res?.avatar_url) {
			persona.value = { ...persona.value, avatar: res.avatar_url };
			avatarUploaderRef.value?.refresh();
		}
	} catch (e) {}
};

const handleLogout = () => {
	uni.showModal({
		title: '确认退出',
		content: '退出登录将清除本地数据',
		success: (res) => {
			if (res.confirm) {
				userStore.logout();
			}
		}
	});
};

const goEdit = () => {
	uni.navigateTo({ url: '/pages/profile/edit' });
};

const goSettings = () => {
	uni.navigateTo({ url: '/pages/settings/settings' });
};

const goAbout = () => {
	uni.navigateTo({ url: '/pages/settings/about' });
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.profile-page {
	display: flex;
	flex-direction: column;
	min-height: 100vh;
	background: $color-bg-page;
}

.profile-header {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 60rpx 40rpx 40rpx;
	background: linear-gradient(180deg, $color-primary-light 0%, #FFFFFF 100%);
	margin-bottom: $spacing-md;
}

.profile-name {
	font-size: $font-size-hero;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	margin-top: $spacing-lg;
}

.profile-desc {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-top: $spacing-sm;
}

.menu-group {
	background: #FFFFFF;
	margin: 0 $spacing-md $spacing-md;
	border-radius: $radius-md;
	overflow: hidden;
	box-shadow: $shadow-card;
}

.menu-item {
	display: flex;
	align-items: center;
	padding: 28rpx $spacing-lg;
	border-bottom: 1rpx solid $color-border;
}

.menu-item:last-child {
	border-bottom: none;
}

.menu-item:active {
	background: $color-bg-page;
}

.menu-icon {
	font-size: 36rpx;
	width: 44rpx;
	text-align: center;
	margin-right: $spacing-md;
	color: $color-primary;
	flex-shrink: 0;
}

.menu-text {
	flex: 1;
	font-size: $font-size-body;
	color: $color-text-body;
}

.menu-arrow {
	font-size: 36rpx;
	color: $color-text-secondary;
	opacity: 0.5;
}

.footer-brand {
	text-align: center;
	padding: 40rpx;
}

.brand-text {
	font-size: $font-size-aux;
	color: $color-primary;
	opacity: 0.6;
}

.logout-item:active {
	background: rgba(255, 59, 48, 0.05);
}

.logout-text {
	color: $color-danger;
}
</style>
