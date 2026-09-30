"""
CT 影像工作台 — 缓存与会话管理
"""
import os
import time
from pathlib import Path
from typing import Optional
import uuid
import threading

CACHE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / 'ct_cache'
CACHE_EXPIRY_SECONDS = 3600
MAX_SESSIONS = 50
SESSIONS: dict = {}
_lock = threading.Lock()

DATA_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '..' / '..' / 'data' / 'ct'
OUTPUT_DIR = DATA_DIR / 'output'

# CQ500 数据集路径
CQ500_DIR = DATA_DIR / 'cq500'
CQ500_VOLUMES_DIR = CQ500_DIR / 'volumes'
CQ500_METADATA_DIR = CQ500_DIR / 'metadata'
CQ500_PROCESSED_DIR = CQ500_DIR / 'processed'


def _cleanup_cache():
    """清理过期缓存"""
    now = time.time()
    expired = [k for k, v in SESSIONS.items() if now - v.get('created', 0) > CACHE_EXPIRY_SECONDS]
    for k in expired:
        del SESSIONS[k]


def _get_cache(session_id: str) -> Optional[dict]:
    with _lock:
        return SESSIONS.get(session_id)


def _set_cache(session_id: str, data: dict):
    with _lock:
        SESSIONS[session_id] = data
        # 有界缓存：超出上限时淘汰最旧的会话
        while len(SESSIONS) > MAX_SESSIONS:
            oldest = min(SESSIONS, key=lambda k: SESSIONS[k].get('created', 0))
            del SESSIONS[oldest]


def _get_or_create_session() -> str:
    with _lock:
        _cleanup_cache()
        sid = str(uuid.uuid4())
        SESSIONS[sid] = {'created': time.time()}
        return sid


def init_ct_data():
    """初始化CT数据目录"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def make_response(success: bool = True, data: dict = None, error: str = None, session_id: str = None):
    """构造统一响应"""
    resp = {"success": success}
    if data:
        resp["data"] = data
    if error:
        resp["error"] = error
    if session_id:
        resp["sessionId"] = session_id
    return resp
