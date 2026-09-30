"""
Traffic ML Model Routes
V2 traffic endpoints extracted from app.py
"""
import json
import os
import sys
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify

from .model_loader import get_models_dict
models = get_models_dict()

traffic_bp = Blueprint('traffic', __name__, url_prefix='/api')


# ────────────────────── V2 Traffic Endpoints ──────────────────────

@traffic_bp.route('/v2/traffic/congestion-predict', methods=['POST'])
def v2_traffic_congestion():
    try:
        data = request.get_json()
        hour = data.get('hour', 12)
        day_of_week = data.get('day_of_week', 3)
        is_weekend = data.get('is_weekend', 0)
        is_holiday = data.get('is_holiday', 0)
        season = data.get('season', 1)
        weather_code = data.get('weather_code', 0)
        section_capacity = data.get('section_capacity', 1800)
        lanes = data.get('lanes', 4)
        speed_limit = data.get('speed_limit', 60)
        road_type = data.get('road_type', 0)

        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)

        features = np.array([[hour_sin, hour_cos, day_sin, day_cos,
                              is_weekend, is_holiday, season,
                              weather_code, section_capacity, lanes,
                              speed_limit, road_type]])

        if models['traffic_scaler']:
            features_scaled = models['traffic_scaler'].transform(features)
        else:
            features_scaled = features

        if models['traffic']:
            pred = models['traffic'].predict(features_scaled)[0]
            avg_speed = round(float(pred[0]), 1)
            flow_count = int(round(pred[1]))
            congestion_index = round(float(pred[2]), 4)
            accident_prob = round(float(pred[3]), 4)

            # Anomaly detection
            is_anomaly = False
            if models['traffic_anomaly']:
                is_anomaly = int(models['traffic_anomaly'].predict(features_scaled)[0]) == -1

            # Congestion level
            if congestion_index < 0.3:
                level = '畅通'
            elif congestion_index < 0.5:
                level = '轻度拥堵'
            elif congestion_index < 0.7:
                level = '中度拥堵'
            else:
                level = '严重拥堵'

            return jsonify({
                'status': 'success',
                'avg_speed': avg_speed,
                'flow_count': flow_count,
                'congestion_index': congestion_index,
                'congestion_level': level,
                'accident_probability': accident_prob,
                'is_anomaly': bool(is_anomaly)
            })
        else:
            return jsonify({'status': 'error', 'message': 'Traffic model not loaded'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@traffic_bp.route('/v2/traffic/anomaly-detect', methods=['POST'])
def v2_traffic_anomaly_detect():
    try:
        data = request.get_json()
        records = data.get('records', [])
        if not records:
            return jsonify({'status': 'error', 'message': '记录不能为空'}), 400

        anomalies = []
        for rec in records:
            hour = rec.get('hour', 12)
            day_of_week = rec.get('day_of_week', 3)
            is_weekend = rec.get('is_weekend', 0)
            is_holiday = rec.get('is_holiday', 0)
            season = rec.get('season', 1)
            weather_code = rec.get('weather_code', 0)
            section_capacity = rec.get('section_capacity', 1800)
            lanes = rec.get('lanes', 4)
            speed_limit = rec.get('speed_limit', 60)
            road_type = rec.get('road_type', 0)

            hour_sin = np.sin(2 * np.pi * hour / 24)
            hour_cos = np.cos(2 * np.pi * hour / 24)
            day_sin = np.sin(2 * np.pi * day_of_week / 7)
            day_cos = np.cos(2 * np.pi * day_of_week / 7)

            features = np.array([[hour_sin, hour_cos, day_sin, day_cos,
                                  is_weekend, is_holiday, season,
                                  weather_code, section_capacity, lanes,
                                  speed_limit, road_type]])

            if models['traffic_scaler']:
                features_scaled = models['traffic_scaler'].transform(features)
            else:
                features_scaled = features

            pred = None
            if models['traffic']:
                pred = models['traffic'].predict(features_scaled)[0]

            is_anomaly = False
            if models['traffic_anomaly']:
                is_anomaly = int(models['traffic_anomaly'].predict(features_scaled)[0]) == -1

            if is_anomaly and pred is not None:
                anomalies.append({
                    'section_id': rec.get('section_id'),
                    'expected_flow': int(round(pred[1])),
                    'expected_speed': round(float(pred[0]), 1),
                    'actual_flow': rec.get('actual_flow', 0),
                    'actual_speed': rec.get('actual_speed', 0),
                    'severity': '严重' if abs(rec.get('actual_flow', 0) - pred[1]) / max(pred[1], 1) > 0.5 else '警告'
                })

        return jsonify({'status': 'success', 'anomalies': anomalies, 'count': len(anomalies)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@traffic_bp.route('/v2/traffic/hourly-flow', methods=['POST'])
def v2_traffic_hourly_flow():
    try:
        data = request.get_json()
        day_of_week = data.get('day_of_week', 3)
        is_weekend = data.get('is_weekend', 0)
        is_holiday = data.get('is_holiday', 0)
        season = data.get('season', 1)
        weather_code = data.get('weather_code', 0)
        section_capacity = data.get('section_capacity', 1800)
        lanes = data.get('lanes', 4)
        speed_limit = data.get('speed_limit', 60)
        road_type = data.get('road_type', 0)

        hourly_data = []
        for hour in range(24):
            hour_sin = np.sin(2 * np.pi * hour / 24)
            hour_cos = np.cos(2 * np.pi * hour / 24)
            day_sin = np.sin(2 * np.pi * day_of_week / 7)
            day_cos = np.cos(2 * np.pi * day_of_week / 7)

            features = np.array([[hour_sin, hour_cos, day_sin, day_cos,
                                  is_weekend, is_holiday, season,
                                  weather_code, section_capacity, lanes,
                                  speed_limit, road_type]])

            if models['traffic_scaler']:
                features_scaled = models['traffic_scaler'].transform(features)
            else:
                features_scaled = features

            if models['traffic']:
                pred = models['traffic'].predict(features_scaled)[0]
                speed = round(float(pred[0]), 1)
                flow = int(round(pred[1]))
                ci = round(float(pred[2]), 4)

                if ci < 0.3:
                    level = '畅通'
                elif ci < 0.5:
                    level = '轻度拥堵'
                elif ci < 0.7:
                    level = '中度拥堵'
                else:
                    level = '严重拥堵'

                hourly_data.append({
                    'hour': hour,
                    'estimatedFlow': flow,
                    'estimatedSpeed': speed,
                    'congestionLevel': level,
                    'congestionIndex': ci
                })

        return jsonify({'status': 'success', 'hourly_data': hourly_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ════════════════════════════════════════════════════════════════
# V5 Traffic 增强模型 (拥堵预测/异常检测/天气/事故/场景仿真)
# ════════════════════════════════════════════════════════════════

def _try_new_model(name: str):
    """尝试加载 V5 新模型"""
    m = get_models_dict().get(name)
    if m is not None:
        return m
    from .model_loader import get_model
    return get_model(name)


def _build_congestion_features(hour, day_of_week, month, is_weekend, is_holiday,
                                weather_code, temperature, humidity,
                                lanes, speed_limit, road_type):
    """构建拥堵预测模型特征向量"""
    season = month // 4 + 1
    hour_sin = np.sin(2 * np.pi * hour / 24)
    hour_cos = np.cos(2 * np.pi * hour / 24)
    day_sin = np.sin(2 * np.pi * day_of_week / 7)
    day_cos = np.cos(2 * np.pi * day_of_week / 7)

    features = [
        hour, day_of_week, month, season, is_weekend, is_holiday,
        weather_code, temperature, humidity,
        lanes, speed_limit,
        hour_sin, hour_cos, day_sin, day_cos,
        road_type
    ]
    return np.array([features])


@traffic_bp.route('/v5/traffic/hourly-forecast', methods=['POST'])
def v5_traffic_hourly_forecast():
    """
    V5 拥堵预测 — 使用 XGBoost 多输出模型预测 24h 逐时流量/速度/拥堵指数
    """
    try:
        model = _try_new_model('traffic_congestion')
        scaler = _try_new_model('traffic_congestion_scaler')

        data = request.get_json() or {}
        day_of_week = data.get('day_of_week', 2)
        month = data.get('month', 5)
        is_weekend = data.get('is_weekend', 0)
        is_holiday = data.get('is_holiday', 0)
        weather_code = data.get('weather_code', 0)
        temperature = data.get('temperature', 20)
        humidity = data.get('humidity', 50)
        lanes = data.get('lanes', 6)
        speed_limit = data.get('speed_limit', 70)
        road_type = data.get('road_type', 1)

        if model is None or scaler is None:
            return jsonify({'status': 'error', 'message': 'V5 拥堵模型未加载'}), 503

        hourly_data = []
        morning_peak_flow, evening_peak_flow = 0, 0
        morning_peak_hour, evening_peak_hour = 8, 18
        daily_total_flow = 0

        for hour in range(24):
            features = _build_congestion_features(
                hour, day_of_week, month, is_weekend, is_holiday,
                weather_code, temperature, humidity,
                lanes, speed_limit, road_type
            )
            features_scaled = scaler.transform(features)
            pred = model.predict(features_scaled)[0]

            flow = int(round(pred[0]))
            speed = round(float(pred[1]), 1)
            ci = round(float(pred[2]), 4)

            if ci < 0.3:
                level = '畅通'
            elif ci < 0.5:
                level = '轻度拥堵'
            elif ci < 0.7:
                level = '中度拥堵'
            else:
                level = '严重拥堵'

            daily_total_flow += flow

            # 追踪早晚高峰
            if 7 <= hour <= 9 and flow > morning_peak_flow:
                morning_peak_flow = flow
                morning_peak_hour = hour
            if 17 <= hour <= 19 and flow > evening_peak_flow:
                evening_peak_flow = flow
                evening_peak_hour = hour

            hourly_data.append({
                'hour': hour,
                'estimatedFlow': flow,
                'estimatedSpeed': speed,
                'congestionLevel': level,
                'congestionIndex': ci,
            })

        return jsonify({
            'status': 'success',
            'hourly_data': hourly_data,
            'summary': {
                'morning_peak': {
                    'hour': f'{morning_peak_hour}:00',
                    'flow': morning_peak_flow,
                },
                'evening_peak': {
                    'hour': f'{evening_peak_hour}:00',
                    'flow': evening_peak_flow,
                },
                'daily_total_flow': daily_total_flow,
                'daily_avg_flow': round(daily_total_flow / 24),
            },
            'model': 'xgb_v5_congestion',
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@traffic_bp.route('/v5/traffic/anomaly-enhanced', methods=['POST'])
def v5_traffic_anomaly_enhanced():
    """
    V5 异常检测增强 — 使用 Isolation Forest 模型
    输入: 路段信息和实际流量/速度值
    输出: 是否异常 + 异常分数
    """
    try:
        model = _try_new_model('traffic_anomaly_iforest')
        scaler = _try_new_model('traffic_anomaly_scaler')
        threshold_data = _try_new_model('traffic_anomaly_threshold')

        data = request.get_json() or {}
        records = data.get('records', [])

        if model is None:
            return jsonify({'status': 'error', 'message': 'V5 异常检测模型未加载'}), 503

        threshold = 0.05
        if threshold_data is not None:
            threshold = threshold_data.get('threshold', 0.05)

        anomalies = []
        for rec in records:
            # 构造特征: [section_id, hour, day_of_week, flow_mean, flow_std,
            #             speed_mean, speed_std, cong_mean, cong_std,
            #             flow_deviation, speed_deviation, flow_count, avg_speed]
            feature_cols = ['section_id', 'hour', 'day_of_week',
                           'flow_mean', 'flow_std', 'speed_mean', 'speed_std',
                           'cong_mean', 'cong_std', 'flow_deviation',
                           'speed_deviation', 'flow_count', 'avg_speed']

            features = np.array([[
                rec.get(k, 0) for k in feature_cols
            ]], dtype=np.float32)

            features_scaled = scaler.transform(features)
            pred = model.predict(features_scaled)[0]
            score = model.score_samples(features_scaled)[0]

            is_anomaly = (pred == -1) or (score < threshold)

            if is_anomaly:
                flow_dev = rec.get('flow_deviation', 0)
                speed_dev = rec.get('speed_deviation', 0)

                if abs(flow_dev) > abs(speed_dev):
                    anom_type = '流量激增' if flow_dev > 0 else '流量锐减'
                else:
                    anom_type = '速度骤降' if speed_dev < 0 else '速度异常'

                severity = '严重' if pred == -1 else '警告'

                anomalies.append({
                    'section_id': rec.get('section_id'),
                    'anomaly_type': anom_type,
                    'severity': severity,
                    'anomaly_score': float(score),
                    'actual_flow': rec.get('flow_count', 0),
                    'actual_speed': rec.get('avg_speed', 0),
                    'expected_flow': rec.get('flow_mean', 0),
                    'expected_speed': rec.get('speed_mean', 0),
                    'possible_cause': '交通事故/封路' if severity == '严重' else '异常交通模式',
                })

        return jsonify({
            'status': 'success',
            'anomalies': anomalies,
            'count': len(anomalies),
            'model': 'iforest_v5_anomaly',
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@traffic_bp.route('/v5/traffic/weather-impact', methods=['POST'])
def v5_traffic_weather_impact():
    """
    V5 天气-交通影响分析 — 使用 XGBoost 模型
    """
    try:
        model_dict = _try_new_model('traffic_weather')
        scaler_dict = _try_new_model('traffic_weather_scaler')
        encoders = _try_new_model('traffic_weather_encoders')

        data = request.get_json() or {}

        if model_dict is None or scaler_dict is None:
            return jsonify({'status': 'error', 'message': 'V5 天气模型未加载'}), 503

        weather_names = {0: "晴", 1: "多云", 2: "小雨", 3: "中雨", 4: "暴雨",
                        5: "小雪", 6: "中雪", 7: "大雪", 8: "雾"}

        # 预测所有天气条件下指定时段的路况
        road_type = data.get('road_type', 1)
        hour = data.get('hour', 14)
        temperature = data.get('temperature', 20)
        humidity = data.get('humidity', 50)

        if encoders is not None and encoders.get('weather_names'):
            weather_names = encoders['weather_names']

        results = []
        for weather_code in range(9):
            sample = np.array([[weather_code, road_type, hour,
                                temperature, humidity]], dtype=np.float32)

            predictions = {}
            for target in ['flow_count', 'avg_speed', 'congestion_index']:
                if target in model_dict and target in scaler_dict:
                    s = scaler_dict[target].transform(sample)
                    pred = model_dict[target].predict(s)[0]
                    predictions[target] = round(float(pred), 2)

            if 'flow_count' in predictions:
                # 判断影响程度
                speed_factor = predictions.get('avg_speed', 50) / 50.0
                if speed_factor < 0.5:
                    congestion_risk = '高风险'
                elif speed_factor < 0.75:
                    congestion_risk = '中风险'
                else:
                    congestion_risk = '低风险'

                results.append({
                    'weather_code': weather_code,
                    'weather_name': weather_names.get(weather_code, f'未知({weather_code})'),
                    'predicted_flow': predictions.get('flow_count'),
                    'predicted_speed': predictions.get('avg_speed'),
                    'predicted_congestion': predictions.get('congestion_index'),
                    'congestion_risk': congestion_risk,
                })

        return jsonify({
            'status': 'success',
            'results': results,
            'model': 'xgb_v5_weather',
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@traffic_bp.route('/v5/traffic/accident-impact', methods=['POST'])
def v5_traffic_accident_impact():
    """
    V5 事故影响预测 — 使用 GradientBoosting 模型
    预测事故导致的流量和速度下降百分比
    """
    try:
        model = _try_new_model('traffic_accident_impact')
        scaler = _try_new_model('traffic_accident_impact_scaler')

        data = request.get_json() or {}

        if model is None or scaler is None:
            return jsonify({'status': 'error', 'message': 'V5 事故影响模型未加载'}), 503

        features = np.array([[  # [section_id, road_type, lanes, speed_limit,
                                #  hour, day_of_week, weather_code,
                                #  accident_severity, normal_flow, normal_speed]
            data.get('section_id', 1),
            data.get('road_type', 1),
            data.get('lanes', 6),
            data.get('speed_limit', 70),
            data.get('hour', 8),
            data.get('day_of_week', 2),
            data.get('weather_code', 0),
            data.get('accident_severity', 0.5),
            data.get('normal_flow', 1500),
            data.get('normal_speed', 45),
        ]])

        features_scaled = scaler.transform(features)
        pred = model.predict(features_scaled)[0]

        flow_reduction_pct = round(float(pred[0]), 1)
        speed_reduction_pct = round(float(pred[1]), 1)

        return jsonify({
            'status': 'success',
            'flow_reduction_pct': flow_reduction_pct,
            'speed_reduction_pct': speed_reduction_pct,
            'predicted_flow': int(data.get('normal_flow', 1500) * (1 - flow_reduction_pct / 100)),
            'predicted_speed': round(data.get('normal_speed', 45) * (1 - speed_reduction_pct / 100), 1),
            'model': 'gb_v5_accident_impact',
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@traffic_bp.route('/v5/traffic/scenario-simulate', methods=['POST'])
def v5_traffic_scenario_simulate():
    """
    V5 交通场景仿真 — 使用 XGBoost 模型
    模拟增减车道/调整限速对交通流的影响
    """
    try:
        model = _try_new_model('traffic_scenario')
        scaler = _try_new_model('traffic_scenario_scaler')

        data = request.get_json() or {}

        if model is None or scaler is None:
            return jsonify({'status': 'error', 'message': 'V5 场景仿真模型未加载'}), 503

        change_type = data.get('change_type', 'add_lane')  # add_lane / change_speed
        change_value = data.get('change_value', 1)
        change_type_code = 0 if change_type == 'add_lane' else 1

        features = np.array([[  # [road_type, lanes, speed_limit, hour, day_of_week,
                                #  change_type_code, change_value, base_flow, base_speed]
            data.get('road_type', 1),
            data.get('lanes', 6),
            data.get('speed_limit', 70),
            data.get('hour', 8),
            data.get('day_of_week', 2),
            change_type_code,
            change_value,
            data.get('base_flow', 1800),
            data.get('base_speed', 40),
        ]])

        features_scaled = scaler.transform(features)
        pred = model.predict(features_scaled)[0]

        base_flow = data.get('base_flow', 1800)
        base_speed = data.get('base_speed', 40)
        result_flow = int(round(pred[0]))
        result_speed = round(float(pred[1]), 1)

        impact = ''
        recommendation = ''
        if change_type == 'add_lane':
            impact = f'增加{change_value}条车道后，通行流量 {base_flow} → {result_flow} 辆/小时'
            recommendation = f'流量提升 {(result_flow / base_flow - 1) * 100:.0f}%' if base_flow else '流量提升 —'
        else:
            impact = f'限速调整后，速度 {base_speed} → {result_speed} km/h'
            recommendation = f'速度变化 {(result_speed / base_speed - 1) * 100:+.0f}%' if base_speed else '速度变化 —'

        return jsonify({
            'status': 'success',
            'impact_description': impact,
            'recommendation': recommendation,
            'predicted_flow': result_flow,
            'predicted_speed': result_speed,
            'flow_change_pct': round((result_flow / base_flow - 1) * 100, 1) if base_flow else 0,
            'speed_change_pct': round((result_speed / base_speed - 1) * 100, 1) if base_speed else 0,
            'model': 'xgb_v5_scenario',
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
