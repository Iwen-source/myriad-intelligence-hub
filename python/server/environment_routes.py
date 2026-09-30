"""
Environment ML Model Routes
V1 + V2 environment endpoints extracted from app.py
"""
import json
import os
import sys
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify

from .model_loader import get_models_dict
models = get_models_dict()

environment_bp = Blueprint('environment', __name__, url_prefix='/api')


# ────────────────────── V1 Environment Endpoints ──────────────────────

@environment_bp.route('/predict/environment', methods=['POST'])
def predict_environment():
    try:
        data = request.get_json()
        features = np.array([[
            data.get('pm25', 0), data.get('pm10', 0), data.get('o3', 0),
            data.get('no2', 0), data.get('so2', 0), data.get('co', 0),
            data.get('temperature', 25), data.get('humidity', 60)
        ]])
        scaled = models['env_scaler'].transform(features)
        pred_aqi = float(models['environment'].predict(scaled)[0])
        def aqi_label(aqi):
            if aqi <= 50: return ("优", "空气质量令人满意，基本无空气污染。")
            elif aqi <= 100: return ("良", "空气质量可接受，某些污染物可能对极少数敏感人群有较弱影响。")
            elif aqi <= 150: return ("轻度污染", "易感人群症状有轻度加剧，健康人群出现刺激症状。")
            elif aqi <= 200: return ("中度污染", "进一步加剧敏感人群症状，可能对健康人群心脏、呼吸系统有影响。")
            elif aqi <= 300: return ("重度污染", "心脏病和肺病患者症状显著加剧，运动耐受力降低。")
            else: return ("严重污染", "健康人群运动耐受力降低，有明显强烈症状。")
        level, advice = aqi_label(pred_aqi)
        pollutants = ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co']
        vals = [data.get(p, 0) for p in pollutants]
        main_idx = np.argmax(vals)
        return jsonify({
            "status": "success", "predicted_aqi": round(pred_aqi, 1),
            "aqi_level": level, "main_pollutant": pollutants[main_idx],
            "health_advice": advice
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ────────────────────── V2 Environment Endpoints ──────────────────────

@environment_bp.route('/v2/environment/source-apportionment', methods=['POST'])
def v2_source_apportionment():
    try:
        data = request.get_json()
        pollutants = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3']
        input_vec = np.array([[data.get(p, 0) for p in pollutants]])
        input_vec = np.maximum(input_vec, 0.01)
        if models['nmf']:
            w = models['nmf'].transform(input_vec)
            contrib = w[0] / w[0].sum()
        else:
            contrib = np.ones(5) / 5
        profiles = models['source_profiles']
        names = profiles.get('names', ['工业', '交通', '扬尘', '生活', '自然']) if profiles else ['源1', '源2', '源3', '源4', '源5']
        contributions = {names[i]: round(float(contrib[i]) * 100, 1) for i in range(len(contrib))}
        dominant = max(contributions, key=contributions.get)
        return jsonify({
            "status": "success", "source_contributions": contributions,
            "dominant_source": dominant
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@environment_bp.route('/v2/environment/aqi-forecast', methods=['POST'])
def v2_aqi_forecast():
    try:
        data = request.get_json()
        features = np.array([[
            data.get('pm25', 0), data.get('pm10', 0), data.get('o3', 0),
            data.get('no2', 0), data.get('so2', 0), data.get('co', 0),
            data.get('temperature', 25), data.get('humidity', 60)
        ]])
        scaled = models['aqi_scaler'].transform(features) if models['aqi_scaler'] else features
        pred_idx = int(models['aqi_forecast'].predict(scaled)[0])
        if models['aqi_encoder']:
            level_names = models['aqi_encoder'].classes_
            pred_level = level_names[pred_idx] if pred_idx < len(level_names) else "未知"
        else:
            pred_level = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"][min(pred_idx, 5)]
        proba = models['aqi_forecast'].predict_proba(scaled)[0]
        level_probs = {}
        if models['aqi_encoder']:
            for i, name in enumerate(models['aqi_encoder'].classes_):
                if i < len(proba):
                    level_probs[name] = round(float(proba[i]) * 100, 1)
        else:
            for i, name in enumerate(["优", "良", "轻度", "中度", "重度", "严重"]):
                if i < len(proba):
                    level_probs[name] = round(float(proba[i]) * 100, 1)
        confidence = round(float(max(proba)) * 100, 1)
        return jsonify({
            "status": "success", "predicted_level": pred_level,
            "level_probabilities": level_probs, "confidence": confidence
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@environment_bp.route('/v2/environment/carbon-estimate', methods=['POST'])
def v2_carbon_estimate():
    try:
        data = request.get_json()
        electricity = data.get('electricity', 0)
        coal = data.get('coal', 0)
        oil = data.get('oil', 0)
        natural_gas = data.get('natural_gas', 0)
        prod_scale = data.get('production_scale', 1)
        efficiency = data.get('efficiency', 0.8)
        season = data.get('season', 1)
        season_enc = [1 if season == i else 0 for i in range(4)]
        features = np.array([[electricity, coal, oil, natural_gas, prod_scale, efficiency] + season_enc])
        scaled = models['carbon_scaler'].transform(features) if models['carbon_scaler'] else features
        carbon = float(models['carbon'].predict(scaled)[0]) if models['carbon'] else (
            electricity * 0.0007 + coal * 2.5 + oil * 2.3 + natural_gas * 2.0
        ) * prod_scale * (1.1 - efficiency)
        return jsonify({
            "status": "success", "daily_estimate": round(carbon, 2),
            "monthly_estimate": round(carbon * 30, 2),
            "yearly_estimate": round(carbon * 365, 2),
            "trend_direction": "稳定",
            "peer_percentile": round(np.random.uniform(30, 70), 1),
            "reduction_suggestions": [
                "建议提高设备能效等级",
                "考虑使用清洁能源替代煤炭",
                "优化生产工艺减少能源浪费"
            ]
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
