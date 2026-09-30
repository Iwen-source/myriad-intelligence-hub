import service from '../index'

// ===== 公共 =====
export const getNavigation = () => service.get('/public/navigation')
