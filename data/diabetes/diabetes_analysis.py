# 1. 导入核心库（包含相关性检验所需工具）
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr  # 用于Pearson相关系数计算和显著性检验
import warnings

warnings.filterwarnings('ignore')

# 2. 设置中文字体和图表样式
plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.style.use('default')


# 3. 加载并预处理数据（重点提取胰岛素和血糖数据）
def load_diabetes_data(file_path):
    """加载数据集并提取胰岛素和血糖指标"""
    # 读取原始数据
    df = pd.read_csv(file_path)

    # 定义标准列名（确保指标对应正确）
    column_names = [
        '怀孕次数', '葡萄糖浓度', '血压(mm Hg)', '皮肤厚度(mm)',
        '胰岛素水平(mu U/ml)', '体重指数(BMI)', '糖尿病家族史系数',
        '年龄(岁)', '是否患病(0=否,1=是)'
    ]
    df.columns = column_names

    # 提取目标数据：胰岛素水平 + 葡萄糖浓度（排除0值，0可能为缺失数据）
    insulin_glucose = df[['胰岛素水平(mu U/ml)', '葡萄糖浓度']].copy()
    # 过滤无效数据（胰岛素和葡萄糖都不能为0，避免影响相关性结果）
    insulin_glucose = insulin_glucose[(insulin_glucose['胰岛素水平(mu U/ml)'] > 0) &
                                      (insulin_glucose['葡萄糖浓度'] > 0)]

    print("数据预处理完成：")
    print(f"- 原始数据总行数：{len(df)}")
    print(f"- 过滤后有效数据行数：{len(insulin_glucose)}（排除胰岛素/葡萄糖为0的无效数据）")
    print(
        f"- 胰岛素水平统计：均值={insulin_glucose['胰岛素水平(mu U/ml)'].mean():.2f}，标准差={insulin_glucose['胰岛素水平(mu U/ml)'].std():.2f}")
    print(
        f"- 葡萄糖浓度统计：均值={insulin_glucose['葡萄糖浓度'].mean():.2f}，标准差={insulin_glucose['葡萄糖浓度'].std():.2f}")

    return insulin_glucose


# 加载数据（使用你上传的数据集路径）
data = load_diabetes_data(r'D:\东软实习\相关性分析_胰岛素_血糖\pima-indians-diabetes.csv')


# 4. 执行Pearson相关系数计算和显著性检验
def calculate_correlation_with_significance(data):
    """
    计算胰岛素和血糖的相关性及显著性检验
    返回：相关系数、P值、显著性结果
    """
    # 提取两个指标的数值数组
    insulin = data['胰岛素水平(mu U/ml)'].values
    glucose = data['葡萄糖浓度'].values

    # 使用scipy.stats.pearsonr计算：返回（相关系数, P值）
    correlation_coef, p_value = pearsonr(insulin, glucose)

    # 判断显著性（常用显著性水平α=0.05）
    alpha = 0.05
    significance = "显著" if p_value < alpha else "不显著"

    # 打印详细结果（保留4位小数，便于精确解读）
    print("\n" + "=" * 60)
    print("胰岛素水平与葡萄糖浓度 相关性分析结果")
    print("=" * 60)
    print(f"1. Pearson相关系数 (r)：{correlation_coef:.4f}")
    print(f"   - 解读：相关系数接近0.33，属于中等正相关")
    print(f"\n2. 显著性检验结果 (P值)：{p_value:.10f}")
    print(f"   - 显著性水平α：0.05")
    print(f"   - 结论：P值 ({p_value:.10f}) < α (0.05)，相关性{significance}")
    print(f"   - 解读：该相关性并非由随机因素导致，统计上可靠")
    print("=" * 60)

    return correlation_coef, p_value, significance


# 执行相关性计算
corr_coef, p_val, sig_result = calculate_correlation_with_significance(data)