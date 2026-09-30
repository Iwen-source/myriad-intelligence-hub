<template>
  <div class="layout">
    <el-container style="height: 100vh;">
      <!-- Sidebar -->
      <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
        <div class="logo" @click="router.push('/')">
          <el-icon :size="28" color="#409eff"><Sunny /></el-icon>
          <span v-show="!isCollapse" class="logo-text">万象智枢</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :router="true"
          background-color="#1d1e2c"
          text-color="#bfcbd9"
          active-text-color="#409eff"
          class="sidebar-menu"
        >
          <el-menu-item index="/home">
            <el-icon><HomeFilled /></el-icon>
            <template #title>首页</template>
          </el-menu-item>

          <el-sub-menu index="dev">
            <template #title>
              <el-icon><DataAnalysis /></el-icon>
              <span>AI发展分析</span>
            </template>
            <el-menu-item index="/development/learning-path">
              <el-icon><TrendCharts /></el-icon>学习路径推荐
            </el-menu-item>
            <el-menu-item index="/development/skill-gap">
              <el-icon><DataBoard /></el-icon>技能差距分析
            </el-menu-item>
            <el-menu-item index="/development/trend-analysis">
              <el-icon><Odometer /></el-icon>技术趋势分析
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="scenario">
            <template #title>
              <el-icon><Grid /></el-icon>
              <span>AI应用场景</span>
            </template>
            <el-menu-item index="/scenarios">场景概览</el-menu-item>
            <el-sub-menu index="scenario-medical">
              <template #title><span>🩺 医疗诊断</span></template>
              <el-menu-item index="/scenarios/medical">总览</el-menu-item>
              <el-menu-item index="/scenarios/ct-workstation">CT影像工作台</el-menu-item>
              <el-menu-item index="/scenarios/medical/ml-predictions">糖尿病·血糖预测</el-menu-item>
            </el-sub-menu>
            <el-sub-menu index="scenario-energy">
              <template #title><span>⚡ 能源管理</span></template>
              <el-menu-item index="/scenarios/energy">总览</el-menu-item>
              <el-menu-item index="/scenarios/energy/load-forecast">负荷预测</el-menu-item>
              <el-menu-item index="/scenarios/energy/failure-predict">设备故障预测</el-menu-item>
            </el-sub-menu>
            <el-sub-menu index="scenario-env">
              <template #title><span>🌤️ 环境监测</span></template>
              <el-menu-item index="/scenarios/environment">总览</el-menu-item>
              <el-menu-item index="/scenarios/environment/extreme-weather">极端天气分类</el-menu-item>
            </el-sub-menu>
            <el-sub-menu index="scenario-fin">
              <template #title><span>💰 金融风控</span></template>
              <el-menu-item index="/scenarios/finance">总览</el-menu-item>
              <el-menu-item index="/scenarios/finance/churn-prediction">客户流失预测</el-menu-item>
            </el-sub-menu>
            <el-sub-menu index="scenario-traffic">
              <template #title><span>🚗 交通仿真</span></template>
              <el-menu-item index="/scenarios/traffic">总览</el-menu-item>
              <el-menu-item index="/scenarios/traffic/accident-risk">事故风险预测</el-menu-item>
            </el-sub-menu>
          </el-sub-menu>

          <el-sub-menu index="forum">
            <template #title>
              <el-icon><ChatDotRound /></el-icon>
              <span>技术论坛</span>
            </template>
            <el-menu-item index="/forum">论坛交流</el-menu-item>
            <el-menu-item index="/forum/quality-analysis">帖子质量分析</el-menu-item>
            <el-menu-item index="/forum/sentiment-analysis">情感分析</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>

      <!-- Main Content -->
      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
              <Fold v-if="!isCollapse" />
              <Expand v-else />
            </el-icon>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/home' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="header-right">
            <AlertBell />
            <el-dropdown @command="handleCommand">
              <span class="user-info">
                <el-avatar :size="32" :icon="UserFilled" />
                <span class="username">{{ authStore.username || '未登录' }}</span>
                <el-tag v-if="authStore.isAdmin" size="small" type="danger" effect="dark" style="margin-left:4px">ADMIN</el-tag>
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                  <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="main-content">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>

    <!-- 个人信息弹窗 -->
    <el-dialog v-model="showProfileDialog" title="个人信息" width="420px" :close-on-click-modal="false">
      <el-form label-width="80px" label-position="left" size="default">
        <el-form-item label="用户名">
          <el-input :model-value="authStore.username" disabled />
        </el-form-item>
        <el-form-item label="注册时间">
          <el-input :model-value="userCreatedAt || '暂无数据'" disabled />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showProfileDialog = false">关闭</el-button>
      </template>
    </el-dialog>
    <!-- 豆芽 智能助手（全站悬浮，含首页） -->
    <DouyaAssistant />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AlertBell from '../components/AlertBell.vue'
import DouyaAssistant from '../components/DouyaAssistant.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isCollapse = ref(false)
const showProfileDialog = ref(false)
const userCreatedAt = ref('')

const activeMenu = computed(() => route.path)

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  } else if (command === 'profile') {
    showProfileDialog.value = true
    try {
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      userCreatedAt.value = user.createdAt || '暂无数据'
    } catch {
      userCreatedAt.value = '暂无数据'
    }
  }
}
</script>

<style scoped>
.sidebar {
  background-color: #1d1e2c;
  transition: width 0.3s;
  overflow: hidden;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  cursor: pointer;
  color: #fff;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.logo-text {
  font-size: 18px;
  font-weight: bold;
  white-space: nowrap;
}
.sidebar-menu {
  border-right: none;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
}
.header-right {
  display: flex;
  align-items: center;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.username {
  font-size: 14px;
  color: #303133;
}
.main-content {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
