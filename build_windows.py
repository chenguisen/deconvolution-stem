#!/usr/bin/env python3
"""
Windows 独立打包脚本
用于将 HAADF-STEM Deconvolution 打包为 Windows 可执行文件
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
import json

# 配置
PROJECT_NAME = "HAADF_STEM_Deconvolution"
VERSION = "1.0.0"
OUTPUT_DIR = "dist"
BUILD_DIR = "build_windows"

def print_step(message):
    """打印构建步骤"""
    print(f"\n{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}\n")

def check_dependencies():
    """检查依赖"""
    print_step("检查依赖")

    required_packages = [
        'PyInstaller',
        'PyQt6',
        'numpy',
        'scipy',
        'matplotlib',
        'mrcfile',
    ]

    missing_packages = []

    for package in required_packages:
        try:
            if package == 'PyInstaller':
                import PyInstaller
            elif package == 'PyQt6':
                import PyQt6
            elif package == 'numpy':
                import numpy
            elif package == 'scipy':
                import scipy
            elif package == 'matplotlib':
                import matplotlib
            elif package == 'mrcfile':
                import mrcfile
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - 未安装")
            missing_packages.append(package)

    if missing_packages:
        print(f"\n错误: 缺少必需的包: {', '.join(missing_packages)}")
        print("请运行: pip install", ' '.join(missing_packages))
        sys.exit(1)

    print("\n所有依赖已满足 ✓")

def clean_build_dirs():
    """清理旧的构建目录"""
    print_step("清理旧的构建目录")

    dirs_to_clean = [OUTPUT_DIR, BUILD_DIR]

    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            print(f"删除: {dir_path}")
            shutil.rmtree(dir_path)
        else:
            print(f"跳过: {dir_path} (不存在)")

def create_config_file():
    """创建配置文件模板"""
    print_step("创建配置文件模板")

    config_template = {
        "application": {
            "name": "HAADF-STEM Image Deconvolution",
            "version": VERSION
        },
        "paths": {
            "default_output": "outputs",
            "auto_create_session_folder": True,
            "session_folder_format": "session_%Y%m%d_%H%M%S"
        },
        "ui": {
            "default_theme": "Dark Mode",
            "remember_window_size": True,
            "window_width": 1400,
            "window_height": 900
        }
    }

    # 创建配置目录（如果不存在）
    config_dir = os.path.join(os.path.expanduser("~"), "HAADF_STEM_Config")
    os.makedirs(config_dir, exist_ok=True)

    config_file = os.path.join(config_dir, "config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_template, f, indent=4, ensure_ascii=False)

    print(f"配置文件模板已创建: {config_file}")

def create_readme():
    """创建发布说明"""
    print_step("创建发布说明")

    readme_content = f"""# HAADF-STEM Image Deconvolution v{VERSION}

## 独立 Windows 版本

这是一个打包好的独立可执行版本，无需安装 Python 和其他依赖即可运行。

### 系统要求

- Windows 10/11 (64位)
- 至少 4GB 内存
- 至少 2GB 可用磁盘空间

### 文件说明

- `HAADF_STEM_Deconvolution.exe` - 主程序（双击运行）
- `testdata/` - 测试数据文件夹（可选）
- `config.json` - 配置文件（首次运行时自动创建）

### 使用方法

1. **首次运行**:
   - 双击 `HAADF_STEM_Deconvolution.exe` 启动程序
   - 程序会自动在用户目录创建配置文件

2. **选择图像**:
   - 点击 "Browse..." 选择 MRC 格式的图像文件
   - 程序支持 `.mrc` 和 `.mrcs` 格式

3. **配置参数**:
   - 设置显微镜参数（电压、球差、离焦等）
   - 选择解卷积算法和参数

4. **处理图像**:
   - 点击 "Preview Probe" 预览探针函数
   - 点击 "Start Processing" 开始解卷积

5. **保存结果**:
   - 结果会自动保存到 `outputs/session_YYYYMMDD_HHMMSS/` 文件夹
   - 文件夹名称包含时间戳，每次处理都会创建新文件夹

### 输出文件说明

处理完成后，会在输出文件夹中生成以下文件：

```
outputs/session_20251225_153045/
├── original.mrc              # 原始图像
├── probe.mrc                # 探针函数
├── result_additive.mrc       # 解卷积结果（加法算法）
├── parameters.json           # 处理参数记录
└── log.txt                 # 处理日志
```

### 文件夹命名规则

默认情况下，每次处理会自动创建一个新文件夹：

- **格式**: `session_YYYYMMDD_HHMMSS`
- **示例**: `session_20251225_153045`
  - 2025: 年份
  - 12: 月份
  - 25: 日期
  - 15: 小时
  - 30: 分钟
  - 45: 秒

### 自定义输出路径

如果需要更改输出路径：

1. 找到配置文件位置：
   - 路径: `C:\\Users\\<用户名>\\HAADF_STEM_Config\\config.json`

2. 用文本编辑器打开配置文件

3. 修改 `paths` 部分：

```json
{{
  "paths": {{
    "default_output": "D:\\MyData\\STEM_Output",
    "auto_create_session_folder": true,
    "session_folder_format": "session_%Y%m%d_%H%M%S"
  }}
}}
```

4. 保存配置文件并重启程序

### 文件夹格式自定义

`session_folder_format` 支持以下占位符：

- `%Y`: 4位年份 (2025)
- `%y`: 2位年份 (25)
- `%m`: 月份 (01-12)
- `%d`: 日期 (01-31)
- `%H`: 小时 (00-23)
- `%M`: 分钟 (00-59)
- `%S`: 秒 (00-59)

**示例格式**:
- `session_%Y%m%d_%H%M%S` → `session_20251225_153045`
- `stem_output_%Y%m%d` → `stem_output_20251225`
- `result_%H%M` → `result_1530`
- `manual_folder` → `manual_folder`（无时间戳，每次覆盖）

### 关闭自动创建文件夹

如果希望在固定文件夹保存所有结果：

```json
{{
  "paths": {{
    "default_output": "outputs",
    "auto_create_session_folder": false,
    "session_folder_format": "results"
  }}
}}
```

### 参数文件说明

每次处理会生成 `parameters.json` 文件，记录所有参数：

```json
{{
  "image_path": "C:\\Users\\test\\image.mrc",
  "output_path": "outputs/session_20251225_153045",
  "voltage_kv": 300.0,
  "defocus_nm": -44.0,
  "algorithm": "additive",
  "iterations": 15,
  ...
}}
```

### 日志文件

处理过程会记录在 `log.txt` 中，包含：
- 开始时间
- 加载的图像信息
- 使用的参数
- 处理进度
- 错误信息（如果有）
- 完成时间

### 常见问题

**Q: 程序无法启动？**
A: 确保 Windows 10/11 64位系统，关闭杀毒软件重试。

**Q: 保存的文件在哪里？**
A: 默认在程序目录下的 `outputs/session_YYYYMMDD_HHMMSS/` 文件夹中。

**Q: 如何修改输出路径？**
A: 编辑配置文件 `C:\\Users\\<用户名>\\HAADF_STEM_Config\\config.json`

**Q: 能否在旧文件夹追加新结果？**
A: 可以，关闭自动创建文件夹功能，手动指定固定路径。

### 技术支持

如遇问题，请访问:
- GitHub: https://github.com/chenguisen/deconvolution-stem
- Issues: https://github.com/chenguisen/deconvolution-stem/issues

---

版本: {VERSION}
发布日期: {datetime.now().strftime('%Y-%m-%d')}
"""

    readme_file = os.path.join(OUTPUT_DIR, "README_Windows.txt")
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"发布说明已创建: {readme_file}")

def build_exe():
    """构建可执行文件"""
    print_step("构建可执行文件")

    # PyInstaller 命令
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'deconvolution_gui.spec'
    ]

    print(f"执行命令: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("警告:", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"错误: 构建失败")
        print("标准输出:", e.stdout)
        print("错误输出:", e.stderr)
        sys.exit(1)

    print("\n构建完成 ✓")

def create_installer_script():
    """创建安装脚本（可选）"""
    print_step("创建安装脚本")

    batch_content = f"""@echo off
echo ========================================
echo HAADF-STEM Deconvolution Setup
echo ========================================
echo.

echo 1. Creating output directories...
if not exist "outputs" mkdir outputs
echo Output directory created.

echo.
echo 2. Creating config directory...
if not exist "%USERPROFILE%\\HAADF_STEM_Config" mkdir "%USERPROFILE%\\HAADF_STEM_Config"
echo Config directory created.

echo.
echo 3. Installation complete!
echo.
echo You can now run HAADF_STEM_Deconvolution.exe
echo.
echo Default output location: outputs\\
echo Config location: %USERPROFILE%\\HAADF_STEM_Config\\
echo.
pause
"""

    batch_file = os.path.join(OUTPUT_DIR, "setup.bat")
    with open(batch_file, 'w', encoding='gbk') as f:
        f.write(batch_content)

    print(f"安装脚本已创建: {batch_file}")

def create_run_script():
    """创建运行脚本"""
    print_step("创建运行脚本")

    batch_content = """@echo off
echo Starting HAADF-STEM Deconvolution...
echo.

REM 检查是否在正确目录
if not exist "HAADF_STEM_Deconvolution.exe" (
    echo Error: HAADF_STEM_Deconvolution.exe not found in current directory!
    echo Please run this script from the installation folder.
    pause
    exit /b 1
)

REM 运行程序
HAADF_STEM_Deconvolution.exe

if errorlevel 1 (
    echo.
    echo Program exited with an error.
    pause
)
"""

    batch_file = os.path.join(OUTPUT_DIR, "run.bat")
    with open(batch_file, 'w', encoding='gbk') as f:
        f.write(batch_content)

    print(f"运行脚本已创建: {batch_file}")

def create_zip():
    """创建压缩包"""
    print_step("创建分发压缩包")

    if not os.path.exists(OUTPUT_DIR):
        print("错误: 输出目录不存在")
        return

    # 使用 7z 或 zip 命令
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_name = f"{PROJECT_NAME}_v{VERSION}_Windows_x64_{timestamp}.zip"
    zip_path = os.path.join(os.path.dirname(OUTPUT_DIR), zip_name)

    print(f"创建压缩包: {zip_name}")

    try:
        # 优先使用 7z（Windows 上更常见）
        if shutil.which('7z'):
            cmd = f'7z a -tzip "{zip_path}" "{os.path.abspath(OUTPUT_DIR)}\\*"'
            subprocess.run(cmd, shell=True, check=True)
        # 使用 Python zipfile
        else:
            import zipfile
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(OUTPUT_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(OUTPUT_DIR))
                        zipf.write(file_path, arcname)

        print(f"压缩包已创建: {zip_name}")
        print(f"大小: {os.path.getsize(zip_path) / 1024 / 1024:.2f} MB")

    except Exception as e:
        print(f"警告: 创建压缩包失败: {e}")
        print(f"请手动压缩 {OUTPUT_DIR} 目录")

def main():
    """主函数"""
    print(f"\n{'#'*60}")
    print(f"# HAADF-STEM Deconvolution Windows 打包工具")
    print(f"# 版本: {VERSION}")
    print(f"#{'#'*60}\n")

    # 1. 检查依赖
    check_dependencies()

    # 2. 清理旧文件
    clean_build_dirs()

    # 3. 创建配置文件
    create_config_file()

    # 4. 构建可执行文件
    build_exe()

    # 5. 创建辅助文件
    create_readme()
    create_installer_script()
    create_run_script()

    # 6. 创建压缩包
    create_zip()

    print(f"\n{'='*60}")
    print("  打包完成!")
    print(f"{'='*60}")
    print(f"\n输出目录: {os.path.abspath(OUTPUT_DIR)}")
    print(f"\n分发文件:")
    print(f"  1. {OUTPUT_DIR}/")
    print(f"  2. {PROJECT_NAME}_v{VERSION}_Windows_x64_*.zip")
    print(f"\n下一步:")
    print(f"  1. 测试运行 {OUTPUT_DIR}/HAADF_STEM_Deconvolution.exe")
    print(f"  2. 将整个 {OUTPUT_DIR} 文件夹或压缩包分发给用户")
    print(f"\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()
