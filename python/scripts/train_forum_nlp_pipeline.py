"""
Forum Content Quality Scoring & Classification - NLP Pipeline
==============================================================
Train NLP models for:
1. Post quality scoring (RandomForest regression, 1-10 scale)
2. Content category classification (LogisticRegression multi-class)
3. Key topic extraction

Dataset: 10,000 synthetic forum posts across 8 categories
Output model: ../models/forum_nlp_pipeline.pkl

Usage: python train_forum_nlp_pipeline.py
"""

import numpy as np
import pandas as pd
import pickle
import os
import json
import re
import logging
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, classification_report, accuracy_score, r2_score
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    log.error("sklearn not installed. Install: pip install scikit-learn")
    exit(1)

try:
    from scipy.sparse import hstack as sparse_hstack, issparse
except ImportError:
    sparse_hstack = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)

# ---------- Hyperparams ----------
N_SAMPLES = 10000
TEST_SIZE = 0.2

CATEGORIES = [
    '技术讨论', '项目求助', '经验分享', '资源推荐',
    '行业动态', '求职交流', '学术问答', '闲聊灌水'
]

# Keywords per category (used for noisy label generation)
CATEGORY_KEYWORDS = {
    '技术讨论': ['框架', '架构', '性能', '优化', '算法', '设计模式', '代码', '编程', 'debug', 'bug',
                  '部署', '数据库', '缓存', '并发', '分布式', '微服务', '容器', '云原生'],
    '项目求助': ['求助', '报错', 'error', '问题', '怎么办', '急', '求教', '请教', '在线等', '没有头绪'],
    '经验分享': ['经验', '踩坑', '总结', '心得', '实践', '实战', '记录', '复盘', '分享一下', '推荐'],
    '资源推荐': ['推荐', '资源', '教程', '课程', '书', '视频', '博客', '工具', '网站', '学习资料'],
    '行业动态': ['新闻', '发布', '更新', '趋势', '未来', '报告', '调查', '融资', '收购', '裁员'],
    '求职交流': ['面试', '简历', 'offer', '内推', '跳槽', '薪资', '实习', '校招', '社招', '面经'],
    '学术问答': ['为什么', '原理', '概念', '区别', '理解', '解释', '证明', '理论', '本质', '如何实现'],
    '闲聊灌水': ['水帖', '签到', '闲聊', '吐槽', '日常', '哈哈哈哈', '哈哈', '笑死', '绝了', '666'],
}

TECH_TERMS = [
    'Spring Boot', 'Vue.js', 'MySQL', 'Redis', 'Docker', 'Kubernetes',
    'Python', 'Java', 'Go', 'Rust', '微服务', '容器化', '数据库',
    'AI', '机器学习', '深度学习', 'NLP', 'API', 'REST', 'gRPC',
    '消息队列', 'Kafka', 'Elasticsearch', 'MongoDB', 'PostgreSQL',
    'React', 'TypeScript', 'Node.js', 'Flask', 'Django',
    '敏捷开发', 'DevOps', 'CI/CD', 'Git', 'Linux', 'AWS',
]


def generate_forum_posts(n=10000):
    """Generate synthetic forum posts with realistic quality variation."""
    np.random.seed(SEED)

    titles_templates = {
        '技术讨论': [
            "关于{}在{}中的{}方案探讨",
            "{} vs {}：{}场景下的{}对比",
            "深入理解{}的原理与{}实现",
            "{}实践：如何优化{}的{}",
            "从零开始搭建基于{}的{}系统",
        ],
        '项目求助': [
            "求助：{}遇到的{}问题",
            "{}报错：{}，有没有大佬遇到过？",
            "急！{}环境下的{}配置问题",
            "前端{}时出现{}，求解决方案",
            "{}框架{}版本出现{}不兼容",
        ],
        '经验分享': [
            "{}三年经验总结：该不该{}",
            "从{}到{}，我的{}转型之路",
            "分享一份超详细的{}学习路线",
            "关于{}的{}实践总结",
            "使用{}后，{}效率提升了{}倍",
        ],
        '资源推荐': [
            "推荐几本关于{}的经典{}",
            "{}入门必看的{}个{}资源",
            "整理了{}个实用的{}工具",
            "分享一份我珍藏的{}学习资料",
            "2024年最好的{}课程推荐",
        ],
        '行业动态': [
            "刚刚！{}发布了{}版本",
            "2024年{}行业{}趋势分析",
            "重磅：{}领域出现{}突破",
            "关于{}公司{}战略的分析",
            "全球{}市场报告：{}增长{}%",
        ],
        '求职交流': [
            "{}大厂{}面经：{}轮技术面",
            "{}岗位的{}到底该怎么准备",
            "拿了{}个{}offer，求建议",
            "工作{}年后想跳槽，值得吗",
            "应届生{}经验分享：如何拿到{}offer",
        ],
        '学术问答': [
            "为什么{}会导致{}？求原理解释",
            "{}和{}有什么区别？",
            "关于{}中{}的理解，不知道对不对",
            "如何理解{}的{}概念？",
            "{}的{}原理是什么？",
        ],
        '闲聊灌水': [
            "今天{}又是摸鱼的一天",
            "{}了，大家{}都在干嘛",
            "哈哈哈哈这个{}太搞笑了",
            "吐槽一下{}的{}，绝了！",
            "{}这种{}是不是只有我一个人觉得？",
        ],
    }

    posts = []
    for i in range(n):
        # Noisy category assignment: 85% follow keyword pattern, 15% random
        if np.random.random() < 0.85:
            category = np.random.choice(CATEGORIES, p=[0.20, 0.15, 0.18, 0.10, 0.10, 0.12, 0.10, 0.05])
        else:
            category = np.random.choice(CATEGORIES)

        templates = titles_templates.get(category, titles_templates['闲聊灌水'])
        template = np.random.choice(templates)
        filled_title = template
        for _ in range(template.count('{}')):
            filled_title = filled_title.replace('{}', np.random.choice(TECH_TERMS), 1)

        # Generate body with category keywords + random tech terms
        body_length = np.random.randint(30, 600)
        cat_keywords = CATEGORY_KEYWORDS.get(category, ['技术', '问题'])
        all_words = cat_keywords + TECH_TERMS + ['的', '了', '是', '在', '有', '不', '就', '都', '和', '也']
        body = ' '.join(np.random.choice(all_words, body_length))

        full_text = filled_title + ' ' + body

        # Compute quality score
        word_count = len(full_text.split())
        has_code = any(kw in full_text.lower() for kw in ['import', 'def ', 'class ', 'const ', 'function'])
        has_question = '?' in full_text or '？' in full_text
        keyword_hits = sum(1 for kw in cat_keywords if kw in filled_title or kw in body[:200])

        quality = (3.0 + min(3.0, word_count / 250) + (1.2 if has_code else 0)
                   + (1.0 if has_question else 0) + min(2.0, keyword_hits * 0.4)
                   + (0.5 if len(filled_title) > 15 else 0)
                   + np.random.normal(0, 0.6))
        quality = max(1.0, min(10.0, round(quality, 1)))

        posts.append({
            'post_id': i + 1,
            'title': filled_title,
            'body': body,
            'category': category,
            'quality_score': quality,
            'word_count': word_count,
        })

    df = pd.DataFrame(posts)
    log.info(f"Generated {n} forum posts across {len(CATEGORIES)} categories")
    log.info(f"Quality: {df['quality_score'].min():.1f} - {df['quality_score'].max():.1f}, "
             f"mean={df['quality_score'].mean():.1f}")
    for cat in CATEGORIES:
        log.info(f"  {cat}: {(df['category']==cat).sum()}")
    return df


def extract_text_features(text_series):
    """Extract meta features from text."""
    features = pd.DataFrame()
    features['word_count'] = text_series.str.split().str.len()
    features['char_count'] = text_series.str.len()
    features['avg_word_len'] = features['char_count'] / (features['word_count'] + 1)
    features['unique_word_ratio'] = text_series.apply(
        lambda x: len(set(x.split())) / max(1, len(x.split())) if isinstance(x, str) else 0
    )
    features['punctuation_count'] = text_series.apply(
        lambda x: sum(1 for c in str(x) if c in '，。！？,.!?;；：:""\'') if isinstance(x, str) else 0
    )
    features['has_numbers'] = text_series.apply(
        lambda x: int(bool(re.search(r'\d+', str(x)))) if isinstance(x, str) else 0
    )
    features['has_english'] = text_series.apply(
        lambda x: int(bool(re.search(r'[a-zA-Z]{2,}', str(x)))) if isinstance(x, str) else 0
    )
    return features.fillna(0)


def main():
    log.info("=" * 60)
    log.info(f"Forum NLP Pipeline ({N_SAMPLES} posts)")
    log.info("=" * 60)

    # 1. Generate data
    df = generate_forum_posts(N_SAMPLES)
    df['full_text'] = df['title'] + ' ' + df['body']

    # Save sample
    sample_path = os.path.join(os.path.dirname(BASE_DIR), 'data', 'sample_forum_posts.csv')
    df.head(1000).to_csv(sample_path, index=False)
    log.info(f"Sample saved to {sample_path}")

    # =========================================================
    # 2. QUALITY SCORING MODEL
    # =========================================================
    log.info(f"\n── Training Quality Scoring Model ──")

    meta_features = extract_text_features(df['full_text'])

    # TF-IDF
    log.info("Fitting TF-IDF vectorizer...")
    q_tfidf = TfidfVectorizer(
        max_features=1500,
        ngram_range=(1, 2),
        max_df=0.85,
        min_df=3,
        strip_accents='unicode',
        analyzer='char_wb',
        sublinear_tf=True,
    )
    q_tfidf_matrix = q_tfidf.fit_transform(df['full_text'])
    log.info(f"  TF-IDF matrix shape: {q_tfidf_matrix.shape}")

    # Combine features
    meta_array = meta_features.values.astype(np.float64)
    if sparse_hstack is not None:
        quality_features = sparse_hstack([q_tfidf_matrix, meta_array])
    else:
        quality_features = np.hstack([q_tfidf_matrix.toarray(), meta_array])
    log.info(f"  Combined features shape: {quality_features.shape}")

    y_quality = df['quality_score'].values

    X_train_q, X_test_q, y_train_q, y_test_q = train_test_split(
        quality_features, y_quality, test_size=TEST_SIZE, random_state=SEED
    )

    quality_model = RandomForestRegressor(
        n_estimators=300,
        max_depth=18,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=SEED
    )
    quality_model.fit(X_train_q, y_train_q)
    q_pred = quality_model.predict(X_test_q)
    q_mae = mean_absolute_error(y_test_q, q_pred)
    q_r2 = r2_score(y_test_q, q_pred)
    log.info(f"  Quality Scoring MAE: {q_mae:.3f}, R²: {q_r2:.3f}")

    # =========================================================
    # 3. CATEGORY CLASSIFIER
    # =========================================================
    log.info(f"\n── Training Category Classifier ──")

    c_tfidf = TfidfVectorizer(
        max_features=2500,
        ngram_range=(1, 3),
        max_df=0.8,
        min_df=3,
        analyzer='char_wb',
        sublinear_tf=True,
    )
    X_cat = c_tfidf.fit_transform(df['full_text'])
    y_cat = df['category'].values
    log.info(f"  TF-IDF matrix shape: {X_cat.shape}")

    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_cat, y_cat, test_size=TEST_SIZE, random_state=SEED, stratify=y_cat
    )

    classifier = LogisticRegression(
        C=1.5,
        max_iter=500,
        solver='lbfgs',
        random_state=SEED,
        n_jobs=-1,
    )
    classifier.fit(X_train_c, y_train_c)
    c_pred = classifier.predict(X_test_c)
    c_acc = accuracy_score(y_test_c, c_pred)
    log.info(f"  Classification Accuracy: {c_acc:.2%}")
    log.info(f"\n  Classification Report:")
    for line in classification_report(y_test_c, c_pred, zero_division=0).split('\n'):
        log.info(f"  {line}")

    # =========================================================
    # 4. SAVE PIPELINE
    # =========================================================
    pipeline = {
        'quality_model': quality_model,
        'quality_tfidf': q_tfidf,
        'quality_meta_columns': list(meta_features.columns),
        'classifier': classifier,
        'classifier_tfidf': c_tfidf,
        'categories': CATEGORIES,
        'n_quality_features': quality_features.shape[1],
        'metrics': {
            'quality_mae': float(q_mae),
            'quality_r2': float(q_r2),
            'classification_accuracy': float(c_acc),
        },
    }

    model_path = os.path.join(MODELS_DIR, 'forum_nlp_pipeline.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(pipeline, f)
    log.info(f"\n✅ Pipeline saved to {model_path}")

    # Config
    config = {
        'model_file': 'forum_nlp_pipeline.pkl',
        'n_samples': N_SAMPLES,
        'quality_mae': round(float(q_mae), 3),
        'quality_r2': round(float(q_r2), 3),
        'classification_accuracy': round(float(c_acc), 4),
        'categories': CATEGORIES,
        'tfidf_features_quality': q_tfidf_matrix.shape[1],
        'tfidf_features_classifier': X_cat.shape[1],
        'meta_features': list(meta_features.columns),
    }
    config_path = os.path.join(MODELS_DIR, 'forum_nlp_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    log.info(f"✅ Config saved to {config_path}")

    # =========================================================
    # 5. DEMO PREDICTIONS
    # =========================================================
    log.info(f"\n📌 Sample Predictions:")
    test_titles = [
        "求助：Spring Boot启动报错NoSuchBeanDefinitionException",
        "三年Java经验总结：从入门到放弃再到重构",
        "哈哈哈哈今天又是摸鱼的一天",
        "推荐几本入门深度学习的经典教材",
    ]

    for title in test_titles:
        # QA: ensure test features have same columns as training
        test_meta = extract_text_features(pd.Series([title]))
        test_tfidf = q_tfidf.transform([title])
        test_meta_arr = test_meta.values.astype(np.float64)
        if sparse_hstack is not None:
            test_feat = sparse_hstack([test_tfidf, test_meta_arr])
        else:
            test_feat = np.hstack([test_tfidf.toarray(), test_meta_arr])
        quality_pred = quality_model.predict(test_feat)[0]

        # Classification
        test_tfidf_c = c_tfidf.transform([title])
        cat_pred = classifier.predict(test_tfidf_c)[0]
        cat_probs = classifier.predict_proba(test_tfidf_c)[0]
        max_prob = max(cat_probs)

        log.info(f"  '{title[:45]}...'")
        log.info(f"    → Quality: {quality_pred:.1f}/10 | Category: {cat_pred} ({max_prob:.0%})")

    log.info("\n🎉 Forum NLP Pipeline training complete!")


if __name__ == '__main__':
    main()
