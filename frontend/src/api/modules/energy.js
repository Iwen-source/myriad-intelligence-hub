import service from '../index'

// ===== 能源 =====
export const getDevices = (params) => service.get('/energy/devices', { params })
export const saveDevice = (data) => service.post('/energy/devices', data)
export const deleteDevice = (id) => service.delete(`/energy/devices/${id}`)
export const getConsumption = (params) => service.get('/energy/consumption', { params })
export const saveConsumption = (data) => service.post('/energy/consumption', data)
export const getMaintenance = (params) => service.get('/energy/maintenance', { params })
export const saveMaintenance = (data) => service.post('/energy/maintenance', data)
export const getEnergyStats = () => service.get('/energy/statistics')
export const getEnergyTrend = () => service.get('/energy/statistics/trend')

// 能源AI分析
export const getEnergyPrediction = (days) => service.get('/energy/analysis/prediction', { params: { days } })
export const getEnergyAnomalies = () => service.get('/energy/analysis/anomalies')
export const getEnergyOptimization = () => service.get('/energy/analysis/optimization')
export const getEnergyDeviceAnalysis = () => service.get('/energy/analysis/device-analysis')
export const getEnergySummaryReport = () => service.get('/energy/analysis/summary-report')

// 🆕 V4 新增强AI
// 负荷预测 (调用真实LSTM/统计模型)
export const getEnergyLoadForecast = (params) => service.post('/energy/analysis/load-forecast', params)
// 设备故障预测 (调用真实XGBoost模型)
export const predictDeviceFailure = (params) => service.post('/energy/analysis/device-failure-predict', params)
