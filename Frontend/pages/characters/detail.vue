<template>
	<view class="character-detail-page">
		<!-- 顶部英雄区 -->
		<view class="detail-hero">
			<view class="hero-overlay"></view>
			<view class="hero-content">
				<AvatarUploader
					:src="character.avatar"
					:show-delete="false"
					@upload="onAvatarUpload"
				/>
				<text class="detail-name">{{ character.name }}</text>
				<text v-if="character.nickname" class="detail-nickname">{{ character.nickname }}</text>
				<view class="detail-meta">
					<text v-if="character.age">{{ character.age }}</text>
					<text v-if="character.gender">{{ character.gender }}</text>
					<text v-if="character.is_system" class="system-tag">系统</text>
					<text v-if="character.is_default" class="default-tag">默认</text>
				</view>
			</view>
		</view>

		<!-- 信息区块 -->
		<scroll-view class="detail-scroll" scroll-y>
			<view class="detail-section">
				<view class="section-title">基础信息</view>
				<view class="info-row" v-if="character.appearance">
					<text class="info-label">外貌</text>
					<text class="info-value">{{ character.appearance }}</text>
				</view>
			</view>

			<view class="detail-section">
				<view class="section-title">核心设定</view>
				<view class="info-row" v-if="character.background">
					<text class="info-label">背景故事</text>
					<text class="info-value">{{ character.background }}</text>
				</view>
				<view class="info-row" v-if="character.personality && character.personality.length">
					<text class="info-label">性格</text>
					<view class="tag-list">
						<text v-for="(tag, i) in personalityTags" :key="i" class="info-tag">{{ tag }}</text>
					</view>
				</view>
				<view class="info-row" v-if="character.speaking_style">
					<text class="info-label">说话风格</text>
					<text class="info-value">{{ character.speaking_style }}</text>
				</view>
				<view class="info-row" v-if="emotionalTriggers">
					<text class="info-label">情感触发</text>
					<view class="kv-list">
						<view v-for="(val, key) in emotionalTriggers" :key="key" class="kv-item">
							<text class="kv-key">{{ key }}</text>
							<text class="kv-arrow">→</text>
							<text class="kv-val">{{ val }}</text>
						</view>
					</view>
				</view>
				<view class="info-row" v-if="taboos.length">
					<text class="info-label">禁忌</text>
					<view class="tag-list">
						<text v-for="(tag, i) in taboos" :key="i" class="info-tag danger">{{ tag }}</text>
					</view>
				</view>
			</view>

			<view class="detail-section" v-if="examples.length">
				<view class="section-title">示例对话</view>
				<view v-for="(ex, i) in examples" :key="i" class="example-box">
					<view class="example-user">
						<text class="example-label">你</text>
						<text class="example-text">{{ ex.user }}</text>
					</view>
					<view class="example-assistant">
						<text class="example-label">{{ character.name }}</text>
						<text class="example-text">{{ ex.assistant }}</text>
					</view>
				</view>
			</view>

			<view class="detail-section" v-if="character.world_setting">
				<view class="section-title">世界观</view>
				<text class="info-value">{{ character.world_setting }}</text>
			</view>

			<view class="scroll-bottom"></view>
		</scroll-view>

		<!-- 底部操作 -->
		<view class="detail-footer">
			<button class="btn-edit" @click="goEdit">编辑</button>
			<button class="btn-chat" @click="startChat">开始对话</button>
		</view>
	</view>
</template>

<script setup>
import { ref, computed } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { useCharacterStore, useSessionStore } from '@/store/index.js';
import AvatarUploader from '@/components/character/AvatarUploader.vue';

const store = useCharacterStore();
const sessionStore = useSessionStore();
const character = ref({});
const characterId = ref(null);

const personalityTags = computed(() => {
	const p = character.value.personality;
	if (Array.isArray(p)) return p;
	if (typeof p === 'string') {
		try { return JSON.parse(p); } catch (e) { return []; }
	}
	return [];
});

const emotionalTriggers = computed(() => {
	const t = character.value.emotional_triggers;
	if (typeof t === 'object' && !Array.isArray(t)) return t;
	if (typeof t === 'string') {
		try { return JSON.parse(t); } catch (e) { return null; }
	}
	return null;
});

const taboos = computed(() => {
	const t = character.value.taboos;
	if (Array.isArray(t)) return t;
	if (typeof t === 'string') {
		try { return JSON.parse(t); } catch (e) { return []; }
	}
	return [];
});

const examples = computed(() => {
	const e = character.value.examples;
	if (Array.isArray(e)) return e;
	if (typeof e === 'string') {
		try { return JSON.parse(e); } catch (err) { return []; }
	}
	return [];
});

onLoad((options) => {
	const id = options?.id;
	if (id) {
		characterId.value = parseInt(id);
		loadCharacter();
	}
});

const loadCharacter = async () => {
	const data = await store.getCharacter(characterId.value);
	if (data) {
		character.value = data;
	} else {
		uni.showToast({ title: '角色不存在', icon: 'none' });
		setTimeout(() => uni.navigateBack(), 1500);
	}
};

const onAvatarUpload = async (filePath) => {
	try {
		await store.uploadAvatar(characterId.value, filePath);
		await loadCharacter();
	} catch (e) {}
};

const goEdit = () => {
	uni.navigateTo({
		url: `/pages/characters/design?id=${characterId.value}`
	});
};

const startChat = async () => {
	uni.showLoading({ title: '加载中...' });
	const session = await sessionStore.getOrCreateSession(characterId.value);
	uni.hideLoading();
	if (session) {
		uni.navigateTo({ url: `/pages/chat/chat?character_id=${characterId.value}` });
	}
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.character-detail-page {
	display: flex;
	flex-direction: column;
	height: 100vh;
	background: $color-bg-page;
}

.detail-hero {
	position: relative;
	padding: 40rpx 30rpx;
	background: linear-gradient(180deg, $color-primary-light 0%, #FFFFFF 100%);
}

.hero-content {
	display: flex;
	flex-direction: column;
	align-items: center;
	position: relative;
	z-index: 1;
}

.detail-name {
	font-size: $font-size-title;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	margin-top: $spacing-md;
}

.detail-nickname {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-top: $spacing-xs;
}

.detail-meta {
	display: flex;
	gap: 16rpx;
	margin-top: $spacing-sm;
	font-size: $font-size-aux;
	color: $color-text-secondary;
}

.system-tag, .default-tag {
	padding: 4rpx 14rpx;
	border-radius: $radius-xs;
	font-size: $font-size-micro;
}

.system-tag {
	background: $color-warm-bg;
	color: $color-warning;
}

.default-tag {
	background: $color-primary-light;
	color: $color-primary-dark;
}

.detail-scroll {
	flex: 1;
	padding: $spacing-md;
	box-sizing: border-box;
}

.detail-section {
	background: #FFFFFF;
	border-radius: $radius-xl;
	padding: $spacing-xl;
	margin-bottom: $spacing-md;
	box-shadow: $shadow-card;
	box-sizing: border-box;
	width: 100%;
}

.section-title {
	font-size: $font-size-body;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	margin-bottom: 20rpx;
}

.info-row {
	margin-bottom: 24rpx;
}

.info-row:last-child {
	margin-bottom: 0;
}

.info-label {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	display: block;
	margin-bottom: 8rpx;
}

.info-value {
	font-size: $font-size-body;
	color: $color-text-body;
	line-height: 1.6;
}

.tag-list {
	display: flex;
	flex-wrap: wrap;
	gap: 12rpx;
}

.info-tag {
	background: $color-primary-light;
	color: $color-primary-dark;
	padding: 8rpx 20rpx;
	border-radius: $radius-xxl;
	font-size: $font-size-aux;
}

.info-tag.danger {
	background: $color-warm-pink;
	color: $color-danger;
}

.kv-list {
	display: flex;
	flex-direction: column;
	gap: 16rpx;
}

.kv-item {
	display: flex;
	align-items: center;
	gap: 12rpx;
	background: $color-bg-page;
	padding: 16rpx 20rpx;
	border-radius: $radius-sm;
}

.kv-key {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	font-weight: $font-weight-medium;
}

.kv-arrow {
	color: $color-text-secondary;
	font-size: $font-size-aux;
}

.kv-val {
	font-size: $font-size-aux;
	color: $color-text-body;
	flex: 1;
}

.example-box {
	background: $color-bg-page;
	border-radius: $radius-sm;
	padding: 20rpx;
	margin-bottom: 16rpx;
}

.example-box:last-child {
	margin-bottom: 0;
}

.example-user, .example-assistant {
	margin-bottom: 12rpx;
}

.example-assistant {
	margin-bottom: 0;
}

.example-label {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-right: 16rpx;
	font-weight: $font-weight-medium;
}

.example-text {
	font-size: $font-size-body;
	color: $color-text-body;
}

.scroll-bottom {
	height: 20rpx;
}

.detail-footer {
	display: flex;
	gap: 20rpx;
	padding: 20rpx 30rpx;
	background: #FFFFFF;
	border-top: 1rpx solid $color-border;
	box-sizing: border-box;
}

.btn-edit, .btn-chat {
	flex: 1;
	border-radius: $radius-xxl;
	font-size: $font-size-body;
	height: 80rpx;
	line-height: 80rpx;
	border: none;
	transition: transform $duration-fast $ease-default;
}

.btn-edit:active, .btn-chat:active {
	transform: scale(0.96);
}

.btn-edit {
	background: $color-bg-page;
	color: $color-text-body;
}

.btn-chat {
	background: $color-primary;
	color: #FFFFFF;
}
</style>
