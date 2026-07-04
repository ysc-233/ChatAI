import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import http from '@/utils/request.js';
import { clearTokens } from '@/utils/constants.js';

export const useUserStore = defineStore('user', () => {
	const user = ref(null);
	const isLoggedIn = computed(() => !!user.value);

	const fetchUser = async () => {
		try {
			const res = await http.get('/api/auth/me');
			user.value = res.data;
			return res.data;
		} catch (err) {
			console.error('Fetch user failed:', err);
			user.value = null;
			return null;
		}
	};

	const logout = () => {
		user.value = null;
		clearTokens();
		uni.reLaunch({ url: '/pages/auth/login' });
	};

	return { user, isLoggedIn, fetchUser, logout };
});
