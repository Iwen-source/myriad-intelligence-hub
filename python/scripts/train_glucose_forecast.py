"""
Glucose Time-Series Forecast — 用 9 位患者真实 CGM 数据训练
滑动窗口 + XGBoost 预测未来血糖
生成: glucose_forecast_model.joblib, glucose_forecast_scaler.joblib, glucose_forecast_info.joblib
"""

import numpy as np
import pandas as pd
import joblib
import os
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

warnings.filterwarnings('ignore')

DATA_DIR = r'D:\东软实习\相关性分析_胰岛素_血糖'
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED = 42
np.random.seed(SEED)

# ── 滑动窗口参数 ──
# 使用过去 12 个点（≈1小时 CGM 数据）预测未来
LOOKBACK = 12
# 预测未来几点的血糖：6步≈30分钟，12步≈60分钟
FORWARD_STEPS = [6, 12]
GLUCOSE_FILES = [f'glucose_{i:02d}.csv' for i in range(1, 10)]


def load_all_cgm():
    """加载所有患者的 CGM 数据"""
    all_data = []
    stats = []

    for fname in GLUCOSE_FILES:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  跳过: {fname} (文件不存在)")
            continue

        df = pd.read_csv(fpath, parse_dates=[[0, 1]])
        df.rename(columns={df.columns[0]: 'datetime', 'glucose': 'glucose'}, inplace=True)
        df.sort_values('datetime', inplace=True)
        df['glucose'] = pd.to_numeric(df['glucose'], errors='coerce')
        df.dropna(subset=['glucose'], inplace=True)

        # 血糖单位转换为 mmol/L 标准
        # 正常范围: 3.9-6.1 mmol/L, 糖尿病: >7.0 mmol/L
        g = df['glucose'].values
        pid = fname.replace('glucose_', '').replace('.csv', '')

        stats.append({
            'patient': pid, 'count': len(g),
            'min': g.min(), 'max': g.max(), 'mean': g.mean(), 'std': g.std()
        })
        all_data.append(g)

        print(f"  {fname}: {len(g)} 条, 均值={g.mean():.2f}, 范围=[{g.min():.1f}, {g.max():.1f}]")

    print(f"\n总计: {sum(s['count'] for s in stats)} 条 CGM 记录")
    print(f"患者数: {len(all_data)}")
    return all_data, stats


def create_sliding_windows(data_list, lookback=12, forward_steps=None):
    """为所有患者创建滑动窗口特征"""
    if forward_steps is None:
        forward_steps = [6, 12]

    X_all, y_dict = [], {f'step_{s}': [] for s in forward_steps}
    patients_info = []

    for pid_idx, series in enumerate(data_list):
        n = len(series)
        if n < lookback + max(forward_steps):
            continue

        for i in range(lookback, n - max(forward_steps)):
            window = series[i - lookback:i]
            X_all.append(window)

            for step in forward_steps:
                target = series[i + step - 1]
                y_dict[f'step_{step}'].append(target)

        patients_info.append({
            'patient_id': pid_idx,
            'samples': n - lookback - max(forward_steps) + 1,
        })

    X = np.array(X_all)
    y_30min = np.array(y_dict['step_6'])   # ~30分钟
    y_60min = np.array(y_dict['step_12'])  # ~60分钟

    print(f"\n滑动窗口数据集:")
    print(f"  特征: 过去 {lookback} 个血糖读数")
    print(f"  样本数: {len(X)}")
    print(f"  预测15分钟 (step_3): 目标均值={y_30min.mean():.2f}")
    print(f"  预测60分钟 (step_12): 目标均值={y_60min.mean():.2f}")

    return X, y_30min, y_60min


def train_glucose_model(X, y, step_name):
    """训练单个时间步的预测模型"""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = XGBRegressor(
        n_estimators=200, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        random_state=SEED
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\n  {step_name}:")
    print(f"    MAE  = {mae:.4f} mmol/L")
    print(f"    RMSE = {rmse:.4f} mmol/L")
    print(f"    R2   = {r2:.4f}")

    # 葡萄糖水平分类评估
    # 低血糖: <3.9, 正常: 3.9-6.1, 高血糖: 6.1-7.0, 糖尿病: >7.0
    y_test_mmol = y_test
    y_pred_mmol = y_pred
    within_one = np.mean(np.abs(y_pred_mmol - y_test_mmol) < 1.0)
    within_half = np.mean(np.abs(y_pred_mmol - y_test_mmol) < 0.5)
    print(f"    误差<1.0 mmol/L: {within_one:.1%}")
    print(f"    误差<0.5 mmol/L: {within_half:.1%}")

    return model, scaler


def main():
    print("=" * 60)
    print("血糖时序预测模型训练 (真实 CGM 数据)")
    print("=" * 60)

    # 加载数据
    data_list, stats = load_all_cgm()

    # 创建滑动窗口
    X, y_30min, y_60min = create_sliding_windows(
        data_list, lookback=LOOKBACK, forward_steps=FORWARD_STEPS
    )

    # 训练模型
    print(f"\n{'=' * 60}")
    print(f"训练 30分钟血糖预测模型 (step_6)")
    print(f"{'=' * 60}")
    model_30min, scaler_30min = train_glucose_model(X, y_30min, "30分钟预测")

    print(f"\n{'=' * 60}")
    print(f"训练 60分钟血糖预测模型 (step_12)")
    print(f"{'=' * 60}")
    model_60min, scaler_60min = train_glucose_model(X, y_60min, "60分钟预测")

    # 保存模型
    model_path = os.path.join(OUT_DIR, 'glucose_forecast_model.joblib')
    scaler_path = os.path.join(OUT_DIR, 'glucose_forecast_scaler.joblib')
    info_path = os.path.join(OUT_DIR, 'glucose_forecast_info.joblib')

    joblib.dump({
        'model_30min': model_30min,
        'model_60min': model_60min,
    }, model_path)

    joblib.dump({
        'scaler_30min': scaler_30min,
        'scaler_60min': scaler_60min,
    }, scaler_path)

    info = {
        'lookback': LOOKBACK,
        'forward_steps': FORWARD_STEPS,
        'total_samples': len(X),
        'patients': len(data_list),
        'patient_stats': stats,
    }
    joblib.dump(info, info_path)

    print(f"\n模型已保存:")
    print(f"  {model_path}")
    print(f"  {scaler_path}")
    print(f"  {info_path}")
    print("\nGlucose Forecast 训练完成！")


if __name__ == '__main__':
    main()
