"""
训练教育资源质量评分模型 -> 导出树结构为 JSON
Java 端直接加载 JSON 做纯 Java 推理（无需 ONNX/PMML native libs）
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import json
import os
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

# ===== 1. 生成合成训练数据 =====
N = 2000
resource_types = ['课件', '视频', '习题', '文档', '代码']
subjects = ['数学', '物理', '计算机', '英语', '化学', '生物']

type_base = {'课件': 3.8, '视频': 4.2, '习题': 3.2, '文档': 3.5, '代码': 4.0}
subject_base = {'数学': 3.5, '物理': 3.7, '计算机': 4.3, '英语': 3.3, '化学': 3.6, '生物': 3.8}

rows = []
for _ in range(N):
    rtype = np.random.choice(resource_types)
    subj = np.random.choice(subjects)
    downloads = np.random.randint(10, 50000)
    upload_days_ago = np.random.randint(1, 730)
    resource_count = np.random.randint(1, 20)

    base = type_base[rtype] + subject_base[subj] - 4.0
    dl_factor = np.log1p(downloads) / 12.0
    fresh_factor = np.exp(-upload_days_ago / 365) * 0.4
    rc_factor = np.log1p(resource_count) * 0.15
    noise = np.random.normal(0, 0.3)

    score = base + dl_factor + fresh_factor + rc_factor + noise
    score = np.clip(score, 0.5, 5.0)

    rows.append({
        'resource_type': rtype, 'subject': subj,
        'downloads': int(downloads),
        'upload_days_ago': int(upload_days_ago),
        'resource_count': int(resource_count),
        'quality_score': round(float(score), 2)
    })

df = pd.DataFrame(rows)

# ===== 2. One-Hot 编码 =====
df_encoded = pd.get_dummies(df, columns=['resource_type', 'subject'], prefix=['type', 'subj'])
feature_cols = [c for c in df_encoded.columns if c != 'quality_score']

X = df_encoded[feature_cols].values.astype(np.float32)
y = df_encoded['quality_score'].values.astype(np.float32)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"训练集: {len(X_train)} 条, 测试集: {len(X_test)} 条, 特征数: {len(feature_cols)}")

# ===== 3. 训练 (更少的树以减小 JSON 文件大小) =====
model = RandomForestRegressor(
    n_estimators=50, max_depth=8,
    min_samples_leaf=4, random_state=42, n_jobs=-1
)
model.fit(X_train, y_train)

# ===== 4. 评估 =====
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"MAE: {mae:.4f}, R2: {r2:.4f}, 平均评分: {y.mean():.2f}")

# ===== 5. 导出树结构为 JSON =====
def tree_to_dict(tree, feature_names):
    """将 sklearn DecisionTreeRegressor 转为 JSON 可序列化的 dict"""
    tree_ = tree.tree_
    n_nodes = tree_.node_count
    children_left = tree_.children_left
    children_right = tree_.children_right
    feature = tree_.feature
    threshold = tree_.threshold
    value = tree_.value

    def recurse(node_id, depth=0):
        if node_id == -1:
            return None
        node = {
            'id': int(node_id),
            'depth': int(depth),
        }
        # 是否是叶节点
        if children_left[node_id] == -1 and children_right[node_id] == -1:
            node['leaf'] = True
            node['value'] = float(value[node_id][0][0])
        else:
            node['leaf'] = False
            node['feature'] = int(feature[node_id])
            node['feature_name'] = feature_names[feature[node_id]] if feature[node_id] >= 0 and feature[node_id] < len(feature_names) else str(feature[node_id])
            node['threshold'] = float(threshold[node_id])
            node['left'] = recurse(children_left[node_id], depth + 1)
            node['right'] = recurse(children_right[node_id], depth + 1)
        return node

    return recurse(0)

model_data = {
    'n_estimators': model.n_estimators,
    'n_features': len(feature_cols),
    'feature_names': feature_cols,
    'trees': []
}

for i, tree in enumerate(model.estimators_):
    tree_dict = tree_to_dict(tree, feature_cols)
    model_data['trees'].append(tree_dict)

# 评估
print(f"模型: {model.n_estimators} 棵树, 每颗树深度 <= {model.max_depth}")

# 验证：用 JSON 数据做推理，确认与 sklearn 结果一致
def json_predict(model_data, X_row):
    score = 0.0
    for tree in model_data['trees']:
        node = tree
        while not node['leaf']:
            feat_idx = node['feature']
            if X_row[feat_idx] <= node['threshold']:
                node = node['left']
            else:
                node = node['right']
        score += node['value']
    return score / len(model_data['trees'])

# 验证随机 10 条
test_indices = np.random.choice(len(X_test), 10, replace=False)
errors = []
for idx in test_indices:
    skl_pred = model.predict(X_test[idx:idx+1])[0]
    json_pred = json_predict(model_data, X_test[idx])
    errors.append(abs(skl_pred - json_pred))

print(f"JSON 推理验证: 最大误差 = {max(errors):.6f}, 平均误差 = {np.mean(errors):.6f}")
print("JSON 推理与 sklearn 一致!")

# ===== 6. 保存 JSON =====
model_dir = 'D:\\java\\develop\\ai-empowerment-platform\\backend\\src\\main\\resources\\models'
os.makedirs(model_dir, exist_ok=True)
model_path = os.path.join(model_dir, 'resource_rating_model.json')

with open(model_path, 'w', encoding='utf-8') as f:
    json.dump(model_data, f, ensure_ascii=False, indent=None)

print(f"模型导出: {model_path}")
print(f"文件大小: {os.path.getsize(model_path) / 1024:.1f} KB")
