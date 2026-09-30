import service from '../index'

// ===== AI发展分析 =====
// ?? V4 AI增强: 学习路径推荐
export const recommendLearningPath = (data) => service.post('/development/ai/recommend-path', data)
export const analyzeSkillGap = (data) => service.post('/development/ai/skill-gap-analysis', data)
export const getTrendAnalysis = () => service.get('/development/ai/trend-analysis')
