"""
Drug Recommendation Model: Content-Based Filtering + KNN using cosine similarity
Generates: drug_vectorizer.joblib, drug_similarity_matrix.joblib, drug_features.joblib, drug_database.csv
"""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import os
import random

random.seed(42)
np.random.seed(42)

CATEGORIES = [
    "抗生素", "解热镇痛药", "抗过敏药", "心血管药", "消化系统药",
    "呼吸系统药", "神经系统药", "内分泌药", "抗病毒药", "中成药"
]

DRUG_NAMES = [
    "阿莫西林", "头孢克肟", "青霉素V钾", "罗红霉素", "阿奇霉素",
    "布洛芬", "对乙酰氨基酚", "双氯芬酸", "萘普生", "塞来昔布",
    "氯雷他定", "西替利嗪", "孟鲁司特", "扑尔敏", "酮替芬",
    "硝苯地平", "卡托普利", "美托洛尔", "氨氯地平", "缬沙坦",
    "奥美拉唑", "雷贝拉唑", "多潘立酮", "莫沙必利", "铝碳酸镁",
    "氨溴索", "右美沙芬", "沙丁胺醇", "布地奈德", "茶碱",
    "阿普唑仑", "艾司西酞普兰", "佐匹克隆", "卡马西平", "苯巴比妥",
    "二甲双胍", "格列美脲", "阿卡波糖", "胰岛素", "吡格列酮",
    "奥司他韦", "阿昔洛韦", "更昔洛韦", "利巴韦林", "恩替卡韦",
    "金银花颗粒", "板蓝根", "连花清瘟", "蒲地蓝", "复方甘草片",
    "黄连素", "蒙脱石散", "乳果糖", "整肠生", "双歧杆菌",
]

# Generate inducedications and contraindications per drug
CORE_INDICATIONS = [
    "上呼吸道感染", "细菌感染", "发热", "头痛", "咳嗽",
    "过敏性鼻炎", "高血压", "心绞痛", "胃酸过多", "胃炎",
    "支气管炎", "哮喘", "糖尿病", "焦虑", "失眠",
    "腹泻", "便秘", "病毒性感染", "炎症", "疼痛",
]

CORE_CONTRAINDICATIONS = [
    "青霉素过敏", "肝功能不全", "肾功能不全", "孕妇", "哺乳期",
    "哮喘患者", "胃溃疡", "出血倾向", "低血压", "心动过缓",
    "青光眼", "前列腺肥大", "儿童", "老年人", "酒精依赖",
]

CORE_SIDE_EFFECTS = [
    "恶心", "呕吐", "头晕", "皮疹", "腹泻",
    "嗜睡", "口干", "心悸", "血压升高", "食欲不振",
    "便秘", "胃不适", "乏力", "失眠", "过敏反应",
]


def generate_drug_db(n_drugs=500):
    drugs = []
    cat_repeats = (n_drugs + len(CATEGORIES) - 1) // len(CATEGORIES)

    drug_idx = 0
    for cat in CATEGORIES:
        for i in range(cat_repeats):
            if drug_idx >= n_drugs:
                break
            name = f"{random.choice(DRUG_NAMES)}_{drug_idx}" if drug_idx >= len(DRUG_NAMES) else DRUG_NAMES[drug_idx % len(DRUG_NAMES)]

            # Generate indications (2-5)
            n_ind = random.randint(2, 5)
            indications = random.sample(CORE_INDICATIONS, n_ind)

            # Generate contraindications (1-3)
            n_contra = random.randint(1, 3)
            contraindications = random.sample(CORE_CONTRAINDICATIONS, n_contra)

            # Generate side effects (2-4)
            n_side = random.randint(2, 4)
            side_effects = random.sample(CORE_SIDE_EFFECTS, n_side)

            drugs.append({
                "drug_name": name,
                "category": cat,
                "indications_text": " ".join(indications),
                "contraindications_text": " ".join(contraindications),
                "side_effects_text": " ".join(side_effects),
                "all_attributes": f"{cat} {' '.join(indications)} {' '.join(contraindications)} {' '.join(side_effects)}",
            })
            drug_idx += 1

    df = pd.DataFrame(drugs).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"Generated drug database: {len(df)} drugs")
    return df


def train():
    print("=" * 60)
    print("Training Drug Recommendation Model")
    print("=" * 60)

    df = generate_drug_db(500)

    # Save the database
    csv_path = os.path.join(os.path.dirname(__file__), "drug_database.csv")
    df.to_csv(csv_path, index=False)
    print(f"Saved drug database to {csv_path}")

    # Build TF-IDF vectorizer on the combined attributes
    vectorizer = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=5000,
        min_df=1,
        stop_words=None,
    )
    drug_features = vectorizer.fit_transform(df["all_attributes"])
    print(f"Feature matrix shape: {drug_features.shape}")

    # Compute cosine similarity matrix
    similarity_matrix = cosine_similarity(drug_features)
    print(f"Similarity matrix shape: {similarity_matrix.shape}")

    # Save artifacts
    out_dir = os.path.dirname(__file__)
    joblib.dump(vectorizer, os.path.join(out_dir, "drug_vectorizer.joblib"))
    joblib.dump(similarity_matrix, os.path.join(out_dir, "drug_similarity_matrix.joblib"))
    joblib.dump(drug_features, os.path.join(out_dir, "drug_features.joblib"))
    print(f"Models saved to {out_dir}")


def recommend(disease_name, patient_age=30, allergies=None):
    """Recommend drugs for a given disease description."""
    out_dir = os.path.dirname(__file__)
    vectorizer = joblib.load(os.path.join(out_dir, "drug_vectorizer.joblib"))
    similarity_matrix = joblib.load(os.path.join(out_dir, "drug_similarity_matrix.joblib"))
    drug_features = joblib.load(os.path.join(out_dir, "drug_features.joblib"))
    df = pd.read_csv(os.path.join(out_dir, "drug_database.csv"))

    # Vectorize the query
    query_vec = vectorizer.transform([disease_name])

    # Compute similarity to all drugs
    query_sim = cosine_similarity(query_vec, drug_features).flatten()

    # Get top 5 indices
    top_indices = np.argsort(query_sim)[::-1][:5]

    results = []
    for idx in top_indices:
        drug = df.iloc[idx]
        results.append({
            "drug_name": drug["drug_name"],
            "category": drug["category"],
            "match_score": round(float(query_sim[idx]), 4),
            "side_effects": drug["side_effects_text"].split(),
            "indications": drug["indications_text"].split(),
            "contraindications": drug["contraindications_text"].split(),
        })

    # Check allergy contraindications
    if allergies:
        for r in results:
            allergy_flags = [a for a in allergies.split(",") if a.strip() in r["contraindications"]]
            r["drug_interaction_warnings"] = allergy_flags if allergy_flags else []

    return results


if __name__ == "__main__":
    train()

    # Test
    print("\nTest recommendation for '咳嗽发热上呼吸道感染':")
    results = recommend("咳嗽发热上呼吸道感染")
    for r in results:
        print(f"  {r['drug_name']}: score={r['match_score']}, cat={r['category']}")
