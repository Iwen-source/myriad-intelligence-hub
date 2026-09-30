"""
Medical Routes — all medical-related ML model endpoints extracted from app.py
Uses Flask Blueprint pattern.
"""
import json
import os
import re
import numpy as np
import pandas as pd
import logging
from flask import Blueprint, request, jsonify

from .model_loader import get_models_dict

log = logging.getLogger(__name__)

# 加载PyTorch DNN/LSTM模型 (糖尿病风险 + 血糖预测)
import sys
_dnn_base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
if _dnn_base not in sys.path:
    sys.path.insert(0, _dnn_base)
try:
    from medical_dnn_inference import get_diabetes_predictor, get_glucose_predictor
    _diabetes_dnn = get_diabetes_predictor()
    _glucose_lstm = get_glucose_predictor()
except Exception as e:
    log.warning("PyTorch DNN/LSTM加载失败(将使用XGBoost回退): %s", e)
    _diabetes_dnn = None
    _glucose_lstm = None

models = get_models_dict()
# 将DNN/LSTM预测器注入models字典供路由代码使用
if _diabetes_dnn is not None:
    models['diabetes_dnn'] = _diabetes_dnn
if _glucose_lstm is not None:
    models['glucose_lstm'] = _glucose_lstm

# BASE_DIR 指向项目根目录: E:\毕业设计\ai-empowerment-platform
_BASE_THIS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(_BASE_THIS)  # python/ 的父目录 = 项目根目录
MODELS_DIR = os.path.join(BASE_DIR, 'models')

medical_bp = Blueprint('medical', __name__, url_prefix='/api')

# ────────────────────── V1 Medical ──────────────────────

@medical_bp.route('/predict/medical', methods=['POST'])
def predict_medical():
    try:
        data = request.get_json()
        symptoms = data.get('symptoms', '')
        if not symptoms:
            return jsonify({"status": "error", "message": "症状不能为空"}), 400
        X = models['medical_vec'].transform([symptoms])
        pred = models['medical'].predict(X)[0]
        probs = models['medical'].predict_proba(X)[0]
        disease = models['medical_label'].inverse_transform([pred])[0]
        confidence = float(max(probs))
        dep_map = {
            '上呼吸道感染': '呼吸内科', '肺炎': '呼吸内科', '支气管炎': '呼吸内科',
            '胃炎': '消化内科', '胃溃疡': '消化内科', '偏头痛': '神经内科',
            '高血压': '心血管内科', '糖尿病': '内分泌科', '过敏性鼻炎': '耳鼻喉科',
            '皮肤过敏': '皮肤科'
        }
        sev_map = {'上呼吸道感染': 'low', '过敏性鼻炎': 'low', '支气管炎': 'mid',
                   '胃炎': 'mid', '偏头痛': 'mid', '肺炎': 'high', '高血压': 'high',
                   '糖尿病': 'high', '皮肤过敏': 'low', '胃溃疡': 'mid'}
        suggestion_map = {
            '上呼吸道感染': '多喝水、注意休息、服用感冒药，如症状加重请及时就医。',
            '肺炎': '建议立即就医，可能需要住院治疗。不要自行用药。',
            '胃炎': '规律饮食、少食多餐、避免辛辣刺激食物，建议消化内科就诊。',
            '偏头痛': '保持充足睡眠，避免强光刺激，必要时服用止痛药。',
            '过敏性鼻炎': '避免接触过敏原，使用抗组胺药物，保持室内通风。',
            '高血压': '定期监测血压，低盐饮食，规律服药，定期复查。',
            '糖尿病': '控制饮食、规律运动、监测血糖，按时服用降糖药物。',
            '支气管炎': '注意保暖、避免烟雾刺激、多饮水，如持续咳嗽请就医。',
            '皮肤过敏': '避免接触过敏原，外用止痒药膏，必要时口服抗过敏药物。',
            '胃溃疡': '规律服药、避免空腹服用刺激性药物、定期复查胃镜。'
        }
        return jsonify({
            "status": "success", "disease": disease, "confidence": confidence,
            "department": dep_map.get(disease, '全科'), "severity": sev_map.get(disease, 'mid'),
            "suggestions": suggestion_map.get(disease, '请及时就医。')
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ────────────────────── V2 Medical Endpoints ──────────────────────

@medical_bp.route('/v2/medical/drug-recommend', methods=['POST'])
def v2_drug_recommend():
    try:
        data = request.get_json()
        disease = data.get('disease_name', '')
        if not disease:
            return jsonify({"status": "error", "message": "疾病名称不能为空"}), 400
        drug_db_path = os.path.join(MODELS_DIR, 'drug_database.csv')
        drug_db = pd.read_csv(drug_db_path) if os.path.exists(drug_db_path) else pd.DataFrame()
        query_vec = models['drug_vec'].transform([disease])
        sims = query_vec.dot(models['drug_features'].T).toarray()[0]
        top_idx = np.argsort(sims)[-10:][::-1]
        drugs = []
        for idx in top_idx:
            s = float(sims[idx])
            if s < 0.01: continue
            row = drug_db.iloc[idx] if idx < len(drug_db) else None
            drug_name = re.sub(r'_[0-9]+$', '', row['drug_name']) if row is not None else f"药物_{idx}"
            drugs.append({
                "drugName": drug_name,
                "category": row['category'] if row is not None else "常规",
                "matchScore": round(float(s), 4),
                "indications": row.get('indications_text', '')[:100] if row is not None else "",
                "note": row.get('side_effects_text', '')[:100] if row is not None else ""
            })
        if not drugs:
            drugs = [
                {"drugName": "阿莫西林胶囊", "category": "抗生素", "matchScore": 0.65, "note": "适用于敏感菌引起的感染"},
                {"drugName": "布洛芬缓释胶囊", "category": "解热镇痛", "matchScore": 0.58, "note": "适用于发热及疼痛症状"},
                {"drugName": "板蓝根颗粒", "category": "中成药", "matchScore": 0.52, "note": "适用于病毒性感冒"}
            ]
        is_ml = len(drugs) > 0 and not all(d['matchScore'] in [0.65, 0.58, 0.52] for d in drugs)
        return jsonify({"status": "success", "drugs": drugs, "isMlResult": is_ml})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@medical_bp.route('/v2/medical/epidemic-forecast', methods=['POST'])
def v2_epidemic_forecast():
    try:
        data = request.get_json()
        disease = data.get('disease_name', 'all')
        days = data.get('forecast_days', 14)
        ep_data = models['epidemic']
        if ep_data is None:
            return jsonify({"status": "fallback", "message": "模型未加载"})
        # Handle nested dict: {'models': {'disease': {...}}, 'metrics': {...}}
        ep_models = ep_data.get('models', ep_data) if isinstance(ep_data, dict) else ep_data
        result = {}
        for dname, ddata in ep_models.items():
            if disease != 'all' and dname != disease:
                continue
            forecasts = []
            trend = '稳定'
            alarm = '正常'
            mae = 0
            rmse = 0
            if isinstance(ddata, dict):
                forecasts = ddata.get('forecast', ddata.get('predicted', []))
                trend = ddata.get('trend', ddata.get('trend_direction', '稳定'))
                alarm = ddata.get('alarm', ddata.get('alarm_level', '正常'))
                mae = ddata.get('mae', 0)
                rmse = ddata.get('rmse', 0)
            elif isinstance(ddata, list):
                forecasts = ddata
            elif isinstance(ddata, np.ndarray):
                forecasts = ddata.tolist()
            result[dname] = {
                "forecast": [round(float(f), 1) for f in list(forecasts)[:days]] if forecasts else [],
                "trend": trend,
                "alarm": alarm,
                "mae": float(mae) if not isinstance(mae, str) else 0,
                "rmse": float(rmse) if not isinstance(rmse, str) else 0
            }
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@medical_bp.route('/v2/medical/health-score', methods=['POST'])
def v2_health_score():
    try:
        data = request.get_json()
        features = np.array([[
            data.get('age', 30), data.get('visit_frequency', 0),
            data.get('past_illness_count', 0), data.get('symptom_severity', 1),
            data.get('diagnosis_diversity', 0)
        ]])
        scaled = models['health_scaler'].transform(features)
        score = float(models['health_scoring'].predict(scaled)[0])
        score = max(0, min(100, score))
        risk = "低风险" if score >= 80 else ("中风险" if score >= 50 else "高风险")
        dimensions = {
            "年龄适应性": 80, "就诊规律性": min(100, 60 + data.get('visit_frequency', 0) * 5),
            "病史负担": max(0, 100 - data.get('past_illness_count', 0) * 10),
            "症状严重度": max(0, 100 - data.get('symptom_severity', 1) * 15),
            "诊断多样性": min(100, data.get('diagnosis_diversity', 0) * 20 + 50)
        }
        return jsonify({
            "status": "success", "overall_score": round(score, 1),
            "risk_level": risk, "dimension_breakdown": dimensions
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@medical_bp.route('/v2/medical/complication-predict', methods=['POST'])
def v2_complication_predict():
    try:
        data = request.get_json()
        disease = data.get('disease', '')
        symptoms = data.get('symptoms', [])
        if not disease:
            return jsonify({"status": "error", "message": "疾病不能为空"}), 400
        comp_info = models.get('complication')
        comp_model = comp_info.get('model') if isinstance(comp_info, dict) else None
        comp_labels = comp_info.get('complications', []) if isinstance(comp_info, dict) else []
        diseases_list = comp_info.get('diseases', []) if isinstance(comp_info, dict) else []

        if comp_model and hasattr(comp_model, 'predict_proba'):
            n_features = comp_model.n_features_in_
            demo_vec = np.zeros((1, n_features))
            if disease in diseases_list:
                demo_vec[0, diseases_list.index(disease)] = 1.0
            for i, sym in enumerate(symptoms[:5]):
                idx = min((hash(sym) % 3) + len(diseases_list), n_features - 1)
                demo_vec[0, idx] = 0.5
            probs_arr = comp_model.predict_proba(demo_vec)
            # probs_arr is a list of arrays (one per label in multi-output)
            complications = []
            for i, label in enumerate(comp_labels[:8]):
                if isinstance(probs_arr, list):
                    prob = float(probs_arr[i][0][1]) if i < len(probs_arr) and len(probs_arr[i][0]) > 1 else 0
                else:
                    prob = float(probs_arr[0][i]) if i < len(probs_arr[0]) else 0
                if prob > 0.05:
                    complications.append({
                        "name": str(label),
                        "probability": round(prob * 100, 1),
                        "prevention": "建议定期检查，保持健康生活方式。"
                    })
        else:
            complications = [{"name": l, "probability": round(100 / max(len(comp_labels), 1), 1), "prevention": "建议定期检查"} for l in comp_labels[:3]]
        complications.sort(key=lambda x: x['probability'], reverse=True)
        return jsonify({"status": "success", "complications": complications[:5]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@medical_bp.route('/v2/medical/resource-forecast', methods=['POST'])
def v2_resource_forecast():
    try:
        data = request.get_json()
        # Resource model expects: season + temperature + humidity + booked_count + historical_same_day + day_of_week + is_holiday + 10 department one-hot
        season = data.get('season', 1)
        meta = models['resource_meta']
        departments = meta.get('departments', []) if isinstance(meta, dict) else []
        dept = data.get('department', '')
        features = np.array([[
            season, data.get('temperature', 20), data.get('humidity', 60),
            data.get('booked_count', 0), data.get('historical_same_day', 0),
            data.get('day_of_week', 0), data.get('is_holiday', 0)
        ] + [1 if d == dept else 0 for d in departments]])
        if models['resource_scaler'] and features.shape[1] == models['resource_scaler'].n_features_in_:
            scaled = models['resource_scaler'].transform(features)
        else:
            scaled = features
        visits = int(models['resource'].predict(scaled)[0])
        doctors = max(1, visits // 15)
        return jsonify({
            "status": "success", "predicted_visits": visits,
            "suggested_doctors": doctors,
            "peak_hours": ["08:00-10:00", "14:00-16:00"]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@medical_bp.route('/v2/medical/semantic-search', methods=['POST'])
def v2_semantic_search():
    try:
        data = request.get_json()
        query = data.get('query', '')
        if not query:
            return jsonify({"status": "error", "message": "查询不能为空"}), 400
        query_vec = models['search_vec'].transform([query])
        scores = query_vec.dot(models['search_tfidf'].T).toarray()[0]
        top_idx = np.argsort(scores)[-10:][::-1]
        records = []
        recs = models['search_records']
        for idx in top_idx:
            s = float(scores[idx])
            if s < 0.05:
                continue
            if isinstance(recs, pd.DataFrame):
                text = str(recs.iloc[idx].get('text', f'病历_{idx}')) if idx < len(recs) else f'病历_{idx}'
            elif isinstance(recs, list) and idx < len(recs):
                rec = recs[idx]
                text = rec.get('text', rec) if isinstance(rec, dict) else str(rec)
            else:
                text = f'病历_{idx}'
            records.append({
                "recordId": f"MR-{idx:04d}", "summary": text[:100],
                "relevanceScore": round(s, 3)
            })
        return jsonify({"status": "success", "records": records, "total": len(records)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ────────────────────── V3 Medical Endpoints (真實數據模型) ──────────────────────

@medical_bp.route('/v3/medical/diabetes-risk', methods=['POST'])
def v3_diabetes_risk():
    """
    糖尿病风险预测 — 基于 PIMA 真实临床数据 (PyTorch DNN)

    输入参数:
        pregnancies: 怀孕次数
        glucose: 血糖浓度 (mg/dL)
        blood_pressure: 血压 (mm Hg)
        skin_thickness: 皮褶厚度 (mm)
        insulin: 胰岛素水平 (mu U/ml)
        bmi: 体重指数
        diabetes_pedigree: 糖尿病家族史系数
        age: 年龄

    返回:
        risk_probability: 患病概率 (0-1)
        risk_level: 低/中/高 风险
        recommendations: 个性化建议
        key_factors: 关键风险因素
    """
    try:
        data = request.get_json()

        # 验证必要字段
        required = ['glucose', 'bmi', 'age']
        for field in required:
            if field not in data:
                return jsonify({'status': 'error', 'message': f'缺少必要字段: {field}'}), 400

        # 构建特征向量 (8个特征, 与PIMA一致)
        features = np.array([
            float(data.get('pregnancies', 0)),
            float(data['glucose']),
            float(data.get('blood_pressure', 72)),
            float(data.get('skin_thickness', 20)),
            float(data.get('insulin', 79)),
            float(data['bmi']),
            float(data.get('diabetes_pedigree', 0.47)),
            float(data['age'])
        ])

        # 优先使用PyTorch DNN模型
        dnn_predictor = models.get('diabetes_dnn')
        if dnn_predictor and dnn_predictor.is_loaded:
            result = dnn_predictor.predict(features)
            # 补充关键因素分析
            glucose_val = float(data['glucose'])
            bmi_val = float(data['bmi'])
            key_factors = []
            if glucose_val >= 100:
                key_factors.append({
                    'factor': '血糖浓度',
                    'value': f'{glucose_val} mg/dL',
                    'status': '偏高' if glucose_val < 126 else '高',
                    'risk': True
                })
            if bmi_val >= 24:
                key_factors.append({
                    'factor': '体重指数(BMI)',
                    'value': f'{bmi_val:.1f}',
                    'status': '超重' if bmi_val < 28 else '肥胖',
                    'risk': True
                })
            if int(data.get('age', 0)) >= 45:
                key_factors.append({
                    'factor': '年龄',
                    'value': f'{data["age"]}岁',
                    'status': '高危年龄',
                    'risk': True
                })
            if float(data.get('diabetes_pedigree', 0)) > 0.5:
                key_factors.append({
                    'factor': '糖尿病家族史',

                    'value': f'{data["diabetes_pedigree"]}',
                    'status': '家族遗传风险',
                    'risk': True
                })

            result['key_factors'] = key_factors
            result['model_info'] = {
                'name': 'PIMA真实数据 (PyTorch DNN, BatchNorm+Dropout)',
                'samples': 768,
                'features': 8,
                'is_real_data': True
            }
            return jsonify({'status': 'success', **result})

        # 回退: XGBoost模型
        model = models.get('diabetes_risk')
        scaler = models.get('diabetes_risk_scaler')
        if model is None or scaler is None:
            return jsonify({'status': 'error', 'message': '糖尿病风险模型未加载'}), 500

        features_2d = features.reshape(1, -1)
        features_scaled = scaler.transform(features_2d)
        probability = float(model.predict_proba(features_scaled)[0, 1])

        if probability < 0.3:
            risk_level, risk_label, advice = 'low', '低风险', '您的糖尿病风险较低。建议保持健康生活方式，定期体检。'
        elif probability < 0.6:
            risk_level, risk_label, advice = 'medium', '中风险', '您的糖尿病风险处于中等水平。建议控制饮食、增加运动、定期监测血糖。'
        else:
            risk_level, risk_label, advice = 'high', '高风险', '您的糖尿病风险较高！强烈建议尽快就医。'

        glucose_val = float(data['glucose'])
        glucose_status = '高' if glucose_val >= 126 else ('偏高' if glucose_val >= 100 else '正常')
        bmi_val = float(data['bmi'])
        bmi_status = '肥胖' if bmi_val >= 28 else ('超重' if bmi_val >= 24 else '正常')

        key_factors = []
        if glucose_val >= 100:
            key_factors.append({'factor': '血糖浓度', 'value': f'{glucose_val} mg/dL', 'status': glucose_status, 'risk': True})
        if bmi_val >= 24:
            key_factors.append({'factor': '体重指数(BMI)', 'value': f'{bmi_val:.1f}', 'status': bmi_status, 'risk': True})
        if int(data.get('age', 0)) >= 45:
            key_factors.append({'factor': '年龄', 'value': f'{data["age"]}岁', 'status': '高危年龄', 'risk': True})
        if float(data.get('diabetes_pedigree', 0)) > 0.5:
            key_factors.append({'factor': '糖尿病家族史', 'value': f'{data["diabetes_pedigree"]}', 'status': '家族遗传风险', 'risk': True})

        return jsonify({
            'status': 'success',
            'risk_probability': round(probability, 4),
            'risk_percentage': round(probability * 100, 1),
            'risk_level': risk_level, 'risk_label': risk_label,
            'health_advice': advice,
            'glucose_status': glucose_status, 'bmi_status': bmi_status,
            'key_factors': key_factors,
            'model_info': {'name': 'PIMA数据(XGBoost fallback)', 'samples': 768, 'features': 8, 'is_real_data': True}
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


def _add_glucose_suggestions(result):
    """为血糖预测结果补充健康建议"""
    fg = result.get('forecast_glucose')
    if not fg:
        return
    suggestions = []
    if fg < 3.9:
        suggestions.append('立即补充碳水化合物（如150ml果汁或3块方糖）')
        suggestions.append('15分钟后复测血糖，若仍低于3.9请再次补充')
        suggestions.append('如频繁发生低血糖，建议调整胰岛素或降糖药剂量')
    elif fg > 11.1:
        suggestions.append('建议加测血酮，警惕糖尿病酮症酸中毒')
        suggestions.append('如持续高血糖，请咨询医生调整治疗方案')
        suggestions.append('多饮水有助于降低血糖浓度')
    elif fg > 7.0:
        suggestions.append('餐后适当运动（如散步15-30分钟）可帮助降低血糖')
        suggestions.append('注意控制碳水化合物摄入量')
    else:
        suggestions.append('血糖控制良好，请继续保持当前生活方式')
        suggestions.append('建议保持规律监测，每周至少3天记录血糖')
    result['suggestions'] = suggestions


@medical_bp.route('/v3/medical/glucose-forecast', methods=['POST'])
def v3_glucose_forecast():
    """
    血糖时序预测 — 基于真实 CGM 数据 (PyTorch BiLSTM + Attention)

    输入参数 (格式A - readings数组):
        readings: 过去12个血糖读数列表 (mmol/L, 5分钟间隔)
        predict_minutes: 预测分钟数 (30 或 60)

    输入参数 (格式B - 前端简化格式):
        current_glucose: 当前血糖值 (mmol/L)
        prediction_minutes: 预测分钟数 (30/60/120)
        postprandial_hours: 餐后时长 (0=空腹, 1/2/3)
        avg_glucose_3d: 近3天平均血糖 (mmol/L)
        hba1c: 糖化血红蛋白 (%)

    返回:
        current_glucose: 当前血糖
        forecast_glucose: 预测血糖值
        trend: 趋势 (上升/下降/平稳)
        alert: 预警信息
        chart_data: 历史+预测数据点
        health_advice: 健康建议
    """
    try:
        data = request.get_json()

        # ── 试图读取 readings 数组（格式A）──
        readings = data.get('readings', [])

        # ── 如果 readings 不存在或不足12个，尝试从前端简化字段构建（格式B）──
        if len(readings) < 12:
            current_glucose_field = data.get('current_glucose')
            if current_glucose_field is not None:
                current_glucose_val = float(current_glucose_field)
                prediction_minutes = int(data.get('prediction_minutes', 30))
                postprandial_hours = float(data.get('postprandial_hours', 0))
                avg_glucose_3d = float(data.get('avg_glucose_3d', current_glucose_val))
                hba1c_raw = float(data.get('hba1c', 6.5))
                predict_minutes = prediction_minutes

                # 生成12个合成历史读数（基于当前值 + 3日均值 + HbA1c）
                # 模拟CGM的5分钟间隔数据：最近12个点 = 1小时历史
                base_line = (avg_glucose_3d * 0.6 + current_glucose_val * 0.4)
                # HbA1c 偏移：每1% HbA1c ≈ 1.59 mmol/L 估算平均血糖(ADAG公式)
                hba1c_offset = (hba1c_raw - 6.5) * 1.59 * 0.2

                np.random.seed(42)  # 固定种子确保可复现的随机波动
                readings = []
                for i in range(12):
                    t = i / 11.0  # 0→1
                    # 从 base_line 渐变到 current_glucose_val
                    trend_val = base_line + (current_glucose_val - base_line) * t
                    # 餐后效应
                    meal_effect = 0
                    if postprandial_hours > 0:
                        # 餐后1-2小时血糖上升，3小时回归
                        meal_peak = postprandial_hours * 0.5 if postprandial_hours <= 2 else (3 - postprandial_hours) * 0.5
                        peak_pos = 0.7  # 在序列70%位置达到峰值
                        meal_factor = 1 - abs(t - peak_pos) * 3
                        meal_factor = max(0, meal_factor)
                        meal_effect = meal_peak * meal_factor
                    # 小幅随机波动 (±0.3 mmol/L)
                    noise = np.random.uniform(-0.3, 0.3)
                    val = trend_val + hba1c_offset + meal_effect + noise
                    readings.append(round(max(2.0, min(25.0, val)), 1))
            else:
                return jsonify({'status': 'error', 'message': '缺少必要字段：需要readings列表或current_glucose'}), 400

        predict_minutes = data.get('predict_minutes', data.get('prediction_minutes', 30))
        try:
            predict_minutes = int(predict_minutes)
        except (ValueError, TypeError):
            predict_minutes = 30

        # 确保至少12个读数
        if len(readings) < 12:
            return jsonify({'status': 'error', 'message': f'至少需要12个血糖读数，当前{len(readings)}个'}), 400

        # 优先使用PyTorch LSTM模型
        lstm_predictor = models.get('glucose_lstm')
        if lstm_predictor and lstm_predictor.is_loaded:
            result = lstm_predictor.predict(readings, predict_minutes)
            if result.get('forecast_glucose') is not None:
                result['predict_minutes'] = predict_minutes
                result['model_info'] = {
                    'name': '9患者CGM真实数据 (PyTorch BiLSTM+Attention)',
                    'patients': 9, 'samples': 8230, 'lookback': 12,
                    'architecture': 'Bidirectional LSTM + Attention',
                    'is_real_data': True
                }
                # 补充健康建议
                result.setdefault('suggestions', [])
                _add_glucose_suggestions(result)
                return jsonify({'status': 'success', **result})

        # 回退: XGBoost模型
        recent = np.array(readings[-12:], dtype=np.float32).reshape(1, -1)
        model_dict = models.get('glucose_forecast')
        scaler_dict = models.get('glucose_forecast_scaler')

        if model_dict is None or scaler_dict is None:
            return jsonify({'status': 'error', 'message': '血糖预测模型未加载'}), 500

        step_key = 'model_30min' if predict_minutes <= 30 else 'model_60min' if predict_minutes <= 60 else 'model_60min'
        scaler_key = 'scaler_30min' if predict_minutes <= 30 else 'scaler_60min' if predict_minutes <= 60 else 'scaler_60min'
        model = model_dict.get(step_key)
        scaler = scaler_dict.get(scaler_key)

        if model is None:
            return jsonify({'status': 'error', 'message': f'不支持{predict_minutes}分钟预测'}), 400

        scaled = scaler.transform(recent)
        forecast = float(model.predict(scaled)[0])
        current = float(readings[-1])
        change = forecast - current

        if change > 0.5:    trend, trend_label = 'rapid_rise', '快速上升'
        elif change > 0.2:  trend, trend_label = 'rise', '缓慢上升'
        elif change < -0.5: trend, trend_label = 'rapid_fall', '快速下降'
        elif change < -0.2: trend, trend_label = 'fall', '缓慢下降'
        else:               trend, trend_label = 'stable', '平稳'

        alert = None
        if forecast < 3.9:
            alert = {'level': 'danger', 'type': 'hypoglycemia', 'message': f'预测血糖 {forecast:.1f} mmol/L，可能发生低血糖！'}
        elif forecast > 11.1:
            alert = {'level': 'danger', 'type': 'hyperglycemia', 'message': f'预测血糖 {forecast:.1f} mmol/L，高于诊断标准！'}
        elif forecast > 7.0:
            alert = {'level': 'warning', 'type': 'elevated', 'message': f'预测血糖 {forecast:.1f} mmol/L，偏高。'}

        chart_data = [
            {'time': f'T-{(12-i)*5}', 'value': round(float(val), 1), 'type': 'history'}
            for i, val in enumerate(readings[-12:])
        ]
        chart_data.append({'time': f'T+{predict_minutes}', 'value': round(forecast, 1), 'type': 'forecast'})

        result = {
            'status': 'success',
            'current_glucose': round(current, 1),
            'forecast_glucose': round(forecast, 1),
            'predict_minutes': predict_minutes,
            'change': round(change, 1),
            'trend': trend,
            'trend_label': trend_label,
            'alert': alert,
            'chart_data': chart_data,
            'alerts': [alert] if alert else [],
            'suggestions': [],
            'model_info': {'name': 'CGM数据(XGBoost)', 'patients': 9, 'is_real_data': True}
        }
        _add_glucose_suggestions(result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ────────────────────── V3 Medical Data Analysis Endpoints (GET) ──────────────────────

@medical_bp.route('/medical/v3/insulin-glucose-correlation', methods=['GET'])
def insulin_glucose_correlation():
    """PIMA 胰岛素-血糖相关性分析"""
    data_path = os.path.join(BASE_DIR, 'data', 'diabetes', 'pima-indians-diabetes.csv')

    from scipy.stats import pearsonr
    import pandas as pd
    import numpy as np

    try:
        df = pd.read_csv(data_path)
        cols = ['Pregnancies','Glucose','BloodPressure','SkinThickness','Insulin','BMI','DiabetesPedigreeFunction','Age','Outcome']
        df.columns = cols

        # 过滤有效数据
        valid = df[(df['Insulin'] > 0) & (df['Glucose'] > 0)]
        insulin = valid['Insulin'].values
        glucose = valid['Glucose'].values

        r, p_value = pearsonr(insulin, glucose)

        # 散点数据（采样最多200个点防止过大）
        scatter_data = []
        step = max(1, len(valid) // 200)
        for _, row in valid.iloc[::step].iterrows():
            scatter_data.append({'insulin': float(row['Insulin']), 'glucose': float(row['Glucose'])})

        # Convert to Python native types for JSON serialization
        import math
        r_val = 0.0 if (r is None or math.isnan(float(r))) else float(round(r, 4))
        p_val = 1.0 if (p_value is None or math.isnan(float(p_value))) else float(round(p_value, 6))
        sig = bool(p_val < 0.05)

        result = {
            'correlation_coefficient': r_val,
            'p_value': p_val,
            'significant': sig,
            'sample_size': int(len(valid)),
            'scatter_data': scatter_data,
            'summary': {}
        }
        if len(valid) > 0:
            result['summary'] = {
                'mean_insulin': float(valid['Insulin'].mean()),
                'std_insulin': float(valid['Insulin'].std()),
                'mean_glucose': float(valid['Glucose'].mean()),
                'std_glucose': float(valid['Glucose'].std()),
            }

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@medical_bp.route('/medical/v3/glucose-patients', methods=['GET'])
def glucose_patients():
    """返回9位患者的CGM血糖数据概览"""
    import pandas as pd
    data_dir = os.path.join(BASE_DIR, 'data', 'diabetes')

    patients = []
    for i in range(1, 10):
        fname = f'glucose_0{i}.csv'
        fpath = os.path.join(data_dir, fname)
        if os.path.exists(fpath):
            try:
                df = pd.read_csv(fpath)
                # glucose 列是第3列(index 2)
                if df.shape[1] >= 3:
                    vals = pd.to_numeric(df.iloc[:, 2], errors='coerce').dropna().values
                else:
                    vals = pd.to_numeric(df.iloc[:, 0], errors='coerce').dropna().values
                patients.append({
                    'id': f'0{i}',
                    'file': fname,
                    'samples': len(vals),
                    'mean_glucose': round(float(vals.mean()), 2),
                    'min_glucose': round(float(vals.min()), 2),
                    'max_glucose': round(float(vals.max()), 2),
                    'std_glucose': round(float(vals.std()), 2),
                })
            except Exception as e:
                patients.append({'id': f'0{i}', 'file': fname, 'error': str(e)})

    return jsonify({'patients': patients})


@medical_bp.route('/medical/v3/glucose-patient/<patient_id>', methods=['GET'])
def glucose_patient_detail(patient_id):
    """返回指定患者的完整血糖时序数据"""
    import pandas as pd
    import numpy as np

    data_dir = os.path.join(BASE_DIR, 'data', 'diabetes')
    fname = f'glucose_{patient_id}.csv'
    fpath = os.path.join(data_dir, fname)

    if not os.path.exists(fpath):
        return jsonify({'error': f'Patient {patient_id} not found'}), 404

    try:
        df = pd.read_csv(fpath)

        # 时间在第1列(index 0)，血糖值在第3列(index 2)
        if df.shape[1] >= 3:
            time_col = df.columns[0]
            glucose_col = df.columns[2]
            readings = []
            for idx, row in df.iterrows():
                try:
                    gval = float(row[glucose_col]) if pd.notna(row[glucose_col]) else None
                except (ValueError, TypeError):
                    gval = None
                readings.append({
                    'time': str(row[time_col]) if pd.notna(row[time_col]) else str(idx),
                    'value': gval
                })
            readings = [r for r in readings if r['value'] is not None]
        else:
            vals = df.iloc[:, 0].values
            readings = [{'time': str(i), 'value': float(v)} for i, v in enumerate(vals)]

        vals_arr = np.array([r['value'] for r in readings])

        return jsonify({
            'patient_id': patient_id,
            'readings': readings,
            'stats': {
                'count': len(readings),
                'mean': round(float(vals_arr.mean()), 2),
                'std': round(float(vals_arr.std()), 2),
                'min': round(float(vals_arr.min()), 2),
                'max': round(float(vals_arr.max()), 2),
                'median': round(float(np.median(vals_arr)), 2),
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@medical_bp.route('/medical/v3/symptom-predict', methods=['POST'])
def symptom_predict():
    """症状-诊断预测（自训练模型）"""
    data = request.get_json() or {}
    symptoms = data.get('symptoms', '')
    if not symptoms:
        return jsonify({'error': '请填写症状描述'}), 400

    import sys, pickle
    _script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _scripts_path = os.path.join(_script_dir, 'scripts')
    if _scripts_path not in sys.path:
        sys.path.insert(0, _scripts_path)

    try:
        from train_symptom_model import predict, MODEL_FILE, VECTORIZER_FILE, train_model, create_sample_data

        # 如果模型不存在则自动训练
        if not os.path.exists(MODEL_FILE) or not os.path.exists(VECTORIZER_FILE):
            create_sample_data()
            train_model()

        result = predict(symptoms)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@medical_bp.route('/medical/v3/symptom-train-data', methods=['GET', 'POST'])
def symptom_train_data():
    """管理症状训练数据"""
    import csv, sys
    _script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _scripts_path = os.path.join(_script_dir, 'scripts')
    if _scripts_path not in sys.path:
        sys.path.insert(0, _scripts_path)
    from train_symptom_model import DATA_FILE, DATA_DIR

    if request.method == 'POST':
        # 添加新数据
        data = request.get_json() or {}
        row = {
            'symptoms': data.get('symptoms', ''),
            'diagnosis': data.get('diagnosis', ''),
            'medication': data.get('medication', ''),
            'department': data.get('department', ''),
            'severity': data.get('severity', '轻'),
        }
        if not row['symptoms'] or not row['diagnosis']:
            return jsonify({'error': '症状和诊断不能为空'}), 400

        file_exists = os.path.exists(DATA_FILE)
        with open(DATA_FILE, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['symptoms','diagnosis','medication','department','severity'])
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

        return jsonify({'success': True, 'message': '数据已添加，请重新训练模型'})

    # GET: 返回所有训练数据
    import csv
    if not os.path.exists(DATA_FILE):
        from train_symptom_model import create_sample_data
        create_sample_data()

    rows = []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    return jsonify({'data': rows, 'count': len(rows)})


@medical_bp.route('/medical/v3/symptom-retrain', methods=['POST'])
def symptom_retrain():
    """重新训练症状模型"""
    import sys, pickle
    _script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _scripts_path = os.path.join(_script_dir, 'scripts')
    if _scripts_path not in sys.path:
        sys.path.insert(0, _scripts_path)

    try:
        from train_symptom_model import train_model, create_sample_data
        create_sample_data()
        train_model()
        return jsonify({'success': True, 'message': '模型训练完成'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

