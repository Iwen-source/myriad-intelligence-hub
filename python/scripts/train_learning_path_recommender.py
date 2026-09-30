"""
Learning Path Recommender - Collaborative & Content-based Filtering
====================================================================
Train a hybrid recommendation system for AI/tech learning paths.
Combines collaborative filtering (user similarity) with content-based filtering
(skill vector similarity) to recommend the optimal learning roadmap.

Output model: ../models/learning_path_recommender.pkl

Usage: python train_learning_path_recommender.py
"""

import numpy as np
import pandas as pd
import pickle
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import StandardScaler, MultiLabelBinarizer
    from sklearn.neighbors import NearestNeighbors
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import precision_score, recall_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    log.error("sklearn not installed. Install: pip install scikit-learn")
    exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)

# Define learning paths / skill trees
LEARNING_PATHS = {
    'ai_ml_engineer': {
        'name': 'AI/ML 工程师',
        'difficulty': 4,
        'category': 'AI',
        'duration_months': 8,
        'skills': ['Python', '线性代数', '概率统计', '机器学习基础', '深度学习',
                   'TensorFlow/PyTorch', 'NLP', '计算机视觉', '模型部署', 'MLOps'],
    },
    'full_stack_developer': {
        'name': '全栈开发工程师',
        'difficulty': 3,
        'category': '开发',
        'duration_months': 6,
        'skills': ['HTML/CSS', 'JavaScript', 'Vue.js/React', 'Node.js', 'Spring Boot',
                   '数据库', 'REST API', 'Docker', 'Git', 'CI/CD'],
    },
    'data_scientist': {
        'name': '数据科学家',
        'difficulty': 4,
        'category': '数据',
        'duration_months': 7,
        'skills': ['Python', 'SQL', '统计学', '数据可视化', '机器学习',
                   '特征工程', 'A/B测试', 'Spark', '数据仓库', 'Tableau'],
    },
    'devops_engineer': {
        'name': 'DevOps 工程师',
        'difficulty': 3,
        'category': '运维',
        'duration_months': 5,
        'skills': ['Linux', 'Docker', 'Kubernetes', 'CI/CD', 'Jenkins',
                   'Terraform', 'AWS/GCP', '监控系统', 'Shell脚本', '网络基础'],
    },
    'backend_engineer': {
        'name': '后端开发工程师',
        'difficulty': 3,
        'category': '开发',
        'duration_months': 5,
        'skills': ['Java', 'Spring Boot', 'MySQL', 'Redis', '消息队列',
                   '微服务', 'Docker', '设计模式', 'Git', 'REST API'],
    },
    'frontend_engineer': {
        'name': '前端开发工程师',
        'difficulty': 3,
        'category': '开发',
        'duration_months': 4,
        'skills': ['HTML/CSS', 'JavaScript', 'Vue.js/React', 'TypeScript',
                   'Webpack/Vite', '前端性能优化', '组件库', 'Git', '浏览器原理'],
    },
    'data_engineer': {
        'name': '数据工程师',
        'difficulty': 4,
        'category': '数据',
        'duration_months': 6,
        'skills': ['Python', 'SQL', 'Spark', 'Hadoop', 'Kafka',
                   '数据仓库', 'ETL', 'Airflow', 'MongoDB', 'ClickHouse'],
    },
    'ai_researcher': {
        'name': 'AI 研究员',
        'difficulty': 5,
        'category': 'AI',
        'duration_months': 12,
        'skills': ['Python', '高等数学', '概率统计', '机器学习', '深度学习',
                   '论文阅读', 'PyTorch', '强化学习', '生成模型', '学术写作'],
    },
    'cybersecurity_analyst': {
        'name': '网络安全分析师',
        'difficulty': 4,
        'category': '安全',
        'duration_months': 6,
        'skills': ['网络基础', '操作系统', 'Web安全', '渗透测试', '加密技术',
                   '安全工具', '日志分析', 'Python', '应急响应', '合规'],
    },
    'product_manager': {
        'name': '技术产品经理',
        'difficulty': 2,
        'category': '产品',
        'duration_months': 4,
        'skills': ['产品思维', '用户研究', '数据分析', 'Axure/Figma', '敏捷管理',
                   '需求分析', 'A/B测试', '文档写作', '沟通协作', '市场分析'],
    },
}


def generate_user_profiles(n_users=2000):
    """Generate synthetic user profiles with skills, experience, and preferences."""
    np.random.seed(SEED)

    # All unique skills
    all_skills = sorted(set(
        skill for path in LEARNING_PATHS.values()
        for skill in path['skills']
    ))
    n_skills = len(all_skills)

    users = []
    for uid in range(n_users):
        # Random skill level (0-5) for each skill
        skill_levels = np.random.beta(1.5, 3, n_skills) * 5

        # Some users are more advanced
        if np.random.random() < 0.3:
            skill_levels = np.clip(skill_levels + 1.5, 0, 5)

        # Experience
        years_exp = np.random.exponential(3) + 0.5
        years_exp = min(years_exp, 15)

        # Preferred difficulty
        pref_difficulty = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.15, 0.35, 0.30, 0.15])

        # Preferred category
        categories = ['AI', '开发', '数据', '运维', '安全', '产品']
        pref_category = np.random.choice(categories, p=[0.25, 0.30, 0.15, 0.10, 0.10, 0.10])

        # Current level (junior/mid/senior weighted by years)
        if years_exp < 1.5:
            level = 'junior'
        elif years_exp < 4:
            level = 'mid'
        else:
            level = 'senior'

        # Enrolled paths (some users already follow certain paths)
        enrolled = []
        path_keys = list(LEARNING_PATHS.keys())
        if np.random.random() < 0.7:
            chosen = np.random.choice(path_keys)
            enrolled.append(chosen)

        users.append({
            'user_id': uid,
            'years_experience': round(years_exp, 1),
            'level': level,
            'preferred_difficulty': pref_difficulty,
            'preferred_category': pref_category,
            'skill_levels': skill_levels.tolist(),
            'enrolled_paths': enrolled,
        })

    log.info(f"Generated {n_users} user profiles")
    log.info(f"Level distribution: junior={sum(1 for u in users if u['level']=='junior')}, "
             f"mid={sum(1 for u in users if u['level']=='mid')}, "
             f"senior={sum(1 for u in users if u['level']=='senior')}")
    return users, all_skills


def build_path_skill_matrix():
    """Build skill matrix for each learning path."""
    path_keys = list(LEARNING_PATHS.keys())
    all_skills = sorted(set(
        skill for path in LEARNING_PATHS.values()
        for skill in path['skills']
    ))

    matrix = np.zeros((len(path_keys), len(all_skills)))
    for i, key in enumerate(path_keys):
        for skill in LEARNING_PATHS[key]['skills']:
            j = all_skills.index(skill)
            matrix[i, j] = 1.0

    return matrix, path_keys, all_skills


def recommend_for_user(user_skills, n_recommendations=3):
    """
    Recommend learning paths for a user based on skill vector.
    Returns path recommendations with confidence scores.
    """
    path_matrix, path_keys, all_skills = build_path_skill_matrix()

    # User skill vector (same skill order)
    user_vec = np.array(user_skills).reshape(1, -1)

    # Content similarity = cosine similarity between user skills and path requirements
    content_sim = cosine_similarity(user_vec, path_matrix)[0]

    # Gap analysis: which paths have the most unexplored skills for the user
    gaps = []
    for i, key in enumerate(path_keys):
        path = LEARNING_PATHS[key]
        required_skills = path['skills']
        skill_idxs = [all_skills.index(s) for s in required_skills]
        user_skill_gaps = sum(1 for idx in skill_idxs if user_skills[idx] < 2.0)
        total_required = len(required_skills)
        gap_ratio = user_skill_gaps / total_required
        gaps.append(gap_ratio)

    # Combined score: higher similarity + moderate gap (not too many gaps, not too few)
    gap_penalty = np.array([max(0, g - 0.1) for g in gaps])  # at least 10% gap
    combined = content_sim - gap_penalty * 0.3

    # Filter out already enrolled
    # (enrollment filter done at application level)

    # Top N
    top_indices = np.argsort(combined)[::-1][:n_recommendations]

    recommendations = []
    for idx in top_indices:
        if combined[idx] > 0:
            path_key = path_keys[idx]
            path = LEARNING_PATHS[path_key]
            recommendations.append({
                'path_key': path_key,
                'name': path['name'],
                'difficulty': path['difficulty'],
                'category': path['category'],
                'duration_months': path['duration_months'],
                'match_score': round(float(combined[idx] * 100), 1),
                'skill_gaps': round(float(gaps[idx] * 100), 1),
                'skills_to_learn': [s for i, s in enumerate(LEARNING_PATHS[path_key]['skills'])
                                    if user_skills[all_skills.index(s)] < 2.0][:5],
            })

    return recommendations


def main():
    log.info("=" * 60)
    log.info("Learning Path Recommender - Model Training")
    log.info("=" * 60)

    # 1. Generate user data
    users, all_skills = generate_user_profiles(2000)

    # 2. Build path-skill matrix
    path_matrix, path_keys, _ = build_path_skill_matrix()
    log.info(f"Path-skill matrix: {path_matrix.shape} "
             f"({len(path_keys)} paths x {len(all_skills)} skills)")

    # 3. Train nearest neighbors for skill-based user clustering
    skill_vectors = np.array([u['skill_levels'] for u in users])
    scaler = StandardScaler()
    skill_vectors_scaled = scaler.fit_transform(skill_vectors)

    nn_model = NearestNeighbors(n_neighbors=10, metric='cosine', algorithm='brute')
    nn_model.fit(skill_vectors_scaled)
    log.info("✅ NearestNeighbors model trained for user similarity")

    # 4. Evaluate on test set (simulate recommendations)
    test_users = users[:100]
    hit_count = 0
    for u in test_users:
        recs = recommend_for_user(u['skill_levels'], n_recommendations=3)
        if recs:
            # Check if recommended path matches user's current path
            if u['enrolled_paths'] and any(r['path_key'] in u['enrolled_paths'] for r in recs):
                hit_count += 1

    log.info(f"Validation hit rate (known path in top-3): {hit_count}/{len(test_users)} "
             f"({hit_count/len(test_users):.1%})")

    # 5. Save model
    model_data = {
        'scaler': scaler,
        'nn_model': nn_model,
        'all_skills': all_skills,
        'path_matrix': path_matrix,
        'path_keys': path_keys,
        'learning_paths': LEARNING_PATHS,
        # 'recommend_func': recommend_for_user,  # 不复用pickle函数（会在route中直接用cosine_similarity计算）
    }

    model_path = os.path.join(MODELS_DIR, 'learning_path_recommender.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    log.info(f"\n✅ Model saved to {model_path}")

    # 6. Demo recommendations for sample users
    log.info("\n📌 Sample Recommendations:")
    sample_users = [
        {'name': '新手后端', 'skills': {s: i for i, s in enumerate(all_skills)}},
        {'name': '中级全栈', 'skills': {s: i for i, s in enumerate(all_skills)}},
        {'name': '高级AI', 'skills': {s: i for i, s in enumerate(all_skills)}},
    ]

    # Create specific skill profiles
    test_profiles = [
        # Junior backend developer
        [3 if s in ['Java', 'Spring Boot', 'MySQL', 'Git'] else
         1 if s in ['Docker', '微服务', 'Redis'] else
         2 if s in ['Python', 'Linux'] else
         0 for s in all_skills],
        # Mid-level full stack
        [4 if s in ['JavaScript', 'Vue.js/React', 'HTML/CSS', 'Git', '数据库'] else
         3 if s in ['Node.js', 'Spring Boot', 'Docker', 'TypeScript'] else
         1 if s in ['Kubernetes', 'AWS/GCP'] else
         0 for s in all_skills],
        # Senior AI researcher
        [5 if s in ['Python', '机器学习', '深度学习', 'PyTorch'] else
         4 if s in ['NLP', '计算机视觉', '概率统计'] else
         2 if s in ['模型部署', 'MLOps'] else
         1 if s in ['Java', 'SQL', 'Docker'] else
         0 for s in all_skills],
    ]

    profile_names = ['Junior Backend Developer',
                     'Mid-level Full Stack Developer',
                     'Senior AI Researcher']

    for i, (name, skills) in enumerate(zip(profile_names, test_profiles)):
        log.info(f"\n  ── {name} ──")
        recs = recommend_for_user(skills, n_recommendations=3)
        for j, rec in enumerate(recs):
            log.info(f"    {j+1}. {rec['name']} (match: {rec['match_score']}%)")
            log.info(f"       Difficulty: {rec['difficulty']}/5 | Duration: {rec['duration_months']}mo")
            log.info(f"       Skills to learn: {', '.join(rec['skills_to_learn'][:3])}")
            log.info(f"       Gap: {rec['skill_gaps']}%")

    # 7. Config
    config = {
        'model_file': 'learning_path_recommender.pkl',
        'n_paths': len(path_keys),
        'n_skills': len(all_skills),
        'model_type': 'cosine_similarity + nearest_neighbors',
        'path_names': {k: v['name'] for k, v in LEARNING_PATHS.items()},
        'categories': list(set(v['category'] for v in LEARNING_PATHS.values())),
    }
    config_path = os.path.join(MODELS_DIR, 'learning_path_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    log.info(f"✅ Config saved to {config_path}")

    log.info("\n🎉 Learning Path Recommender training complete!")


if __name__ == '__main__':
    main()
