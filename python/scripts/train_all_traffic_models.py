import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
"""
[TRAFFIC] 交通模块 - 一键训练所有模型

用法: python scripts/train_all_traffic_models.py

按顺序:
1. 生成交通数据 (generate_traffic_data.py 中的数据生成函数)
2. 训练拥堵预测模型
3. 训练异常检测模型
4. 训练天气影响模型
5. 训练事故影响模型
6. 训练场景仿真模型

输出全部保存在 python/models/ 目录
"""
import os
import sys
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')

STEPS = [
    ("[DATA] 步骤1: 生成交通数据", 
     ["python", os.path.join(SCRIPTS_DIR, '..', 'data', 'traffic', 'generate_traffic_data.py')]),
    ("[TRAFFIC] 步骤2: 训练拥堵预测模型", 
     ["python", os.path.join(SCRIPTS_DIR, 'train_traffic_congestion.py')]),
    ("[ALERT] 步骤3: 训练异常检测模型", 
     ["python", os.path.join(SCRIPTS_DIR, 'train_traffic_anomaly.py')]),
    ("🌤️ 步骤4: 训练天气影响模型", 
     ["python", os.path.join(SCRIPTS_DIR, 'train_traffic_weather.py')]),
    ("[ACCIDENT] 步骤5: 训练事故影响模型", 
     ["python", os.path.join(SCRIPTS_DIR, 'train_traffic_accident_impact.py')]),
    ("[SCENARIO] 步骤6: 训练场景仿真模型", 
     ["python", os.path.join(SCRIPTS_DIR, 'train_traffic_scenario.py')]),
]

def run_step(description, cmd):
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    start = time.time()
    
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=False, text=True)
    
    elapsed = time.time() - start
    if result.returncode == 0:
        print(f"  [OK] 完成 (耗时 {elapsed:.1f}s)")
        return True
    else:
        print(f"  [FAIL] 失败 (返回码 {result.returncode})")
        print(f"  错误: {result.stderr[:500] if result.stderr else '无输出'}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("[TRAFFIC][TRAFFIC][TRAFFIC] 交通模块 - 一键训练所有模型")
    print("=" * 60)
    print(f"工作目录: {BASE_DIR}")
    print(f"模型输出: {os.path.join(BASE_DIR, 'models')}")
    
    results = []
    for label, cmd in STEPS:
        ok = run_step(label, cmd)
        results.append((label, ok))
    
    print(f"\n{'=' * 60}")
    print("[DATA] 训练结果汇总:")
    print(f"{'=' * 60}")
    all_ok = True
    for label, ok in results:
        status = "[OK]" if ok else "[FAIL]"
        print(f"  {status} {label}")
        if not ok:
            all_ok = False
    
    print(f"\n{'=' * 60}")
    if all_ok:
        print("🎉 所有模型训练成功!")
        
        # 列出生成的模型文件
        models_dir = os.path.join(BASE_DIR, 'models')
        traffic_models = [f for f in os.listdir(models_dir) if f.startswith("traffic_")]
        print(f"\n  共 {len(traffic_models)} 个交通模型文件:")
        for f in sorted(traffic_models):
            size = os.path.getsize(os.path.join(models_dir, f)) / 1024
            print(f"    {f:55s} {size:>8.1f} KB")
    else:
        print("⚠️ 部分模型训练失败，请检查错误信息")
    
    print(f"{'=' * 60}")
