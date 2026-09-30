"""
Diabetes Risk Prediction — 用真实 PIMA 数据训练
生成: diabetes_risk_model.joblib, diabetes_risk_scaler.joblib, diabetes_risk_info.joblib
"""

import numpy as np
import pandas as pd
import joblib
import os

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

import warnings
warnings.filterwarnings('ignore')

DATA_PATH = r'D:\东软实习\相关性分析_胰岛素_血糖\pima-indians-diabetes.csv'
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED = 42
np.random.seed(SEED)

# ── 列名 ──
COLUMNS = [
    'pregnancies',       # 怀孕次数
    'glucose',           # 血糖浓度 (mg/dL)
    'blood_pressure',    # 血压 (mm Hg)
    'skin_thickness',    # 皮褶厚度 (mm)
    'insulin',           # 胰岛素水平 (mu U/ml)
    'bmi',               # 体重指数
    'diabetes_pedigree', # 糖尿病家族史系数
    'age',               # 年龄
    'outcome'            # 0=未患病, 1=患病
]

FEATURE_NAMES = [
    ('怀孕次数', 'pregnancies', '次'),
    ('血糖浓度', 'glucose', 'mg/dL'),
    ('血压', 'blood_pressure', 'mm Hg'),
    ('皮褶厚度', 'skin_thickness', 'mm'),
    ('胰岛素水平', 'insulin', 'mu U/ml'),
    ('BMI', 'bmi', 'kg/m²'),
    ('糖尿病家族史系数', 'diabetes_pedigree', ''),
    ('年龄', 'age', '岁'),
]

# ── 风险等级划分阈值 ──
RISK_THRESHOLDS = {
    'low': 0.3,
    'medium': 0.6
}


def load_and_clean():
    """加载 PIMA 数据，处理缺失值（0值替换为中位数）"""
    df = pd.read_csv(DATA_PATH, header=None, names=COLUMNS)

    print("=" * 60)
    print("PIMA 印第安人糖尿病数据集")
    print("=" * 60)
    print(f"样本总数: {len(df)}")
    print(f"患病比例: {df['outcome'].mean():.2%}")
    print(f"\n特征统计:")
    print(df.describe().to_string())
    print()

    # 处理缺失值：glucose, blood_pressure, skin_thickness, insulin, bmi 的0值替换为中位数
    zero_replace_cols = ['glucose', 'blood_pressure', 'skin_thickness', 'insulin', 'bmi']
    for col in zero_replace_cols:
        median_val = df[df[col] > 0][col].median()
        count_zero = (df[col] == 0).sum()
        df[col] = df[col].replace(0, median_val)
        print(f"  {col}: 替换 {count_zero} 个0值为中位数 {median_val:.2f}")

    print(f"\n清洗后数据: {len(df)} 条")
    return df


def train_models(X_train, y_train, X_test, y_test, feature_names):
    """训练多个模型并选出最优"""
    models = {
        'XGBoost': XGBClassifier(
            n_estimators=200, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            random_state=SEED, eval_metric='logloss', use_label_encoder=False
        ),
        'RandomForest': RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_split=5,
            random_state=SEED, n_jobs=-1
        ),
        'GradientBoosting': GradientBoostingClassifier(
            n_estimators=150, max_depth=4, learning_rate=0.1,
            random_state=SEED
        ),
        'LogisticRegression': LogisticRegression(
            C=1.0, max_iter=1000, random_state=SEED, n_jobs=-1
        ),
    }

    best_model = None
    best_name = ''
    best_score = 0
    results = []

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred)
        rec = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)

        cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
        cv_mean = cv_scores.mean()

        results.append({
            'model': name, 'accuracy': acc, 'precision': prec,
            'recall': recall_score(y_test, y_pred),
            'f1': f1, 'auc': auc, 'cv_auc': cv_mean
        })

        print(f"  {name:25s}  Acc={acc:.4f}  Prec={prec:.4f}  Rec={rec:.4f}  F1={f1:.4f}  AUC={auc:.4f}  CV-AUC={cv_mean:.4f}")

        if cv_mean > best_score:
            best_score = cv_mean
            best_model = model
            best_name = name

    print(f"\n>>> 最优模型: {best_name} (CV-AUC={best_score:.4f})")

    # 特征重要性
    if hasattr(best_model, 'feature_importances_'):
        importances = best_model.feature_importances_
        indices = np.argsort(importances)[::-1]
        print(f"\n特征重要性 ({best_name}):")
        for i in indices:
            cn, en, unit = feature_names[i]
            unit_str = f" ({unit})" if unit else ""
            print(f"  {cn}{unit_str}: {importances[i]:.4f}")

    return best_model, best_name


def save_models(model, scaler, feature_names):
    """保存模型及元数据"""
    model_path = os.path.join(OUT_DIR, 'diabetes_risk_model.joblib')
    scaler_path = os.path.join(OUT_DIR, 'diabetes_risk_scaler.joblib')
    info_path = os.path.join(OUT_DIR, 'diabetes_risk_info.joblib')

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    info = {
        'feature_names': feature_names,
        'risk_thresholds': RISK_THRESHOLDS,
        'model_type': type(model).__name__,
    }
    joblib.dump(info, info_path)

    print(f"\n模型已保存:")
    print(f"  {model_path}")
    print(f"  {scaler_path}")
    print(f"  {info_path}")


def main():
    df = load_and_clean()

    X = df.drop('outcome', axis=1).values
    y = df['outcome'].values

    # 划分训练/测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )

    print(f"\n训练集: {len(X_train)} 条, 测试集: {len(X_test)} 条")
    print(f"训练集患病比例: {y_train.mean():.2%}, 测试集患病比例: {y_test.mean():.2%}")

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("\n训练模型...")
    best_model, best_name = train_models(
        X_train_scaled, y_train, X_test_scaled, y_test, FEATURE_NAMES
    )

    # 最终评估
    y_pred = best_model.predict(X_test_scaled)
    y_proba = best_model.predict_proba(X_test_scaled)[:, 1]

    print(f"\n{'=' * 60}")
    print(f"最终模型评估 ({best_name})")
    print(f"{'=' * 60}")
    print(f"准确率:      {accuracy_score(y_test, y_pred):.4f}")
    print(f"精确率:      {precision_score(y_test, y_pred):.4f}")
    print(f"召回率:      {recall_score(y_test, y_pred):.4f}")
    print(f"F1分数:      {f1_score(y_test, y_pred):.4f}")
    print(f"AUC:         {roc_auc_score(y_test, y_proba):.4f}")
    print(f"\n混淆矩阵:")
    cm = confusion_matrix(y_test, y_pred)
    print(f"  TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"  FN={cm[1,0]}  TP={cm[1,1]}")

    save_models(best_model, scaler, FEATURE_NAMES)
    print("\nDiabetes Risk 训练完成！")


if __name__ == '__main__':
    main()
