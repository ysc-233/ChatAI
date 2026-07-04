<template>
	<view class="persona-list-page">
		<scroll-view class="list-scroll" scroll-y refresher-enabled :refresher-triggered="isRefreshing" @refresherrefresh="onRefresh">
			<!-- 设置入口 -->
			<view class="settings-entry" @click="goToSettings">
				<text class="settings-icon">⚙</text>
				<text class="settings-text">应用设置</text>
				<text class="settings-arrow">›</text>
			</view>

			<view class="section-title">我的身份</view>

			<view v-if="personas.length === 0 && !isLoading" class="empty-wrapper">
				<EmptyState
					title="还没有身份"
					description="创建一个虚拟身份，体验不同视角的对话"
					show-button
					button-text="创建身份"
					@click="goToDesign"
				/>
			</view>
			<view v-else :key="listKey" class="persona-list">
				<CharacterCard
					v-for="item in personas"
					:key="`p_${item.id}_${item.avatar || 'none'}`"
					:data="item"
					:is-selected="item.id === selectedId"
					@click="onCardClick(item)"
					@longpress="onCardLongPress(item)"
				/>
			</view>
		</scroll-view>

		<view class="fab-btn" @click="goToDesign">
			<text class="fab-icon">+</text>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { onShow } from '@dcloudio/uni-app';
import { usePersonaStore } from '@/store/index.js';
import CharacterCard from '@/components/character/CharacterCard.vue';
import EmptyState from '@/components/common/EmptyState.vue';

const store = usePersonaStore();
const isRefreshing = ref(false);
const selectedId = ref(null);
const listKey = ref(0);

const personas = computed(() => store.personas);
const isLoading = computed(() => store.isLoading);

onMounted(() => {
	loadPersonas();
});

onShow(() => {
	listKey.value++;
	loadPersonas();
});

const loadPersonas = async () => {
	await store.fetchPersonas();
};

const onRefresh = async () => {
	isRefreshing.value = true;
	await loadPersonas();
	isRefreshing.value = false;
};

const onCardClick = (item) => {
	uni.navigateTo({
		url: `/pages/personas/design?id=${item.id}`
	});
};

const onCardLongPress = (item) => {
	const itemList = [];
	if (item.id !== 1) {
		itemList.push('删除');
	}
	itemList.push(item.is_default ? '取消默认' : '设为默认');

	uni.showActionSheet({
		itemList,
		success: (res) => {
			const action = itemList[res.tapIndex];
			if (action === '删除') {
				confirmDelete(item);
			} else if (action.includes('默认')) {
				store.setDefaultPersona(item.id);
			}
		}
	});
};

const confirmDelete = (item) => {
	uni.showModal({
		title: '确认删除',
		content: `确定要删除身份「${item.name}」吗？`,
		confirmColor: '#FF3B30',
		success: (res) => {
			if (res.confirm) {
				store.deletePersona(item.id);
			}
		}
	});
};

const goToDesign = () => {
	uni.navigateTo({ url: '/pages/personas/design' });
};

const goToSettings = () => {
	uni.navigateTo({ url: '/pages/settings/settings' });
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.persona-list-page {
	display: flex;
	flex-direction: column;
	height: 100vh;
	background: $color-bg-page;
}

.list-scroll {
	flex: 1;
	padding: $spacing-md;
}

.settings-entry {
	display: flex;
	align-items: center;
	background: #FFFFFF;
	padding: $spacing-xl $spacing-lg;
	border-radius: $radius-xl;
	margin-bottom: $spacing-md;
	box-shadow: $shadow-card;
}

.settings-entry:active {
	opacity: 0.7;
}

.settings-icon {
	font-size: 40rpx;
	margin-right: $spacing-md;
	color: $color-primary;
}

.settings-text {
	flex: 1;
	font-size: $font-size-body;
	color: $color-text-body;
}

.settings-arrow {
	font-size: 36rpx;
	color: $color-text-secondary;
	opacity: 0.5;
}

.section-title {
	font-size: $font-size-title;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	margin: $spacing-md 0 $spacing-md 8rpx;
}

.empty-wrapper {
	padding-top: 60rpx;
}

.persona-list {
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
