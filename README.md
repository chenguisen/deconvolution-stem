# HAADF-STEM Image Deconvolution

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Academic%20Use-blue.svg)](LICENSE)

一个用于 HAADF-STEM (High-Angle Annular Dark-Field Scanning Transmission Electron Microscopy) 图像解卷积的 Python 工具包，提供完整的图形界面和命令行工具。

## 功能特性

- 🖥️ **现代化的图形界面** - 基于 PyQt6 的用户友好界面
- 🧮 **多种解卷积算法**
  - Richardson-Lucy 加法算法 (Additive)
  - Richardson-Lucy 乘法算法 (Multiplicative) - 支持 Biggs-Andrews 加速与阻尼(Damping)控制
  - FISTA (Fast Iterative Shrinkage-Thresholding Algorithm) - 结合全变分(TV)正则化
- 🔬 **完整的显微镜参数配置**
  - 加速电压 (Voltage)
  - 球差系数 (Cs3, Cs5)
  - 离焦量 (Defocus)
  - 物镜光阑 (Objective Aperture)
  - 高级像差参数 (A2, A3, B2 等)
- 👁️ **实时探针预览**
- 📊 **多视图显示**
  - 实空间 / 频域
  - 线性 / 功率谱 / 对数
  - 多种色彩映射
- 🎨 **多种主题配色**
  - Professional Blue
  - Dark Mode
  - Light Clean
  - Nature Green
  - Sunset Orange
- 🛠️ **高级后处理与滤波选项**
  - 径向维纳滤波 (Radial Wiener Filter)
  - P-样条滤波 (P-spline Filter) - 用于复杂背景估计
  - 径向差分滤波 (Radial Difference Filter)
- 🎛️ **自动停止准则** (RL Multiplicative, GUI 可配置)
  - 残差型停止 (Residual-based) - 检测信号提取→噪声拟合转变
  - 熵平台检测 (Entropy Plateau) - 监测信息熵变化趋于平稳
  - 锐度最小检测 (Sharpness Minimum) - 检测锐度 U 型曲线最小值
- 📁 **MRC 文件格式支持**

## 系统要求

- Python 3.9 或更高版本
- 操作系统：Linux, macOS, Windows

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/chenguisen/dec_stem_for_computer.git
cd dec_stem_for_computer
```

### 2. 创建虚拟环境（推荐）

```bash
# 使用 venv
python -m venv venv

# Linux/macOS 激活
source venv/bin/activate

# Windows 激活
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖包说明

| 包名 | 版本要求 | 用途 |
|------|----------|------|
| PyQt6 | >=6.0.0 | 图形界面框架 |
| numpy | >=1.20.0 | 数值计算 |
| scipy | >=1.7.0 | 科学计算 |
| matplotlib | >=3.5.0 | 数据可视化 |
| mrcfile | >=1.4.0 | MRC 文件读写 |
| numba | >=0.56.0 | 性能加速（可选） |
| scikit-image | >=0.19.0 | 图像处理（可选） |
| tqdm | >=4.62.0 | 进度条（可选） |

## 使用方法

### 图形界面（推荐）

启动 GUI 应用：

```bash
python deconvolution_gui.py
```

#### GUI 使用步骤：

1. **选择图像文件** - 点击 "Browse..." 选择 MRC 格式的图像
2. **设置输出路径** - 指定结果保存目录
3. **配置显微镜参数** - 根据您的设备设置电压、球差、离焦等参数
4. **选择算法** - 选择一种解卷积算法：
   - Richardson-Lucy Additive：适合大多数情况
   - Richardson-Lucy Multiplicative：适合强度变化较大的图像，支持加速和阻尼
   - FISTA：适合需要稀疏约束和TV正则化的场景
5. **调整参数** - 设置迭代次数、正则化参数、停止准则、边界处理等高级选项
6. **选择后处理** - 可叠加使用 Wiener / P-spline / 径向差分滤波
7. **预览探针** - 点击 "Preview Probe" 查看生成的探针函数
8. **开始处理** - 点击 "Start Processing" 执行解卷积
9. **查看结果** - 在三个标签页中查看探针、原始数据和结果
10. **保存结果** - 点击 "Save Results" 保存解卷积图像

#### 主题切换

通过菜单栏 `🎨 Theme` 切换不同的界面主题。

#### 显示控制

每个图像显示区域都有三个控制选项：

- **Space**: 选择实空间 (Real Space) 或频域 (Frequency Space)
- **Mode**: 选择线性 (Linear)、功率谱 (Power) 或对数 (Log) 显示
- **Colormap**: 选择颜色映射方案

### 命令行使用

对于批量处理或自动化流程，可以使用命令行工具：

```bash
python run_deconv.py
```

**注意**：默认示例代码需要修改图像路径和参数。请在 `run_deconv.py` 中配置参数。

#### 参数说明

- `image_path`: 输入 MRC 文件路径
- `output_path`: 输出文件路径
- `voltage`: 加速电压 (kV)
- `cs3`: 三级球差系数 (mm)
- `cs5`: 五级球差系数 (mm)
- `defocus`: 离焦量 (nm)
- `obj_aperture`: 物镜光阑 (mrad)
- `iterations`: 解卷积迭代次数
- `lambda_reg`: 正则化参数
- `reg_type`: 正则化类型 ("TV" 或 "L2")

### 结果对比

使用 `compare_results.py` 对比不同算法的结果：

```bash
python compare_results.py
```

## 解卷积算法说明

### Richardson-Lucy Additive

适用于 HAADF-STEM 图像的加法模型，适合大多数情况。

**特点**：
- 数值稳定
- 收敛性好
- 适合一般图像

### Richardson-Lucy Multiplicative

基于乘法模型的 RL 算法，带有 TV 正则化和自动化停止准则，适合强度变化较大的图像。

**特点**：
- TV 正则化（空间自适应边缘保持）
- 乘法约束，自然保持非负性
- Biggs-Andrews 向量外推加速（数据依赖步长，0-1 钳位）
- 阻尼(Damping)控制以抑制平坦区域的噪声放大
- 三种自动化停止准则：残差型、熵平台检测、锐度最小检测
- 停止时自动回滚到最佳迭代结果

### FISTA

快速迭代收缩阈值算法，结合全变分(TV)正则化和 Chambolle 投影近端算子。

**特点**：
- Nesterov 加速（动量外推）
- Chambolle 对偶投影算法实现 TV 近端算子
- 强大的保边去噪能力 (TV正则化)
- 适合极低信噪比及高斯噪声主导的图像

## 后处理

### 径向维纳滤波 (Radial Wiener Filter)

用于抑制高频噪声，提高信噪比。

### P-样条滤波 (P-spline Filter)

基于 P-样条的高级滤波方法，提供更好的复杂背景估计和频率响应控制。

**参数**：
- `P-spline Lambda`: 样条平滑参数
- `Information Limit`: 信息截止频率（可自动估计）

### 径向差分滤波 (Radial Difference Filter)

通过减去径向平均背景来增强结构信息。

## 文件结构

```
dec_stem_for_computer/
├── deconvolution_gui.py      # GUI 主程序
├── run_deconv.py            # 命令行工具
├── compare_results.py        # 结果对比工具
├── test_damping.py           # 阻尼参数测试
├── config_manager.py         # 配置管理
├── session_logger.py         # 会话日志记录
├── requirements.txt          # 依赖包列表
├── tests/                   # 测试
│   └── test_pipeline.py     # Pipeline 集成测试
├── testdata/                # 测试数据
├── stem_deconv/             # 核心算法库
│   ├── core.py              # 解卷积算法 (RL, RL-TV, FISTA-TV)
│   ├── physics.py           # 电子光学与探针计算 (CTF)
│   ├── postprocess.py       # 滤波与后处理 (Wiener, P-spline)
│   ├── regularization.py    # 正则化方法 (TV, Tikhonov-Miller)
│   ├── io.py                # MRC/DM3 文件读写
│   ├── display.py           # 图像显示与频谱可视化
│   ├── metrics.py           # 定量评估 (SNR, SSIM, MSE, FRC)
│   └── utils.py             # FFT 工具函数
```

## 常见问题 (FAQ)

### Q: 如何获取显微镜参数？

A: 这些参数通常由显微镜厂商提供，可以从图像文件的元数据中读取，或参考设备手册。

### Q: 迭代次数如何选择？

A: 一般 10-30 次迭代即可。迭代次数过多可能导致噪声放大，可尝试不同次数找到最佳值。

### Q: 正则化参数 λ 如何调整？

A: λ 越小，图像越锐利但噪声也越多；λ 越大，图像越平滑。建议从 0.001-0.01 范围开始尝试。

### Q: 为什么需要边界处理？

A: 由于傅里叶变换的周期性假设，图像边界可能出现伪影。边界处理可以减少这些伪影。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

Academic Use License

## 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues: https://github.com/chenguisen/dec_stem_for_computer/issues

## 更新日志

### v1.2.1 (2026-05)
- GUI 新增三种停止准则独立控制（残差、熵平台、锐度最小）
- GUI 新增径向差分滤波选项
- P-spline 滤波可独立启用，不再依赖 Wiener 总开关
- 所有后处理滤波可叠加使用
- 清理 postprocess.py 死代码，更新 scipy.fftpack → scipy.fft

### v1.2.0 (2026-05)
- 增强 Biggs-Andrews 向量外推加速（数据依赖步长）
- 实现 Chambolle 投影算法用于 FISTA-TV 近端算子
- 新增三种自动化停止准则：残差、熵平台、锐度最小检测
- 新增 `metrics.py` 模块（SNR, SSIM, MSE, FRC 定量评估）
- FFT 零填充默认策略更新为 2 的幂次
- 更新依赖版本：Python 3.9+, PyQt6, scikit-image 0.19+
- 代码与 CPC 期刊论文描述对齐

### v1.1.0 (2026-02)
- 增加 FISTA 算法与 TV 正则化
- 增加 RL 乘法算法的 Biggs-Andrews 加速与阻尼控制
- 增加 P-样条滤波和径向差分滤波
- 优化 GUI 界面与高级参数设置

### v1.0.0 (2025-12-25)
- 初始版本发布
- 完整的 GUI 界面
- 三种解卷积算法
- 多主题支持
- 实时探针预览
- 后处理功能
