import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import warnings

warnings.filterwarnings('ignore')

# 字体设置（和你发的图风格对齐）
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3


# ----------------------
# 1. 时序特征构建（关键！和你发的图对齐）
# ----------------------
def build_time_series_features(df, n_lags=5):
    """
    构建时序预测特征：用过去n个时间点的血糖值预测下一个值
    """
    df = df.copy().sort_values('datetime').reset_index(drop=True)

    # 创建滞后特征（过去n个血糖值）
    for lag in range(1, n_lags + 1):
        df[f'glucose_lag_{lag}'] = df['glucose'].shift(lag)

    # 计算差分特征（变化量）
    df['glucose_diff_1'] = df['glucose'].diff(1)
    df['glucose_diff_2'] = df['glucose'].diff(2)

    # 去除空值
    df = df.dropna().reset_index(drop=True)
    return df


# ----------------------
# 2. 读取每个患者数据，单独建模预测
# ----------------------
file_paths = [f'D:\东软实习\相关性分析_胰岛素_血糖\glucose_0{i}.csv' for i in range(1, 10)]
patient_results = []

for i, path in enumerate(file_paths):
    patient_id = i + 1
    print(f"处理患者 {patient_id}...")

    # 读取并预处理
    df = pd.read_csv(path)
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
    df = df.sort_values('datetime').reset_index(drop=True)

    # 构建时序特征
    df_ts = build_time_series_features(df, n_lags=5)

    # 确保数据集不为空
    if len(df_ts) == 0:
        print(f"警告：患者 {patient_id} 的数据集为空，跳过此患者。")
        continue

    # 划分训练集/测试集（按时间顺序，前80%训练，后20%测试）
    split_idx = int(len(df_ts) * 0.8)
    train_df = df_ts.iloc[:split_idx]
    test_df = df_ts.iloc[split_idx:]

    # 确保训练集不为空
    if len(train_df) == 0:
        print(f"警告：患者 {patient_id} 的训练集为空，跳过此患者。")
        continue

    # 构建X和y
    feature_cols = [col for col in df_ts.columns if 'lag' in col or 'diff' in col]
    X_train, y_train = train_df[feature_cols], train_df['glucose']
    X_test, y_test = test_df[feature_cols], test_df['glucose']

    # 训练随机森林模型（针对单个患者）
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=8,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # 预测测试集
    y_pred = model.predict(X_test)

    # 评估指标
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    # 保存结果
    patient_results.append({
        'patient_id': patient_id,
        'datetime': test_df['datetime'],
        'y_true': y_test.values,
        'y_pred': y_pred,
        'rmse': rmse,
        'r2': r2,
        'n_samples': len(test_df)
    })

# ----------------------
# 3. 绘制和你发的图一样的九宫格
# ----------------------
fig, axes = plt.subplots(3, 3, figsize=(14, 11))
fig.suptitle('测试集时序预测（3×3，全量测试点）', fontsize=12, y=0.98)

for ax, res in zip(axes.flatten(), patient_results):
    # 绘制真实值和预测值
    ax.plot(res['datetime'], res['y_true'], color='#666666', linewidth=1, label='真实')
    ax.plot(res['datetime'], res['y_pred'], color='#ff6b6b', linewidth=1, label='预测')

    # 设置标题（和你发的图格式对齐）
    ax.set_title(f'glucose_0{res["patient_id"]} (n={res["n_samples"]})', fontsize=9)
    ax.set_ylabel('mmol/L', fontsize=8)
    ax.tick_params(axis='x', rotation=45, labelsize=7)
    ax.tick_params(axis='y', labelsize=7)
    ax.legend(fontsize=7, loc='upper right')
    ax.grid(True, linestyle='-', alpha=0.3)

plt.tight_layout()
plt.subplots_adjust(top=0.94)
plt.savefig('测试集时序预测_九宫格.png', dpi=300, bbox_inches='tight')
plt.show()

# ----------------------
# 4. 输出每个患者的测试集性能
# ----------------------
print("\n" + "=" * 60)
print("测试集时序预测 - 随机森林性能汇总")
print("=" * 60)
for res in patient_results:
    print(
        f"患者0{res['patient_id']} | 测试样本数: {res['n_samples']:3d} | RMSE: {res['rmse']:.2f} | R²: {res['r2']:.3f}")