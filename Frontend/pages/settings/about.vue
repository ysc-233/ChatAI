<template>
	<view class="about-page">
		<view class="about-header">
			<image class="about-logo" src="/static/logo.png" mode="aspectFill" />
			<text class="about-name">AI 聊天伴侣</text>
			<text class="about-version">v1.0.0</text>
		</view>

		<view class="about-section">
			<view class="section-header">
				<text class="section-title">应用信息</text>
			</view>
			<view class="info-row">
				<text class="info-label">应用名称</text>
				<text class="info-value">AI 聊天伴侣</text>
			</view>
			<view class="info-row">
				<text class="info-label">版本号</text>
				<text class="info-value">1.0.0</text>
			</view>
			<view class="info-row">
				<text class="info-label">技术栈</text>
				<text class="info-value">uni-app + FastAPI + SQLite</text>
			</view>
		</view>

		<view class="about-section">
			<view class="section-header">
				<text class="section-title">功能特性</text>
			</view>
			<view class="feature-item">
				<text class="feature-icon">🤖</text>
				<text class="feature-text">自定义 AI 角色，打造专属聊天伙伴</text>
			</view>
			<view class="feature-item">
				<text class="feature-icon">💬</text>
				<text class="feature-text">实时 WebSocket 通讯，流畅对话体验</text>
			</view>
			<view class="feature-item">
				<text class="feature-icon">🎭</text>
				<text class="feature-text">多角色切换，一个角色一个会话</text>
			</view>
			<view class="feature-item">
				<text class="feature-icon">👤</text>
				<text class="feature-text">自定义用户人格，扮演不同身份</text>
			</view>
			<view class="feature-item">
				<text class="feature-icon">📝</text>
				<text class="feature-text">长期记忆，AI 记住你的喜好与过往</text>
			</view>
		</view>

		<view class="about-section">
			<view class="section-header">
				<text class="section-title">法律信息</text>
			</view>
			<view class="menu-item">
				<text class="menu-text">隐私政策</text>
				<text class="menu-arrow">›</text>
			</view>
			<view class="menu-item">
				<text class="menu-text">用户协议</text>
				<text class="menu-arrow">›</text>
			</view>
		</view>

		<view class="about-footer">
			<text class="brand-slogan">你的对话，只属于你</text>
			<text class="copyright">AI Chat Companion  © 2026</text>
		</view>
	</view>
</template>

<script setup>
</script>

<style lang="scss" scoped>
@import '@/common/styles/theme.scss';

.about-page {
	min-height: 100vh;
	background: $color-bg-page;
	padding: $spacing-md;
	padding-bottom: 60rpx;
}

.about-header {
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 60rpx 30rpx 40rpx;
}

.about-logo {
	width: 140rpx;
	height: 140rpx;
	border-radius: 32rpx;
	background: $color-primary-light;
	margin-bottom: $spacing-lg;
	box-shadow: 0 8rpx 32rpx rgba(138, 164, 255, 0.2);
}

.about-name {
	font-size: $font-size-title;
	font-weight: $font-weight-bold;
	color: $color-text-title;
	margin-bottom: $spacing-sm;
}

.about-version {
	font-size: $font-size-body;
	color: $color-text-secondary;
}

.about-section {
	background: #FFFFFF;
	margin-bottom: $spacing-md;
	border-radius: $radius-xl;
	padding: $spacing-xl;
	box-shadow: $shadow-card;
}

.section-header {
	margin-bottom: 20rpx;
}

.section-title {
	font-size: $font-size-aux;
	color: $color-text-secondary;
	font-weight: $font-weight-medium;
}

.info-row {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 16rpx 0;
	border-bottom: 1rpx solid $color-border;
}

.info-row:last-child {
	border-bottom: none;
}

.info-label {
	font-size: $font-size-body;
	color: $color-text-body;
}

.info-value {
	font-size: $font-size-body;
	color: $color-text-secondary;
}

.feature-item {
	display: flex;
	align-items: center;
	padding: 16rpx 0;
	border-bottom: 1rpx solid $color-border;
}

.feature-item:last-child {
	border-bottom: none;
}

.feature-icon {
	font-size: 36rpx;
	margin-right: 20rpx;
	flex-shrink: 0;
}

.feature-text {
	font-size: $font-size-body;
	color: $color-text-body;
	line-height: 1.5;
}

.menu-item {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 20rpx 0;
	border-bottom: 1rpx solid $color-border;
}

.menu-item:last-child {
	border-bottom: none;
}

.menu-text {
	font-size: $font-size-body;
	color: $color-text-body;
}

.menu-arrow {
	font-size: 36rpx;
	color: $color-text-secondary;
	opacity: 0.5;
}

.about-footer {
	text-align: center;
	padding: 40rpx 30rpx;
}

.brand-slogan {
	display: block;
	font-size: $font-size-aux;
	color: $color-primary;
	font-weight: $font-weight-medium;
	margin-bottom: 16rpx;
}

.copyright {
	font-size: $font-size-micro;
	color: $color-text-secondary;
	opacity: 0.5;
}
</style>
