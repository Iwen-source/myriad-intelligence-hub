"""
Medical Model: Symptom → Disease Classification
TF-IDF vectorization + RandomForestClassifier
Generates: medical_model.joblib, vectorizer.joblib
"""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder
import joblib
import os
import random

random.seed(42)
np.random.seed(42)

# ── Synthetic symptom-disease dataset ──────────────────────────────────

DISEASE_DB = {
    "上呼吸道感染": {
        "symptoms": [
            "发热咳嗽头痛流鼻涕",
            "喉咙痛打喷嚏鼻塞",
            "发热咽喉痛咳嗽咳痰",
            "鼻塞流清涕头痛乏力",
            "咳嗽咽喉红肿发热畏寒",
            "打喷嚏流鼻涕声音嘶哑",
            "头痛鼻塞咳嗽咳白色痰",
            "喉咙干痒咳嗽低热",
        ],
        "department": "呼吸内科",
        "severity_weights": {"低热": "low", "发热": "mid", "高热": "high"},
        "suggestions": "多喝温水、注意休息、服用感冒药，如症状加重请及时就医。",
    },
    "肺炎": {
        "symptoms": [
            "高热持续不退咳嗽咳黄痰",
            "胸痛呼吸困难咳嗽剧烈",
            "发热寒战咳嗽痰中带血",
            "呼吸急促胸闷咳嗽不止",
            "高热咳嗽胸痛咳脓痰",
            "咳嗽胸痛呼吸困难发热",
            "持续发热咳嗽夜间加重",
            "咳嗽胸痛高热寒战乏力",
        ],
        "department": "呼吸内科",
        "severity_weights": {"低热": "mid", "发热": "high", "高热": "high"},
        "suggestions": "请立即就医！肺炎需要抗生素治疗，避免延误病情。",
    },
    "胃炎": {
        "symptoms": [
            "上腹痛恶心呕吐反酸",
            "胃胀嗳气食欲不振",
            "上腹隐痛饭后加重烧心",
            "恶心呕吐胃痛腹泻",
            "饭后腹胀反酸嗳气",
            "上腹灼烧感恶心打嗝",
            "胃痛食欲差口臭",
            "胃部不适反酸呕吐清水",
        ],
        "department": "消化内科",
        "severity_weights": {"低热": "low", "发热": "mid", "高热": "mid"},
        "suggestions": "注意饮食规律、避免辛辣刺激食物，建议做胃镜检查。",
    },
    "偏头痛": {
        "symptoms": [
            "单侧头痛搏动性痛怕光怕声",
            "剧烈头痛恶心呕吐视觉先兆",
            "头痛头晕一侧搏动痛",
            "反复发作头痛怕光恶心",
            "眼部周围疼痛头痛恶心",
            "单侧太阳穴跳痛头晕",
            "头痛呕吐怕光怕声",
            "搏动性头痛恶心视觉模糊",
        ],
        "department": "神经内科",
        "severity_weights": {"低热": "low", "发热": "low", "高热": "low"},
        "suggestions": "保持规律作息、避免触发因素，疼痛剧烈时可服用止痛药。",
    },
    "过敏性鼻炎": {
        "symptoms": [
            "阵发性打喷嚏流清水鼻涕鼻痒",
            "鼻塞鼻痒眼痒打喷嚏",
            "流清涕鼻塞打喷嚏眼红",
            "晨起连续打喷嚏鼻塞流涕",
            "鼻腔发痒打喷嚏流清水样涕",
            "眼痒鼻塞打喷嚏嗅觉减退",
            "接触花粉后打喷嚏流鼻涕",
            "季节性鼻塞打喷嚏眼痒流泪",
        ],
        "department": "耳鼻喉科",
        "severity_weights": {"低热": "low", "发热": "low", "高热": "low"},
        "suggestions": "避免接触过敏原，可使用抗组胺药物或鼻喷激素。",
    },
    "高血压": {
        "symptoms": [
            "头晕头痛面红耳鸣",
            "眩晕颈项僵硬心悸",
            "头痛失眠面部潮红",
            "头晕眼花胸闷心悸",
            "头重脚轻烦躁易怒",
            "眩晕耳鸣失眠多梦",
            "头痛恶心视力模糊",
            "头晕乏力心悸气短",
        ],
        "department": "心血管内科",
        "severity_weights": {"低热": "low", "发热": "mid", "高热": "high"},
        "suggestions": "定期测量血压、低盐饮食、规律服药，保持情绪稳定。",
    },
    "糖尿病": {
        "symptoms": [
            "多饮多尿多食体重下降",
            "口渴多饮尿频饥饿感",
            "体重减轻乏力视力模糊",
            "手脚麻木伤口愈合慢",
            "多饮多尿皮肤瘙痒",
            "口干尿多易饥饿消瘦",
            "疲劳乏力口渴多尿",
            "视力模糊手脚麻木尿频",
        ],
        "department": "内分泌科",
        "severity_weights": {"低热": "low", "发热": "mid", "高热": "high"},
        "suggestions": "控制饮食、适量运动、监测血糖，定期复查糖化血红蛋白。",
    },
    "急性阑尾炎": {
        "symptoms": [
            "转移性右下腹痛恶心呕吐",
            "右下腹压痛反跳痛发热",
            "腹痛从上腹转移到右下腹",
            "右下腹痛走路时加重",
            "腹痛恶心呕吐低热",
            "右下腹剧烈疼痛发热",
            "腹部压痛反跳痛腹肌紧张",
            "右下腹痛伴恶心食欲差",
        ],
        "department": "普外科",
        "severity_weights": {"低热": "mid", "发热": "high", "高热": "high"},
        "suggestions": "立即就医！急性阑尾炎需急诊手术处理。",
    },
    "颈椎病": {
        "symptoms": [
            "颈肩痛手臂麻木头晕",
            "颈部僵硬肩背酸痛头痛",
            "低头后颈部疼痛手臂放射痛",
            "头晕恶心颈部活动受限",
            "颈痛肩痛手指麻木",
            "颈部不适头晕转头加重",
            "肩背酸沉手臂无力麻木",
            "颈部僵硬疼痛头痛头晕",
        ],
        "department": "骨科",
        "severity_weights": {"低热": "low", "发热": "low", "高热": "low"},
        "suggestions": "避免长时间低头、做颈部保健操，严重时需理疗或手术。",
    },
    "病毒性肝炎": {
        "symptoms": [
            "乏力食欲减退恶心黄疸",
            "尿黄眼黄皮肤黄乏力",
            "肝区不适食欲差恶心呕吐",
            "疲倦无力厌油腻尿黄",
            "右上腹痛黄疸发热",
            "食欲差恶心腹胀皮肤黄",
            "乏力恶心肝区隐痛尿黄",
            "眼黄尿黄乏力厌食",
        ],
        "department": "消化内科",
        "severity_weights": {"低热": "mid", "发热": "high", "高热": "high"},
        "suggestions": "及时就医检查肝功能，注意休息、保肝治疗，避免饮酒。",
    },
}

SEVERITY_LEVELS = ["low", "mid", "high"]
DEPARTMENTS = list(set(d["department"] for d in DISEASE_DB.values()))


def generate_dataset(n_samples=600):
    """Generate synthetic symptom-disease dataset."""
    data = []
    diseases = list(DISEASE_DB.keys())

    # Ensure balanced-ish distribution
    per_disease = max(30, n_samples // len(diseases))

    for disease, info in DISEASE_DB.items():
        symp_list = info["symptoms"]
        for _ in range(per_disease):
            # Pick a base symptom text
            base = random.choice(symp_list)

            # Randomly add/swap symptom intensity modifiers for variety
            if random.random() < 0.3:
                words = list(base)
                if random.random() < 0.5:
                    words.append("严重")
                else:
                    words.append("轻微")
                base = "".join(words)

            # Assign severity - biased by the disease info
            sev_keys = list(info["severity_weights"].keys())
            sev = info["severity_weights"][random.choice(sev_keys)]
            # Some randomness in severity assignment
            if random.random() < 0.2:
                sev = random.choice(SEVERITY_LEVELS)

            data.append(
                {
                    "symptoms_text": base,
                    "disease": disease,
                    "severity": sev,
                    "department": info["department"],
                }
            )

    df = pd.DataFrame(data)
    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"Generated dataset: {len(df)} samples, {df['disease'].nunique()} disease classes")
    print(f"Disease distribution:\n{df['disease'].value_counts().to_string()}")
    return df


def train():
    print("=" * 60)
    print("Training Medical Model (Symptom → Disease Classification)")
    print("=" * 60)

    # Generate dataset
    df = generate_dataset(600)

    # Separate features and labels
    X_text = df["symptoms_text"]
    y_disease = df["disease"]

    # Encode disease labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y_disease)

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(1, 3),
        max_features=5000,
        min_df=2,
    )
    X_vec = vectorizer.fit_transform(X_text)
    print(f"Vocabulary size: {X_vec.shape[1]}")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_vec, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    # Train RandomForest classifier
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nTest Accuracy: {acc:.4f}")

    # Get per-class probabilities for confidence
    y_proba = model.predict_proba(X_test)
    confidences = np.max(y_proba, axis=1)
    print(f"Mean confidence: {confidences.mean():.4f}")

    # Detailed report
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Save artifacts
    os.makedirs(os.path.dirname(__file__), exist_ok=True)
    model_path = os.path.join(os.path.dirname(__file__), "medical_model.joblib")
    vec_path = os.path.join(os.path.dirname(__file__), "medical_vectorizer.joblib")
    le_path = os.path.join(os.path.dirname(__file__), "medical_label_encoder.joblib")

    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vec_path)
    joblib.dump(le, le_path)

    print(f"\nModels saved:")
    print(f"  {model_path}")
    print(f"  {vec_path}")
    print(f"  {le_path}")
    print("Training complete!")


def predict(symptoms_text: str):
    """Load model and predict disease from symptoms text."""
    model_dir = os.path.dirname(__file__)
    model = joblib.load(os.path.join(model_dir, "medical_model.joblib"))
    vectorizer = joblib.load(os.path.join(model_dir, "medical_vectorizer.joblib"))
    le = joblib.load(os.path.join(model_dir, "medical_label_encoder.joblib"))

    X = vectorizer.transform([symptoms_text])
    pred_encoded = model.predict(X)[0]
    probas = model.predict_proba(X)[0]
    confidence = float(np.max(probas))
    disease = le.inverse_transform([pred_encoded])[0]

    # Get severity heuristic based on keywords
    severity = "mid"
    sev_keywords = {"严重": "high", "剧烈": "high", "持续": "mid", "轻微": "low"}
    for kw, sev in sev_keywords.items():
        if kw in symptoms_text:
            severity = sev
            break

    info = DISEASE_DB.get(disease, {})
    department = info.get("department", "全科")
    suggestions = info.get("suggestions", "建议及时就医检查。")

    return {
        "disease": disease,
        "confidence": round(confidence, 4),
        "severity": severity,
        "department": department,
        "suggestions": suggestions,
    }


if __name__ == "__main__":
    train()

    # Test prediction
    print("\n" + "=" * 60)
    print("Test predictions:")
    print("=" * 60)
    test_cases = [
        "发热咳嗽头痛流鼻涕",
        "右下腹剧烈疼痛发热",
        "多饮多尿体重下降乏力",
        "颈部僵硬手臂麻木头晕",
    ]
    for tc in test_cases:
        result = predict(tc)
        print(f"  Input: {tc}")
        print(f"  → {result['disease']} (conf={result['confidence']:.2f}, dept={result['department']})")
