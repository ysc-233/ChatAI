<template>
	<view class="message-list-page">
		<!-- 消息列表 -->
		<scroll-view class="list-scroll" scroll-y refresher-enabled :refresher-triggered="isRefreshing" @refresherrefresh="onRefresh">
			<view v-if="conversations.length === 0 && !isLoading" class="empty-wrapper">
				<EmptyState
					title="还没有对话"
					description="选择一个角色，开始你们的悄悄话吧～"
					show-button
					button-text="去角色页"
					@click="goToCharacters"
				/>
			</view>
			<view v-else class="conversation-list">
				<view
					v-for="item in conversations"
					:key="item.id"
					class="conversation-item"
					:class="{ 'privacy-blur': isPrivacyMode }"
					@click="enterChat(item)"
					@longpress="onLongPress(item)"
				>
					<view class="item-avatar-wrap">
						<image class="item-avatar" :src="getAvatarUrl(item.character)" mode="aspectFill" />
						<view v-if="item.character?.is_online" class="online-dot"></view>
					</view>
					<view class="item-info">
						<view class="item-header-row">
							<text class="item-name">{{ item.character?.name || '未知角色' }}</text>
							<text class="item-time">{{ formatTime(item.last_message_time || item.updated_at) }}</text>
						</view>
						<view class="item-preview-row">
							<text class="item-preview">{{ item.last_message || '暂无消息' }}</text>
							<view v-if="item.unread_count" class="unread-badge">
								<text class="unread-text">{{ item.unread_count > 99 ? '99+' : item.unread_count }}</text>
							</view>
						</view>
					</view>
				</view>
			</view>
		</scroll-view>
	</view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { useSessionStore } from '@/store/index.js';
import { getServerConfig } from '@/utils/constants.js';
import EmptyState from '@/components/common/EmptyState.vue';

const sessionStore = useSessionStore();
const isRefreshing = ref(false);
const isPrivacyMode = ref(false);

const conversations = computed(() => sessionStore.sessions);
const isLoading = computed(() => sessionStore.isLoading);

onMounted(() => {
	loadConversations();
	checkPrivacyMode();
});

onShow(() => {
	loadConversations();
	checkPrivacyMode();
});

const loadConversations = async () => {
	await sessionStore.fetchSessions({ include_last_message: 1 });
};

const checkPrivacyMode = () => {
	isPrivacyMode.value = !!uni.getStorageSync('privacy_mode');
};

const onRefresh = async () => {
	isRefreshing.value = true;
	await loadConversations();
	isRefreshing.value = false;
};

const getAvatarUrl = (character) => {
	if (!character?.avatar) return '/static/images/default-avatar.png';
	if (character.avatar.startsWith('http') || character.avatar.startsWith('/static/')) return character.avatar;
	const { serverUrl } = getServerConfig();
	if (serverUrl) return serverUrl.replace(/\/$/, '') + character.avatar;
	return character.avatar;
};

const parseDate = (dateStr) => {
	if (!dateStr) return null;
	if (dateStr.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(dateStr)) {
		return new Date(dateStr);
	}
	const normalized = dateStr.replace(' ', 'T');
	return new Date(normalized + 'Z');
};

const formatTime = (timeStr) => {
	if (!timeStr) return '';
	const date = parseDate(timeStr);
	if (!date || isNaN(date.getTime())) return '';
	const now = new Date();
	const isToday = date.toDateString() === now.toDateString();
	if (isToday) {
		return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
	}
	return `${date.getMonth() + 1}/${date.getDate()}`;
};

const enterChat = (item) => {
	const characterId = item.character?.id;
	if (!characterId) return;
	uni.navigateTo({ url: `/pages/chat/chat?character_id=${characterId}` });
};

const goToCharacters = () => {
	uni.switchTab({ url: '/pages/characters/list' });
};

const onLongPress = (item) => {
	uni.showActionSheet({
		itemList: ['清空消息', '删除会话'],
		success: (res) => {
			const action = ['清空消息', '删除会话'][res.tapIndex];
			if (action === '清空消息') {
				confirmClear(item);
			} else if (action === '删除会话') {
				confirmDelete(item);
			}
		}
	});
};

const confirmClear = (item) => {
	uni.showModal({
		title: '确认清空',
		content: `清空与「${item.character?.name || '未知角色'}」的所有消息？`,
		success: (res) => {
			if (res.confirm) {
				sessionStore.clearSessionMessages(item.id);
			}
		}
	});
};

const confirmDelete = (item) => {
	uni.showModal({
		title: '确认删除',
		content: `删除与「${item.character?.name || '未知角色'}」的会话？此操作不可恢复。`,
		confirmColor: '#FF3B30',
		success: (res) => {
			if (res.confirm) {
				sessionStore.deleteSession(item.id);
			}
		}
	});
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.message-list-page {
	display: flex;
	flex-direction: column;
	height: 100vh;
	background: $color-bg-page;
}

.list-scroll {
	flex: 1;
	padding: $spacing-md;
	box-sizing: border-box;
	width: 100%;
}

.empty-wrapper {
	padding-top: 120rpx;
}

.conversation-list {
	display: flex;
	flex-direction: column;
	gap: 16rpx;
}

.conversation-item {
	display: flex;
	align-items: center;
	padding: $spacing-lg;
	background: #FFFFFF;
	border-radius: $radius-lg;
	box-shadow: $shadow-card;
	transition: transform $duration-fast $ease-default;
	box-sizing: border-box;
	width: 100%;
}

.conversation-item:active {
	transform: scale(0.98);
	box-shadow: $shadow-card-hover;
}

.item-avatar-wrap {
	position: relative;
	flex-shrink: 0;
	margin-right: $spacing-lg;
}

.item-avatar {
	width: 96rpx;
	height: 96rpx;
	border-radius: $radius-round;
	background: $color-bg-page;
	border: 2rpx solid $color-primary-light;
}

.online-dot {
	position: absolute;
	right: 2rpx;
	bottom: 2rpx;
	width: 18rpx;
	height: 18rpx;
	background: $color-success;
	border-radius: $radius-round;
	border: 2rpx solid #FFFFFF;
}

.item-info {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: 8rpx;
}

.item-header-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.item-name {
	font-size: $font-size-body;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	flex: 1;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.item-time {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-left: 16rpx;
	white-space: nowrap;
}

.item-preview-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.item-preview {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	flex: 1;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.unread-badge {
	min-width: 36rpx;
	height: 36rpx;
	background: $color-danger;
	border-radius: 18rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-left: 12rpx;
	padding: 0 10rpx;
}

.unread-text {
	font-size: $font-size-micro;
	color: #FFFFFF;
	font-weight: $font-weight-bold;
}
</style>
