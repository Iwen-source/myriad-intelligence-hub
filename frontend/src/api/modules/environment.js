import service from '../index'

// ===== 环境 =====
export const getEnvPoints = () => service.get('/environment/points')
export const saveEnvPoint = (data) => service.post('/environment/points', data)
export const deleteEnvPoint = (id) => service.delete(`/environment/points/${id}`)
export const getEnvironmentData = (params) => service.get('/environment/data', { params })
export const saveEnvRecord = (data) => service.post('/environment/data', data)
export const getEnvironmentSummary = () => service.get('/environment/summary')
export const getEnvStatistics = () => service.get('/environment/statistics')

// 环境AI分析 (基础)
export const getAirPrediction = (days) => service.get('/environment/analysis/prediction', { params: { days } })
export const getPollutionAlerts = () => service.get('/environment/analysis/alerts')

// 环境AI分析 (增强)
export const getEnvironmentHealthIndex = () => service.get('/environment/analysis/health-index')
export const getPollutionSourceAnalysis = () => service.get('/environment/analysis/pollution-source')
export const getSeasonalTrendAnalysis = () => service.get('/environment/analysis/seasonal-trend')
export const getHealthImpactAssessment = () => service.get('/environment/analysis/health-impact')
export const getCrossPointCorrelation = () => service.get('/environment/analysis/correlation')
export const getPollutantBreakdown = (pointId) => service.get('/environment/analysis/pollutant-breakdown', { params: { pointId } })
export const getSmartRecommendations = () => service.get('/environment/analysis/recommendations')
export const getEnvironmentalAnomalies = () => service.get('/environment/analysis/anomalies')
export const getEnvironmentAiReport = () => service.get('/environment/analysis/ai-report')
export const getMultiFactorPrediction = () => service.get('/environment/analysis/multi-factor-prediction')
export const getHealthExposureRisk = () => service.get('/environment/analysis/exposure-risk')

// 🆕 V4 AI增强: 极端天气分类
export const classifyExtremeWeather = (data) => service.post('/environment/analysis/extreme-weather', data)

// 🆕 获取当前极端天气分析（自动基于最新监测数据）
export const getCurrentExtremeWeather = () => service.get('/environment/analysis/extreme-weather/current')
