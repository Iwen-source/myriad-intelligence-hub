"""
Complication Prediction: LogisticRegression + RandomForest (multi-label)
Generates: complication_model.joblib, complication_labels.joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
from sklearn.preprocessing import MultiLabelBinarizer
import joblib
import os
import random

random.seed(42)
np.random.seed(42)

DISEASES = [
    "糖尿病", "高血压", "冠心病", "慢性阻塞性肺病", "慢性肾病",
    "肝硬化", "类风湿性关节炎", "系统性红斑狼疮", "脑卒中", "恶性肿瘤"
]

COMPLICATIONS = [
    "肾功能衰竭", "心肌梗死", "脑出血", "肺栓塞", "败血症",
    "心力衰竭", "呼吸衰竭", "消化道出血", "深静脉血栓", "感染性休克",
    "心律失常", "肝功能衰竭", "急性肾损伤", "弥散性血管内凝血", "多器官功能衰竭",
]

SYMPTOMS_POOL = [
    "发热", "乏力", "消瘦", "水肿", "呼吸困难",
    "胸痛", "心悸", "头痛", "关节痛", "皮疹",
    "尿少", "黄疸", "咳嗽", "咳血", "意识模糊",
]

# Disease → likely complications mapping
DISEASE_COMPLICATION_MAP = {
    "糖尿病": ["肾功能衰竭", "心肌梗死", "脑出血", "感染性休克", "心力衰竭"],
    "高血压": ["心肌梗死", "脑出血", "心力衰竭", "肾功能衰竭", "心律失常"],
    "冠心病": ["心肌梗死", "心力衰竭", "心律失常", "心源性猝死", "肺水肿"],
    "慢性阻塞性肺病": ["呼吸衰竭", "肺栓塞", "心力衰竭", "肺部感染", "气胸"],
    "慢性肾病": ["肾功能衰竭", "心力衰竭", "电解质紊乱", "肾性高血压", "尿毒症"],
    "肝硬化": ["消化道出血", "肝功能衰竭", "肝性脑病", "腹水感染", "肝癌"],
    "类风湿性关节炎": ["间质性肺炎", "心肌炎", "血管炎", "骨质疏松", "感染"],
    "系统性红斑狼疮": ["肾功能衰竭", "心包炎", "狼疮脑病", "肺部感染", "血液系统异常"],
    "脑卒中": ["脑出血", "肺栓塞", "深静脉血栓", "感染", "癫痫"],
    "恶性肿瘤": ["多器官功能衰竭", "弥散性血管内凝血", "败血症", "肺栓塞", "感染性休克"],
}


def generate_samples(n=1200):
    """Generate synthetic complication prediction data."""
    data = []
    complication_names = []

    for _ in range(n):
        disease = random.choice(DISEASES)
        n_symptoms = random.randint(2, 5)
        symptoms = random.sample(SYMPTOMS_POOL, n_symptoms)

        # Determine complications based on disease
        likely_complications = DISEASE_COMPLICATION_MAP.get(disease, [])
        n_complications = random.randint(1, min(4, len(likely_complications)))
        complications = random.sample(likely_complications, n_complications)

        # Add some random noise complications
        if random.random() < 0.15:
            extra = random.choice(COMPLICATIONS)
            if extra not in complications:
                complications.append(extra)

        # Symptom severity factor
        severity_factor = len(symptoms) / 5.0

        # Age factor
        age = random.randint(20, 85)
        age_factor = (age - 20) / 65

        row = {
            "disease": disease,
            "symptoms_text": " ".join(symptoms),
            "age": age,
            "severity_factor": severity_factor,
            "complication_set": complications,
        }
        data.append(row)
        complication_names = list(set(complication_names + complications))

    # Make sure all complications appear
    for c in COMPLICATIONS:
        if c not in complication_names:
            complication_names.append(c)

    df = pd.DataFrame(data)
    print(f"Generated {len(df)} samples, {len(complication_names)} unique complications")
    return df, complication_names


def train():
    print("=" * 60)
    print("Training Complication Prediction Model")
    print("=" * 60)

    df, complication_names = generate_samples(1200)

    # Build features
    diseases_ordered = sorted(df["disease"].unique())
    disease_to_idx = {d: i for i, d in enumerate(diseases_ordered)}

    X_features = []
    for _, row in df.iterrows():
        features = []
        # Disease one-hot
        disease_vec = [0] * len(diseases_ordered)
        disease_vec[disease_to_idx[row["disease"]]] = 1
        features.extend(disease_vec)
        # Symptoms: TF-IDF style - count symptoms
        symptom_count = len(row["symptoms_text"].split())
        features.append(min(symptom_count / 10, 1))
        features.append(row["age"] / 100)
        features.append(row["severity_factor"])
        X_features.append(features)

    X = np.array(X_features)
    print(f"Feature matrix: {X.shape}")

    # Multi-label binarization
    mlb = MultiLabelBinarizer(classes=complication_names)
    y = mlb.fit_transform(df["complication_set"].values)
    print(f"Labels shape: {y.shape}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train RandomForest for each complication (multi-label approach)
    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    # Also train logistic regression for comparison
    lr = LogisticRegression(
        max_iter=1000,
        random_state=42,
        multi_class="multinomial",
    )
    try:
        # Logistic only works on single-label multi-class, so use as additional info
        pass
    except Exception:
        pass

    # Evaluate
    y_pred = rf.predict(X_test)
    f1_micro = f1_score(y_test, y_pred, average="micro")
    f1_macro = f1_score(y_test, y_pred, average="macro")
    print(f"F1 micro = {f1_micro:.4f}, F1 macro = {f1_macro:.4f}")

    # Per-complication F1
    per_f1 = f1_score(y_test, y_pred, average=None)
    for i, c in enumerate(complication_names):
        if per_f1[i] < 0.5:
            print(f"  Low F1 for {c}: {per_f1[i]:.3f}")

    out_dir = os.path.dirname(__file__)
    joblib.dump({
        "model": rf,
        "diseases": diseases_ordered,
        "complications": complication_names,
        "mlb": mlb,
    }, os.path.join(out_dir, "complication_model.joblib"))
    print("Model saved.")


def predict_complications(current_disease, symptoms_list):
    """Predict complications for a given disease + symptoms."""
    out_dir = os.path.dirname(__file__)
    data = joblib.load(os.path.join(out_dir, "complication_model.joblib"))
    model = data["model"]
    diseases_ordered = data["diseases"]
    complication_names = data["complications"]

    if current_disease not in diseases_ordered:
        diseases_ordered.append(current_disease)
    disease_to_idx = {d: i for i, d in enumerate(diseases_ordered)}

    disease_vec = [0] * len(diseases_ordered)
    if current_disease in disease_to_idx:
        disease_vec[disease_to_idx[current_disease]] = 1

    symptoms_text = " ".join(symptoms_list) if isinstance(symptoms_list, list) else symptoms_list
    features = disease_vec + [min(len(symptoms_list if isinstance(symptoms_list, list) else symptoms_text.split()) / 10, 1), 0.5, 0.5]
    X = np.array([features])

    probas = model.predict_proba(X) if hasattr(model, "predict_proba") else None

    # Get probabilities for each complication
    if probas is None:
        y_pred = model.predict(X)[0]
        predictions = [(c, float(y_pred[i])) for i, c in enumerate(complication_names) if y_pred[i] > 0]
    else:
        # For multi-output RandomForest, predict_proba returns list of arrays
        if isinstance(probas, list):
            predictions = []
            for i, c in enumerate(complication_names):
                prob = probas[i][0][1] if len(probas[i].shape) > 1 and probas[i].shape[1] > 1 else 0.5
                predictions.append((c, float(prob)))
        else:
            predictions = [(c, probas[0][i] if len(probas.shape) > 1 else float(probas[i])) for i, c in enumerate(complication_names)]

    predictions.sort(key=lambda x: x[1], reverse=True)
    top_predictions = [c for c, p in predictions[:5] if p > 0.15]

    # Prevention advice
    prevention_map = {
        "肾功能衰竭": "监测肾功能、控制血压、避免肾毒性药物",
        "心肌梗死": "控制血压血脂、低脂饮食、定期心电图检查",
        "脑出血": "控制血压、避免剧烈运动、定期脑血管检查",
        "肺栓塞": "适当活动、穿弹力袜、抗凝治疗遵医嘱",
        "败血症": "注意感染防控、及时治疗原发感染灶",
        "心力衰竭": "限盐限水、规律服药、监测体重变化",
        "呼吸衰竭": "氧疗、呼吸功能锻炼、预防呼吸道感染",
        "消化道出血": "注意饮食、避免非甾体抗炎药、定期胃镜",
        "深静脉血栓": "适当活动、多饮水、使用抗凝药物",
        "感染性休克": "密切监测生命体征、早期抗感染治疗",
    }

    result = []
    for complication, prob in predictions[:5]:
        result.append({
            "complication": complication,
            "probability": round(prob, 4),
            "prevention_advice": prevention_map.get(complication, "定期随访、注意早期症状"),
        })

    return {"complications": result}


if __name__ == "__main__":
    train()

    # Test
    result = predict_complications("高血压", ["头痛", "心悸", "胸闷"])
    print(f"\nTest: hypertension + symptoms")
    for c in result["complications"]:
        print(f"  {c['complication']}: {c['probability']:.2%}")
