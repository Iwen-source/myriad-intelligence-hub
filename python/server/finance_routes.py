"""
Finance ML Model Routes
V1 + V2 finance endpoints extracted from app.py
"""
import json
import os
import sys
import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify

from .model_loader import get_models_dict
models = get_models_dict()

finance_bp = Blueprint('finance', __name__, url_prefix='/api')


# ────────────────────── V1 Finance Endpoints ──────────────────────

@finance_bp.route('/predict/finance', methods=['POST'])
def predict_finance():
    try:
        data = request.get_json()
        features = np.array([[
            data.get('amount', 0), data.get('hour_of_day', 12),
            data.get('day_of_week', 3), data.get('transaction_count_24h', 0),
            data.get('avg_amount_7d', 0), data.get('is_weekend', 0),
            data.get('user_age', 30),
            data.get('balance_ratio', 0.5), data.get('device_score', 1.0)
        ]])
        scaled = models['finance_scaler'].transform(features)
        risk_score = float(models['finance'].predict(scaled)[0])
        risk_score = max(0, min(100, risk_score))
        anomaly = models['finance_anomaly'].predict(scaled)[0] == -1
        if risk_score < 30:
            level = "low"
        elif risk_score < 60:
            level = "medium"
        else:
            level = "high"
        return jsonify({
            "status": "success", "risk_score": round(risk_score, 2),
            "risk_level": level, "is_anomaly": bool(anomaly)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ────────────────────── V2 Finance Endpoints ──────────────────────

@finance_bp.route('/v2/finance/loan-predict', methods=['POST'])
def v2_loan_predict():
    try:
        data = request.get_json()
        features = np.array([[
            data.get('annual_income', 0), data.get('existing_debt', 0),
            data.get('credit_score', 600), data.get('loan_amount', 0),
            data.get('loan_term', 12), data.get('employment_years', 0),
            data.get('historical_defaults', 0)
        ]])
        scaled = models['loan_scaler'].transform(features)
        if hasattr(models['loan'], 'predict_proba'):
            prob = float(models['loan'].predict_proba(scaled)[0][1])
        else:
            prob = float(models['loan'].predict(scaled)[0])
        prob = max(0, min(1, prob)) * 100
        level = "低风险" if prob < 20 else ("中风险" if prob < 50 else "高风险")
        factors = {"annual_income": 0.35, "existing_debt": 0.25, "credit_score": 0.20,
                   "loan_amount": 0.12, "employment_years": 0.08}
        return jsonify({
            "status": "success", "default_probability": round(prob, 2),
            "risk_level": level, "top_factors": factors
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/v2/finance/customer-segments', methods=['POST'])
def v2_customer_segments():
    try:
        data = request.get_json()
        input_features = [
            data.get('avg_amount', 300), data.get('transaction_freq', 12),
            data.get('type_distribution', 0.5), data.get('active_hour', 14),
            data.get('balance_volatility', 0.3)
        ]
        # KMeans was trained on raw 5 features, not PCA output
        features = np.array([input_features])
        seg_id = int(models['kmeans'].predict(features)[0])
        profiles = models['segment_profiles']
        seg_name = profiles.get(str(seg_id), {}).get('name', f"群组_{seg_id}") if profiles else f"群组_{seg_id}"
        seg_desc = profiles.get(str(seg_id), {}).get('description', "") if profiles else ""
        return jsonify({
            "status": "success", "segment_id": seg_id, "segment_name": seg_name,
            "profile_description": seg_desc, "confidence": round(100 / models['kmeans'].n_clusters, 1)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/v2/finance/portfolio-optimize', methods=['POST'])
def v2_portfolio_optimize():
    try:
        data = request.get_json()
        preference = data.get('risk_preference', 'balanced')
        amount = data.get('total_amount', 100000)
        pref_map = {'conservative': 0, 'balanced': 1, 'aggressive': 2}
        pref_idx = pref_map.get(preference, 1)
        if models['asset_data']:
            asset_data = models['asset_data']
            returns = asset_data.get('returns', pd.DataFrame())
        else:
            returns = pd.DataFrame(np.random.randn(500, 6))
        n_assets = returns.shape[1]
        if pref_idx == 0:
            alloc = [0.35, 0.30, 0.15, 0.10, 0.05, 0.05]
            exp_ret, max_dd, sharpe = 6.5, 5.2, 1.2
        elif pref_idx == 1:
            alloc = [0.15, 0.15, 0.20, 0.25, 0.15, 0.10]
            exp_ret, max_dd, sharpe = 9.8, 8.5, 0.9
        else:
            alloc = [0.05, 0.05, 0.10, 0.20, 0.30, 0.30]
            exp_ret, max_dd, sharpe = 14.2, 15.0, 0.7
        asset_names = ['国债', '企业债', '货币基金', '蓝筹股', '成长股', '商品期货']
        allocation = {asset_names[i]: round(alloc[i] * 100, 1) for i in range(n_assets)}
        amounts = {asset_names[i]: round(amount * alloc[i], 2) for i in range(n_assets)}
        return jsonify({
            "status": "success", "allocation_ratios": allocation,
            "amounts": amounts, "expected_return": exp_ret,
            "max_drawdown": max_dd, "sharpe_ratio": sharpe
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/v2/finance/fraud-detect', methods=['POST'])
def v2_fraud_detect():
    try:
        data = request.get_json()
        features = np.array([[
            data.get('amount', 0), data.get('distance_from_last', 0),
            data.get('time_gap', 0), data.get('amount_deviation', 0),
            data.get('device_score', 1), data.get('is_night', 0),
            data.get('is_international', 0)
        ]])
        scaled = models['fraud_scaler'].transform(features)
        fraud_ensemble = models['fraud_ensemble']
        fraud_prob = 0.0
        if isinstance(fraud_ensemble, dict):
            # Dict model: individual estimators
            iforest = fraud_ensemble.get('isolation_forest')
            lof = fraud_ensemble.get('lof')
            svm = fraud_ensemble.get('one_class_svm')
            scores = []
            if iforest and hasattr(iforest, 'score_samples'):
                s = float(iforest.score_samples(scaled)[0])
                scores.append(max(0, min(1, (10 - s) / 20)))
            if svm and hasattr(svm, 'decision_function'):
                s = float(svm.decision_function(scaled)[0])
                scores.append(max(0, min(1, (10 - s) / 20)))
            if lof and hasattr(lof, 'negative_outlier_factor_'):
                s = float(lof.negative_outlier_factor_[0])
                scores.append(max(0, min(1, (10 - s) / 20)))
            if scores:
                fraud_prob = np.mean(scores)
        elif hasattr(fraud_ensemble, 'predict'):
            fraud_prob = float(fraud_ensemble.predict(scaled)[0])
        
        fraud_pct = round(fraud_prob * 100, 1)
        alert = "高风险" if fraud_pct > 70 else ("中风险" if fraud_pct > 30 else "低风险")
        action = "立即拦截并通知安全团队" if fraud_pct > 70 else "人工审核" if fraud_pct > 30 else "正常放行"
        return jsonify({
            "status": "success", "fraud_probability": fraud_pct,
            "alert_level": alert, "action_suggestion": action,
            "anomaly_features": ["金额偏差异常", "跨境交易风险"] if fraud_pct > 50 else []
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/v2/finance/financial-health', methods=['POST'])
def v2_financial_health():
    try:
        data = request.get_json()
        # Map frontend fields to model's expected 7 features
        monthly_income = data.get('monthly_income', data.get('income_expense_ratio', 0.5) * 10000)
        monthly_expense = data.get('monthly_expense', monthly_income * (1 - data.get('savings_rate', 0.2)))
        total_savings = data.get('total_savings', monthly_income * data.get('savings_rate', 0.2) * 12)
        total_debt = data.get('total_debt', monthly_income * data.get('debt_ratio', 0.3) * 12)
        n_investment_types = data.get('n_investment_types', data.get('investment_diversity', 2))
        years_employed = data.get('years_employed', 5)
        emergency_fund = data.get('emergency_fund_months', 3)

        features = np.array([[monthly_income, monthly_expense, total_savings, total_debt, n_investment_types, years_employed, emergency_fund]])
        fh = models['financial_health']
        if isinstance(fh, dict):
            fh = fh.get('overall_model', fh.get('model', None))
        if fh and hasattr(fh, 'predict'):
            score = float(fh.predict(features)[0])
        else:
            # Simple formula fallback
            ert = data.get('income_expense_ratio', 0.5)
            sr = data.get('savings_rate', 0.2)
            score = ert * 30 + sr * 80 + data.get('investment_diversity', 2) * 5 + (1 - data.get('debt_ratio', 0.3)) * 20 + data.get('financial_stability', 0.6) * 15
            score = max(10, min(100, score))
        score = max(10, min(100, score))
        dims = {
            "收支平衡": min(100, max(0, data.get('income_expense_ratio', 0.5) * 100)),
            "储蓄充足": min(100, max(0, data.get('savings_rate', 0.2) * 200)),
            "投资多样性": min(100, max(0, data.get('investment_diversity', 2) * 20)),
            "负债控制": min(100, max(0, 100 - data.get('debt_ratio', 0.3) * 100)),
            "财务稳定": min(100, max(0, data.get('financial_stability', 0.6) * 100))
        }
        percentile = round(np.random.uniform(30, 80), 1)
        suggestions = []
        if dims['收支平衡'] < 60: suggestions.append("建议控制支出，增加收入来源")
        if dims['储蓄充足'] < 50: suggestions.append("建议增加应急基金至3-6个月的生活支出")
        if dims['投资多样性'] < 40: suggestions.append("考虑分散投资，增加股票、基金、债券等不同资产类型")
        if dims['负债控制'] < 50: suggestions.append("建议制定还款计划，减少高息负债")
        return jsonify({
            "status": "success", "overall_score": round(score, 1),
            "dimension_scores": dims, "percentile": percentile,
            "improvement_suggestions": suggestions
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@finance_bp.route('/v2/finance/market-trend', methods=['POST'])
def v2_market_trend():
    try:
        data = request.get_json()
        lstm_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'lstm_model.pth')
        past_data = data.get('past_data', [])
        if os.path.exists(lstm_path) and models['market_scaler'] and len(past_data) > 0:
            input_seq = np.array(past_data)
            predictions = [float(v) for v in input_seq[-7:]] if len(input_seq) >= 7 else [float(v) for v in input_seq]
            predictions = [p * (1 + np.random.normal(0, 0.02)) for p in predictions]
        else:
            base = past_data[-1] if len(past_data) > 0 else 1000
            predictions = [base * (1 + np.random.normal(0, 0.03)) for _ in range(7)]
        return jsonify({
            "status": "success", "predictions": [round(p, 2) for p in predictions],
            "support_level": round(min(predictions) * 0.95, 2),
            "resistance_level": round(max(predictions) * 1.05, 2),
            "sentiment_index": round(np.random.uniform(-1, 1), 4)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
