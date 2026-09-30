"""
Semantic Medical Search: TF-IDF + Cosine Similarity
Generates: search_vectorizer.joblib, search_tfidf_matrix.joblib, search_records.joblib
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

MEDICAL_TEMPLATES = [
    "患者因{症状}{时间}就诊，诊断为{疾病}，予{治疗}治疗，{效果}。",
    "主诉：{症状}。查体：{体征}。辅助检查：{检查}。诊断：{疾病}。",
    "患者{年龄}岁，{性别}，因{症状}{时间}入院。既往{既往史}。",
    "入院诊断：{疾病}。诊疗经过：给予{治疗}治疗{天数}天，患者{效果}。",
    "门诊病历：患者{症状}反复发作{时间}，查体{体征}，建议{建议}。",
    "出院小结：患者因{疾病}住院治疗，住院期间{治疗}，{效果}出院。",
    "急诊记录：患者{时间}因{症状}急诊就诊，诊断为{疾病}，处理后{效果}。",
    "检验报告：{检查}结果提示{结果}，建议定期复查。",
    "影像学检查：{部位}{影像}，考虑{疾病}可能。",
    "病理报告：{部位}活检示{病理}，符合{疾病}表现。",
]

SYMPTOMS = ["发热", "咳嗽", "头痛", "腹痛", "胸痛", "呼吸困难", "恶心呕吐", "乏力",
            "关节痛", "皮疹", "水肿", "出血", "意识障碍", "心悸", "腹泻"]
DISEASES = ["上呼吸道感染", "肺炎", "胃炎", "高血压", "糖尿病", "冠心病", "脑梗死",
            "慢性阻塞性肺病", "肝炎", "肾炎", "贫血", "甲亢", "骨折", "阑尾炎"]
TREATMENTS = ["抗感染治疗", "对症支持治疗", "手术治疗", "介入治疗", "化疗", "放疗",
              "免疫治疗", "靶向治疗", "中医药治疗", "康复治疗"]
EFFECTS = ["好转", "痊愈", "稳定", "缓解", "明显改善", "部分缓解", "无效", "加重"]
SIGNS = ["体温升高", "血压升高", "肺部啰音", "腹部压痛", "下肢水肿", "皮肤黄染",
         "浅表淋巴结肿大", "心脏杂音", "神经系统阳性体征"]
CHECKS = ["血常规", "生化全套", "胸部CT", "腹部B超", "心电图", "MRI", "X光片",
          "胃镜", "肠镜", "超声心动图"]
ADVICE = ["定期随访", "注意休息", "低盐饮食", "规律服药", "适当运动", "避免劳累",
          "控制饮食", "定期复查"]
IMAGES = ["可见高密度影", "可见低密度灶", "增强后明显强化", "边界清晰", "边界模糊",
          "有钙化", "有积液", "未见明显异常"]
PATHS = ["可见炎性细胞浸润", "见异型细胞", "见坏死组织", "见纤维化", "见增生"]
PARTS = ["肺部", "肝脏", "胃部", "脑部", "肾脏", "骨关节", "甲状腺", "乳腺"]

DURATIONS = ["1天", "2天", "3天", "1周", "2周", "1个月", "3个月", "半年", "1年"]
TIMES = ["3天前", "1周前", "2周前", "1个月前", "半年前", "1年前", "3小时前", "急诊"]
PAST_HISTORY = ["高血压病史", "糖尿病病史", "手术史", "外伤史", "过敏史", "无特殊"]


def generate_records(n=600):
    """Generate synthetic medical records."""
    records = []

    for i in range(n):
        template = random.choice(MEDICAL_TEMPLATES)
        record = template.format(
            症状=random.choice(SYMPTOMS),
            时间=random.choice(TIMES),
            疾病=random.choice(DISEASES),
            治疗=random.choice(TREATMENTS),
            效果=random.choice(EFFECTS),
            体征=random.choice(SIGNS),
            检查=random.choice(CHECKS),
            年龄=random.randint(15, 85),
            性别=random.choice(["男", "女"]),
            既往史=random.choice(PAST_HISTORY),
            天数=random.randint(3, 30),
            建议=random.choice(ADVICE),
            部位=random.choice(PARTS),
            影像=random.choice(IMAGES),
            病理=random.choice(PATHS),
            结果=random.choice(["升高", "降低", "正常", "异常"]),
        )
        records.append({
            "record_id": f"MR-{i+1:04d}",
            "text": record,
            "disease": random.choice(DISEASES),
            "department": random.choice(["内科", "外科", "儿科", "急诊科"]),
        })

    df = pd.DataFrame(records)
    print(f"Generated {len(df)} medical records")
    return df


def train():
    print("=" * 60)
    print("Training Semantic Medical Search")
    print("=" * 60)

    df = generate_records(600)

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(1, 3),
        max_features=8000,
        min_df=2,
    )
    tfidf_matrix = vectorizer.fit_transform(df["text"])
    print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")

    out_dir = os.path.dirname(__file__)
    joblib.dump(vectorizer, os.path.join(out_dir, "search_vectorizer.joblib"))
    joblib.dump(tfidf_matrix, os.path.join(out_dir, "search_tfidf_matrix.joblib"))
    joblib.dump(df, os.path.join(out_dir, "search_records.joblib"))
    print("Models saved.")


def search(query: str, top_k=10):
    """Search medical records by query."""
    out_dir = os.path.dirname(__file__)
    vectorizer = joblib.load(os.path.join(out_dir, "search_vectorizer.joblib"))
    tfidf_matrix = joblib.load(os.path.join(out_dir, "search_tfidf_matrix.joblib"))
    df = joblib.load(os.path.join(out_dir, "search_records.joblib"))

    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            record = df.iloc[idx]
            text = record["text"]
            # Generate snippet
            snippet = text[:100] + "..." if len(text) > 100 else text
            results.append({
                "record_id": record["record_id"],
                "summary_snippet": snippet,
                "relevance_score": round(float(scores[idx]), 4),
                "disease": record["disease"],
                "department": record["department"],
            })

    return {"results": results, "total_found": len(results)}


if __name__ == "__main__":
    train()

    # Test
    result = search("发热咳嗽呼吸困难")
    print(f"\nSearch: '发热咳嗽呼吸困难'")
    for r in result["results"][:3]:
        print(f"  [{r['record_id']}] score={r['relevance_score']:.3f}: {r['summary_snippet'][:60]}...")
