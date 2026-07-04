<template>
    <view class="error-page">
        <view>
            <text class="error-title">
                404 Page Not Found
            </text>
        </view>
        <view>
            <text class="error-desc">
                {{errMsg}}
            </text>
        </view>
    </view>
</template>

<script>
    export default {
        data() {
            return {

            }
        },
        onLoad(query) {
            this.errMsg = query.errMsg || ''
        },
        methods: {

        }
    }
</script>

<style lang="scss">
@import '@/common/styles/theme.scss';

.error-page {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: $color-bg-page;
}

.error-title {
    font-size: 40rpx;
    color: $color-text-title;
    font-weight: 600;
}

.error-desc {
    font-size: 28rpx;
    color: $color-text-secondary;
    margin-top: 20rpx;
}
</style>
