"""
AI Development Trend Analyzer - Time Series + NLP
=================================================
Analyzes AI development trends from historical event data.
Uses TF-IDF + time series decomposition to identify:
1. Technology maturity levels over time
2. Research hotspots and emerging trends
3. Technology lifecycle stage classification

Output model: ../models/development_trend_analyzer.pkl

Usage: python train_development_trend_analyzer.py
"""

import numpy as np
import pandas as pd
import pickle
import os
import json
import logging
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import NMF, PCA
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    log.error("sklearn not installed.")
    exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)
N_EVENTS = 5000


def generate_ai_events(n=5000):
    """Generate synthetic AI development events spanning different eras."""
    np.random.seed(SEED)

    eras = {
        '1950-1970': {'years': range(1950, 1971), 'weight': 0.05,
                      'keywords': ['图灵', '感知机', 'Lisp', '逻辑理论家', '神经网络', '符号推理',
                                   '机器翻译', '模式识别', '数学证明', '博弈论']},
        '1970-1990': {'years': range(1970, 1991), 'weight': 0.08,
                      'keywords': ['专家系统', '知识库', '推理引擎', 'MYCIN', 'DENDRAL', '机器学习',
                                   '反向传播', '决策树', '自然语言', '规划']},
        '1990-2005': {'years': range(1990, 2005), 'weight': 0.12,
                      'keywords': ['SVM', '随机森林', 'Adaboost', '贝叶斯网络', 'HMM', 'CRF',
                                   '数据挖掘', '聚类', '降维', '强化学习', 'AlphaGo']},
        '2005-2015': {'years': range(2005, 2016), 'weight': 0.25,
                      'keywords': ['深度学习', 'ImageNet', 'CNN', 'RNN', 'LSTM', 'GPU训练',
                                   'Word2Vec', 'Dropout', 'BatchNorm', '迁移学习', '语义分割']},
        '2016-2020': {'years': range(2016, 2021), 'weight': 0.30,
                      'keywords': ['Transformer', 'BERT', 'GPT', 'GAN', '图神经网络', '自监督',
                                   '预训练', 'BERT', 'XLNet', '多模态', '知识蒸馏', '联邦学习']},
        '2020-2026': {'years': range(2020, 2027), 'weight': 0.20,
                      'keywords': ['大模型', 'ChatGPT', '多模态', 'AIGC', '扩散模型', 'RLHF',
                                   'LangChain', '向量数据库', 'RAG', 'Agent', '具身智能', 'AI安全']},
    }

    # Technology categories
    tech_categories = {
        '计算机视觉': ['CNN', 'ImageNet', 'YOLO', '语义分割', '目标检测', '图像生成', 'GAN', '扩散模型'],
        '自然语言处理': ['NLP', 'BERT', 'GPT', 'Transformer', '机器翻译', '情感分析', '词向量', '预训练'],
        '语音技术': ['语音识别', 'TTS', '声学模型', '语音合成', '说话人识别', '语音分离'],
        '强化学习': ['RL', 'Q学习', '策略梯度', 'MCTS', 'AlphaGo', '多智能体', '奖励函数'],
        '知识表示': ['知识图谱', '本体', '推理', '知识蒸馏', '符号推理', '逻辑'],
        'AI基础设施': ['GPU', 'TPU', 'MLOps', '模型部署', '联邦学习', '边缘计算', '分布式训练'],
    }

    events = []
    for era_name, era_info in eras.items():
        n_era = max(50, int(n * era_info['weight']))
        for _ in range(n_era):
            year = np.random.choice(list(era_info['years']))
            keywords = np.random.choice(era_info['keywords'],
                                        size=np.random.randint(2, 5), replace=False)

            # Technology category
            cat = np.random.choice(list(tech_categories.keys()))
            cat_kw = np.random.choice(tech_categories[cat], size=min(1, len(tech_categories[cat])))

            # Impact score (1-100)
            impact = np.random.beta(2, 3) * 100
            # Later years tend to have higher impact (survivorship bias)
            impact *= 1.0 + (year - 1950) / 100

            # Maturity level
            years_since = 2026 - year
            if years_since > 30:
                maturity = '成熟'
            elif years_since > 15:
                maturity = '增长'
            elif years_since > 5:
                maturity = '新兴'
            else:
                maturity = '前沿'

            # Research intensity (simulated citation count)
            research_intensity = np.random.poisson(max(1, impact * years_since / 10))

            description = ' '.join(list(keywords) + list(cat_kw))
            events.append({
                'year': year,
                'era': era_name,
                'description': description,
                'keywords': list(keywords),
                'category': cat,
                'impact_score': min(100, round(impact)),
                'maturity': maturity,
                'research_intensity': min(10000, research_intensity),
            })

    df = pd.DataFrame(events)
    log.info(f"Generated {len(df)} AI events spanning {df['year'].min()}-{df['year'].max()}")
    log.info(f"Category distribution:")
    for cat, count in df['category'].value_counts().items():
        log.info(f"  {cat}: {count}")
    return df


def build_trend_features(df):
    """Build features for trend analysis."""
    # Time-based aggregations
    yearly = df.groupby('year').agg({
        'impact_score': ['mean', 'sum', 'count'],
        'research_intensity': ['mean', 'sum'],
    }).fillna(0)
    yearly.columns = ['_'.join(c).strip() for c in yearly.columns]
    yearly = yearly.reset_index()
    yearly['year_since_1950'] = yearly['year'] - 1950

    # Rolling averages
    for col in ['impact_score_sum', 'research_intensity_sum', 'impact_score_count']:
        yearly[f'{col}_ma3'] = yearly[col].rolling(3, min_periods=1).mean()
        yearly[f'{col}_ma5'] = yearly[col].rolling(5, min_periods=1).mean()

    # Growth rates
    yearly['impact_growth'] = yearly['impact_score_sum'].pct_change(periods=1).fillna(0)
    yearly['research_growth'] = yearly['research_intensity_sum'].pct_change(periods=1).fillna(0)

    # Category diversity per year
    cat_diversity = df.groupby('year')['category'].apply(lambda x: len(set(x)))
    yearly['category_diversity'] = yearly['year'].map(cat_diversity).fillna(1)

    yearly = yearly.fillna(0).replace([np.inf, -np.inf], 0)
    return yearly


def main():
    log.info("=" * 60)
    log.info("AI Development Trend Analyzer Training")
    log.info("=" * 60)

    df = generate_ai_events(N_EVENTS)

    # Save sample
    sample_dir = os.path.join(BASE_DIR, '..', 'data')
    df.head(1000).to_csv(os.path.join(sample_dir, 'sample_ai_events.csv'), index=False)

    # 1. Build category evolution model (NMF on TF-IDF)
    log.info("\n── Building Technology Category Evolution Model ──")
    tfidf = TfidfVectorizer(max_features=1000, ngram_range=(1, 2), stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['description'])
    log.info(f"  TF-IDF: {tfidf_matrix.shape}")

    # NMF for topic extraction
    n_topics = 6
    nmf = NMF(n_components=n_topics, random_state=SEED, max_iter=500)
    topic_matrix = nmf.fit_transform(tfidf_matrix)
    df['topic'] = topic_matrix.argmax(axis=1)

    # Map topics to categories
    topic_categories = {}
    for topic_id in range(n_topics):
        top_words = [tfidf.get_feature_names_out()[i]
                     for i in nmf.components_[topic_id].argsort()[-5:]]
        log.info(f"  Topic {topic_id}: {', '.join(top_words)}")
        topic_categories[f'topic_{topic_id}'] = top_words

    # 2. Build trend features
    log.info("\n── Building Trend Time Series ──")
    trend_features = build_trend_features(df)
    log.info(f"  Trend features shape: {trend_features.shape}")

    # 3. Lifecycle stage classifier
    log.info("\n── Training Lifecycle Stage Classifier ──")
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report

    # Features for stage classification
    stage_features = df[['year', 'impact_score', 'research_intensity']].copy()
    stage_features['years_since'] = 2026 - stage_features['year']
    stage_features['impact_per_year'] = stage_features['impact_score'] / (stage_features['years_since'] + 1)

    X_stage = stage_features.values
    y_stage = df['maturity'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X_stage, y_stage, test_size=0.2, random_state=SEED
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    stage_clf = RandomForestClassifier(
        n_estimators=200, max_depth=10, random_state=SEED
    )
    stage_clf.fit(X_train, y_train)
    y_pred = stage_clf.predict(X_test)

    log.info(f"\n  Classification Report:")
    for line in classification_report(y_test, y_pred).split('\n'):
        log.info(f"    {line}")

    # 4. Capability prediction model
    log.info("\n── Building Capability Prediction Model ──")
    from sklearn.linear_model import LinearRegression

    # Predict next decade's impact based on historical trends
    X_time = trend_features['year_since_1950'].values.reshape(-1, 1)
    y_impact = trend_features['impact_score_sum'].values

    impact_model = LinearRegression()
    impact_model.fit(X_time, y_impact)
    r2 = impact_model.score(X_time, y_impact)
    log.info(f"  Impact prediction R²: {r2:.4f}")

    # Predict for next 5 years
    future_years = np.arange(2026, 2031).reshape(-1, 1)
    future_impact = impact_model.predict(future_years)
    log.info(f"  2026 impact prediction: {future_impact[0]:.0f}")

    # 5. Save model
    model_data = {
        'tfidf': tfidf,
        'nmf': nmf,
        'n_topics': n_topics,
        'topic_categories': topic_categories,
        'stage_classifier': stage_clf,
        'stage_scaler': scaler,
        'impact_predictor': impact_model,
        'trend_features': trend_features.to_dict('records'),
        'stage_labels': ['成熟', '增长', '新兴', '前沿'],
        'category_techs': {
            '计算机视觉': ['CNN', 'ImageNet', 'YOLO', 'GAN', '扩散模型'],
            '自然语言处理': ['BERT', 'GPT', 'Transformer', 'RAG', 'Agent'],
            '语音技术': ['语音识别', 'TTS', '语音合成'],
            '强化学习': ['RL', 'AlphaGo', '多智能体'],
            '知识表示': ['知识图谱', '推理', '符号AI'],
            'AI基础设施': ['GPU', 'MLOps', '联邦学习', '边缘计算'],
        },
    }

    model_path = os.path.join(MODELS_DIR, 'development_trend_analyzer.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    log.info(f"\n✅ Model saved to {model_path}")

    # Config
    config = {
        'model_file': 'development_trend_analyzer.pkl',
        'n_events': N_EVENTS,
        'n_topics': n_topics,
        'stage_r2': round(float(r2), 4),
    }
    config_path = os.path.join(MODELS_DIR, 'development_trend_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # 6. Demo analysis
    log.info(f"\n📌 Trend Analysis Summary:")
    log.info(f"  Total events analyzed: {len(df)}")
    log.info(f"  Year range: {df['year'].min()}-{df['year'].max()}")
    log.info(f"  Categories: {df['category'].nunique()}")

    # Current hot topics
    recent = df[df['year'] >= 2022]
    top_cats = recent['category'].value_counts().head(3)
    log.info(f"\n  Hot categories (2022-2026):")
    for cat, count in top_cats.items():
        log.info(f"    {cat}: {count} events")

    log.info("\n🎉 Development Trend Analyzer training complete!")


if __name__ == '__main__':
    main()
