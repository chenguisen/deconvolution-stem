# Windows 打包指南 (Windows Packaging Guide)

本文档详细说明如何将 HAADF-STEM 解卷积工具打包为 Windows 独立可执行文件。

## 目录

- [打包概述](#打包概述)
- [系统要求](#系统要求)
- [打包前准备](#打包前准备)
- [打包步骤](#打包步骤)
- [打包目录结构](#打包目录结构)
- [测试可执行文件](#测试可执行文件)
- [分发指南](#分发指南)
- [常见问题](#常见问题)

## 打包概述

使用 PyInstaller 将 Python 应用程序打包为独立的 Windows 可执行文件（.exe），用户无需安装 Python 和依赖包即可运行。

### 打包特性

- ✅ **完全独立运行** - 不需要 Python 环境
- ✅ **自动输出文件夹** - 每次处理自动创建带时间戳的会话文件夹
- ✅ **配置文件支持** - 首次运行自动创建配置
- ✅ **日志记录** - 自动记录处理过程到日志文件
- ✅ **参数记录** - 每次处理保存参数到 JSON 文件
- ✅ **单文件分发** - 整个应用打包在一个文件夹中

## 系统要求

### 打包环境

- **操作系统**: Windows 10/11 (64位)
- **Python**: 3.9 - 3.11 (推荐 3.10)
- **Python 架构**: 64 位 (必须与目标系统一致)

### 工具依赖

```bash
pip install pyinstaller
```

## 打包前准备

### 1. 安装打包依赖

```bash
# 激活虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装所有依赖
pip install -r requirements.txt

# 安装 PyInstaller
pip install pyinstaller
```

### 2. 检查 Python 环境

```bash
python --version
# 应该显示 Python 3.9.x 或更高版本

python -c "import struct; print(struct.calcsize('P') * 8)"
# 应该显示 64 (64 位)
```

### 3. 测试应用程序

在打包前，确保应用程序能正常运行：

```bash
python deconvolution_gui.py
```

### 4. 准备测试数据（可选）

确保 `testdata/` 文件夹中有测试用的 MRC 文件：

```
testdata/
└── HAADF 14.0 Mx 20211225 0002 DCFI(HAADF)_Real_0.mrc
```

## 打包步骤

### 方法 1: 使用自动打包脚本（推荐）

这是最简单的方法，使用提供的 `build_windows.py` 脚本。

#### 步骤 1: 运行打包脚本

```bash
python build_windows.py
```

#### 脚本执行内容

1. **检查依赖** - 验证所有必需包已安装
2. **清理旧文件** - 删除之前的构建目录
3. **创建配置文件** - 生成配置模板
4. **构建可执行文件** - 调用 PyInstaller
5. **创建辅助文件** - 生成 README 和批处理脚本
6. **创建压缩包** - 打包为 ZIP 文件分发

#### 预期输出

```
deconvolution-stem/
├── build_windows/          # PyInstaller 构建临时文件
├── dist_windows/             # 最终输出目录
│   ├── HAADF_STEM_Deconvolution/       # 应用程序文件夹
│   │   ├── HAADF_STEM_Deconvolution.exe   # 主程序
│   │   ├── config.json                     # 配置模板
│   │   ├── README_Windows.txt             # 使用说明
│   │   ├── setup.bat                      # 安装脚本
│   │   ├── run.bat                        # 运行脚本
│   │   ├── stem_deconv/                   # Python 模块
│   │   ├── testdata/                      # 测试数据
│   │   └── _internal/                    # 内部依赖
│   └── HAADF_STEM_Deconvolution_v1.0.0_Windows_x64_20251225.zip
└── build_windows.spec        # PyInstaller 配置文件
```

### 方法 2: 手动使用 PyInstaller

如果需要更多控制，可以手动运行 PyInstaller。

#### 步骤 1: 修改 .spec 文件（可选）

编辑 `deconvolution_gui.spec` 以自定义打包配置：

```python
# 修改版本号
VERSION = '1.0.0'

# 添加图标（如果有）
icon='icon.ico'

# 排除不需要的模块以减小体积
excludes=['matplotlib.tests', 'numpy.tests', ...]
```

#### 步骤 2: 运行 PyInstaller

```bash
# 基础打包
pyinstaller --clean deconvolution_gui.spec

# 带详细输出
pyinstaller --clean --log-level=DEBUG deconvolution_gui.spec

# 创建单个可执行文件（不推荐，体积大）
pyinstaller --clean --onefile deconvolution_gui.spec
```

#### 步骤 3: 手动创建辅助文件

复制 README 和配置文件到输出目录：

```bash
# 复制配置模板
copy config.json dist_windows\HAADF_STEM_Deconvolution\

# 复制使用说明
copy README_Windows.txt dist_windows\HAADF_STEM_Deconvolution\
```

## 打包目录结构

### 完整的应用程序文件夹

打包完成后，`dist_windows/HAADF_STEM_Deconvolution/` 目录结构如下：

```
HAADF_STEM_Deconvolution/
├── HAADF_STEM_Deconvolution.exe     # 主可执行文件 (~80-150 MB)
├── config.json                       # 配置文件（可选，首次运行自动生成）
├── README_Windows.txt                 # 详细使用说明
├── setup.bat                        # 初始化脚本（可选）
├── run.bat                          # 快速运行脚本（可选）
├── stem_deconv/                      # Python 模块
│   ├── __init__.py
│   ├── core.py
│   ├── physics.py
│   ├── postprocess.py
│   └── ...
├── testdata/                         # 测试数据（可选）
│   └── HAADF 14.0 Mx ... .mrc
└── _internal/                        # PyInstaller 内部文件
    ├── PyQt6/
    ├── numpy/
    ├── scipy/
    └── ...
```

### 输出目录结构（运行时）

用户运行程序后，会自动创建输出目录：

```
outputs/                              # 默认输出根目录
├── session_20251225_153045/           # 会话文件夹 1
│   ├── original.mrc                    # 原始图像
│   ├── probe.mrc                      # 探针函数
│   ├── result_additive.mrc             # 解卷积结果
│   ├── parameters.json                  # 处理参数
│   └── log.txt                        # 处理日志
├── session_20251225_154230/           # 会话文件夹 2
│   ├── original.mrc
│   ├── probe.mrc
│   ├── result_multiplicative.mrc
│   ├── parameters.json
│   └── log.txt
└── session_20251225_155812/           # 会话文件夹 3
    ...
```

## 测试可执行文件

### 1. 基本功能测试

```bash
# 进入输出目录
cd dist_windows\HAADF_STEM_Deconvolution

# 运行程序
HAADF_STEM_Deconvolution.exe

# 或者使用批处理脚本
run.bat
```

**测试项目**:
- ✅ 程序正常启动
- ✅ 界面显示正常
- ✅ 主题切换正常
- ✅ 浏览文件功能正常
- ✅ 加载测试图像成功

### 2. 图像处理测试

1. **加载测试图像**:
   - 点击 "Browse..."
   - 选择 `testdata/HAADF 14.0 Mx ... .mrc`

2. **预览探针**:
   - 点击 "Preview Probe"
   - 检查探针图像是否正确显示

3. **运行解卷积**:
   - 点击 "Start Processing"
   - 观察进度条和日志输出

4. **检查输出**:
   - 进入 `outputs/session_YYYYMMDD_HHMMSS/` 文件夹
   - 验证生成的文件：
     - `original.mrc` - 原始图像
     - `probe.mrc` - 探针
     - `result_*.mrc` - 解卷积结果
     - `parameters.json` - 参数记录
     - `log.txt` - 日志文件

### 3. 配置文件测试

检查配置文件是否正确创建：

```bash
# Windows
%USERPROFILE%\HAADF_STEM_Config\config.json

# 示例路径
C:\Users\<用户名>\AppData\Roaming\HAADF_STEM_Config\config.json
```

**验证内容**:
```json
{
  "application": {
    "name": "HAADF-STEM Image Deconvolution",
    "version": "1.0.0"
  },
  "paths": {
    "default_output": "outputs",
    "auto_create_session_folder": true,
    "session_folder_format": "session_%Y%m%d_%H%M%S"
  },
  "ui": {
    "default_theme": "Dark Mode",
    "remember_window_size": true,
    "window_width": 1400,
    "window_height": 900
  }
}
```

### 4. 不同系统测试

在以下环境测试（如果可能）:

- ✅ Windows 10 家庭版
- ✅ Windows 10 专业版
- ✅ Windows 11 家庭版
- ✅ Windows 11 专业版
- ✅ 带有/没有杀毒软件的环境
- ✅ 静态 IP / 动态 IP 环境

## 分发指南

### 方法 1: 分发文件夹

**优点**: 简单直接，适合局域网

**步骤**:
1. 压缩 `dist_windows/HAADF_STEM_Deconvolution/` 文件夹
2. 分发压缩文件
3. 用户解压后直接运行

**分发命令**:
```bash
# 创建分发压缩包
cd dist_windows
powershell Compress-Archive -Path HAADF_STEM_Deconvolution -DestinationPath HAADF_STEM_Deconvolution_v1.0.0.zip

# 或使用 7-Zip
7z a HAADF_STEM_Deconvolution_v1.0.0.zip HAADF_STEM_Deconvolution\
```

### 方法 2: 分发单个 ZIP 文件

**优点**: 单文件下载，适合互联网分发

**步骤**:
1. 使用 `build_windows.py` 自动创建 ZIP
2. 上传到文件服务器或 GitHub Releases
3. 用户提供下载链接

**自动创建的 ZIP**:
```
HAADF_STEM_Deconvolution_v1.0.0_Windows_x64_20251225.zip (~150-300 MB)
```

### 方法 3: 安装包（可选）

创建 Windows 安装程序（.msi 或 .exe）。

**需要的工具**:
- NSIS (Nullsoft Scriptable Install System)
- Inno Setup

**基本 NSIS 脚本示例**:
```nsis
; HAADF_STEM_Deconvolution.nsi

!define APP_NAME "HAADF-STEM Deconvolution"
!define APP_VERSION "1.0.0"

Name "${APP_NAME}"
OutFile "${APP_NAME}_${APP_VERSION}_Setup.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
RequestExecutionLevel admin

Section "Main Files"
  SetOutPath $INSTDIR
  File /r "dist_windows\HAADF_STEM_Deconvolution\*.*"
  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Desktop Shortcut"
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\HAADF_STEM_Deconvolution.exe"
SectionEnd
```

**构建安装包**:
```bash
makensis HAADF_STEM_Deconvolution.nsi
```

### 分发清单

准备分发时，确保包含以下文件和文档：

- [ ] 可执行文件: `HAADF_STEM_Deconvolution.exe`
- [ ] 使用说明: `README_Windows.txt`
- [ ] 配置模板: `config.json`（可选）
- [ ] 许可证: `LICENSE`
- [ ] 测试数据: `testdata/`（可选）
- [ ] 版本信息: version.txt

## 常见问题

### Q: 打包后文件太大？

**原因**: 包含了所有依赖，包括 matplotlib 和 numpy。

**解决方案**:
1. 在 `.spec` 文件中添加 `excludes` 排除测试模块
2. 使用 `--onefile` 会更大，但方便分发
3. 考虑使用 UPX 压缩（已启用）

### Q: 运行时报错 "DLL not found"

**原因**: 缺少系统依赖或库版本不兼容。

**解决方案**:
1. 在开发机器安装 Visual C++ Redistributable
2. 将缺失的 DLL 复制到输出目录
3. 重新打包

### Q: 图像无法加载？

**原因**: 路径问题或文件格式不支持。

**解决方案**:
1. 检查文件是否为有效的 MRC 格式
2. 确保文件路径不含特殊字符
3. 查看日志文件 `log.txt` 获取详细错误信息

### Q: 输出文件在哪里？

**位置**:
- 默认: `程序目录\outputs\session_YYYYMMDD_HHMMSS\`
- 可通过配置文件修改: `%USERPROFILE%\HAADF_STEM_Config\config.json`

**自定义**:
```json
{
  "paths": {
    "default_output": "D:\\MyData\\STEM_Output"
  }
}
```

### Q: 如何更新程序？

**步骤**:
1. 用户停止旧版本程序
2. 备份 `outputs/` 文件夹
3. 替换 `HAADF_STEM_Deconvolution.exe`
4. 重新运行

### Q: 病毒扫描报警？

**原因**: PyInstaller 打包的程序可能被误报。

**解决方案**:
1. 添加到杀毒软件白名单
2. 代码签名（需要购买证书）
3. 使用信誉良好的分发平台

### Q: 打包时内存不足？

**原因**: PyInstaller 在分析大型依赖时占用大量内存。

**解决方案**:
1. 关闭其他应用程序
2. 在 `.spec` 文件中排除不必要的模块
3. 增加虚拟内存大小

## 高级配置

### 自定义图标

添加应用图标：

1. 准备 `.ico` 文件（推荐 256x256, 32 位）
2. 放置在项目根目录
3. 修改 `.spec` 文件：
```python
exe = EXE(
    ...
    icon='icon.ico',
    ...
)
```

### 减小体积

方法：

1. **排除测试模块**:
```python
excludes=['matplotlib.tests', 'numpy.tests', 'scipy.tests']
```

2. **优化导入**:
```python
hiddenimports=[
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'numpy',
    # 只包含必要的模块
]
```

3. **使用 UPX 压缩**:
```python
exe = EXE(
    ...
    upx=True,  # 已默认启用
    ...
)
```

### 启用加密（可选）

保护 Python 代码：

```python
# 生成加密密钥
python pyinstaller_utils/gen_cipherkey.py

# 在 .spec 文件中使用
block_cipher = block_cipher = pyi_crypto.PyiBlockCipher('your_key_here')

a = Analysis(
    ...
    cipher=block_cipher,
    ...
)
```

## 性能优化建议

### 打包优化

- 使用 64 位 Python 和 64 位 PyInstaller
- 清理构建目录后重新打包
- 关闭杀毒软件加速打包过程

### 运行时优化

- 确保使用 numba 加速（如果安装）
- 使用 SSD 存储输出文件
- 关闭不必要的后台应用程序

## 参考资源

- [PyInstaller 官方文档](https://pyinstaller.org/en/stable/)
- [PyQt6 官方文档](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [打包最佳实践](https://github.com/pyinstaller/pyinstaller/wiki)

## 附录

### 文件夹命名格式

`session_folder_format` 支持的占位符：

| 占位符 | 说明 | 示例 |
|---------|------|--------|
| `%Y` | 4位年份 | 2025 |
| `%y` | 2位年份 | 25 |
| `%m` | 月份 | 01-12 |
| `%d` | 日期 | 01-31 |
| `%H` | 小时 | 00-23 |
| `%M` | 分钟 | 00-59 |
| `%S` | 秒 | 00-59 |

**示例**:
- `session_%Y%m%d_%H%M%S` → `session_20251225_153045`
- `stem_%y%m%d` → `stem_251225`
- `result_%H%M` → `result_1530`

### 配置文件位置

不同操作系统的配置文件位置：

| 操作系统 | 路径 |
|---------|------|
| Windows | `%APPDATA%\HAADF_STEM_Config\config.json` |
| Linux | `~/.config/HAADF_STEM_Config/config.json` |
| macOS | `~/Library/Application Support/HAADF_STEM_Config/config.json` |

---

如有问题，请访问 [GitHub Issues](https://github.com/chenguisen/deconvolution-stem/issues)。
