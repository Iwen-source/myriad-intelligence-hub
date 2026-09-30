import service from '../index'

// ===== 医疗 =====
export const getPatients = (params) => service.get('/medical/patients', { params })
export const savePatient = (data) => service.post('/medical/patients', data)
export const deletePatient = (id) => service.delete(`/medical/patients/${id}`)
export const getDiagnosis = (params) => service.get('/medical/diagnosis', { params })
export const saveDiagnosis = (data) => service.post('/medical/diagnosis', data)
export const deleteDiagnosis = (id) => service.delete(`/medical/diagnosis/${id}`)

// 医疗AI分析
export const analyzeSymptom = (symptoms) => service.post('/medical/analysis/symptom', { symptoms })
export const getSimilarCases = (patientId) => service.get(`/medical/analysis/similar/${patientId}`)
export const getDiagnosisTrend = () => service.get('/medical/analysis/trend')
export const aiConsult = (data) => service.post('/medical/ai-doctor/consult', data)
export const aiModelConsult = (data) => service.post('/medical/ai-model/consult', data)

// 疾病知识库
export const getDiseaseLibrarySearch = (params) => service.get('/medical/disease-library/search', { params })
export const getDiseaseLibraryOverview = () => service.get('/medical/disease-library/overview')
export const getDiseaseDetail = (name) => service.get(`/medical/disease-library/${encodeURIComponent(name)}`)

// 患者健康档案
export const getPatientHealthProfile = (id) => service.get(`/medical/patients/${id}/health-profile`)

// ==== V3+ 糖尿病增强分析 ====
export const getInsulinGlucoseCorrelation = () => service.get('/medical/v3/insulin-glucose-correlation')
export const getGlucosePatients = () => service.get('/medical/v3/glucose-patients')
export const getGlucosePatientDetail = (patientId) => service.get(`/medical/v3/glucose-patient/${patientId}`)

// V3 真实数据模型
export const diabetesRiskPredict = (data) => service.post('/medical/v3/diabetes-risk', data)
export const glucoseForecastPredict = (data) => service.post('/medical/v3/glucose-forecast', data)

// CT 影像工作站
export const ctNewSession = () => service.get('/medical/ct/session/new')
export const ctSessionInfo = () => service.get('/medical/ct/session/info')
export const ctLoadData = (params) => service.post('/medical/ct/load', params)
export const ctGetSlice = (params) => service.post('/medical/ct/slice', params)
export const ctGetMpr = (params) => service.post('/medical/ct/mpr', params)
export const ctFilterCompare = (params) => service.post('/medical/ct/filter-compare', params)
export const ctGetHistogram = (params) => service.post('/medical/ct/histogram', params)
export const ctGetStatistics = (params) => service.post('/medical/ct/statistics', params)
export const ctSegment3d = (params) => service.post('/medical/ct/segment-3d', params)
export const ctMetalDetect = (params) => service.post('/medical/ct/metal-detect', params)
export const ctGetMontage = (params) => service.post('/medical/ct/montage', params)
export const ctGenerateReport = (params) => service.post('/medical/ct/report', params)
export const ctExportMask = (params) => service.post('/medical/ct/export-mask', params)
export const ctGetWindowPresets = () => service.get('/medical/ct/window-presets')
export const ctListDataFiles = () => service.get('/medical/ct/data-files')

// CT AI分析
export const ctAiAnalyze = (params) => service.post('/medical/ct/ai-analyze', params)

// CT 伪影AI分割（UNet3D）
export const ctAiArtifactSegment = (params) => service.post('/medical/ct/ai-artifact-segment', params)

// CQ500 数据集支持
export const cq500GetStats = () => service.get('/medical/ct/cq500/stats')
export const cq500ListCases = (params) => service.get('/medical/ct/cq500/cases', { params })
export const cq500LoadCase = (caseKey) => service.post('/medical/ct/cq500/load', { case_key: caseKey })


// ==== 症状自训练模型 ====
export const symptomPredict = (data) => service.post("/medical/v3/symptom-predict", data)
export const getSymptomTrainData = () => service.get("/medical/v3/symptom-train-data")
export const addSymptomTrainData = (data) => service.post("/medical/v3/symptom-train-data", data)
export const retrainSymptomModel = () => service.post("/medical/v3/symptom-retrain")
