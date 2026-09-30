"""
AI Empowerment Platform - Python ML Model API Server
====================================================
轻量入口：注册 Blueprint 并启动 Flask 服务。
领域路由已按模块拆分到 server/ 下各 *_routes.py 文件。
模型加载使用 model_loader 实现懒加载 + 重试机制。
"""
import os
import sys
import logging
from flask import Flask, jsonify
from flask_cors import CORS

# Windows 控制台/管道默认使用 GBK(cp936)，直接 print emoji 会抛 UnicodeEncodeError，
# 导致依赖打印的接口（如 /medical/v3/symptom-retrain）返回 500。
# 这里保留原有编码，仅把编码错误降级为替换字符（中文不受影响，emoji 显示为 ?），避免崩溃。
try:
    sys.stdout.reconfigure(errors='replace')
    sys.stderr.reconfigure(errors='replace')
except Exception:
    pass

# ────────────────────── 路径配置 ──────────────────────
# 确保能导入 server 下的模块（同时支持 python app.py 和 python server/app.py 两种启动方式）
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJ_DIR = os.path.dirname(_FILE_DIR)  # python/
if _FILE_DIR not in sys.path:
    sys.path.insert(0, _FILE_DIR)
if _PROJ_DIR not in sys.path:
    sys.path.insert(0, _PROJ_DIR)

MODELS_DIR = os.path.join(_PROJ_DIR, 'models')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# ────────────────────── Flask 应用 ──────────────────────
app = Flask(__name__)
# 默认只允许本机前端开发源，避免任意站点跨域访问内部 ML 服务
_allowed_origins = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8088,http://127.0.0.1:8088",
).split(",")
CORS(app, origins=[o.strip() for o in _allowed_origins if o.strip()])

# ────────────────────── 全局模型缓存 ──────────────────────
from server.model_loader import warmup_models
_loaded = warmup_models()
log.info(f"Models loaded: {sum(1 for v in _loaded.values() if v)}/{len(_loaded)}")

# ────────────────────── 注册 Blueprint ──────────────────────
from server.ct.routes import ct_bp
app.register_blueprint(ct_bp)

from server.medical_routes import medical_bp
app.register_blueprint(medical_bp)

# 领域路由（由子模块按需注册）
try:
    from server.finance_routes import finance_bp
    app.register_blueprint(finance_bp)
    log.info("✅ finance_routes registered")
except ImportError as e:
    log.warning(f"⚠️  finance_routes not available: {e}")

try:
    from server.environment_routes import environment_bp
    app.register_blueprint(environment_bp)
    log.info("✅ environment_routes registered")
except ImportError as e:
    log.warning(f"⚠️  environment_routes not available: {e}")

try:
    from server.traffic_routes import traffic_bp
    app.register_blueprint(traffic_bp)
    log.info("✅ traffic_routes registered")
except ImportError as e:
    log.warning(f"⚠️  traffic_routes not available: {e}")

# ── V4 Enhanced Module Routes (新增强模块) ──
try:
    from server.enhanced_routes import enhanced_bp
    app.register_blueprint(enhanced_bp)
    log.info("✅ enhanced_routes registered (Energy/Forum/Dev/Traffic/Finance/Environment)")
except ImportError as e:
    log.warning(f"⚠️  enhanced_routes not available: {e}")

# ────────────────────── 健康检查 ──────────────────────
@app.route('/api/health', methods=['GET'])
def health():
    from server.model_loader import get_models_dict
    models_dict = get_models_dict()
    return jsonify({
        "status": "ok",
        "all_models_loaded": all(v is not None for v in models_dict.values()) if models_dict else False,
        "models": {k: v is not None for k, v in models_dict.items()} if models_dict else {}
    })

# ────────────────────── 启动 ──────────────────────
if __name__ == '__main__':
    from server.ct.session import init_ct_data
    init_ct_data()

    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    log.info(f"Starting AI Empowerment ML Server on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)
