import service from '../index'

// ===== 交通 =====
export const getTrafficSections = () => service.get('/traffic/sections')
export const saveTrafficSection = (data) => service.post('/traffic/sections', data)
export const deleteTrafficSection = (id) => service.delete(`/traffic/sections/${id}`)
export const getTrafficFlow = (params) => service.get('/traffic/flow', { params })
export const saveTrafficFlow = (data) => service.post('/traffic/flow', data)
export const getTrafficOverview = () => service.get('/traffic/overview')
export const getTrafficFlowData = () => service.get('/traffic/flow-data')

// 交通AI分析
export const predictCongestion = (date) => service.get('/traffic/analysis/congestion', { params: { date } })
export const getRouteOptimization = () => service.get('/traffic/analysis/routes')
export const getPredictionCalendar = (days) => service.get('/traffic/analysis/prediction-calendar', { params: { days } })
export const getTrafficHeatmap = () => service.get('/traffic/analysis/heatmap')
export const getSmartDepartureTips = () => service.get('/traffic/analysis/departure-tips')
export const analyzeAccidentImpact = (sectionId) => service.get('/traffic/analysis/accident-impact', { params: { sectionId } })
export const analyzeWeatherTraffic = () => service.get('/traffic/analysis/weather-impact')
export const detectTrafficAnomalies = () => service.get('/traffic/analysis/anomalies')
export const simulateWhatIf = (sectionId, data) => service.post(`/traffic/analysis/what-if?sectionId=${sectionId}`, data)

// 🆕 V4 AI增强: 事故风险预测
export const predictAccidentRisk = (data) => service.post('/traffic/analysis/accident-risk', data)
