<template>
	<view class="edit-page">
		<view class="form-scroll">
			<view class="avatar-section">
				<AvatarUploader
					:src="form.avatar"
					:show-delete="false"
					@upload="onAvatarUpload"
				/>
			</view>

			<view class="form-section">
				<view class="section-title">基础信息</view>
				<FormField label="昵称" v-model="form.name" required placeholder="如：小明" />
				<FormField label="简介" v-model="form.description" type="textarea" placeholder="一句话介绍自己" />
			</view>

			<view class="form-section">
				<view class="section-title">核心设定</view>
				<FormField label="背景故事" v-model="form.background" type="textarea" hint="你的背景故事" placeholder="我是一名..." />
				<FormField label="性格特征" v-model="form.personality" type="tag-input" hint="输入性格标签，如：开朗、幽默" />
				<FormField label="说话风格" v-model="form.speaking_style" type="textarea" hint="你说话的方式" placeholder="说话轻松随意..." />
			</view>

			<view class="form-bottom"></view>
		</view>

		<view class="footer">
			<button class="btn-save" :loading="isSaving" @click="save">保存修改</button>
		</view>
	</view>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { usePersonaStore } from '@/store/index.js';
import AvatarUploader from '@/components/character/AvatarUploader.vue';
import FormField from '@/components/common/FormField.vue';

const store = usePersonaStore();
const isSaving = ref(false);

const form = reactive({
	name: '',
	description: '',
	background: '',
	personality: [],
	speaking_style: '',
	avatar: ''
});

onMounted(() => {
	loadPersona();
});

const loadPersona = async () => {
	const data = await store.getDefaultPersona();
	if (data) {
		Object.assign(form, {
			name: data.name || '',
			description: data.description || '',
			background: data.background || '',
			personality: parseArray(data.personality),
			speaking_style: data.speaking_style || '',
			avatar: data.avatar || ''
		});
	}
};

const parseArray = (val) => {
	if (Array.isArray(val)) return val;
	if (typeof val === 'string' && val) {
		try { return JSON.parse(val); } catch (e) { return []; }
	}
	return [];
};

const onAvatarUpload = async (filePath) => {
	const data = await store.getDefaultPersona();
	if (data?.id) {
		try {
			const res = await store.uploadAvatar(data.id, filePath);
			form.avatar = res.avatar_url;
		} catch (e) {}
	}
};

const validate = () => {
	if (!form.name.trim()) {
		uni.showToast({ title: '昵称不能为空', icon: 'none' });
		return false;
	}
	return true;
};

const save = async () => {
	if (!validate()) return;
	isSaving.value = true;

	const data = await store.getDefaultPersona();
	if (!data?.id) {
		uni.showToast({ title: '无法获取用户信息', icon: 'none' });
		isSaving.value = false;
		return;
	}

	const payload = {
		name: form.name.trim(),
		description: form.description.trim() || undefined,
		background: form.background.trim() || undefined,
		personality: form.personality,
		speaking_style: form.speaking_style.trim() || undefined
	};

	try {
		await store.updatePersona(data.id, payload);
		setTimeout(() => uni.navigateBack(), 500);
	} catch (e) {
	} finally {
		isSaving.value = false;
	}
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.edit-page {
	display: flex;
	flex-direction: column;
	height: 100vh;
	background: $color-bg-page;
}

.form-scroll {
	flex: 1;
	padding: $spacing-md;
	overflow-y: auto;
}

.avatar-section {
	display: flex;
	justify-content: center;
	padding: $spacing-xxl 0;
}

.form-section {
	background: #FFFFFF;
	border-radius: $radius-xl;
	padding: $spacing-xl;
	margin-bottom: $spacing-md;
	box-shadow: $shadow-card;
}

.section-title {
	font-size: $font-size-title;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	margin-bottom: $spacing-lg;
	padding-bottom: $spacing-md;
	border-bottom: 1rpx solid $color-border;
}

.form-bottom {
	height: 120rpx;
}

.footer {
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	padding: $spacing-md $spacing-xl;
	background: #FFFFFF;
	border-top: 1rpx solid $color-border;
	z-index: 100;
}

.btn-save {
	width: 100%;
	background: linear-gradient(135deg, $color-primary, $color-primary-dark);
	color: #FFFFFF;
	font-size: $font-size-title;
	font-weight: $font-weight-bold;
	border-radius: $radius-xxl;
	height: 88rpx;
	line-height: 88rpx;
	border: none;
	transition: transform $duration-fast $ease-default;
}

.btn-save:active {
	transform: scale(0.97);
}
</style>
