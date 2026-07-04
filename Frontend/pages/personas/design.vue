<template>
	<view class="design-page">
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
				<FormField label="身份名称" v-model="form.name" required placeholder="如：霸道总裁" />
				<FormField label="简介" v-model="form.description" type="textarea" placeholder="一句话描述这个身份" />
			</view>

			<view class="form-section">
				<view class="section-title">核心设定</view>
				<FormField label="背景故事" v-model="form.background" type="textarea" hint="该身份下的背景故事" placeholder="你是一家..." />
				<FormField label="性格特征" v-model="form.personality" type="tag-input" hint="输入性格标签，如：强势、冷静" />
				<FormField label="说话风格" v-model="form.speaking_style" type="textarea" hint="这个身份下你说话的方式" placeholder="说话简洁有力..." />
			</view>

			<view class="form-bottom"></view>
		</view>

		<view class="footer">
			<button class="btn-save" :loading="isSaving" @click="save">{{ isEdit ? '保存修改' : '创建身份' }}</button>
		</view>
	</view>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { usePersonaStore } from '@/store/index.js';
import AvatarUploader from '@/components/character/AvatarUploader.vue';
import FormField from '@/components/common/FormField.vue';

const store = usePersonaStore();
const isEdit = ref(false);
const personaId = ref(null);
const isSaving = ref(false);

const form = reactive({
	name: '',
	description: '',
	background: '',
	personality: [],
	speaking_style: '',
	avatar: ''
});

onLoad((options) => {
	const id = options?.id;
	if (id) {
		isEdit.value = true;
		personaId.value = parseInt(id);
		loadPersona();
	}
});

const loadPersona = async () => {
	const data = await store.getPersona(personaId.value);
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
	if (isEdit.value && personaId.value) {
		try {
			const res = await store.uploadAvatar(personaId.value, filePath);
			form.avatar = res.avatar_url;
		} catch (e) {}
	} else {
		form._tempAvatar = filePath;
		uni.showToast({ title: '请先保存身份，再上传头像', icon: 'none' });
	}
};

const validate = () => {
	if (!form.name.trim()) {
		uni.showToast({ title: '身份名称不能为空', icon: 'none' });
		return false;
	}
	return true;
};

const save = async () => {
	if (!validate()) return;
	isSaving.value = true;

	const data = {
		name: form.name.trim(),
		description: form.description.trim() || undefined,
		background: form.background.trim() || undefined,
		personality: form.personality,
		speaking_style: form.speaking_style.trim() || undefined
	};

	try {
		if (isEdit.value) {
			await store.updatePersona(personaId.value, data);
		} else {
			const res = await store.createPersona(data);
			personaId.value = res.id;
			if (form._tempAvatar) {
				await store.uploadAvatar(personaId.value, form._tempAvatar);
			}
		}
		setTimeout(() => uni.navigateBack(), 500);
	} catch (e) {
	} finally {
		isSaving.value = false;
	}
};
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.design-page {
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
