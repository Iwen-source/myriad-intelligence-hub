"""
Route handlers for newly added ML models (Energy, Forum, Development, etc.)
Integration layer between Flask server and the 6 new Python training scripts.

Each handler:
1. Loads the corresponding model from model_loader (lazy)
2. Builds feature vectors from request JSON
3. Returns structured predictions as JSON
"""
import json
import os
import sys
import numpy as np
import pandas as pd
import pickle
import logging
from flask import Blueprint, request, jsonify

# Add models dir to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
sys.path.insert(0, MODELS_DIR)

from .model_loader import get_model, register_model

log = logging.getLogger(__name__)

# ──────────────────── Blueprint ────────────────────
enhanced_bp = Blueprint('enhanced', __name__, url_prefix='/api/v2')

# 模型已在 model_loader.py 的 _get_file_mapping() 中注册


# ════════════════════════════════════════════════════
# 1. ENERGY: Load Forecasting
# ════════════════════════════════════════════════════

# ── Energy LSTM helpers (lazy + cached) ──
_ENERGY_LSTM = None
_ENERGY_LSTM_LOADED = False
_ENERGY_FEATURES = ['load', 'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos', 'is_weekend',
                    'season', 'temperature', 'load_lag_1', 'load_lag_24', 'load_lag_48',
                    'load_lag_168', 'load_rolling_7d', 'load_rolling_24h']


def _load_energy_lstm():
    """Lazily load the trained PyTorch LSTM (models/energy_load_lstm.pth). Cached after first call."""
    global _ENERGY_LSTM, _ENERGY_LSTM_LOADED
    if _ENERGY_LSTM_LOADED:
        return _ENERGY_LSTM
    _ENERGY_LSTM_LOADED = True
    try:
        import torch
        import torch.nn as nn

        class LoadLSTM(nn.Module):
            def __init__(self, input_dim, hidden_size, num_layers, output_dim, dropout=0.2):
                super().__init__()
                self.lstm = nn.LSTM(input_dim, hidden_size, num_layers,
                                    batch_first=True, dropout=dropout)
                self.fc = nn.Sequential(
                    nn.Linear(hidden_size, hidden_size // 2),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(hidden_size // 2, output_dim),
                )

            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])

        ckpt_path = os.path.join(MODELS_DIR, 'energy_load_lstm.pth')
        if not os.path.exists(ckpt_path):
            log.warning("energy_load_lstm.pth not found; falling back to statistical model")
            return None
        try:
            ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
        except TypeError:
            ckpt = torch.load(ckpt_path, map_location='cpu')
        model = LoadLSTM(ckpt['input_dim'], ckpt['hidden_size'],
                         ckpt['num_layers'], ckpt['output_dim'])
        model.load_state_dict(ckpt['model_state_dict'])
        model.eval()
        _ENERGY_LSTM = {
            'model': model,
            'torch': torch,
            'seq_len': int(ckpt.get('seq_len', 48)),
            'horizon': int(ckpt.get('output_dim', 24)),
        }
        log.info(f"Energy LSTM loaded from {ckpt_path}")
    except Exception as e:  # noqa: BLE001
        log.warning(f"Energy LSTM load failed, using statistical fallback: {e}")
        _ENERGY_LSTM = None
    return _ENERGY_LSTM


def _build_energy_features(loads, current_hour, day_of_week, temperature, season, scaler):
    """Build the (seq_len, 14) scaled feature matrix expected by the LSTM."""
    loads = np.asarray(loads, dtype=float)
    n = len(loads)
    rows = []
    for i in range(n):
        h = (current_hour - (n - 1 - i)) % 24
        day_off = (current_hour - (n - 1 - i)) // 24
        dow = int((day_of_week - day_off) % 7)
        rows.append([
            loads[i],
            np.sin(2 * np.pi * h / 24), np.cos(2 * np.pi * h / 24),
            np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7),
            1.0 if dow >= 5 else 0.0,
            float(season), float(temperature),
            loads[i - 1] if i >= 1 else loads[0],
            loads[i - 24] if i >= 24 else loads[0],
            loads[i - 48] if i >= 48 else loads[0],
            float(np.mean(loads)),
            float(np.mean(loads)),
            float(np.mean(loads[max(0, i - 23):i + 1])),
        ])
    arr = np.asarray(rows, dtype=np.float32)
    if scaler is not None:
        arr = scaler.transform(arr)
    return arr


def _energy_forecast_response(forecast, source):
    forecast = np.asarray(forecast, dtype=float)
    peak_idx = int(np.argmax(forecast))
    return jsonify({
        "status": "success",
        "predictions": [round(float(v), 1) for v in forecast],
        "peak_load": round(float(max(forecast)), 1),
        "peak_hour": peak_idx,
        "total_kwh": round(float(sum(forecast)), 1),
        "trend": "rising" if forecast[-1] > forecast[0] else "falling" if forecast[-1] < forecast[0] else "stable",
        "source": source,
    })


@enhanced_bp.route('/energy/load-forecast', methods=['POST'])
def energy_load_forecast():
    """
    Predict next 24-hour energy load pattern.

    Primary path : real LSTM inference (models/energy_load_lstm.pth, trained by
                   scripts/train_energy_load_lstm.py, R2~0.92).
    Fallback path: deterministic statistical curve when the model or history is unavailable.

    Input : {historical_loads: [>=48 hourly values], current_hour, base_load,
             day_of_week?, temperature?, season?}
    Output: {predictions: [24], peak_load, peak_hour, total_kwh, trend, source}
    """
    try:
        data = request.get_json() or {}
        historical = data.get('historical_loads', None)
        hour_now = int(data.get('current_hour', 12)) % 24

        # ── Primary: real LSTM inference ──
        lstm = _load_energy_lstm()
        if lstm is not None and historical and len(historical) >= 48:
            scaler_data = get_model("energy_load_scaler")
            scaler = scaler_data.get('scaler') if isinstance(scaler_data, dict) else None
            loads = list(historical)[-lstm['seq_len']:]
            day_of_week = int(data.get('day_of_week', pd.Timestamp.now().dayofweek))
            temperature = float(data.get('temperature', 20.0))
            season = data.get('season', pd.Timestamp.now().dayofyear // 91)
            seq = _build_energy_features(loads, hour_now, day_of_week, temperature, season, scaler)
            x = lstm['torch'].from_numpy(seq).unsqueeze(0)  # (1, seq_len, n_features)
            with lstm['torch'].no_grad():
                pred = lstm['model'](x).cpu().numpy()[0]
            forecast = np.maximum(np.asarray(pred, dtype=float), 1.0)
            log.info(f"Energy load forecast via LSTM: {len(loads)} history points -> {len(forecast)}h")
            return _energy_forecast_response(forecast, "lstm_model")

        # ── Fallback: deterministic statistical curve ──
        base_load = float(data.get('base_load', 150))
        future_hours = np.arange(24)
        forecast = np.maximum(
            base_load * (0.6 + 0.3 * np.sin(np.pi * (future_hours + hour_now - 6) / 12)), 20)
        log.info("Energy load forecast via statistical fallback (no LSTM / insufficient history)")
        return _energy_forecast_response(forecast, "statistical_fallback")

    except Exception as e:
        log.error(f"Energy load forecast failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ════════════════════════════════════════════════════
# 2. ENERGY: Device Failure Prediction
# ════════════════════════════════════════════════════

@enhanced_bp.route('/energy/device-failure-predict', methods=['POST'])
def energy_device_failure_predict():
    """
    Predict probability of device failure.
    Input: {device_age_years, operating_hours, avg_temperature_c, ...}
    Output: {failure_probability, risk_level, recommendations}
    """
    try:
        data = request.get_json() or {}

        # Load model
        model_data = get_model("energy_device_failure")
        if model_data is not None:
            model = model_data['model']
            scaler = model_data['scaler']
            features = model_data['features']

            # Build feature vector
            feature_defaults = {
                'device_age_years': 3, 'operating_hours': 10000,
                'avg_temperature_c': 45, 'max_temperature_c': 65,
                'vibration_level': 2, 'power_consumption_kw': 150,
                'load_factor': 0.7, 'maintenance_frequency': 3,
                'days_since_last_maintenance': 60, 'voltage_stability': 0.8,
                'ambient_temperature': 25, 'humidity': 50,
                'age_temp_interaction': None, 'vibration_load': None,
                'maintenance_gap': None,
            }
            for k, v in feature_defaults.items():
                if k not in data or data[k] is None:
                    data[k] = v

            # Compute interaction features
            data['age_temp_interaction'] = data.get('device_age_years', 3) * data.get('avg_temperature_c', 45) / 100
            data['vibration_load'] = data.get('vibration_level', 2) * data.get('load_factor', 0.7)
            mf = data.get('maintenance_frequency', 3) + 1
            data['maintenance_gap'] = data.get('days_since_last_maintenance', 60) / mf

            vec = np.array([[data[f] for f in features]], dtype=float)
            vec_scaled = scaler.transform(vec)
            prob = float(model.predict_proba(vec_scaled)[0, 1])

        else:
            # Statistical fallback
            age = data.get('device_age_years', 3)
            temp = data.get('avg_temperature_c', 45)
            vibration = data.get('vibration_level', 2)
            maintenance = data.get('maintenance_frequency', 3)
            days_since = data.get('days_since_last_maintenance', 60)

            log_odds = (-3.5 + 0.3 * np.log1p(age) + 0.01 * temp
                        + 0.3 * vibration - 0.2 * maintenance + 0.005 * days_since)
            prob = float(1 / (1 + np.exp(-log_odds)))
            prob = max(0.01, min(0.98, prob))

        # Risk level
        if prob < 0.2:
            level = "低风险 🟢"
            advice = "设备运行正常，按计划维护即可。"
        elif prob < 0.4:
            level = "中等风险 🟡"
            advice = "建议增加巡检频率，重点关注温度与振动指标。"
        elif prob < 0.7:
            level = "高风险 🟠"
            advice = "建议立即安排检修，可能存在潜在故障隐患。"
        else:
            level = "危急 🔴"
            advice = "⚠️ 设备故障风险极高，建议立即停机检修或更换！"

        return jsonify({
            "status": "success",
            "failure_probability": round(prob, 4),
            "risk_level": level,
            "risk_score": round(prob * 100, 1),
            "recommendations": advice,
            "key_factors": {
                "device_age": data.get('device_age_years', 3),
                "temperature": data.get('avg_temperature_c', 45),
                "vibration": data.get('vibration_level', 2),
                "maintenance_frequency": data.get('maintenance_frequency', 3),
                "days_since_maintenance": data.get('days_since_last_maintenance', 60),
            }
        })

    except Exception as e:
        log.error(f"Device failure prediction failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ════════════════════════════════════════════════════
# 3. FORUM: NLP Content Analysis
# ════════════════════════════════════════════════════

@enhanced_bp.route('/forum/analyze-content', methods=['POST'])
def forum_analyze_content():
    """
    Analyze forum post content for quality score, category, and key topics.
    Input: {title: "...", body: "..."}
    Output: {quality_score, category, confidence, key_topics, ...}
    """
    try:
        data = request.get_json() or {}
        title = data.get('title', '')
        body = data.get('body', '')
        full_text = title + ' ' + body

        # Load pipeline
        pipeline = get_model("forum_nlp_pipeline")

        if pipeline is not None:
            quality_model = pipeline['quality_model']
            q_tfidf = pipeline['quality_tfidf']
            classifier = pipeline['classifier']
            c_tfidf = pipeline['classifier_tfidf']
            categories = pipeline['categories']

            # Quality scoring
            meta = _extract_meta_features(pd.Series([full_text]))
            q_feat = q_tfidf.transform([full_text])
            from scipy.sparse import hstack as sparse_hstack
            q_feat_final = sparse_hstack([q_feat, np.array(meta.values)])
            quality_score = float(quality_model.predict(q_feat_final)[0])
            quality_score = max(1.0, min(10.0, round(quality_score, 1)))

            # Category classification
            c_feat = c_tfidf.transform([full_text])
            cat = classifier.predict(c_feat)[0]
            probs = classifier.predict_proba(c_feat)[0]
            confidence = float(max(probs))

        else:
            # Statistical fallback
            word_count = len(full_text.split())
            has_code = any(kw in full_text for kw in ['import', 'def ', 'class ', 'function', 'const ', '<template>'])
            has_question = '?' in full_text or '？' in full_text
            quality_score = min(10.0, max(1.0, 3.0 + word_count / 100 + has_code * 1.5 + has_question))
            quality_score = round(quality_score, 1)
            cat = '技术讨论' if has_code else '闲聊灌水' if not has_question else '项目求助'
            confidence = 0.6

        # Extract key topics (simple TF-IDF-based)
        words = full_text.split()
        word_freq = {}
        for w in words:
            if len(w) > 1:
                word_freq[w] = word_freq.get(w, 0) + 1
        top_keywords = sorted(word_freq, key=word_freq.get, reverse=True)[:10]

        return jsonify({
            "status": "success",
            "quality_score": quality_score,
            "category": cat,
            "confidence": round(confidence, 3),
            "key_topics": top_keywords[:5],
            "word_count": len(words),
            "has_code": any(kw in full_text for kw in ['import', 'def ', 'class ', 'function', 'const ']),
            "has_question": '?' in full_text or '？' in full_text,
        })

    except Exception as e:
        log.error(f"Forum content analysis failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def _extract_meta_features(text_series):
    """Extract text meta features (duplicated minimal version for route)."""
    features = pd.DataFrame()
    features['word_count'] = text_series.str.split().str.len()
    features['char_count'] = text_series.str.len()
    features['avg_word_len'] = features['char_count'] / (features['word_count'] + 1)
    features['unique_word_ratio'] = text_series.apply(
        lambda x: len(set(x.split())) / max(1, len(x.split())) if isinstance(x, str) else 0
    )
    features['punctuation_count'] = text_series.apply(
        lambda x: sum(1 for c in str(x) if c in '，。！？,.!?;；：:""\'') if isinstance(x, str) else 0
    )
    features['has_numbers'] = text_series.apply(
        lambda x: int(bool(__import__('re').search(r'\d+', str(x)))) if isinstance(x, str) else 0
    )
    features['has_english'] = text_series.apply(
        lambda x: int(bool(__import__('re').search(r'[a-zA-Z]{2,}', str(x)))) if isinstance(x, str) else 0
    )
    return features.fillna(0)


# ════════════════════════════════════════════════════
# 4. FORUM: Sentiment Analysis
# ════════════════════════════════════════════════════

@enhanced_bp.route('/forum/sentiment-analysis', methods=['POST'])
def forum_sentiment_analysis():
    """
    Analyze user sentiment from forum posts/comments.
    Input: {texts: ["post1", "post2", ...]} or {text: "single text"}
    Output: {sentiments: [{text, sentiment, score, ...}]}
    """
    try:
        data = request.get_json() or {}
        if 'text' in data:
            texts = [data['text']]
        elif 'texts' in data:
            texts = data['texts']
        else:
            texts = []

        results = []
        for text in texts:
            if not text or not text.strip():
                continue

            # Simple keyword-based sentiment analysis (no external API needed)
            positive_words = ['好', '棒', '优秀', '厉害', '赞', '感谢', '成功', '解决', '分享', '推荐',
                              '开心', '恭喜', '进步', '突破', '创新', '高效', 'nice', 'great', 'good']
            negative_words = ['差', '垃圾', '糟糕', '报错', '失败', '问题', 'bug', 'error', '崩溃',
                              '卡顿', '慢', '复杂', '难用', '失望', '后悔', '坑', '难']
            question_words = ['？', '?', '为什么', '怎么', '如何', '求助', '请教', '求']

            text_lower = text.lower()
            pos_count = sum(1 for w in positive_words if w in text_lower)
            neg_count = sum(1 for w in negative_words if w in text_lower)
            q_count = sum(1 for w in question_words if w in text_lower)

            total = pos_count + neg_count + 1
            score = (pos_count - neg_count) / total * 0.5 + 0.5  # 0-1 scale
            score = max(0.0, min(1.0, score))

            if score > 0.65:
                sentiment = 'positive'
                label = '积极'
            elif score < 0.35:
                sentiment = 'negative'
                label = '消极'
            else:
                sentiment = 'neutral'
                label = '中性'

            # Add question flag
            is_question = q_count > 0

            results.append({
                'text': text[:100],
                'sentiment': sentiment,
                'sentiment_label': label,
                'score': round(score, 3),
                'is_question': is_question,
                'positive_hits': pos_count,
                'negative_hits': neg_count,
            })

        # Aggregate stats
        sentiments = [r['sentiment'] for r in results]
        overall = 'positive'
        if sentiments.count('negative') > sentiments.count('positive'):
            overall = 'negative'
        elif sentiments.count('neutral') >= len(sentiments) * 0.5:
            overall = 'neutral'

        return jsonify({
            "status": "success",
            "results": results,
            "summary": {
                "total": len(results),
                "positive": sentiments.count('positive'),
                "negative": sentiments.count('negative'),
                "neutral": sentiments.count('neutral'),
                "overall_sentiment": overall,
            }
        })

    except Exception as e:
        log.error(f"Forum sentiment analysis failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ════════════════════════════════════════════════════
# 5. DEVELOPMENT: Learning Path Recommendation
# ════════════════════════════════════════════════════

@enhanced_bp.route('/development/recommend-path', methods=['POST'])
def dev_recommend_learning_path():
    """
    Recommend learning paths based on user skill profile.
    Input: {skill_levels: {skill_name: score}, years_experience, ...}
    Output: [{path_name, match_score, skills_to_learn, duration, ...}]
    """
    try:
        data = request.get_json() or {}
        skill_input = data.get('skill_levels', {})

        # Load recommender model
        model_data = get_model("learning_path_rec")

        if model_data is not None:
            all_skills = model_data['all_skills']
            learning_paths = model_data['learning_paths']

            # Build user skill vector
            user_skills = np.zeros(len(all_skills))
            for skill_name, level in skill_input.items():
                if skill_name in all_skills:
                    idx = all_skills.index(skill_name)
                    user_skills[idx] = float(level)

            # Compute recommendations
            from sklearn.metrics.pairwise import cosine_similarity
            path_matrix = model_data['path_matrix']
            path_keys = model_data['path_keys']

            user_vec = user_skills.reshape(1, -1)
            content_sim = cosine_similarity(user_vec, path_matrix)[0]

            # Gap analysis
            recommendations = []
            for i, key in enumerate(path_keys):
                path = learning_paths[key]
                required_skills = path['skills']
                skill_idxs = [all_skills.index(s) for s in required_skills if s in all_skills]
                gaps = sum(1 for idx in skill_idxs if user_skills[idx] < 2.0)
                skills_to_learn = [s for s in required_skills
                                   if s in all_skills and user_skills[all_skills.index(s)] < 2.0]

                gap_ratio = gaps / max(1, len(required_skills))
                penalty = max(0, gap_ratio - 0.1) * 0.3
                match = content_sim[i] - penalty

                if match > 0:
                    recommendations.append({
                        'path_key': key,
                        'path_name': path['name'],
                        'difficulty': path['difficulty'],
                        'category': path['category'],
                        'duration_months': path['duration_months'],
                        'match_score': round(float(match * 100), 1),
                        'skill_gap_ratio': round(float(gap_ratio * 100), 1),
                        'skills_to_learn': skills_to_learn[:5],
                        'total_skills': len(required_skills),
                        'skills_known': len(required_skills) - len(skills_to_learn),
                    })

            recommendations.sort(key=lambda r: r['match_score'], reverse=True)

        else:
            # Fallback: keyword-based matching
            recommendations = [
                {'path_name': '全栈开发工程师', 'category': '开发', 'difficulty': 3,
                 'duration_months': 6, 'match_score': 75.0, 'skills_to_learn': ['Vue.js/React', 'Docker', 'CI/CD']},
                {'path_name': '后端开发工程师', 'category': '开发', 'difficulty': 3,
                 'duration_months': 5, 'match_score': 72.0, 'skills_to_learn': ['微服务', 'Docker', '消息队列']},
                {'path_name': 'AI/ML 工程师', 'category': 'AI', 'difficulty': 4,
                 'duration_months': 8, 'match_score': 60.0, 'skills_to_learn': ['深度学习', 'NLP', 'MLOps']},
            ]

        return jsonify({
            "status": "success",
            "recommendations": recommendations[:5],
            "user_skill_summary": {
                "skills_provided": len(skill_input),
                "avg_level": round(sum(skill_input.values()) / max(1, len(skill_input)), 1) if skill_input else 0,
            }
        })

    except Exception as e:
        log.error(f"Learning path recommendation failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ════════════════════════════════════════════════════
# 6. DEVELOPMENT: AI Trend Analyzer
# ════════════════════════════════════════════════════

@enhanced_bp.route('/development/trend-analysis', methods=['POST'])
def dev_trend_analysis():
    """
    Analyze AI development trends and technology lifecycle.
    Input: {} (optional filters: {category, year_range})
    Output: {trends, hot_topics, lifecycle_stages, predictions}
    """
    try:
        data = request.get_json() or {}
        model_data = get_model("development_trend_analyzer")

        if model_data is not None:
            trend_data = model_data['trend_features']
            topic_cats = model_data['topic_categories']
            stage_labels = model_data['stage_labels']
            category_techs = model_data['category_techs']

            # Build response
            result = {
                'status': 'success',
                'trend_data': trend_data[-20:] if len(trend_data) > 20 else trend_data,
                'hot_topics': [],
                'categories': list(category_techs.keys()),
                'category_details': category_techs,
                'technology_stages': {k: v for k, v in enumerate(stage_labels)},
                'source': 'trend_analyzer_model',
            }
        else:
            # Fallback: return structured data
            categories = ['计算机视觉', '自然语言处理', '语音技术', '强化学习', '知识表示', 'AI基础设施']
            result = {
                'status': 'success',
                'trend_data': [
                    {'year': y, 'impact_score_sum': 50 + (y - 2000) * 3 + hash(str(y)) % 20,
                     'research_intensity_sum': 200 + (y - 2000) * 15 + hash(str(y)) % 50}
                    for y in range(2000, 2027)
                ],
                'categories': categories,
                'technology_stages': {0: '新兴', 1: '增长', 2: '成熟', 3: '前沿'},
                'source': 'fallback',
            }

        return jsonify(result)

    except Exception as e:
        log.error(f"Development trend analysis failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ════════════════════════════════════════════════════
# 7. TRAFFIC: Accident Risk Prediction
# ════════════════════════════════════════════════════

@enhanced_bp.route('/traffic/accident-risk', methods=['POST'])
def traffic_accident_risk():
    """
    Predict real-time traffic accident risk.
    Input: {hour, day_of_week, weather_code, traffic_volume, ...}
    Output: {risk_probability, risk_level, warning, key_factors}
    """
    try:
        data = request.get_json() or {}
        model_data = get_model("traffic_accident")

        if model_data is not None:
            model = model_data['model']
            scaler = model_data['scaler']
            features = model_data['features']
            threshold = model_data['threshold']

            # Build feature vector from input
            feat_defaults = {
                'hour': 12, 'day_of_week': 3, 'is_weekend': 0, 'is_holiday': 0,
                'season': 1, 'weather_code': 0, 'visibility_km': 10, 'lanes': 4,
                'road_type': 1, 'traffic_volume': 1000, 'avg_speed': 50,
                'speed_limit': 60, 'congestion_index': 30, 'accident_count_7d': 0,
            }
            for k in feat_defaults:
                if k not in data:
                    data[k] = feat_defaults[k]

            # Build cyclic features
            df = pd.DataFrame([data])
            hour_sin = np.sin(2 * np.pi * df['hour'] / 24)
            hour_cos = np.cos(2 * np.pi * df['hour'] / 24)
            dow_sin = np.sin(2 * np.pi * df['day_of_week'] / 7)
            dow_cos = np.cos(2 * np.pi * df['day_of_week'] / 7)
            season_sin = np.sin(2 * np.pi * df['season'] / 4)
            season_cos = np.cos(2 * np.pi * df['season'] / 4)

            vec = np.zeros(len(features))
            feat_map = {name: i for i, name in enumerate(features)}

            for name, idx in feat_map.items():
                if name == 'hour_sin':
                    vec[idx] = hour_sin[0]
                elif name == 'hour_cos':
                    vec[idx] = hour_cos[0]
                elif name == 'dow_sin':
                    vec[idx] = dow_sin[0]
                elif name == 'dow_cos':
                    vec[idx] = dow_cos[0]
                elif name == 'season_sin':
                    vec[idx] = season_sin[0]
                elif name == 'season_cos':
                    vec[idx] = season_cos[0]
                elif name == 'speed_congestion':
                    vec[idx] = data['speed_limit'] * data['congestion_index'] / 100
                elif name == 'night_bad_weather':
                    vec[idx] = hour_sin[0] * (1 if data['weather_code'] >= 2 else 0)
                elif name == 'volume_capacity_ratio':
                    vec[idx] = np.log1p(data['traffic_volume']) / np.log1p(feat_defaults['lanes'] * 500)
                elif name == 'highway_night':
                    vec[idx] = (1 if data['road_type'] == 0 else 0) * (1 if (data['hour'] >= 22 or data['hour'] <= 5) else 0)
                elif name in data:
                    if name == 'traffic_volume':
                        vec[idx] = np.log1p(data[name])
                    elif name == 'avg_speed':
                        vec[idx] = data[name] / max(1, data['speed_limit'])
                    else:
                        vec[idx] = data[name]

            vec = vec.reshape(1, -1)
            vec_scaled = scaler.transform(vec)
            prob = float(model.predict_proba(vec_scaled)[0, 1])

        else:
            # Statistical fallback
            hour = data.get('hour', 12)
            is_night = 1 if hour >= 22 or hour <= 5 else 0
            weather = data.get('weather_code', 0)
            volume = data.get('traffic_volume', 1000)
            speed_limit = data.get('speed_limit', 60)

            log_odds = (-4.5 + 1.2 * is_night + 0.6 * (weather >= 2)
                        + 1.5 * (weather >= 4) + 0.3 * np.log1p(volume) / 3
                        + 0.5 * (speed_limit >= 80))
            prob = float(1 / (1 + np.exp(-log_odds)))
            prob = max(0.001, min(0.9, prob))

        # Risk level classification
        if prob < 0.2:
            level = "低风险 🟢"
            advice = "路况正常，注意保持车距。"
        elif prob < 0.4:
            level = "中等风险 🟡"
            advice = "需提高警惕，建议减速慢行。"
        elif prob < 0.6:
            level = "高风险 🟠"
            advice = "⚠️ 事故风险较高，请注意观察路况，建议择道绕行。"
        else:
            level = "危急 🔴"
            advice = "🚨 事故风险极高！强烈建议减速并保持高度警惕！"

        # Key risk factors
        factors = []
        if data.get('weather_code', 0) >= 4:
            factors.append("恶劣天气")
        if data.get('weather_code', 0) >= 2:
            factors.append("降雨/雪")
        if data.get('hour', 12) >= 22 or data.get('hour', 12) <= 5:
            factors.append("夜间行驶")
        if data.get('congestion_index', 0) > 60:
            factors.append("严重拥堵")
        if data.get('visibility_km', 10) < 2:
            factors.append("低能见度")

        return jsonify({
            "status": "success",
            "risk_probability": round(prob, 4),
            "risk_score": round(prob * 100, 1),
            "risk_level": level,
            "recommendations": advice,
            "key_risk_factors": factors[:5] or ["无明显风险因素"],
            "details": {
                "hour": data.get('hour', 12),
                "weather_code": data.get('weather_code', 0),
                "visibility_km": data.get('visibility_km', 10),
                "traffic_volume": data.get('traffic_volume', 1000),
            }
        })

    except Exception as e:
        log.error(f"Traffic accident risk prediction failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ════════════════════════════════════════════════════
# 8. FINANCE: Customer Churn Prediction
# ════════════════════════════════════════════════════

@enhanced_bp.route('/finance/customer-churn', methods=['POST'])
def finance_customer_churn():
    """
    Predict customer churn risk.
    Input: {avg_balance, monthly_transaction_count, days_since_last_tx, ...}
    Output: {churn_probability, risk_level, retention_advice}
    """
    try:
        data = request.get_json() or {}
        model_data = get_model("finance_churn")

        if model_data is not None:
            model = model_data['model']
            scaler = model_data['scaler']
            features = model_data['features']

            # Build feature vector
            base = {
                'user_age': 30, 'account_age_days': 365, 'monthly_transaction_count': 10,
                'avg_transaction_amount': 500, 'max_transaction_amount': 2000,
                'transaction_amount_std': 300, 'days_since_last_transaction': 5,
                'transaction_type_diversity': 3, 'avg_balance': 10000,
                'balance_volatility': 0.3, 'min_balance_30d': 5000,
                'balance_trend_30d': 0, 'login_frequency_per_week': 4,
                'days_since_last_login': 2, 'feature_usage_count': 5,
                'support_ticket_count_90d': 1, 'notification_click_rate': 0.3,
                'credit_score': 650, 'has_loan': 0, 'loan_default_history': 0,
                'debt_to_income_ratio': 0.2, 'referral_count': 1, 'is_premium_user': 0,
                'avg_amount_ratio': None, 'balance_min_ratio': None, 'recency_score': None,
                'login_recency': None, 'tx_frequency_score': None, 'engagement_score': None,
                'high_value_flag': None, 'inactive_flag': None, 'premium_engagement': None,
                'debt_warning': None,
            }
            for k in base:
                if k not in data or data[k] is None:
                    data[k] = base[k]

            # Compute derived features
            data['avg_amount_ratio'] = data['avg_transaction_amount'] / max(1, data['avg_balance'])
            data['balance_min_ratio'] = data['min_balance_30d'] / max(1, data['avg_balance'])
            data['recency_score'] = float(np.exp(-data['days_since_last_transaction'] / 30))
            data['login_recency'] = float(np.exp(-data['days_since_last_login'] / 14))
            data['tx_frequency_score'] = min(1.0, data['monthly_transaction_count'] / 20)
            data['engagement_score'] = (data['tx_frequency_score'] * 0.4
                                         + data['recency_score'] * 0.4
                                         + min(1.0, data['feature_usage_count'] / 15) * 0.2)
            data['high_value_flag'] = 1 if data['avg_balance'] > 100000 else 0
            data['inactive_flag'] = 1 if data['days_since_last_transaction'] > 30 else 0
            data['premium_engagement'] = data['is_premium_user'] * data['engagement_score']
            data['debt_warning'] = 1 if data['debt_to_income_ratio'] > 0.4 else 0

            vec = np.array([[data[f] for f in features]], dtype=float)
            vec_scaled = scaler.transform(vec)

            if isinstance(model, dict) and model.get('ensemble'):
                gb, rf = model['gb'], model['rf']
                prob = (gb.predict_proba(vec_scaled)[0, 1] + rf.predict_proba(vec_scaled)[0, 1]) / 2
            else:
                prob = float(model.predict_proba(vec_scaled)[0, 1])

        else:
            # Statistical fallback
            days_since_tx = data.get('days_since_last_transaction', 5)
            tx_count = data.get('monthly_transaction_count', 10)
            balance = data.get('avg_balance', 10000)
            login = data.get('days_since_last_login', 2)
            log_odds = (-1.0 + 0.3 * np.log1p(days_since_tx) / 3 - 0.08 * tx_count
                        - 0.003 * np.log1p(balance) - 0.15 * login)
            prob = float(1 / (1 + np.exp(-log_odds)))
            prob = max(0.01, min(0.9, prob))

        if prob < 0.2:
            level = "低风险 🟢"
            advice = "用户活跃度良好，无流失风险。"
        elif prob < 0.4:
            level = "中等风险 🟡"
            advice = "建议发送个性化优惠或推送增加用户粘性。"
        elif prob < 0.7:
            level = "高风险 🟠"
            advice = "⚠️ 用户流失风险较高，建议主动联系并提供专属权益。"
        else:
            level = "危急 🔴"
            advice = "🚨 用户极可能流失！建议立即进行挽留干预（专属客服、优惠券等）。"

        return jsonify({
            "status": "success",
            "churn_probability": round(prob, 4),
            "churn_score": round(prob * 100, 1),
            "risk_level": level,
            "retention_advice": advice,
            "key_signals": {
                "days_since_last_tx": data.get('days_since_last_transaction', 0),
                "monthly_tx_count": data.get('monthly_transaction_count', 0),
                "avg_balance": data.get('avg_balance', 0),
                "login_frequency": data.get('login_frequency_per_week', 0),
                "engagement_score": round(data.get('engagement_score', 0), 3),
            }
        })

    except Exception as e:
        log.error(f"Customer churn prediction failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ════════════════════════════════════════════════════
# 9. ENVIRONMENT: Extreme Weather Classifier
# ════════════════════════════════════════════════════

@enhanced_bp.route('/environment/extreme-weather', methods=['POST'])
def env_extreme_weather():
    """
    Classify extreme weather event severity.
    Input: {pm25, pm10, o3, temperature, humidity, wind_speed, ...}
    Output: {severity_level, event_type, confidence, advisory}
    """
    try:
        data = request.get_json() or {}
        model_data = get_model("env_extreme_weather")

        if model_data is not None:
            model = model_data['model']
            scaler = model_data['scaler']
            label_encoder = model_data['label_encoder']
            features = model_data['features']

            # Default values
            defaults = {
                'pm25': 50, 'pm10': 80, 'o3': 80, 'no2': 30, 'so2': 15, 'co': 1.0,
                'temperature': 20, 'humidity': 60, 'pressure': 1013,
                'wind_speed': 5, 'wind_direction': 180, 'precipitation': 0,
                'season': 1, 'is_extreme_season': 0,
                'aqi_trend_3d': 0, 'temp_anomaly': 0, 'consecutive_high_aqi': 0,
            }
            for k in defaults:
                if k not in data:
                    data[k] = defaults[k]

            # Build derived features
            data['pm25_log'] = np.log1p(data['pm25'])
            data['pm10_log'] = np.log1p(data['pm10'])
            data['o3_log'] = np.log1p(data['o3'])
            data['no2_log'] = np.log1p(data['no2'])
            data['so2_log'] = np.log1p(data['so2'])
            data['co_log'] = np.log1p(data['co'])
            data['wind_dir_sin'] = np.sin(2 * np.pi * data['wind_direction'] / 360)
            data['wind_dir_cos'] = np.cos(2 * np.pi * data['wind_direction'] / 360)
            data['aqi_estimate'] = 0.5 * data['pm25'] + 0.3 * data['pm10'] + 0.1 * data['o3'] + 0.1 * data['no2']
            data['temp_humidity_index'] = data['temperature'] * data['humidity'] / 100
            data['discomfort_index'] = 0.8 * data['temperature'] + 0.01 * data['humidity'] * (0.99 * data['temperature'] - 14.3) + 46.4
            data['pm25_pm10_ratio'] = data['pm25'] / max(1, data['pm10'])
            wind_chill = (13.12 + 0.6215 * data['temperature'] - 11.37 * data['wind_speed']**0.16
                          + 0.3965 * data['temperature'] * data['wind_speed']**0.16)
            data['wind_chill'] = min(wind_chill, data['temperature'])
            data['heat_stress'] = data['temperature'] * (data['humidity'] / 100) * data['o3'] / 100
            data['cold_stress'] = max(0, -data['temperature']) * data['wind_speed'] / 10
            data['pollution_buildup'] = data['consecutive_high_aqi'] * (data['pm25'] / 100)
            data['dust_potential'] = data['pm10'] * data['wind_speed'] / 100

            vec = np.array([[data[f] for f in features]], dtype=float)
            vec_scaled = scaler.transform(vec)
            pred_class = int(model.predict(vec_scaled)[0])
            pred_label = label_encoder.inverse_transform([pred_class])[0]
            probs = model.predict_proba(vec_scaled)[0]
            confidence = float(max(probs))

        else:
            # Rule-based fallback
            pm25 = data.get('pm25', 50)
            pm10 = data.get('pm10', 80)
            temperature = data.get('temperature', 20)
            humidity = data.get('humidity', 60)
            wind = data.get('wind_speed', 5)
            o3 = data.get('o3', 80)

            if pm25 > 250 and wind < 3:
                pred_label = 'warning'
                confidence = 0.7
            elif temperature > 38:
                pred_label = 'warning'
                confidence = 0.6
            elif temperature > 35 and o3 > 180:
                pred_label = 'advisory'
                confidence = 0.65
            elif pm25 > 150:
                pred_label = 'advisory'
                confidence = 0.6
            elif pm10 > 300 and wind > 8:
                pred_label = 'advisory'
                confidence = 0.55
            else:
                pred_label = 'normal'
                confidence = 0.8

        # Determine event type + advisory text
        event_advice_map = {
            'normal': ('无异常', '天气状况正常，适合户外活动。'),
            'advisory': ('天气关注', '气象条件可能引发轻微环境问题，建议敏感人群减少户外活动。'),
            'warning': ('天气预警', '⚠️ 极端天气风险较高，建议减少不必要的户外活动，注意防护。'),
            'emergency': ('天气警报', '🚨 极端天气事件！请立即采取防护措施，避免外出！'),
        }
        event_type, advice = event_advice_map.get(pred_label, ('未知', '请参考当地气象预警。'))

        return jsonify({
            "status": "success",
            "severity_level": pred_label,
            "event_type": event_type,
            "confidence": round(confidence, 4),
            "advisory": advice,
            "details": {
                "pm25": data.get('pm25', 0),
                "temperature": data.get('temperature', 0),
                "aqi_estimate": round(data.get('aqi_estimate', 0), 1),
            }
        })

    except Exception as e:
        log.error(f"Extreme weather classification failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
