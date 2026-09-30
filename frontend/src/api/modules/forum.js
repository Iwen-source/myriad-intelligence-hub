import service from '../index'

// ===== 论坛 =====
export const getForumPosts = (category) => service.get(`/forum/posts/${category}`)
export const getForumPostDetail = (id) => service.get(`/forum/posts/detail/${id}`)
export const addForumPost = (data) => service.post('/forum/posts', data)
export const updateForumPost = (id, data) => service.put(`/forum/posts/${id}`, data)
export const deleteForumPost = (id) => service.delete(`/forum/posts/${id}`)
export const likeForumPost = (id) => service.post(`/forum/posts/${id}/like`)
export const getForumStats = () => service.get('/forum/stats')

// 论坛AI分析
export const getForumHotTopics = () => service.get('/forum/analysis/hot-topics')
export const getForumRecommendations = (limit) => service.get('/forum/analysis/recommendations', { params: { limit } })
export const getForumTrends = () => service.get('/forum/analysis/trends')
export const getForumActivity = () => service.get('/forum/analysis/activity')

// 🆕 V4 NLP AI增强
// 内容质量评分 (NLP模型)
export const analyzeContentQuality = (data) => service.post('/forum/analysis/quality-score', data)
// 用户情感分析
export const analyzeSentiment = (data) => service.post('/forum/analysis/sentiment', data)
