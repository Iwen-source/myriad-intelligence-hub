"""
症状-诊断-用药 自训练模型
================================
你可以自己添加症状数据 (CSV格式)，训练一个模型来自动分析病因和推荐用药。

用法:
  1. 准备数据: 编辑 data/symptom_training/symptom_data.csv
  2. 训练模型: python train_symptom_model.py
  3. API调用: POST /api/medical/v3/symptom-predict
"""

import os, sys, json, csv, pickle
import numpy as np
import pandas as pd
from pathlib import Path

# Windows 控制台默认 GBK(cp936)，直接 print emoji 会抛 UnicodeEncodeError。
# 保留原编码，仅把编码错误降级为替换字符（中文不受影响），避免脚本/接口崩溃。
try:
    sys.stdout.reconfigure(errors='replace')
    sys.stderr.reconfigure(errors='replace')
except Exception:
    pass

# ==================== 配置 ====================
BASE_DIR = Path(__file__).resolve().parent.parent  # python/
DATA_DIR = BASE_DIR.parent / 'data' / 'symptom_training'
MODEL_DIR = BASE_DIR / 'models'
DATA_FILE = DATA_DIR / 'symptom_data.csv'
MODEL_FILE = MODEL_DIR / 'symptom_model.pkl'
VECTORIZER_FILE = MODEL_DIR / 'symptom_vectorizer.pkl'

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


def create_sample_data():
    """创建示例训练数据（你也可以自己编辑）"""
    if DATA_FILE.exists():
        return

    sample_data = [
        # symptoms, diagnosis, medication, department, severity
        ["头痛、发热、咳嗽、喉咙痛", "上呼吸道感染", "阿莫西林, 布洛芬, 复方甘草片", "内科", "轻"],
        ["头痛剧烈、恶心呕吐、怕光", "偏头痛", "舒马普坦, 布洛芬", "神经内科", "中"],
        ["胸痛、胸闷、气短、出汗", "冠心病", "阿司匹林, 硝酸甘油", "心内科", "重"],
        ["腹痛、腹泻、恶心", "急性肠胃炎", "蒙脱石散, 口服补液盐", "消化内科", "轻"],
        ["咳嗽、咳痰、发热、呼吸困难", "肺炎", "阿奇霉素, 氨溴索", "呼吸内科", "重"],
        ["皮肤红疹、瘙痒", "过敏性皮炎", "氯雷他定, 炉甘石洗剂", "皮肤科", "轻"],
        ["关节肿痛、晨僵", "类风湿性关节炎", "甲氨蝶呤, 布洛芬", "风湿免疫科", "中"],
        ["多饮多尿、体重下降", "糖尿病", "二甲双胍", "内分泌科", "中"],
        ["头晕、耳鸣、失眠", "神经衰弱", "谷维素, 维生素B1", "神经内科", "轻"],
        ["腹痛、反酸、烧心", "胃食管反流", "奥美拉唑, 多潘立酮", "消化内科", "轻"],
        ["尿频、尿急、尿痛", "尿路感染", "左氧氟沙星", "泌尿外科", "轻"],
        ["背痛、僵硬、活动受限", "腰肌劳损", "双氯芬酸, 乙哌立松", "骨科", "轻"],
        ["眼红、眼痛、视力下降", "青光眼", "毛果芸香碱, 噻吗洛尔滴眼液", "眼科", "重"],
        ["月经不调、腹痛", "月经失调", "益母草颗粒, 布洛芬", "妇科", "轻"],
        ["咽喉肿痛、吞咽困难", "急性扁桃体炎", "头孢克肟, 开喉剑喷雾", "耳鼻喉科", "中"],
        ["发热、皮疹、关节痛", "登革热", "对乙酰氨基酚, 补液", "感染科", "重"],
        ["腹胀、嗳气、食欲不振", "功能性消化不良", "多酶片, 莫沙必利", "消化内科", "轻"],
        ["心悸、心慌、乏力", "心律失常", "美托洛尔, 稳心颗粒", "心内科", "中"],
        ["咳嗽、喘息、胸闷", "支气管哮喘", "沙丁胺醇气雾剂, 布地奈德", "呼吸内科", "中"],
        ["腰痛、血尿", "肾结石", "坦索罗辛, 双氯芬酸", "泌尿外科", "中"],
        ["失眠、焦虑、紧张", "焦虑症", "艾司西酞普兰, 阿普唑仑", "精神科", "中"],
        ["食欲亢进、手抖、消瘦", "甲状腺功能亢进", "甲巯咪唑, 普萘洛尔", "内分泌科", "中"],
        ["面色苍白、头晕、乏力", "贫血", "硫酸亚铁, 维生素C", "血液科", "轻"],
        ["肩颈酸痛、手臂麻木", "颈椎病", "颈复康颗粒, 乙哌立松", "骨科", "轻"],
        ["打喷嚏、流清涕、鼻塞", "过敏性鼻炎", "氯雷他定, 布地奈德鼻喷雾", "耳鼻喉科", "轻"],
    ]

    with open(DATA_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['symptoms', 'diagnosis', 'medication', 'department', 'severity'])
        writer.writerows(sample_data)

    print(f"✅ 已创建示例训练数据: {DATA_FILE} ({len(sample_data)}条)")


def train_model():
    """训练症状分类模型"""
    # 1. 加载数据
    df = pd.read_csv(DATA_FILE)
    print(f"📊 训练数据: {len(df)} 条")

    X_text = df['symptoms'].values
    y_diagnosis = df['diagnosis'].values
    y_medication = df['medication'].values
    y_department = df['department'].values
    y_severity = df['severity'].values

    # 2. 文本向量化 (TF-IDF)
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.model_selection import cross_val_score

    vectorizer = TfidfVectorizer(
        analyzer='char', ngram_range=(1, 3),
        max_features=5000, min_df=1
    )
    X = vectorizer.fit_transform(X_text)
    print(f"📐 特征维度: {X.shape[1]}")

    # 3. 训练多个分类器
    models = {}
    for name, y, clf in [
        ('diagnosis', y_diagnosis, MultinomialNB(alpha=0.1)),
        ('department', y_department, MultinomialNB(alpha=0.1)),
        ('severity', y_severity, MultinomialNB(alpha=0.1)),
    ]:
        clf.fit(X, y)
        models[name] = clf
        try:
            scores = cross_val_score(clf, X, y, cv=min(5, len(df)))
            print(f"  {name}: 准确率={scores.mean():.3f} (+/- {scores.std():.3f})")
        except:
            print(f"  {name}: 训练完成")

    # 4. 用药推荐模型 (一对多)
    medication_data = []
    for i, med_str in enumerate(y_medication):
        for m in str(med_str).split(','):
            m = m.strip()
            if m:
                medication_data.append({'symptom_vec': X[i].toarray()[0], 'medication': m})

    if medication_data:
        med_df = pd.DataFrame(medication_data)
        from sklearn.ensemble import RandomForestClassifier
        med_clf = RandomForestClassifier(n_estimators=100, random_state=42)
        med_X = np.stack(med_df['symptom_vec'].values)
        med_y = med_df['medication'].values
        med_clf.fit(med_X, med_y)
        models['medication'] = med_clf
        print(f"  用药推荐: {len(set(med_y))} 种药物, 训练完成")

    # 5. 保存模型
    with open(MODEL_FILE, 'wb') as f:
        pickle.dump({
            'models': models,
            'classes': {
                'diagnosis': list(set(y_diagnosis)),
                'department': list(set(y_department)),
                'severity': list(set(y_severity)),
            }
        }, f)
    with open(VECTORIZER_FILE, 'wb') as f:
        pickle.dump(vectorizer, f)

    print(f"\n✅ 模型已保存: {MODEL_FILE}")
    return models, vectorizer


def predict(symptoms_text, models=None, vectorizer=None):
    """预测症状对应的诊断、科室、用药"""
    if models is None or vectorizer is None:
        if not MODEL_FILE.exists() or not VECTORIZER_FILE.exists():
            raise FileNotFoundError("模型未训练，请先运行训练脚本")
        with open(MODEL_FILE, 'rb') as f:
            data = pickle.load(f)
            models = data['models']
        with open(VECTORIZER_FILE, 'rb') as f:
            vectorizer = pickle.load(f)

    X = vectorizer.transform([symptoms_text])

    # 诊断预测
    diag_proba = models['diagnosis'].predict_proba(X)[0]
    top3_diag = sorted(
        [(models['diagnosis'].classes_[i], float(p)) for i, p in enumerate(diag_proba)],
        key=lambda x: -x[1]
    )[:3]

    # 科室预测
    dept = models['department'].predict(X)[0]
    severity = models['severity'].predict(X)[0]

    # 用药推荐
    if 'medication' in models:
        med_proba = models['medication'].predict_proba(X)[0]
        top_meds = sorted(
            [(models['medication'].classes_[i], float(p)) for i, p in enumerate(med_proba)],
            key=lambda x: -x[1]
        )[:5]
        top_meds = [m for m, p in top_meds if p > 0.05][:3]
    else:
        top_meds = []

    return {
        'possible_diagnoses': [{'name': d, 'probability': f'{p*100:.0f}%'} for d, p in top3_diag],
        'primary_diagnosis': top3_diag[0][0] if top3_diag else '未知',
        'department': str(dept),
        'severity': str(severity),
        'recommended_medications': top_meds,
    }


# ==================== 主入口 ====================
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='症状-诊断-用药自训练模型')
    parser.add_argument('--train', action='store_true', help='训练模型')
    parser.add_argument('--predict', type=str, help='测试预测: 输入症状描述')
    parser.add_argument('--init-data', action='store_true', help='创建示例训练数据')
    args = parser.parse_args()

    if args.init_data:
        create_sample_data()
    elif args.train:
        create_sample_data()
        train_model()
    elif args.predict:
        result = predict(args.predict)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 交互模式
        create_sample_data()
        print("训练模型中...")
        models, vec = train_model()
        print("\n" + "=" * 40)
        print("🩺 症状诊断测试")
        print("=" * 40)
        while True:
            try:
                text = input("\n请输入症状 (输入 q 退出): ").strip()
                if text.lower() == 'q':
                    break
                if text:
                    result = predict(text, models, vec)
                    print(f"\n📋 诊断结果:")
                    for d in result['possible_diagnoses']:
                        print(f"  {d['name']} ({d['probability']})")
                    print(f"🏥 建议科室: {result['department']}")
                    print(f"⚠️  严重程度: {result['severity']}")
                    if result['recommended_medications']:
                        print(f"💊 推荐用药: {', '.join(result['recommended_medications'])}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"错误: {e}")
