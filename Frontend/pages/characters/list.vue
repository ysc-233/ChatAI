<template>
	<view class="character-list-page">
		<!-- 搜索栏 -->
		<view class="search-bar">
			<uni-search-bar v-model="keyword" placeholder="搜索角色" @confirm="onSearch" @cancel="onClear" />
		</view>

		<!-- 角色列表 -->
		<scroll-view class="list-scroll" scroll-y refresher-enabled :refresher-triggered="isRefreshing" @refresherrefresh="onRefresh" @scrolltolower="onLoadMore">
			<view v-if="characters.length === 0 && !isLoading" class="empty-wrapper">
				<EmptyState
					title="还没有角色"
					description="创建一个独特的 AI 角色，开始对话吧"
					show-button
					button-text="创建角色"
					@click="goToDesign"
				/>
			</view>
			<view v-else :key="listKey" class="character-list">
				<CharacterCard
					v-for="item in characters"
					:key="`c_${item.id}_${item.avatar || 'none'}`"
					:data="item"
					:is-selected="item.id === selectedId"
					@click="onCardClick(item)"
					@longpress="onCardLongPress(item)"
				/>
				<uni-load-more v-if="characters.length > 0" :status="loadMoreStatus" />
			</view>
		</scroll-view>

		<!-- 新建按钮 -->
		<view class="fab-btn" @click="goToDesign">
			<text class="fab-icon">+</text>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { useCharacterStore, useSessionStore } from '@/store/index.js';
import CharacterCard from '@/components/character/CharacterCard.vue';
import EmptyState from '@/components/common/EmptyState.vue';

const store = useCharacterStore();
const sessionStore = useSessionStore();
const keyword = ref('');
const isRefreshing = ref(false);
const selectedId = ref(null);
const page = ref(1);
const hasMore = ref(true);
const listKey = ref(0);

const characters = computed(() => store.characters);
const isLoading = computed(() => store.isLoading);
const loadMoreStatus = computed(() => {
	if (isLoading.value) return 'loading';
	if (!hasMore.value) return 'noMore';
	return 'more';
});

onMounted(() => {
	loadCharacters();
});

onShow(() => {
	listKey.value++;
	loadCharacters();
});

const loadCharacters = async (refresh = false) => {
	if (refresh) page.value = 1;
	const params = {
		page: page.value,
		page_size: 20,
		keyword: keyword.value || undefined
	};
	try {
		const res = await store.fetchCharacters(params);
		hasMore.value = res.length >= 20;
	} catch (e) {
		hasMore.value = false;
	}
};

const onRefresh = async () => {
	isRefreshing.value = true;
	await loadCharacters(true);
	isRefreshing.value = false;
};

const onLoadMore = () => {
	if (isLoading.value || !hasMore.value) return;
	page.value++;
	loadCharacters();
};

const onSearch = () => {
	page.value = 1;
	loadCharacters(true);
};

const onClear = () => {
	keyword.value = '';
	onSearch();
};

const onCardClick = (item) => {
	uni.navigateTo({
		url: `/pages/characters/detail?id=${item.id}`
	});
};

const onCardLongPress = (item) => {
	const itemList = [];
	itemList.push('编辑');
	if (!item.is_system) {
		itemList.push('删除');
	}
	itemList.push('开始对话');

	uni.showActionSheet({
		itemList,
		success: (res) => {
			const action = itemList[res.tapIndex];
			if (action === '编辑') {
				uni.navigateTo({ url: `/pages/characters/design?id=${item.id}` });
			} else if (action === '删除') {
				confirmDelete(item);
			} else if (action === '开始对话') {
				startChat(item.id);
			}
		}
	});
};

const confirmDelete = (item) => {
	uni.showModal({
		title: '确认删除',
		content: `确定要删除角色「${item.name}」吗？这将删除所有关联的会话和消息。`,
		confirmColor: '#FF3B30',
		success: (res) => {
			if (res.confirm) {
				store.deleteCharacter(item.id);
			}
		}
	});
};

const startChat = async (characterId) => {
	uni.showLoading({ title: '加载中...' });
	const session = await sessionStore.getOrCreateSession(characterId);
	uni.hideLoading();
	if (session) {
		uni.navigateTo({ url: `/pages/chat/chat?character_id=${characterId}` });
	}
};

const goToDesign = () => {
	uni.navigateTo({ url: '/pages/characters/design' });
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.character-list-page {
	display: flex;
	flex-direction: column;
	height: 100vh;
	background: $color-bg-page;
}

.search-bar {
	background: #FFFFFF;
	padding: 0 20rpx;
	border-bottom: 1rpx solid $color-border;
}

.list-scroll {
	flex: 1;
	padding: $spacing-md;
	box-sizing: border-box;
}

.empty-wrapper {
	padding-top: 100rpx;
}

.character-list {
	padding-bottom: 120rpx;
	display: flex;
	flex-direction: column;
	gap: $spacing-md;
}

.fab-btn {
	position: fixed;
	right: 40rpx;
	bottom: 160rpx;
	width: 96rpx;
	height: 96rpx;
	background: $color-primary;
	border-radius: $radius-round;
	display: flex;
	align-items: center;
	justify-content: center;
	box-shadow: $shadow-fab;
	z-index: 100;
	transition: transform $duration-fast $ease-default;
}

.fab-btn:active {
	transform: scale(0.92);
}

.fab-icon {
	color: #FFFFFF;
	font-size: 48rpx;
	font-weight: 300;
}
</style>
