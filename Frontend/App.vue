<script>
import { isLoggedIn, clearTokens } from '@/utils/constants.js';
import { useUserStore } from '@/store/index.js';

export default {
	onLaunch: async function() {
		console.log('App Launch');

		// Route guard: check login status
		if (!isLoggedIn()) {
			uni.reLaunch({ url: '/pages/auth/login' });
			return;
		}

		// Initialize user info and auto-login
		try {
			const userStore = useUserStore();
			const user = await userStore.fetchUser();
			if (user) {
				uni.switchTab({ url: '/pages/message/list' });
			} else {
				clearTokens();
				uni.reLaunch({ url: '/pages/auth/login' });
			}
		} catch (e) {
			console.warn('Failed to fetch user:', e);
			clearTokens();
			uni.reLaunch({ url: '/pages/auth/login' });
		}
	},
	onShow: function() {
		console.log('App Show');
	},
	onHide: function() {
		console.log('App Hide');
	}
};
</script>

<style lang="scss">
@import '@/uni_modules/uni-scss/index.scss';
@import '@/common/styles/theme.scss';
@import '@/common/styles/animations.scss';
@import './common/uni.css';
@import '@/static/customicons.css';

page {
	background-color: $color-bg-page;
	height: 100%;
	font-size: $font-size-body;
	font-family: $font-family;
	color: $color-text-body;
	line-height: $line-height-base;
}

/* #ifdef H5 */
@media screen and (min-width: 768px) {
	body {
		overflow-y: scroll;
	}
}

uni-page-body {
	background-color: $color-bg-page !important;
	min-height: 100% !important;
	height: auto !important;
}
/* #endif */

/* === 全局按钮重置 === */
button {
	font-family: $font-family;
	&::after { border: none; }
}

/* === 全局滚动条 === */
::-webkit-scrollbar {
	width: 0;
	height: 0;
}

/* === 页面过渡动画 === */
.page-enter-active {
	animation: pageSlideIn $duration-normal $ease-default;
}

@keyframes pageSlideIn {
	from { transform: translateX(30rpx); opacity: 0; }
	to { transform: translateX(0); opacity: 1; }
}
</style>
