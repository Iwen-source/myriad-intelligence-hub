import service from '../index'

// ===== 金融 =====
export const getFinanceTransactions = (params) => service.get('/finance/transactions', { params })
export const saveFinanceTransaction = (data) => service.post('/finance/transactions', data)
export const deleteFinanceTransaction = (id) => service.delete(`/finance/transactions/${id}`)
export const getFinanceRules = () => service.get('/finance/rules')
export const saveFinanceRule = (data) => service.post('/finance/rules', data)
export const updateFinanceRule = (id, data) => service.put(`/finance/rules/${id}`, data)
export const deleteFinanceRule = (id) => service.delete(`/finance/rules/${id}`)
export const getFinanceDashboard = () => service.get('/finance/dashboard')

// 金融AI分析 (基础)
export const evaluateRisk = (id) => service.get(`/finance/analysis/risk/${id}`)
export const getRuleHits = () => service.get('/finance/analysis/rule-hits')

// 金融AI分析 (增强)
export const getFinanceTrendPrediction = (days) => service.get('/finance/analysis/trend-prediction', { params: { days } })
export const getUserBehaviorProfiles = () => service.get('/finance/analysis/user-profiles')
export const getSuspiciousTransactions = () => service.get('/finance/analysis/suspicious')
export const getMultiDimensionalRisk = (id) => service.get(`/finance/analysis/multi-risk/${id}`)
export const getTransactionNetwork = () => service.get('/finance/analysis/network')
export const getRiskAssessmentReport = () => service.get('/finance/analysis/report')
export const getFinanceAlerts = () => service.get('/finance/analysis/alerts')
export const getRiskTrend = () => service.get('/finance/analysis/risk-trend')

// 🆕 V4 AI增强: 客户流失预测
export const predictCustomerChurn = (data) => service.post('/finance/analysis/customer-churn', data)
