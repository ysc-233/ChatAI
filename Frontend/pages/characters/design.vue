<template>
	<view class="design-page">
		<view class="form-scroll">
			<!-- 头像区域 -->
			<view class="avatar-section">
				<AvatarUploader
					:src="form.avatar"
					:show-delete="false"
					@upload="onAvatarUpload"
				/>
			</view>

			<view class="form-section">
				<view class="section-title">基础信息</view>
				<FormField label="角色名" v-model="form.name" required placeholder="如：小雨" />
				<FormField label="昵称" v-model="form.nickname" placeholder="如：雨儿" />
				<FormField label="年龄" v-model="form.age" placeholder="如：17岁" />
				<FormField label="性别" v-model="form.gender" type="radio" :options="genderOptions" />
				<FormField label="外貌" v-model="form.appearance" type="textarea" placeholder="描述角色的外貌特征..." />
			</view>

			<view class="form-section">
				<view class="section-title">核心设定</view>
				<FormField label="背景故事" v-model="form.background" type="textarea" required hint="角色的身世、经历、生活环境" placeholder="你是一名..." />
				<FormField label="性格特征" v-model="form.personality" type="tag-input" hint="输入性格标签，如：温柔、傲娇" />
				<FormField label="说话风格" v-model="form.speaking_style" type="textarea" hint="角色说话的方式、口头禅、用词习惯" placeholder="说话喜欢用..." />
				<FormField label="情感触发" v-model="form.emotional_triggers" type="key-value" hint="什么情况下角色会有什么反应" />
				<FormField label="禁忌话题" v-model="form.taboos" type="tag-input" hint="角色不会讨论的话题" />
			</view>

			<view class="form-section">
				<view class="section-title">示例对话</view>
				<view class="examples-list">
					<view v-for="(example, index) in form.examples" :key="index" class="example-card">
						<view class="example-header">
							<text class="example-index">示例 {{ index + 1 }}</text>
							<text class="example-delete" @click="removeExample(index)">删除</text>
						</view>
						<FormField label="用户" v-model="example.user" placeholder="用户说的话" />
						<FormField label="角色" v-model="example.assistant" placeholder="角色的回复" />
					</view>
					<button class="btn-add-example" @click="addExample">+ 添加示例</button>
				</view>
			</view>

			<view class="form-section">
				<view class="section-title">世界观</view>
				<FormField label="世界观设定" v-model="form.world_setting" type="textarea" hint="角色所处的世界观、与用户的相遇背景" placeholder="你们通过..." />
			</view>

			<view class="form-section">
				<view class="section-title">高级能力</view>
				<view class="search-toggle">
					<view class="toggle-label">
						<text class="toggle-title">联网搜索</text>
						<text class="toggle-hint">开启后，角色可在需要时搜索实时信息（新闻、天气、事实查询等）</text>
					</view>
					<switch :checked="form.search_enabled" @change="form.search_enabled = $event.detail.value" color="#8AA4FF" />
				</view>
			</view>

			<view class="form-section">
				<view class="section-title">初始状态</view>
				<FormField label="初始心情" v-model="form.initial_mood" placeholder="如：平静" />
				<FormField label="初始好感度" v-model="form.initial_affection" type="slider" :min="0" :max="100" hint="0-100，初始的好感度" />
			</view>

			<view v-if="isEdit" class="form-section">
				<view class="section-title">数据管理</view>
				<button class="btn-clear-memories" @click="clearMemories">清除长期记忆</button>
				<text class="clear-memories-hint">删除该角色所有已记住的对话信息，角色将忘记之前的互动</text>
			</view>

			<view class="form-bottom"></view>
		</view>

		<view class="footer">
			<button class="btn-save" :loading="isSaving" @click="save">{{ isEdit ? '保存修改' : '创建角色' }}</button>
		</view>
	</view>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { onLoad } from '@dcloudio/uni-app';
import { useCharacterStore } from '@/store/index.js';
import { GENDER_OPTIONS } from '@/utils/constants.js';
import AvatarUploader from '@/components/character/AvatarUploader.vue';
import FormField from '@/components/common/FormField.vue';

const store = useCharacterStore();
const isEdit = ref(false);
const characterId = ref(null);
const isSaving = ref(false);
const genderOptions = GENDER_OPTIONS;

const form = reactive({
	name: '',
	nickname: '',
	age: '',
	gender: '',
	appearance: '',
	background: '',
	personality: [],
	speaking_style: '',
	emotional_triggers: {},
	taboos: [],
	examples: [],
	world_setting: '',
	initial_mood: '平静',
	initial_affection: 50,
	avatar: '',
	search_enabled: false
});

onLoad((options) => {
	const id = options?.id;
	if (id) {
		isEdit.value = true;
		characterId.value = parseInt(id);
		loadCharacter();
	}
});

const loadCharacter = async () => {
	const data = await store.getCharacter(characterId.value);
	if (data) {
		Object.assign(form, {
			name: data.name || '',
			nickname: data.nickname || '',
			age: data.age || '',
			gender: data.gender || '',
			appearance: data.appearance || '',
			background: data.background || '',
			personality: parseArray(data.personality),
			speaking_style: data.speaking_style || '',
			emotional_triggers: parseObject(data.emotional_triggers),
			taboos: parseArray(data.taboos),
			examples: parseArray(data.examples),
			world_setting: data.world_setting || '',
			initial_mood: data.initial_mood || '平静',
			initial_affection: data.initial_affection !== undefined ? data.initial_affection : 50,
			avatar: data.avatar || '',
			search_enabled: data.search_enabled ? true : false
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

const parseObject = (val) => {
	if (typeof val === 'object' && val !== null && !Array.isArray(val)) return val;
	if (typeof val === 'string' && val) {
		try { return JSON.parse(val); } catch (e) { return {}; }
	}
	return {};
};

const addExample = () => {
	if (form.examples.length >= 10) {
		uni.showToast({ title: '最多10条示例', icon: 'none' });
		return;
	}
	form.examples.push({ user: '', assistant: '' });
};

const removeExample = (index) => {
	form.examples.splice(index, 1);
};

const onAvatarUpload = async (filePath) => {
	if (isEdit.value && characterId.value) {
		try {
			const res = await store.uploadAvatar(characterId.value, filePath);
			form.avatar = res.avatar_url;
		} catch (e) {}
	} else {
		form._tempAvatar = filePath;
		uni.showToast({ title: '请先保存角色，再上传头像', icon: 'none' });
	}
};

const clearMemories = () => {
	uni.showModal({
		title: '确认清除',
		content: '确定要清除该角色的所有长期记忆吗？角色将忘记与你之前的互动，此操作不可撤销。',
		confirmText: '确认清除',
		confirmColor: '#FF3B30',
		success: async (res) => {
			if (res.confirm) {
				try {
					await store.clearMemories(characterId.value);
				} catch (e) {}
			}
		}
	});
};

const validate = () => {
	if (!form.name.trim()) {
		uni.showToast({ title: '角色名称不能为空', icon: 'none' });
		return false;
	}
	if (!form.background.trim()) {
		uni.showToast({ title: '背景故事不能为空', icon: 'none' });
		return false;
	}
	if (form.personality.length === 0) {
		uni.showToast({ title: '性格特征至少填写一项', icon: 'none' });
		return false;
	}
	return true;
};

const save = async () => {
	if (!validate()) return;
	isSaving.value = true;

	const data = {
		name: form.name.trim(),
		nickname: form.nickname.trim() || undefined,
		age: form.age.trim() || undefined,
		gender: form.gender || undefined,
		appearance: form.appearance.trim() || undefined,
		background: form.background.trim(),
		personality: form.personality,
		speaking_style: form.speaking_style.trim() || undefined,
		emotional_triggers: form.emotional_triggers,
		taboos: form.taboos,
		examples: form.examples.filter(ex => ex.user.trim() || ex.assistant.trim()),
		world_setting: form.world_setting.trim() || undefined,
		initial_mood: form.initial_mood.trim() || undefined,
		initial_affection: form.initial_affection,
		search_enabled: form.search_enabled ? 1 : 0
	};

	try {
		if (isEdit.value) {
			await store.updateCharacter(characterId.value, data);
		} else {
			const res = await store.createCharacter(data);
			characterId.value = res.id;
			if (form._tempAvatar) {
				await store.uploadAvatar(characterId.value, form._tempAvatar);
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

.examples-list {
	display: flex;
	flex-direction: column;
	gap: $spacing-md;
}

.example-card {
	background: $color-bg-page;
	border-radius: $radius-sm;
	padding: $spacing-md;
}

.example-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 16rpx;
}

.example-index {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	font-weight: $font-weight-medium;
}

.example-delete {
	font-size: $font-size-aux;
	color: $color-danger;
	padding: 4rpx 8rpx;
}

.btn-add-example {
	background: $color-bg-page;
	color: $color-text-secondary;
	font-size: $font-size-body;
	border: none;
	border-radius: $radius-sm;
	padding: $spacing-md;
	margin-top: 8rpx;
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

.search-toggle {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 10rpx 0;
}

.toggle-label {
	flex: 1;
	display: flex;
	flex-direction: column;
}

.toggle-title {
	font-size: $font-size-body;
	color: $color-text-body;
	font-weight: $font-weight-medium;
}

.toggle-hint {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-top: 4rpx;
}

.btn-clear-memories {
	width: 100%;
	background: $color-warm-pink;
	color: $color-danger;
	font-size: $font-size-body;
	border: 1rpx solid #FFD4D4;
	border-radius: $radius-sm;
	padding: $spacing-md;
	margin-bottom: $spacing-sm;
}

.btn-clear-memories:active {
	background: #FFD4D4;
}

.clear-memories-hint {
	font-size: $font-size-micro;
	color: $color-text-secondary;
	display: block;
	text-align: center;
}
</style>
