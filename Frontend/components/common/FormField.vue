<template>
	<view class="form-field">
		<view class="field-label" v-if="label">
			<text>{{ label }}</text>
			<text v-if="required" class="required-mark">*</text>
		</view>
		<view class="field-hint" v-if="hint">{{ hint }}</view>

		<!-- text / number / email -->
		<input
			v-if="type === 'text' || type === 'number' || type === 'email'"
			class="field-input"
			:type="inputType"
			:value="innerModel"
			:placeholder="placeholder"
			:maxlength="maxlength"
			:disabled="false"
			:cursor-spacing="100"
			@input="handleInput"
			@blur="onBlur"
		/>

		<!-- textarea -->
		<textarea
			v-else-if="type === 'textarea'"
			class="field-textarea"
			:value="innerModel"
			:placeholder="placeholder"
			:maxlength="maxlength"
			:auto-height="autoHeight"
			:disabled="false"
			@input="handleInput"
			@blur="onBlur"
		/>

		<!-- radio -->
		<view v-else-if="type === 'radio'" class="field-radio-group">
			<view
				v-for="(opt, idx) in options"
				:key="idx"
				class="radio-item"
				:class="{ active: localValue === opt.value }"
				@click="handleRadioClick(opt.value)"
			>
				<text>{{ opt.text }}</text>
			</view>
		</view>

		<!-- slider -->
		<view v-else-if="type === 'slider'" class="field-slider">
			<slider
				:min="min"
				:max="max"
				:step="step"
				:value="Number(localValue)"
				@change="e => localValue = e.detail.value"
				show-value
			/>
		</view>

		<!-- tag-input -->
		<TagInput
			v-else-if="type === 'tag-input'"
			v-model="tagValue"
			:placeholder="placeholder"
			:max-tags="maxTags"
		/>

		<!-- key-value (object) -->
		<view v-else-if="type === 'key-value'" class="field-keyvalue">
			<view
				v-for="(val, key) in keyValueData"
				:key="key"
				class="kv-item"
			>
				<view class="kv-row">
					<input class="kv-key" :value="val.key" @input="e => val.key = getInputValue(e)" placeholder="触发场景" />
					<input class="kv-val" :value="val.value" @input="e => val.value = getInputValue(e)" placeholder="角色反应" />
					<text class="kv-delete" @click="removeKv(val._id)">×</text>
				</view>
			</view>
			<button class="kv-add-btn" @click="addKv">+ 添加</button>
		</view>

		<!-- 错误提示 -->
		<text v-if="error" class="field-error">{{ error }}</text>
	</view>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import TagInput from '../character/TagInput.vue';

const props = defineProps({
	label: { type: String, default: '' },
	hint: { type: String, default: '' },
	type: { type: String, default: 'text' },
	modelValue: { default: '' },
	placeholder: { type: String, default: '' },
	required: { type: Boolean, default: false },
	maxlength: { type: Number, default: -1 },
	options: { type: Array, default: () => [] },
	min: { type: Number, default: 0 },
	max: { type: Number, default: 100 },
	step: { type: Number, default: 1 },
	maxTags: { type: Number, default: 20 },
	autoHeight: { type: Boolean, default: true },
	validator: { type: Function, default: null }
});

const emit = defineEmits(['update:modelValue', 'blur']);

const localValue = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
});

// 本地可写模型，:value 绑定原生 input/textarea，@input 更新。
// 在 blur 时 emit update:modelValue 同步到父组件。
const innerModel = ref(props.modelValue);

// 父组件改值时（如加载已有角色）同步到本地
watch(() => props.modelValue, (val) => {
	if (val !== innerModel.value) {
		innerModel.value = val;
	}
});

const handleInput = (e) => {
	innerModel.value = e.detail?.value ?? e.target?.value;
};

const error = ref('');

const getInputValue = (e) => e.detail?.value ?? e.target?.value;

const handleRadioClick = (val) => {
	localValue.value = val;
};

const inputType = computed(() => {
	if (props.type === 'number') return 'number';
	if (props.type === 'email') return 'text';
	return 'text';
});

// tag-input 处理（将字符串/数组统一为数组）
const tagValue = computed({
	get() {
		const v = props.modelValue;
		if (Array.isArray(v)) return v;
		if (typeof v === 'string' && v) {
			try { return JSON.parse(v); } catch (e) { return []; }
		}
		return [];
	},
	set(val) {
		emit('update:modelValue', val);
	}
});

// key-value 处理
let kvIdCounter = 0;
const keyValueData = ref([]);

const initKv = () => {
	const v = props.modelValue;
	let newData = [];

	if (v && typeof v === 'object' && !Array.isArray(v)) {
		newData = Object.entries(v).map(([k, val]) => ({
			_id: ++kvIdCounter,
			key: k,
			value: val
		}));
	} else if (typeof v === 'string' && v) {
		try {
			const obj = JSON.parse(v);
			newData = Object.entries(obj).map(([k, val]) => ({
				_id: ++kvIdCounter,
				key: k,
				value: val
			}));
		} catch (e) {}
	}
	// 其他情况（undefined, null, "", {}, []）newData 保持为 []

	// 防循环：比较 key-value 内容，相同则不更新（保留现有对象引用）
	const currentPairs = keyValueData.value.map(i => `${i.key}:${i.value}`);
	const newPairs = newData.map(i => `${i.key}:${i.value}`);
	if (currentPairs.length === newPairs.length &&
		currentPairs.every((p, i) => p === newPairs[i])) {
		return;
	}

	keyValueData.value = newData;
};

watch(() => props.modelValue, initKv, { immediate: true });

watch(keyValueData, (val) => {
	const obj = {};
	val.forEach(item => {
		if (item.key.trim()) obj[item.key.trim()] = item.value.trim();
	});

	// 防循环：比较生成的 obj 与当前 props.modelValue
	const propsVal = props.modelValue;
	let propsObj = {};
	if (propsVal && typeof propsVal === 'object' && !Array.isArray(propsVal)) {
		propsObj = propsVal;
	} else if (typeof propsVal === 'string' && propsVal) {
		try { propsObj = JSON.parse(propsVal); } catch (e) {}
	}

	if (JSON.stringify(obj) === JSON.stringify(propsObj)) {
		return;
	}

	emit('update:modelValue', obj);
}, { deep: true });

const addKv = () => {
	keyValueData.value.push({ _id: ++kvIdCounter, key: '', value: '' });
};

const removeKv = (id) => {
	keyValueData.value = keyValueData.value.filter(item => item._id !== id);
};

const onBlur = () => {
	error.value = '';
	const value = innerModel.value;
	if (props.required && !value) {
		error.value = `${props.label}不能为空`;
	}
	if (props.validator) {
		const msg = props.validator(value);
		if (msg) error.value = msg;
	}
	emit('update:modelValue', value);
	emit('blur', value);
};

const validate = () => {
	onBlur();
	return !error.value;
};

defineExpose({ validate });
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.form-field {
	margin-bottom: 24rpx;
}

.field-label {
	font-size: $font-size-body;
	color: $color-text-body;
	font-weight: $font-weight-medium;
	margin-bottom: $spacing-sm;
	display: flex;
	align-items: center;
}

.required-mark {
	color: $color-danger;
	margin-left: $spacing-xs;
}

.field-hint {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	margin-bottom: $spacing-sm;
}

.field-input {
	width: 100%;
	height: 80rpx;
	line-height: 80rpx;
	background: $color-bg-page;
	border-radius: $radius-md;
	padding: 0 $spacing-lg;
	font-size: $font-size-body;
	color: $color-text-body;
	box-sizing: border-box;
	border: none;
	outline: none;
	transition: background $duration-normal $ease-default;
}

.field-input:focus {
	outline: 2rpx solid $color-primary;
	background: #FFFFFF;
}

.field-textarea {
	width: 100%;
	background: $color-bg-page;
	border-radius: $radius-md;
	padding: 20rpx 24rpx;
	font-size: $font-size-body;
	color: $color-text-body;
	box-sizing: border-box;
	border: 2rpx solid transparent;
	min-height: 120rpx;
	line-height: 1.6;
	transition: border-color $duration-normal $ease-default;
}

.field-textarea:focus {
	border-color: $color-primary;
	background: #FFFFFF;
}

.field-radio-group {
	display: flex;
	gap: $spacing-md;
	flex-wrap: wrap;
}

.radio-item {
	padding: 16rpx 32rpx;
	background: $color-bg-page;
	border-radius: $radius-xxl;
	font-size: $font-size-body;
	color: $color-text-secondary;
	border: 2rpx solid transparent;
	transition: all $duration-normal $ease-default;
}

.radio-item.active {
	background: $color-primary-light;
	color: $color-primary-dark;
	border-color: $color-primary;
}

.field-slider {
	padding: 16rpx 0;
}

.field-error {
	font-size: $font-size-aux;
	color: $color-danger;
	margin-top: $spacing-xs;
}

.field-keyvalue {
	width: 100%;
}

.kv-item {
	margin-bottom: 16rpx;
}

.kv-row {
	display: flex;
	align-items: center;
	gap: 16rpx;
}

.kv-key, .kv-val {
	flex: 1;
	background: $color-bg-page;
	border-radius: $radius-sm;
	padding: 16rpx 20rpx;
	font-size: $font-size-aux;
}

.kv-delete {
	font-size: 36rpx;
	color: $color-danger;
	padding: 0 16rpx;
}

.kv-add-btn {
	background: $color-border;
	color: $color-text-secondary;
	font-size: $font-size-aux;
	border: none;
	border-radius: $radius-sm;
	margin-top: $spacing-xs;
}
</style>
