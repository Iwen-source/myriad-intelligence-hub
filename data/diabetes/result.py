# ==============================
# 随机森林血糖预测 完整代码
# 9个患者 → 九宫格绘图
# ==============================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_squared_error, r2_score
import warnings

warnings.filterwarnings('ignore')

# ---------------------- 字体设置 ----------------------
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows
# plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']  # Linux
# plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # Mac
plt.rcParams['axes.unicode_minus'] = False

# ---------------------- 1. 读取9个患者文件 ----------------------
file_list = [f"D:\东软实习\相关性分析_胰岛素_血糖\glucose_0{i}.csv" for i in range(1, 10)]
patients = []

for i, path in enumerate(file_list):
    try:
        df = pd.read_csv(path)
        df['patient'] = i + 1
        patients.append(df)
        print(f"患者{i + 1}：{len(df)} 条数据")
    except:
        print(f"文件 {path} 读取失败")


# ---------------------- 2. 特征工程（时间+类别编码） ----------------------
def make_features(df):
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
    df = df.sort_values('datetime').reset_index(drop=True)

    # 时间特征
    df['hour'] = df['datetime'].dt.hour
    df['minute'] = df['datetime'].dt.minute
    df['day'] = df['datetime'].dt.day
    df['month'] = df['datetime'].dt.month
    df['dayofweek'] = df['datetime'].dt.dayofweek

    # 分类特征编码
    enc = OneHotEncoder(sparse_output=False, drop='first')
    type_enc = enc.fit_transform(df[['type']])
    type_df = pd.DataFrame(type_enc, columns=[f'type_{c}' for c in enc.categories_[0][1:]])

    # 构建X
    X = df.drop(['date', 'time', 'datetime', 'type', 'comments', 'glucose'], axis=1, errors='ignore')
    X = pd.concat([X, type_df], axis=1)
    y = df['glucose'].values

    return df, X, y


# ---------------------- 3. 训练随机森林 + 预测 ----------------------
results = []
for p_df in patients:
    df, X, y = make_features(p_df)

    # 随机森林模型
    model = RandomForestRegressor(
        n_estimators=150,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X, y)
    y_pred = model.predict(X)

    # 评估
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)

    results.append({
        'patient': df['patient'].iloc[0],
        'datetime': df['datetime'],
        'y_true': y,
        'y_pred': y_pred,
        'rmse': rmse,
        'r2': r2,
        'n': len(df)
    })

# ---------------------- 4. 画九宫格图 ----------------------
fig, axes = plt.subplots(3, 3, figsize=(22, 14))
fig.suptitle('9位患者血糖真实值 vs 随机森林预测值', fontsize=20, y=0.98)

color_true = '#2E86AB'
color_pred = '#F18F01'

for ax, res in zip(axes.flat, results):
    t = res['datetime']
    y_true = res['y_true']
    y_pred = res['y_pred']

    # 太多点会卡顿，降采样
    if len(t) > 800:
        step = len(t) // 800
        t = t[::step]
        y_true = y_true[::step]
        y_pred = y_pred[::step]

    ax.plot(t, y_true, c=color_true, linewidth=2, label='真实值')
    ax.plot(t, y_pred, c=color_pred, linewidth=1.5, alpha=0.8, label='预测值')

    ax.set_title(f"患者{res['patient']} | RMSE={res['rmse']:.2f} | R²={res['r2']:.3f}", fontsize=11)
    ax.tick_params(axis='x', rotation=45)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

plt.tight_layout()
plt.subplots_adjust(top=0.94)
plt.savefig('9患者随机森林血糖预测.png', dpi=300, bbox_inches='tight')
plt.show()

# ---------------------- 5. 输出结果 ----------------------
print("\n" + "=" * 60)
print("随机森林模型 - 9位患者预测结果")
print("=" * 60)
for res in results:
    print(f"患者{res['patient']:2d} | 样本{res['n']:4d} | RMSE={res['rmse']:6.2f} | R²={res['r2']:6.3f}")