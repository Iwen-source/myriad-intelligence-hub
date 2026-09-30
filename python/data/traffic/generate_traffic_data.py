"""
交通流量真实数据生成器

基于真实交通流模型生成模拟数据，特征包括：
- 时间特征 (小时、周几、季节、是否节假日)
- 路段特征 (车道数、限速、道路类型)
- 天气特征 (天气编码、温度、湿度)
- 事故特征

生成的数据保存为 CSV，可直接用于训练 ML 模型。

参考真实数据分布:
  - PeMS (Caltrans): 加州高速公路 5 分钟粒度流量/速度/占有率
  - METR-LA: 洛杉矶 207 个路段交通速度
  - NYC DOT: 纽约市交通流量统计数据
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

sys.stdout.reconfigure(encoding='utf-8')  # 支持 emoji 输出

# 输出路径
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'traffic')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 固定随机种子保证可复现
np.random.seed(42)
random.seed(42)

# =============================================================================
# 1. 路段定义 (模拟 20 条城市道路)
# =============================================================================

ROAD_SECTIONS = [
    {"id": 1, "name": "浑南大道-奥体段",   "type": "主干道", "lanes": 6, "speed_limit": 70, "length_km": 3.2},
    {"id": 2, "name": "青年大街-文化路段",  "type": "快速路", "lanes": 8, "speed_limit": 80, "length_km": 4.1},
    {"id": 3, "name": "南堤路-胜利桥段",    "type": "主干道", "lanes": 4, "speed_limit": 60, "length_km": 2.8},
    {"id": 4, "name": "南京街-和平广场段",  "type": "主干道", "lanes": 6, "speed_limit": 60, "length_km": 3.5},
    {"id": 5, "name": "东西快速干道",       "type": "快速路", "lanes": 6, "speed_limit": 80, "length_km": 5.0},
    {"id": 6, "name": "二环-沈辽路段",      "type": "快速路", "lanes": 6, "speed_limit": 80, "length_km": 4.5},
    {"id": 7, "name": "三好街-文体路段",    "type": "次干道", "lanes": 4, "speed_limit": 50, "length_km": 2.0},
    {"id": 8, "name": "和平大街-中山广场段","type": "主干道", "lanes": 6, "speed_limit": 60, "length_km": 3.0},
    {"id": 9, "name": "北陵大街-泰山路段",  "type": "主干道", "lanes": 6, "speed_limit": 60, "length_km": 2.5},
    {"id": 10, "name": "文化路-南湖公园段", "type": "次干道", "lanes": 4, "speed_limit": 50, "length_km": 1.8},
    {"id": 11, "name": "胜利大街-浑河桥段", "type": "快速路", "lanes": 8, "speed_limit": 80, "length_km": 3.8},
    {"id": 12, "name": "长江街-崇山路段",   "type": "主干道", "lanes": 4, "speed_limit": 60, "length_km": 2.2},
    {"id": 13, "name": "保工街-建设路段",   "type": "主干道", "lanes": 6, "speed_limit": 60, "length_km": 3.3},
    {"id": 14, "name": "东北大马路",        "type": "主干道", "lanes": 6, "speed_limit": 70, "length_km": 4.0},
    {"id": 15, "name": "一环-望花街段",     "type": "快速路", "lanes": 6, "speed_limit": 80, "length_km": 4.2},
    {"id": 16, "name": "五爱街-文艺路段",   "type": "次干道", "lanes": 4, "speed_limit": 50, "length_km": 2.5},
    {"id": 17, "name": "西塔街-抚顺路段",   "type": "次干道", "lanes": 4, "speed_limit": 50, "length_km": 1.6},
    {"id": 18, "name": "珠林路-东陵路段",   "type": "主干道", "lanes": 6, "speed_limit": 60, "length_km": 3.0},
    {"id": 19, "name": "三环-雪莲街段",     "type": "快速路", "lanes": 6, "speed_limit": 100, "length_km": 5.5},
    {"id": 20, "name": "全运路-智慧三街道", "type": "次干道", "lanes": 4, "speed_limit": 60, "length_km": 2.0},
]

# =============================================================================
# 2. 交通流基础模式 (基于真实交通研究数据)
# =============================================================================

def hourly_base_flow(hour: int, road_type: str) -> float:
    """
    每小时基准流量 (PCU/小时/车道)
    
    基于 PeMS 和 METR-LA 数据总结的典型日流量分布:
    - 快速路: 高峰 ~2200, 低谷 ~300
    - 主干道: 高峰 ~1800, 低谷 ~200
    - 次干道: 高峰 ~1200, 低谷 ~100
    """
    # 早高峰 7-9点, 晚高峰 17-19点
    # 使用实际交通流研究中广泛使用的分段函数
    
    if road_type == "快速路":
        base = {
            0: 350, 1: 300, 2: 280, 3: 250, 4: 280, 5: 450,
            6: 800, 7: 1800, 8: 2200, 9: 1700, 10: 1300, 11: 1200,
            12: 1100, 13: 1100, 14: 1200, 15: 1500, 16: 1900,
            17: 2200, 18: 2100, 19: 1800, 20: 1400, 21: 1000,
            22: 700, 23: 500
        }
    elif road_type == "主干道":
        base = {
            0: 250, 1: 200, 2: 180, 3: 150, 4: 200, 5: 350,
            6: 650, 7: 1500, 8: 1800, 9: 1400, 10: 1000, 11: 900,
            12: 850, 13: 850, 14: 950, 15: 1200, 16: 1600,
            17: 1800, 18: 1700, 19: 1400, 20: 1000, 21: 700,
            22: 450, 23: 300
        }
    else:  # 次干道
        base = {
            0: 150, 1: 120, 2: 100, 3: 80, 4: 100, 5: 200,
            6: 400, 7: 900, 8: 1200, 9: 900, 10: 700, 11: 600,
            12: 550, 13: 550, 14: 600, 15: 800, 16: 1000,
            17: 1200, 18: 1100, 19: 900, 20: 650, 21: 450,
            22: 300, 23: 200
        }
    return float(base.get(hour, 500))


def weekly_factor(day_of_week: int) -> float:
    """星期系数: 工作日1-5 ~1.0, 周六 ~0.8, 周日 ~0.65"""
    if day_of_week >= 6:
        return 0.75 if day_of_week == 6 else 0.60
    return 1.0


def seasonal_factor(month: int) -> float:
    """季节系数: 冬季略低, 夏季略高"""
    if month in [12, 1, 2]:
        return 0.90
    elif month in [6, 7, 8]:
        return 1.05
    elif month in [3, 4, 5]:
        return 0.98
    else:
        return 1.02


def weather_speed_factor(weather_code: int) -> float:
    """天气对速度的影响系数 (基于真实研究数据)"""
    # 0=晴, 1=多云, 2=小雨, 3=中雨, 4=暴雨, 5=小雪, 6=中雪, 7=大雪, 8=雾
    factors = {0: 1.00, 1: 0.95, 2: 0.88, 3: 0.78, 4: 0.55,
               5: 0.80, 6: 0.65, 7: 0.45, 8: 0.65}
    return factors.get(weather_code, 1.0)


def weather_flow_factor(weather_code: int) -> float:
    """天气对交通流量的影响系数 (雨雪天流量减少)"""
    factors = {0: 1.00, 1: 0.97, 2: 0.92, 3: 0.85, 4: 0.65,
               5: 0.82, 6: 0.70, 7: 0.50, 8: 0.70}
    return factors.get(weather_code, 1.0)


# =============================================================================
# 3. 速度-流量关系 (基于经典交通流理论: Greenshields 模型)
# =============================================================================

def compute_speed(flow_per_lane: float, speed_limit: int, lanes: int,
                  weather_code: int, is_holiday: int) -> float:
    """
    基于 Greenshields 宏观交通流模型计算速度
    
    流量-速度关系: v = vf * (1 - q / qmax)
    其中 vf = 自由流速度 (限速), qmax = 每车道最大通行能力 ~2000
    """
    free_flow_speed = speed_limit * 1.10  # 自由流速度略高于限速
    capacity_per_lane = 2000.0  # 每车道标准通行能力
    
    # 每车道流量
    q = flow_per_lane / max(lanes, 1)
    
    # Greenshields 模型
    density_ratio = q / capacity_per_lane
    density_ratio = np.clip(density_ratio, 0.0, 1.0)
    speed = free_flow_speed * (1.0 - density_ratio * 0.85)
    
    # 天气影响
    speed *= weather_speed_factor(weather_code)
    
    # 节假日: 速度略高
    if is_holiday:
        speed *= 1.08
    
    # 加入交通流随机波动 (真实数据中速度有10-15%的随机波动)
    noise = np.random.normal(1.0, 0.06)
    speed *= noise
    
    return max(5.0, min(speed, speed_limit * 1.15))


# =============================================================================
# 4. 事故生成器
# =============================================================================

def generate_accidents(n_days: int, sections_ids: list) -> list:
    """生成事故记录: 每天平均每条路段 0.02 次事故"""
    accidents = []
    base_date = datetime(2025, 1, 1)
    
    for day in range(n_days):
        current_date = base_date + timedelta(days=day)
        for section_id in sections_ids:
            # 事故概率: 工作日 0.025, 周末 0.015
            day_of_week = current_date.weekday()
            prob = 0.025 if day_of_week < 5 else 0.015
            if np.random.random() < prob:
                hour = np.random.choice([8, 9, 10, 12, 14, 17, 18, 19], 
                                       p=[0.15, 0.15, 0.1, 0.05, 0.05, 0.25, 0.2, 0.05])
                accident_type = np.random.choice(
                    ["轻微追尾", "车辆故障", "多车碰撞", "单车事故"],
                    p=[0.45, 0.25, 0.15, 0.15]
                )
                # 事故严重程度 (0-1)
                severity_map = {"轻微追尾": 0.2, "车辆故障": 0.15, 
                               "多车碰撞": 0.6, "单车事故": 0.3}
                severity = severity_map[accident_type] + np.random.uniform(-0.05, 0.05)
                severity = np.clip(severity, 0.1, 0.9)
                
                accidents.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "hour": hour,
                    "section_id": section_id,
                    "accident_type": accident_type,
                    "severity": round(severity, 3),
                    "clear_minutes": int(severity * 40 + np.random.uniform(5, 20))
                })
    
    return accidents


# =============================================================================
# 5. 主数据生成
# =============================================================================

def generate_traffic_data(
    n_days: int = 365 * 2,        # 2年数据
    start_date: str = "2024-01-01",
    output_file: str = "traffic_flow_data.csv"
):
    """
    生成真实的交通流量数据
    
    输出字段:
    - section_id, road_name, road_type, lanes, speed_limit, length_km
    - date, hour, day_of_week, month, season, is_weekend, is_holiday
    - weather_code, temperature, humidity
    - flow_count (PCU/小时), avg_speed (km/h), congestion_index
    - has_accident, accident_severity
    """
    base_date = datetime.strptime(start_date, "%Y-%m-%d")
    section_ids = [s["id"] for s in ROAD_SECTIONS]
    
    # 预生成事故
    accidents = generate_accidents(n_days, section_ids)
    accident_lookup = {}
    for acc in accidents:
        key = (acc["date"], acc["hour"], acc["section_id"])
        accident_lookup[key] = acc
    
    records = []
    
    # 中国法定节假日列表 (2024-2025 简化版)
    holidays = {
        "2024-01-01", "2024-02-10", "2024-02-11", "2024-02-12",
        "2024-04-04", "2024-05-01", "2024-06-08", "2024-09-15",
        "2024-10-01", "2024-10-02", "2024-10-03", "2024-10-04", "2024-10-05",
        "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30",
        "2025-04-04", "2025-05-01", "2025-05-31", "2025-10-01", "2025-10-02", "2025-10-03"
    }
    
    for day in range(n_days):
        current_date = base_date + timedelta(days=day)
        date_str = current_date.strftime("%Y-%m-%d")
        day_of_week = current_date.weekday()  # 0=Mon, 6=Sun
        month = current_date.month
        is_weekend = 1 if day_of_week >= 5 else 0
        is_holiday = 1 if date_str in holidays else 0
        season = month // 4 + 1  # 1=冬, 2=春, 3=夏, 4=秋
        
        # 当日天气 (每天一个天气码)
        # 基于沈阳气候统计频率
        weather_probs = {
            0: 0.35, 1: 0.25, 2: 0.08, 3: 0.04, 4: 0.01,
            5: 0.05, 6: 0.03, 7: 0.01, 8: 0.03
        }
        if month in [6, 7, 8]:  # 夏季多雨
            weather_probs[2] = 0.15; weather_probs[3] = 0.08
            weather_probs[0] = 0.25; weather_probs[1] = 0.22
        elif month in [12, 1, 2]:  # 冬季多雪
            weather_probs[5] = 0.12; weather_probs[6] = 0.06
            weather_probs[0] = 0.20; weather_probs[4] = 0.0  # 冬季无暴雨
        
        weather_codes = list(weather_probs.keys())
        weather_weights = list(weather_probs.values())
        weather_weights = np.array(weather_weights) / sum(weather_weights)
        weather_code = np.random.choice(weather_codes, p=weather_weights)
        
        # 温度湿度 (沈阳月均)
        temp_map = {1: -8, 2: -4, 3: 3, 4: 12, 5: 18, 6: 23,
                    7: 26, 8: 24, 9: 19, 10: 12, 11: 3, 12: -5}
        hum_map = {1: 60, 2: 55, 3: 50, 4: 48, 5: 52, 6: 65,
                   7: 72, 8: 70, 9: 62, 10: 58, 11: 55, 12: 58}
        base_temp = temp_map[month]
        base_hum = hum_map[month]
        temperature = round(base_temp + np.random.uniform(-5, 5), 1)
        humidity = round(base_hum + np.random.uniform(-10, 10), 1)
        
        for section in ROAD_SECTIONS:
            sid = section["id"]
            road_type = section["type"]
            lanes = section["lanes"]
            speed_limit = section["speed_limit"]
            
            for hour in range(24):
                # --- 基准流量 ---
                base_flow = hourly_base_flow(hour, road_type)
                
                # 星期调整
                wf = weekly_factor(day_of_week)
                
                # 季节调整
                sf = seasonal_factor(month)
                
                # 天气对流量影响
                wf_weather = weather_flow_factor(weather_code)
                
                # 节假日调整
                hf = 0.60 if is_holiday else 1.0
                
                # 总流量 (每车道)
                flow_per_lane = base_flow * wf * sf * wf_weather * hf
                
                # 事故影响: 发生事故时流量减少
                acc_key = (date_str, hour, sid)
                has_accident = 1 if acc_key in accident_lookup else 0
                accident_severity = 0.0
                accident_type_str = ""
                if has_accident:
                    acc = accident_lookup[acc_key]
                    accident_severity = acc["severity"]
                    accident_type_str = acc["accident_type"]
                    # 事故导致流量下降
                    flow_reduction = accident_severity * 0.5
                    flow_per_lane *= (1.0 - flow_reduction)
                
                # 车流量 = 车道数 × 每车道流量
                total_flow = round(flow_per_lane * lanes)
                total_flow = int(max(10, total_flow))
                
                # --- 计算速度 ---
                avg_speed = compute_speed(total_flow, speed_limit, lanes,
                                         weather_code, is_holiday)
                
                # 事故额外降低速度
                if has_accident:
                    avg_speed *= (1.0 - accident_severity * 0.6)
                
                avg_speed = round(max(3.0, min(avg_speed, speed_limit * 1.15)), 1)
                
                # --- 拥堵指数 (0-1) ---
                free_flow_speed = speed_limit * 1.10
                congestion_index = 1.0 - (avg_speed / free_flow_speed)
                congestion_index = round(np.clip(congestion_index, 0.0, 1.0), 4)
                
                records.append({
                    "section_id": sid,
                    "road_name": section["name"],
                    "road_type": road_type,
                    "lanes": lanes,
                    "speed_limit": speed_limit,
                    "length_km": section["length_km"],
                    "date": date_str,
                    "hour": hour,
                    "day_of_week": day_of_week,
                    "month": month,
                    "season": season,
                    "is_weekend": is_weekend,
                    "is_holiday": is_holiday,
                    "weather_code": weather_code,
                    "temperature": temperature,
                    "humidity": humidity,
                    "flow_count": total_flow,
                    "avg_speed": avg_speed,
                    "congestion_index": congestion_index,
                    "has_accident": has_accident,
                    "accident_severity": accident_severity,
                    "accident_type": accident_type_str,
                })
    
    df = pd.DataFrame(records)
    output_path = os.path.join(OUTPUT_DIR, output_file)
    df.to_csv(output_path, index=False)
    print(f"✅ 交通数据生成完成!")
    print(f"   数据量: {len(df):,} 条记录")
    print(f"   路段数: {len(ROAD_SECTIONS)}")
    print(f"   时间跨度: {n_days} 天 ({start_date} ~ {base_date + timedelta(days=n_days-1):%Y-%m-%d})")
    print(f"   事故记录: {len(accidents)} 条")
    print(f"   保存至: {output_path}")
    print(f"\n字段列表: {list(df.columns)}")
    print(f"\n数据统计:")
    print(df[["flow_count", "avg_speed", "congestion_index"]].describe())
    return df


# =============================================================================
# 6. AI 训练数据集 (为各种模型准备特征)
# =============================================================================

def prepare_training_datasets(df: pd.DataFrame):
    """
    从原始数据中提取各模型训练所需的特征-标签对
    
    输出:
    - congestion_train.csv: 拥堵预测训练数据
    - anomaly_train.csv: 异常检测训练数据
    - weather_train.csv: 天气-交通训练数据
    - accident_train.csv: 事故影响训练数据
    - scenario_train.csv: 场景仿真训练数据
    """
    
    # --- 6.1 拥堵预测: 时间 + 路段特征 → 流量 + 速度 ---
    congestion_cols = [
        "hour", "day_of_week", "month", "season", "is_weekend", "is_holiday",
        "weather_code", "temperature", "humidity",
        "lanes", "speed_limit", "road_type",
        "flow_count", "avg_speed", "congestion_index"
    ]
    df_cong = df[congestion_cols].copy()
    
    # 道路类型编码
    road_type_map = {"快速路": 2, "主干道": 1, "次干道": 0}
    df_cong["road_type"] = df_cong["road_type"].map(road_type_map)
    
    # 时间特征：添加周期性编码
    df_cong["hour_sin"] = np.sin(2 * np.pi * df_cong["hour"] / 24)
    df_cong["hour_cos"] = np.cos(2 * np.pi * df_cong["hour"] / 24)
    df_cong["day_sin"] = np.sin(2 * np.pi * df_cong["day_of_week"] / 7)
    df_cong["day_cos"] = np.cos(2 * np.pi * df_cong["day_of_week"] / 7)
    
    path = os.path.join(OUTPUT_DIR, "congestion_train.csv")
    df_cong.to_csv(path, index=False)
    print(f"✅ 拥堵预测数据集: {len(df_cong)} 条 → {path}")
    
    # --- 6.2 异常检测: 对比实际值 vs 预测值 ---
    # 按 (路段, 小时, 星期) 分组计算每个分组的流量均值和标准差
    df_anom = df.groupby(["section_id", "hour", "day_of_week"]).agg({
        "flow_count": ["mean", "std", "min", "max"],
        "avg_speed": ["mean", "std"],
        "congestion_index": ["mean", "std"],
    }).reset_index()
    df_anom.columns = ["section_id", "hour", "day_of_week",
                        "flow_mean", "flow_std", "flow_min", "flow_max",
                        "speed_mean", "speed_std",
                        "cong_mean", "cong_std"]
    
    # 合并实际值
    df_latest = df.groupby(["section_id", "hour", "day_of_week"]).last().reset_index()
    df_anom = df_anom.merge(
        df_latest[["section_id", "hour", "day_of_week", "flow_count", "avg_speed"]],
        on=["section_id", "hour", "day_of_week"]
    )
    
    # 计算偏差特征
    df_anom["flow_deviation"] = (df_anom["flow_count"] - df_anom["flow_mean"]) / (df_anom["flow_std"] + 0.01)
    df_anom["speed_deviation"] = (df_anom["avg_speed"] - df_anom["speed_mean"]) / (df_anom["speed_std"] + 0.01)
    df_anom["is_anomaly"] = ((abs(df_anom["flow_deviation"]) > 2.5) | 
                              (abs(df_anom["speed_deviation"]) > 2.5)).astype(int)
    
    path = os.path.join(OUTPUT_DIR, "anomaly_train.csv")
    df_anom.to_csv(path, index=False)
    print(f"✅ 异常检测数据集: {len(df_anom)} 条, 异常率 {df_anom['is_anomaly'].mean():.2%} → {path}")
    
    # --- 6.3 天气-交通影响: 天气特征 → 速度/流量变化 ---
    df_weather = df.groupby(["weather_code", "road_type", "hour"]).agg({
        "flow_count": "mean", "avg_speed": "mean", "congestion_index": "mean",
        "temperature": "mean", "humidity": "mean"
    }).reset_index()
    df_weather["road_type"] = df_weather["road_type"].map(road_type_map)
    
    path = os.path.join(OUTPUT_DIR, "weather_train.csv")
    df_weather.to_csv(path, index=False)
    print(f"✅ 天气影响数据集: {len(df_weather)} 条 → {path}")
    
    # --- 6.4 事故影响: 事故发生时的影响数据 ---
    df_acc = df[df["has_accident"] == 1].copy()
    if len(df_acc) > 0:
        # 为每条事故记录找正常时段的对比值
        acc_features = []
        for _, row in df_acc.iterrows():
            normal = df[(df["section_id"] == row["section_id"]) &
                        (df["hour"] == row["hour"]) &
                        (df["day_of_week"] == row["day_of_week"]) &
                        (df["has_accident"] == 0)]
            if len(normal) > 0:
                normal_mean = normal[["flow_count", "avg_speed", "congestion_index"]].mean()
                acc_features.append({
                    "section_id": row["section_id"],
                    "road_type": road_type_map.get(row["road_type"], 0),
                    "lanes": row["lanes"],
                    "speed_limit": row["speed_limit"],
                    "hour": row["hour"],
                    "day_of_week": row["day_of_week"],
                    "weather_code": row["weather_code"],
                    "accident_severity": row["accident_severity"],
                    "normal_flow": normal_mean["flow_count"],
                    "current_flow": row["flow_count"],
                    "normal_speed": normal_mean["avg_speed"],
                    "current_speed": row["avg_speed"],
                    "flow_reduction_pct": (1 - row["flow_count"] / max(normal_mean["flow_count"], 1)) * 100,
                    "speed_reduction_pct": (1 - row["avg_speed"] / max(normal_mean["avg_speed"], 1)) * 100,
                })
        if acc_features:
            df_acc_impact = pd.DataFrame(acc_features)
            path = os.path.join(OUTPUT_DIR, "accident_train.csv")
            df_acc_impact.to_csv(path, index=False)
            print(f"✅ 事故影响数据集: {len(df_acc_impact)} 条 → {path}")
    
    # --- 6.5 场景仿真: 路段特征 + 变化参数 → 影响效果 ---
    scenario_data = []
    for _, row in df.groupby(["section_id", "hour", "day_of_week"]).first().reset_index().iterrows():
        base_flow = row["flow_count"]
        base_speed = row["avg_speed"]
        lanes = row["lanes"]
        speed_limit = row["speed_limit"]
        
        # 模拟各种场景
        for add_lanes in [0, 1, 2]:
            new_flow = base_flow * (1 + add_lanes * 0.12)
            new_speed = base_speed * (1 + add_lanes * 0.10)
            scenario_data.append({
                "section_id": row["section_id"],
                "road_type": road_type_map.get(row["road_type"], 0),
                "lanes": lanes,
                "speed_limit": speed_limit,
                "hour": row["hour"],
                "day_of_week": row["day_of_week"],
                "change_type": "add_lane",
                "change_value": add_lanes,
                "base_flow": base_flow,
                "base_speed": base_speed,
                "result_flow": round(new_flow),
                "result_speed": round(new_speed, 1),
            })
        
        for new_limit in [speed_limit - 10, speed_limit, speed_limit + 10]:
            if new_limit < 20:
                continue
            speed_ratio = new_limit / max(speed_limit, 1)
            scenario_data.append({
                "section_id": row["section_id"],
                "road_type": road_type_map.get(row["road_type"], 0),
                "lanes": lanes,
                "speed_limit": speed_limit,
                "hour": row["hour"],
                "day_of_week": row["day_of_week"],
                "change_type": "change_speed",
                "change_value": new_limit - speed_limit,
                "base_flow": base_flow,
                "base_speed": base_speed,
                "result_flow": round(base_flow * (1 + (speed_ratio - 1) * 0.5)),
                "result_speed": round(base_speed * speed_ratio * 0.9, 1),
            })
    
    if scenario_data:
        df_scenario = pd.DataFrame(scenario_data)
        path = os.path.join(OUTPUT_DIR, "scenario_train.csv")
        df_scenario.to_csv(path, index=False)
        print(f"✅ 场景仿真数据集: {len(df_scenario)} 条 → {path}")
    
    print("\n🎯 所有训练数据集准备完毕!")
    return {
        "congestion": len(df_cong),
        "anomaly": len(df_anom),
        "weather": len(df_weather),
        "accident": len(df_acc_impact) if 'df_acc_impact' in locals() else 0,
        "scenario": len(scenario_data),
    }


if __name__ == "__main__":
    print("=" * 60)
    print("🚗 交通数据生成器")
    print("=" * 60)
    
    # 生成 2 年交通数据
    df = generate_traffic_data(n_days=365 * 2)
    
    print("\n" + "=" * 60)
    print("📊 生成训练数据集")
    print("=" * 60)
    stats = prepare_training_datasets(df)
    
    print("\n" + "=" * 60)
    print(f"✅ 全部完成! 数据集已保存至: {OUTPUT_DIR}")
    print("=" * 60)
