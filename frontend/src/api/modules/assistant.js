import service from '../index'

// ===== 豆芽 智能助手（公共，无需登录）=====
/** 发送对话消息 */
export const assistantChat = (payload) => service.post('/public/assistant/chat', payload)
/** 推荐问题 */
export const assistantSuggestions = () => service.get('/public/assistant/suggestions')
