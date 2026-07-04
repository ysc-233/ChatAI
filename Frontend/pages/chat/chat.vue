<template>
  <view class="chat-page">
    <!-- 自定义导航栏 -->
    <view class="custom-nav" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-content">
        <ChatHeader
          :character-name="characterName"
          :character-avatar="characterAvatar"
          :state="characterState"
          :is-connected="isConnected"
          :is-typing="isTyping"
          @settings="onSettings"
        />
        <view v-if="!isConnected && wsStatus !== 'disconnected'" class="connection-status">
          <text class="status-text">{{ wsStatusText }}</text>
        </view>
      </view>
    </view>

    <!-- 消息列表 -->
    <scroll-view
      class="message-list"
      scroll-y
      :scroll-into-view="scrollIntoViewId"
      :scroll-with-animation="false"
      @scrolltoupper="onScrollToTop"
      :refresher-enabled="false"
    >
      <!-- 加载更多 -->
      <view v-if="isLoadingMessages" class="loading-more">
        <view class="loading-dots">
          <view class="loading-dot"></view>
          <view class="loading-dot"></view>
          <view class="loading-dot"></view>
        </view>
      </view>

      <view v-if="messages.length === 0 && !isLoadingMessages" class="welcome-area">
        <image class="welcome-avatar" :src="characterAvatar" mode="aspectFill" />
        <text class="welcome-name">{{ characterName }}</text>
        <text class="welcome-hint">发送消息开始对话</text>
      </view>

      <!-- 消息气泡 -->
      <MessageBubble
        v-for="(msg, index) in messages"
        :key="msg.id || index"
        :message="msg"
        :character-avatar="characterAvatar"
        :user-avatar="userAvatar"
        @longpress="onMessageLongPress(msg)"
      />

      <!-- 正在输入 -->
      <TypingIndicator v-if="isTyping" />

      <!-- 搜索状态 -->
      <view v-if="searchStatus" class="search-status">
        <view v-if="searchStatus.status === 'searching'" class="search-tag searching">
          <text class="search-tag-text">🔍 正在搜索：{{ searchStatus.query }}</text>
        </view>
        <view v-else-if="searchStatus.status === 'empty'" class="search-tag empty">
          <text class="search-tag-text">未找到相关信息，使用已有知识回复</text>
        </view>
      </view>

      <view class="scroll-bottom" :id="`scroll-bottom-${scrollCounter}`" :style="{ height: (keyboardHeight > 0 ? keyboardHeight + 'px' : '20rpx') }"></view>
    </scroll-view>

    <!-- 底部输入栏 -->
    <view class="input-area">
		<ChatInput
			:is-typing="isTyping"
			placeholder="想说点什么..."
			@send="onSend"
			@stop="onStop"
		/>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { onLoad, onShow } from '@dcloudio/uni-app';
import { useSessionStore, useChatStore, useCharacterStore, usePersonaStore } from '@/store/index.js';
import { WS_STATUS } from '@/utils/constants.js';
import ChatHeader from '@/components/chat/ChatHeader.vue';
import MessageBubble from '@/components/chat/MessageBubble.vue';
import TypingIndicator from '@/components/chat/TypingIndicator.vue';
import ChatInput from '@/components/chat/ChatInput.vue';

const sessionStore = useSessionStore();
const chatStore = useChatStore();
const characterStore = useCharacterStore();
const personaStore = usePersonaStore();

const statusBarHeight = ref(0);
const scrollIntoViewId = ref('');
const scrollCounter = ref(0);
const isLoadingMessages = ref(false);
const isLoadingHistory = ref(false);
const keyboardHeight = ref(0);
const characterId = ref(null);

const messages = computed(() => chatStore.messages);
const isConnected = computed(() => chatStore.isConnected);
const isTyping = computed(() => chatStore.isTyping);
const wsStatus = computed(() => chatStore.wsStatus);
const wsStatusText = computed(() => chatStore.wsStatusText);
const characterState = computed(() => chatStore.characterState);
const searchStatus = computed(() => chatStore.searchStatus);

const activeSession = computed(() => sessionStore.activeSession);
const character = computed(() => activeSession.value?.character || {});
const userPersona = computed(() => activeSession.value?.user_persona || {});

const characterName = computed(() => character.value?.name || 'AI 角色');
const characterAvatar = computed(() => {
  const avatar = character.value?.avatar;
  if (!avatar) return '/static/images/default-avatar.png';
  return avatar;
});
const userAvatar = computed(() => {
  const avatar = userPersona.value?.avatar;
  const charAvatar = character.value?.avatar;
  if (!avatar || avatar === charAvatar) return '';
  return avatar;
});

onMounted(() => {
  const sysInfo = uni.getSystemInfoSync();
  statusBarHeight.value = sysInfo.statusBarHeight || 0;

  uni.onKeyboardHeightChange(onKeyboardHeightChange);
});

onLoad((options) => {
  const charId = options?.character_id;
  if (!charId) {
    uni.showToast({ title: '参数错误', icon: 'none' });
    uni.navigateBack();
    return;
  }
  characterId.value = parseInt(charId);
  initChat(characterId.value);
});

onShow(() => {
  if (characterId.value && !chatStore.isConnected && !chatStore.isTyping && activeSession.value?.id) {
    connectWebSocket();
  }
});

onUnmounted(() => {
  chatStore.disconnect();
  uni.offKeyboardHeightChange(onKeyboardHeightChange);
});

const initChat = async (charId) => {
  chatStore.disconnect();
  chatStore.clearMessages();

  const session = await sessionStore.getOrCreateSession(charId);
  if (!session) {
    uni.showToast({ title: '无法获取会话', icon: 'none' });
    return;
  }

  await sessionStore.activateSession(session.id);
  await loadMessages();
  await chatStore.getCharacterState(session.id);
  connectWebSocket();
  scrollToBottom();
};

const loadMessages = async () => {
  if (!activeSession.value?.id) return;
  isLoadingMessages.value = true;
  await chatStore.fetchMessages(activeSession.value.id);
  isLoadingMessages.value = false;
};

const loadMoreMessages = async () => {
  if (!activeSession.value?.id || isLoadingMessages.value || !chatStore.hasMoreMessages) return;
  const firstMsg = messages.value[0];
  if (!firstMsg) return;
  isLoadingHistory.value = true;
  isLoadingMessages.value = true;
  await chatStore.fetchMessages(activeSession.value.id, { before_id: firstMsg.id, limit: 50 });
  isLoadingMessages.value = false;
  isLoadingHistory.value = false;
};

const onScrollToTop = () => {
  loadMoreMessages();
};

const connectWebSocket = () => {
  if (!activeSession.value?.id) return;
  chatStore.disconnect();
  chatStore.connect(activeSession.value.id);
};

const onSend = (content) => {
  if (!activeSession.value?.id) {
    uni.showToast({ title: '请先创建会话', icon: 'none' });
    return;
  }
  chatStore.addLocalMessage('user', content);
  const sent = chatStore.sendMessage(content);
  scrollToBottom();
};

const onStop = () => {
  chatStore.stopGeneration();
};

const onMessageLongPress = (msg) => {
  if (msg.role !== 'assistant') return;

  const idx = messages.value.findIndex(m => m.id === msg.id);
  if (idx <= 0) return;

  let userMsg = null;
  for (let i = idx - 1; i >= 0; i--) {
    if (messages.value[i].role === 'user') {
      userMsg = messages.value[i];
      break;
    }
  }
  if (!userMsg) return;

  uni.showActionSheet({
    itemList: ['重新生成', '复制内容'],
    success: (res) => {
      if (res.tapIndex === 0) {
        regenerate(msg, userMsg);
      } else if (res.tapIndex === 1) {
        uni.setClipboardData({
          data: msg.content,
          success: () => uni.showToast({ title: '已复制', icon: 'none' })
        });
      }
    }
  });
};

const regenerate = (assistantMsg, userMsg) => {
  if (!chatStore.isConnected) {
    uni.showToast({ title: 'WebSocket 未连接', icon: 'none' });
    return;
  }

  const idx = messages.value.indexOf(assistantMsg);
  if (idx > -1) {
    messages.value.splice(idx, 1);
  }

  chatStore.regenerateMessage(userMsg.content, assistantMsg.id);
};

const onKeyboardHeightChange = (e) => {
  keyboardHeight.value = e.height;
  if (e.height > 0) {
    scrollToBottom();
  }
};

const scrollToBottom = () => {
  scrollCounter.value++;
  scrollIntoViewId.value = '';
  nextTick(() => {
    scrollIntoViewId.value = `scroll-bottom-${scrollCounter.value}`;
  });
};

const onSettings = () => {
  if (characterId.value) {
    uni.navigateTo({ url: `/pages/characters/design?id=${characterId.value}` });
  }
};

watch(() => messages.value.length, (newVal, oldVal) => {
  if (isLoadingHistory.value) return;
  if (newVal > oldVal) {
    scrollToBottom();
  }
});
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: $color-bg-page;
}

.custom-nav {
  background: #FFFFFF;
  border-bottom: 1rpx solid $color-border;
  flex-shrink: 0;
}

.nav-content {
  position: relative;
}

.connection-status {
  text-align: center;
  padding: 8rpx 0;
  background: $color-warm-bg;
}

.status-text {
  font-size: $font-size-aux;
  color: $color-warning;
}

.message-list {
  flex: 1;
  overflow-y: auto;
}

.loading-more {
  display: flex;
  justify-content: center;
  padding: 24rpx;
}

.loading-dots {
  display: flex;
  gap: 12rpx;
}

.loading-dot {
  width: 12rpx;
  height: 12rpx;
  background: $color-primary;
  border-radius: $radius-round;
  opacity: 0.5;
  animation: loadingBounce 1.4s infinite ease-in-out both;
}

.loading-dot:nth-child(1) { animation-delay: -0.32s; }
.loading-dot:nth-child(2) { animation-delay: -0.16s; }
.loading-dot:nth-child(3) { animation-delay: 0s; }

@keyframes loadingBounce {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.welcome-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 40rpx;
}

.welcome-avatar {
  width: 160rpx;
  height: 160rpx;
  border-radius: $radius-round;
  background: $color-bg-page;
  border: 2rpx solid $color-primary-light;
  margin-bottom: $spacing-lg;
}

.welcome-name {
  font-size: $font-size-title;
  font-weight: $font-weight-bold;
  color: $color-text-title;
  margin-bottom: $spacing-sm;
}

.welcome-hint {
  font-size: $font-size-body;
  color: $color-text-secondary;
}

.scroll-bottom {
  /* height via inline style */
}

.input-area {
  flex-shrink: 0;
  background: #FFFFFF;
  border-top: 1rpx solid $color-border;
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

.search-status {
  text-align: center;
  padding: 16rpx 30rpx;
}

.search-tag {
  display: inline-block;
  padding: 8rpx 24rpx;
  border-radius: 20rpx;
  font-size: $font-size-aux;
}

.search-tag.searching {
  background: $color-primary-light;
  color: $color-primary-dark;
}

.search-tag.empty {
  background: $color-warm-bg;
  color: $color-warning;
}

.search-tag-text {
  font-size: $font-size-aux;
}
</style>
