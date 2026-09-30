### 一、SimpleITK简介
#### 1.1 SimpleITK是什么
SimpleITK 是一个简化的、开源的跨语言接口，专为访问功能强大的 C++ 图像处理库ITK (Insight Segmentation and Registration Toolkit)而设计，
是连接高层脚本语言与底层高性能算法的桥梁。
#### 1.2 SimpleITK与ITK之间关系
ITK是一款面向图像处理的功能强大的且复杂的C++模板库，虽然功能强大，学习曲线陡峭、开发门槛高，而SimpleITK则封装了ITK的复杂接口，提供一套简洁、高效、
易用的函数，大幅度的降低了我们上手的难度。   
SimpleITK的四大优势：
1. 跨语言支持：支持 Python, R, Java, C# 等多种语言
2. 简单易用：提供一致、精简且直观的 API 接口
3. 算法能力强：完整继承 ITK 医学图像分析全套算法
4. 全平台兼容：Linux / macOS / Windows 预编译包支持

### 二、核心概念
`Image` 类是 SimpleITK 的核心数据结构。它不仅封装了多维像素数据，更关键的是包含了定义其物理空间属性的元信息，这是医学影像分析中连接“像素坐标”与“真实物理世界”的桥梁。
#### 2.1 图像构造
指定尺寸与像素类型，快速初始化一个空的多维图像对象，用于后续赋值或处理。
```python
import SimpleITK as sitk

# 创建256x128x64的3D图像
# 像素类型为16位有符号整数
img = sitk.Image(256, 128, 64,
sitk.sitkInt16)
```
#### 2.2 关键元信息
• 原点 (Origin):像素坐标(0,0,0)在真实物理空间中的绝对坐标，决定了影像的位置。
• 间距 (Spacing):单个体素在物理空间代表的实际尺寸（单位通常为毫米），用于计算体素体积。
• 方向 (Direction):方向余弦矩阵，描述图像坐标系在物理空间中的旋转角度。

#### 2.3 访问与修改
SimpleITK 提供了直观的 Get/Set 方法来操作元信息，确保数据的准确性与一致性
```python
import SimpleITK as sitk
img = sitk.Image(256, 128, 64,
sitk.sitkInt16)
# 获取属性
sz = img.GetSize() # (W,H,D)
ori = img.GetOrigin()
spc = img.GetSpacing()

# 设置属性
img.SetOrigin((10, 20, 30))
img.SetSpacing((0.5, 0.5, 1.0))

```

### 三、基础操作
#### 3.1 读取单文件 (如 NIfTI)
适用于 NIfTI (`.nii`, `.nii.gz`)、MetaImage (`.mhd`, `.raw`) 等单一文件格式，操作极为便捷。
```python
import SimpleITK as sitk
# 简便函数
image = sitk.ReadImage(
"data/ct_output.nii.gz"
)
```
#### 3.2 读取 DICOM 系列
DICOM通常由多个切片文件组成。需先获取系列ID和文件名列表，再进行批量读取。
```python
import SimpleITK as sitk

def read_dicom_series(dicom_folder):
	"""
	读取 DICOM 序列文件夹，返回 3D 图像
	"""
	# 1. 创建 DICOM 序列读取器
	reader = sitk.ImageSeriesReader()

	# 2. 获取文件夹下所有 DICOM 文件（自动排序，非常重要）
	dicom_names = reader.GetGDCMSeriesFileNames(dicom_folder)

	if not dicom_names:
		raise ValueError("未找到 DICOM 文件！")

	# 3. 设置要读取的文件
	reader.SetFileNames(dicom_names)

	# 4. 执行读取 → 得到 3D 医学图像（带病人坐标系、原点、间距、方向）
	image_3d = reader.Execute()

	return image_3d

# ========== 使用 ==========
if __name__ == "__main__":
	# 你的 DICOM 文件夹路径（里面全是 .dcm 文件）
	dicom_dir = r"data/CT Plain"
	# 读取
	ct_image = read_dicom_series(dicom_dir)
	# 查看 3D 信息
	print("图像大小 (x,y,z):", ct_image.GetSize())
	print("体素间距 (mm):", ct_image.GetSpacing())
	print("病人坐标系原点:", ct_image.GetOrigin())
	print("方向矩阵:", ct_image.GetDirection())
	print("数据类型:", ct_image.GetPixelIDTypeAsString())
```
#### 3.4 写入图像
处理完成后，将 SimpleITK 图像对象保存回磁盘，支持多种医学图像格式的导出。
```python
import SimpleITK as sitk
import os

# 关闭警告
sitk.ProcessObject_SetGlobalWarningDisplay(False)

def read_dicom(dcm_folder):
    reader = sitk.ImageSeriesReader()
    dcm_names = reader.GetGDCMSeriesFileNames(dcm_folder)
    reader.SetFileNames(dcm_names)
    return reader.Execute()

# 自动创建文件夹
def create_folder(path):
    if not os.path.exists(path):
        os.makedirs(path)

# ================== 1. 读取CT ==================
ct = read_dicom(r"data\CT Plain")

# ================== 2. 创建输出目录 ==================
base_out = r"data\out"
dcm_out = r"data\out\dcm_out"
create_folder(base_out)
create_folder(dcm_out)

# ================== 3. 保存 NIfTI / NRRD ==================
sitk.WriteImage(ct, os.path.join(base_out, "ct.nii.gz"))
sitk.WriteImage(ct, os.path.join(base_out, "ct.nrrd"))

slice15 = ct[:, :, 15]
# 窗宽窗位 + 转成 PNG 支持的 uint8 格式
png_img = sitk.IntensityWindowing(slice15, -125, 225, 0, 255)
png_img = sitk.Cast(png_img, sitk.sitkUInt8)
sitk.WriteImage(png_img, os.path.join(base_out, "slice15.png"))


print("✅ 全部保存成功！")
```

#### 3.5 与Numpy互转
SimpleITK 与 NumPy 的互转是医学图像编程中最常用的操作之一。但是两者存储数据的维度顺序不同：
•SimpleITK Image：按物理空间顺序 (x, y, z) 存储，符合放射学阅片习惯。
•NumPy Array：按数组索引顺序 (z, y, x) 存储。
```python
import SimpleITK as sitk
import numpy as np

# 关闭警告
sitk.ProcessObject_SetGlobalWarningDisplay(False)

# ================== 1. 读取 MHD 图像（SimpleITK 格式）==================
sitk_image = sitk.ReadImage(r"data\mhd\1.mhd")  # 你的 mhd 路径
print("✅ 读取成功，SimpleITK 图像大小：", sitk_image.GetSize())  # (x, y, z)


# ================== 2. SimpleITK → NumPy 数组 ==================
numpy_array = sitk.GetArrayFromImage(sitk_image)

print("\n转换为 NumPy 数组：")
print("数组形状：", numpy_array.shape)        # 注意：是 (z, y, x) 顺序！
print("数据类型：", numpy_array.dtype)
print("数值范围：最小值 =", np.min(numpy_array), "，最大值 =", np.max(numpy_array))


# ================== 3. 在 NumPy 里做任意处理（示例）==================
# 比如：把大于 100 的值设为 0
numpy_array_processed = numpy_array.copy()
numpy_array_processed[numpy_array_processed > 100] = 0


# ================== 4. NumPy 数组 → SimpleITK 图像 ==================
# 关键：必须把 空间信息(原点、间距、方向) 复制回去！
new_sitk_image = sitk.GetImageFromArray(numpy_array_processed)

# 继承原始图像的空间信息（非常重要！否则坐标丢失）
new_sitk_image.SetOrigin(sitk_image.GetOrigin())
new_sitk_image.SetSpacing(sitk_image.GetSpacing())
new_sitk_image.SetDirection(sitk_image.GetDirection())


# ================== 5. 保存处理后的图像 ==================
sitk.WriteImage(new_sitk_image, r"data\mhd\result.nii.gz")
print("\n✅ 处理完成并保存成功：result.nii.gz")
```

#### 3.6 图像可视化
SimpleITK本身不提供强大的可视化功能，通常需要结合Python的科学绘图库Matplotlib进行图像切片的显示与分析。
```python
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rc("font", family="Microsoft YaHei")
# 关闭警告
sitk.ProcessObject_SetGlobalWarningDisplay(False)

# ================== 1. 读取图像 ==================
sitk_img = sitk.ReadImage(r"data\mhd\1.mhd")

# ================== 2. 转 numpy ==================
img_arr = sitk.GetArrayFromImage(sitk_img)  # shape (z, y, x)
print("图像形状 (z,y,x):", img_arr.shape)

# ================== 3. 选择要显示的层面 ==================
z_center = img_arr.shape[0] // 2  # 取中间一层
slice_2d = img_arr[z_center]

# ================== 4. 窗宽窗位（关键！不然看不清）==================
# 软组织窗：窗宽350，窗位50
window_width = 350
window_level = 50

# 计算上下限
v_min = window_level - window_width / 2
v_max = window_level + window_width / 2

# 截断（超过范围的切掉）
slice_2d = np.clip(slice_2d, v_min, v_max)

# ================== 5. 显示图像 ==================
plt.figure(figsize=(8, 8))
plt.imshow(slice_2d, cmap="gray")
plt.title(f"CT 第 {z_center} 层 | 软组织窗")
plt.axis("off")
plt.show()
```

### 四、进阶操作
滤波是图像处理的基础操作，主要用于去除图像噪声、平滑纹理或增强边缘特征。SimpleITK 封装了丰富的滤波器接口，仅需简单几步即可实现专业的图像预处理。
#### 4.1 高斯滤波
高斯滤波是线性平滑滤波，基于高斯正态分布函数生成卷积核，对图像做邻域加权平均，主要作用是降噪、平滑图像。
```python
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rc("font", family="Microsoft YaHei")
# 关闭警告
sitk.ProcessObject_SetGlobalWarningDisplay(False)

# ================== 1. 读取 MHD 图像 ==================
sitk_img = sitk.ReadImage(r"data\mhd\1.mhd")

# ================== 2. 高斯滤波（SimpleITK 自带函数）==================
# 高斯核大小：越大越模糊
# 这里使用 [1,1,1] 表示只在平面内模糊，层间不模糊
img_smoothed = sitk.DiscreteGaussian(sitk_img, variance=[1.0, 1.0, 0.0])

# ================== 3. 计算差分图像（原始 - 模糊）==================
img_diff = sitk.Abs(sitk.Subtract(sitk_img, img_smoothed))

# ================== 4. 转成 numpy 用于显示 ==================
def sitk_to_numpy_windowed(sitk_img, ww=350, wl=50):
    """转numpy + 窗宽窗位"""
    arr = sitk.GetArrayFromImage(sitk_img)
    arr = np.clip(arr, wl - ww/2, wl + ww/2)
    return arr

# 取中间一层
z = sitk_to_numpy_windowed(sitk_img).shape[0] // 2

original = sitk_to_numpy_windowed(sitk_img)[z]
smoothed = sitk_to_numpy_windowed(img_smoothed)[z]
diff = sitk_to_numpy_windowed(img_diff, ww=50, wl=25)[z]  # 差分用小窗

# ================== 5. 三图对比显示 ==================
plt.figure(figsize=(15, 5))

plt.subplot(1, 3, 1)
plt.imshow(original, cmap="gray")
plt.title("Original 原始图像")
plt.axis("off")

plt.subplot(1, 3, 2)
plt.imshow(smoothed, cmap="gray")
plt.title("Gaussian Blur 高斯滤波")
plt.axis("off")

plt.subplot(1, 3, 3)
plt.imshow(diff, cmap="gray")
plt.title("Difference 差分图像（边缘/噪声）")
plt.axis("off")

plt.tight_layout()
plt.show()
```

#### 4.2 中值滤波
使用像素邻域中值代替原值，对去除椒盐噪声等脉冲噪声效果显著。
```python
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rc("font", family="Microsoft YaHei")
# 关闭警告
sitk.ProcessObject_SetGlobalWarningDisplay(False)

# ================== 1. 读取图像 ==================
sitk_img = sitk.ReadImage(r"data\mhd\1.mhd")

# ================== 2. 中值滤波（SimpleITK 自带）==================
# radius = 滤波半径（越大去噪越强，越模糊）
img_median = sitk.Median(sitk_img, radius=[1, 1, 0])  # XY平面滤波，Z不动

# ================== 3. 计算差分图 ==================
img_diff = sitk.Abs(sitk.Subtract(sitk_img, img_median))

# ================== 4. 转 numpy + 窗宽窗位（方便显示）==================
def to_numpy(sitk_img, ww=350, wl=50):
    arr = sitk.GetArrayFromImage(sitk_img)
    arr = np.clip(arr, wl - ww/2, wl + ww/2)
    return arr

# 取中间一层
z = to_numpy(sitk_img).shape[0] // 2

original = to_numpy(sitk_img)[z]
median    = to_numpy(img_median)[z]
diff      = to_numpy(img_diff, ww=50, wl=25)[z]

# ================== 5. 画图对比 ==================
plt.figure(figsize=(15,5))

plt.subplot(1,3,1)
plt.imshow(original, cmap="gray")
plt.title("Original 原始图")
plt.axis("off")

plt.subplot(1,3,2)
plt.imshow(median, cmap="gray")
plt.title("Median Filter 中值滤波")
plt.axis("off")

plt.subplot(1,3,3)
plt.imshow(diff, cmap="gray")
plt.title("Difference 差分图")
plt.axis("off")

plt.tight_layout()
plt.show()
```

#### 4.3 边缘检测
通过梯度计算识别图像中灰度突变的区域，常用于提取器官或病灶轮廓。

```python
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt

import matplotlib

matplotlib.rc("font", family="Microsoft YaHei")

sitk.ProcessObject_SetGlobalWarningDisplay(False)

# ================== 工具函数 ==================
def to_numpy(img, ww=350, wl=50):
    arr = sitk.GetArrayFromImage(img)
    return np.clip(arr, wl - ww/2, wl + ww/2)

# ================== 1. 读取图像 ==================
img = sitk.ReadImage(r"data\mhd\1.mhd")

# ================== 2. 必须转浮点（Canny 强制要求）==================
img_float = sitk.Cast(img, sitk.sitkFloat64)

# ================== 3. Canny 边缘检测（最简单、最稳）==================
canny = sitk.CannyEdgeDetection(
    img_float,
    lowerThreshold=20,
    upperThreshold=80,
    variance=[1.0, 1.0, 0.0]
)

# ================== 4. 显示 ==================
z = to_numpy(img).shape[0] // 2
original = to_numpy(img)[z]
canny_out = sitk.GetArrayFromImage(canny)[z]

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.imshow(original, cmap="gray")
plt.title("原始 CT")
plt.axis("off")

plt.subplot(1, 2, 2)
plt.imshow(canny_out, cmap="gray")
plt.title("Canny 边缘检测")
plt.axis("off")

plt.tight_layout()
plt.show()
```

#### 4.4 阈值分割
设定灰度阈值将图像分为前景和背景，是二值化处理和病灶粗定位的基础。
```python
import SimpleITK as sitk
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rc("font", family="Microsoft YaHei")

# 关闭警告
sitk.ProcessObject_SetGlobalWarningDisplay(False)

# ================== 工具函数 ==================
def sitk_to_numpy(img, ww=350, wl=50):
    """转numpy并做窗宽窗位，方便显示"""
    arr = sitk.GetArrayFromImage(img)
    return np.clip(arr, wl - ww/2, wl + ww/2)

# ================== 1. 读取影像 ==================
img = sitk.ReadImage(r"data\mhd\1.mhd")
img_np = sitk_to_numpy(img)
z_center = img_np.shape[0] // 2  # 取中间层

# ================== 2. 阈值分割（核心代码）==================
# 医学CT常用：提取骨骼/软组织/肺部
# 用法：大于 lower 且 小于 upper 的部分设为 1（白），其余 0（黑）
lower_th = 200   # 下限
upper_th = 3000  # 上限（CT骨骼一般>200HU）

binary_img = sitk.BinaryThreshold(
    img,
    lowerThreshold=lower_th,
    upperThreshold=upper_th,
    insideValue=1,    # 符合条件设为1
    outsideValue=0    # 不符合设为0
)

# ================== 3. 转为numpy用于画图 ==================
original_slice = img_np[z_center]
mask_slice = sitk.GetArrayFromImage(binary_img)[z_center]

# ================== 4. 画图展示 ==================
plt.figure(figsize=(15, 5))

# 原始图
plt.subplot(1, 3, 1)
plt.imshow(original_slice, cmap="gray")
plt.title("原始 CT 图像")
plt.axis("off")

# 分割结果（二值图）
plt.subplot(1, 3, 2)
plt.imshow(mask_slice, cmap="gray")
plt.title(f"阈值分割: {lower_th} ~ {upper_th}")
plt.axis("off")

# 叠加图（看得更清楚）
plt.subplot(1, 3, 3)
plt.imshow(original_slice, cmap="gray")
plt.imshow(mask_slice, cmap="jet", alpha=0.4)  # 透明叠加
plt.title("分割叠加效果")
plt.axis("off")

plt.tight_layout()
plt.show()
```


