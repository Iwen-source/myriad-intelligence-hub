import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/home',
    children: [
      { path: 'home', name: 'Home', component: () => import('../views/Home.vue'), meta: { title: '首页', requiresAuth: false } },
      // AI分析（学习路径、技能差距、技术趋势）
      // AI应用场景
      { path: 'scenarios', name: 'Scenarios', component: () => import('../views/scenarios/ScenariosIndex.vue'), meta: { title: 'AI应用场景', requiresAuth: true } },
      { path: 'scenarios/energy', name: 'Energy', component: () => import('../views/scenarios/Energy.vue'), meta: { title: '能源管理', requiresAuth: true } },
      { path: 'scenarios/energy/load-forecast', name: 'EnergyLoadForecast', component: () => import('../views/scenarios/energy/EnergyLoadForecast.vue'), meta: { title: '能源负荷预测', requiresAuth: true } },
      { path: 'scenarios/energy/failure-predict', name: 'EnergyFailurePredict', component: () => import('../views/scenarios/energy/EnergyFailurePredict.vue'), meta: { title: '设备故障预测', requiresAuth: true } },
      { path: 'scenarios/medical', name: 'Medical', component: () => import('../views/scenarios/Medical.vue'), meta: { title: '医疗诊断', requiresAuth: true } },
      { path: 'scenarios/medical/ai-consult', name: 'MedicalAiConsult', component: () => import('../views/scenarios/medical/AiConsult.vue'), meta: { title: 'AI智能问诊', requiresAuth: true } },
      { path: 'scenarios/medical/ml-predictions', name: 'MedicalMlPredict', component: () => import('../views/scenarios/medical/MlPredictPage.vue'), meta: { title: '糖尿病·血糖预测', requiresAuth: true } },
      { path: 'scenarios/ct-workstation', name: 'CtWorkstation', component: () => import('../views/scenarios/CtWorkstation.vue'), meta: { title: 'CT影像工作台', requiresAuth: true } },
      { path: 'scenarios/environment', name: 'Environment', component: () => import('../views/scenarios/Environment.vue'), meta: { title: '环境监测', requiresAuth: true } },
      { path: 'scenarios/environment/extreme-weather', name: 'EnvExtremeWeather', component: () => import('../views/scenarios/environment/EnvironmentExtremeWeather.vue'), meta: { title: '极端天气分类', requiresAuth: true } },
      { path: 'scenarios/finance', name: 'Finance', component: () => import('../views/scenarios/Finance.vue'), meta: { title: '金融风控', requiresAuth: true } },
      { path: 'scenarios/finance/churn-prediction', name: 'FinanceChurn', component: () => import('../views/scenarios/finance/FinanceChurnPrediction.vue'), meta: { title: '客户流失预测', requiresAuth: true } },
      { path: 'scenarios/traffic', name: 'Traffic', component: () => import('../views/scenarios/Traffic.vue'), meta: { title: '交通仿真', requiresAuth: true } },
      { path: 'scenarios/traffic/accident-risk', name: 'TrafficAccidentRisk', component: () => import('../views/scenarios/traffic/TrafficAccidentRisk.vue'), meta: { title: '事故风险预测', requiresAuth: true } },

      // 技术论坛
      { path: 'forum', name: 'Forum', component: () => import('../views/forum/Forum.vue'), meta: { title: '技术论坛', requiresAuth: true } },

      { path: 'forum/quality-analysis', name: 'ForumQuality', component: () => import('../views/forum/ForumQualityAnalysis.vue'), meta: { title: '帖子质量分析', requiresAuth: true } },
      { path: 'forum/sentiment-analysis', name: 'ForumSentiment', component: () => import('../views/forum/ForumSentimentAnalysis.vue'), meta: { title: '情感分析', requiresAuth: true } },

      // AI发展分析
      { path: 'development/learning-path', name: 'DevLearningPath', component: () => import('../views/development/LearningPath.vue'), meta: { title: '学习路径推荐', requiresAuth: true } },
      { path: 'development/skill-gap', name: 'DevSkillGap', component: () => import('../views/development/SkillGapAnalysis.vue'), meta: { title: '技能差距分析', requiresAuth: true } },
      { path: 'development/trend-analysis', name: 'DevTrend', component: () => import('../views/development/TrendAnalysis.vue'), meta: { title: '技术趋势分析', requiresAuth: true } },
    ]
  },
  { path: '/login', name: 'Login', component: () => import('../views/auth/Login.vue'), meta: { title: '登录', requiresAuth: false } },
  { path: '/register', name: 'Register', component: () => import('../views/auth/Register.vue'), meta: { title: '注册', requiresAuth: false } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 公开页面列表（无需登录即可访问）
const publicPages = ['Login', 'Register', 'Home']

/** 需要管理员权限的路由 */
const adminRoutes = []

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 万象智枢` : '万象智枢'

  // Home 和 Login/Register 都是公开页面
  if (to.meta.requiresAuth === false || publicPages.includes(to.name)) {
    next()
    return
  }

  const token = localStorage.getItem('token')
  if (!token) {
    next('/login')
    return
  }

  // 管理员权限检查
  if (adminRoutes.includes(to.name)) {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    if (user.role !== 'ADMIN') {
      next('/home')
      return
    }
  }

  next()
})

export default router
