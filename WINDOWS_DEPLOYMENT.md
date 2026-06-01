# Windows 部署使用指南

本指南说明如何在 Windows 系统上使用独立打包版本。

## 快速开始

### 第一步：获取软件

1. 下载压缩包: `HAADF_STEM_Deconvolution_v1.0.0_Windows_x64.zip`
2. 解压到任意目录（如 `D:\HAADF_STEM\`）

### 第二步：运行程序

**方法 1：双击运行**
- 双击 `HAADF_STEM_Deconvolution.exe`

**方法 2：使用批处理脚本**
- 双击 `run.bat`

### 第三步：使用软件

1. 选择图像文件
2. 配置参数
3. 处理图像
4. 查看结果

## 文件存储逻辑详解

### 自动创建会话文件夹

软件默认会为每次处理创建一个新的会话文件夹。

#### 文件夹命名规则

- **默认格式**: `session_YYYYMMDD_HHMMSS`
- **示例**: `session_20251225_153045`
  - `2025`: 年份
  - `12`: 月份
  - `25`: 日期
  - `15`: 小时
  - `30`: 分钟
  - `45`: 秒

#### 文件夹结构

```
outputs/
├── session_20251225_153045/    ← 第1次处理
│   ├── original.mrc            # 原始图像
│   ├── probe.mrc               # 探针函数
│   ├── result_additive.mrc     # 解卷积结果
│   ├── parameters.json          # 处理参数
│   └── log.txt                # 处理日志
│
├── session_20251225_154230/    ← 第2次处理
│   ├── original.mrc
│   ├── probe.mrc
│   ├── result_multiplicative.mrc
│   ├── parameters.json
│   └── log.txt
│
└── session_20251225_155812/    ← 第3次处理
    ├── original.mrc
    ├── probe.mrc
    ├── result_fista.mrc
    ├── parameters.json
    └── log.txt
```

### 优势

1. **历史追踪**: 每次处理都有独立的文件夹，不会覆盖
2. **时间顺序**: 文件夹按时间排序，易于管理
3. **完整记录**: 每个会话包含所有相关文件
4. **易于备份**: 可以单独备份或删除会话文件夹

## 自定义输出路径

### 查找配置文件

配置文件位于：
- **Windows**: `C:\Users\<用户名>\AppData\Roaming\HAADF_STEM_Config\config.json`

### 修改输出路径

1. 打开配置文件（使用文本编辑器，如 Notepad 或 VS Code）
2. 找到 `paths` 部分
3. 修改 `default_output` 值

#### 示例 1：自定义目录

```json
{
  "paths": {
    "default_output": "D:\\MyData\\STEM_Results",
    "auto_create_session_folder": true,
    "session_folder_format": "session_%Y%m%d_%H%M%S"
  }
}
```

#### 示例 2：使用固定文件夹

如果不想每次创建新文件夹：

```json
{
  "paths": {
    "default_output": "D:\\STEM_Data",
    "auto_create_session_folder": false,
    "session_folder_format": "results"
  }
}
```

**效果**:
- 所有处理结果保存到 `D:\STEM_Data\`
- 文件会相互覆盖（请注意备份！）

#### 示例 3：按日期分组

```json
{
  "paths": {
    "default_output": "outputs",
    "auto_create_session_folder": true,
    "session_folder_format": "%Y%m%d"  // 只有日期，每次处理同一文件夹
  }
}
```

**效果**:
- 同一天的所有处理结果保存在同一文件夹
- 文件名: `original.mrc`, `probe.mrc`, `result_001.mrc`, `result_002.mrc`...

## 会话文件夹格式自定义

### 支持的占位符

| 占位符 | 说明 | 示例 | 备注 |
|---------|------|--------|------|
| `%Y` | 4位年份 | 2025 | |
| `%y` | 2位年份 | 25 | 不推荐，可能有歧义 |
| `%m` | 月份 | 01-12 | 01=一月，12=十二月 |
| `%d` | 日期 | 01-31 | |
| `%H` | 小时 | 00-23 | 24 小时制 |
| `%M` | 分钟 | 00-59 | |
| `%S` | 秒 | 00-59 | |

### 格式示例

| 格式 | 示例输出 | 说明 |
|------|----------|------|
| `session_%Y%m%d_%H%M%S` | `session_20251225_153045` | 默认，最详细 |
| `stem_%Y%m%d` | `stem_20251225` | 按日期分组 |
| `result_%y%m%d_%H%M` | `result_251225_1530` | 省略年份前缀 |
| `output_%H%M%S` | `output_153045` | 只按时间，不包含日期 |
| `session_%Y%m%d_HH` | `session_20251225_15` | 精确到小时 |
| `my_folder` | `my_folder` | 固定名称，每次覆盖 |

## 参数文件说明

每次处理会自动生成 `parameters.json` 文件：

```json
{
  "timestamp": "2025-12-25T15:30:45.123456",
  "version": "1.0.0",
  "parameters": {
    "image_path": "D:\\Data\\test_image.mrc",
    "output_path": "outputs\\session_20251225_153045",
    "voltage_kv": 300.0,
    "cs3_mm": 0.5,
    "cs5_mm": 0.0,
    "defocus_nm": -44.0,
    "obj_aperture_rad": 0.016,
    "iterations": 15,
    "lambda_reg": 0.002,
    "fista_lambda_reg": 0.005,
    "reg_type": "TV",
    "algorithm": 0,
    "boundary_handling": true,
    "acceleration": true,
    "apply_wiener": true,
    "use_p_spline": false,
    "p_spline_lambda": 1000.0,
    "information_limit": null
  }
}
```

### 参数文件用途

1. **复现结果**: 使用相同的参数重新处理
2. **文档记录**: 记录实验参数
3. **批量处理**: 可以读取参数文件进行自动化处理
4. **参数优化**: 比较不同参数的效果

## 日志文件说明

每次处理的日志记录在 `log.txt` 中：

```
======================================================================
HAADF-STEM Image Deconvolution - Processing Log
======================================================================

Session started: 2025-12-25 15:30:45
Session folder: outputs\session_20251225_153045
System: win32
Python version: 3.10.12

----------------------------------------------------------------------

--- Parameters ---
image_path: D:\Data\test_image.mrc
voltage_kv: 300.0
defocus_nm: -44.0
...

----------------------------------------------------------------------

[15:30:46] [PROGRESS] Loading image...
[15:30:47] [PROGRESS] Image loaded: (512, 512), Pixel size: 0.1 nm
[15:30:47] [PROGRESS] Generating probe...
[15:30:48] [PROGRESS] Running Richardson-Lucy Additive...
[15:31:02] [PROGRESS] Applying post-processing...
[15:31:05] [PROGRESS] Processing completed!

----------------------------------------------------------------------

--- Results ---
output_shape: (512, 512)
processing_time: 18.5s
algorithm: additive

----------------------------------------------------------------------

--- Saved Files ---
- outputs\session_20251225_153045\original.mrc
- outputs\session_20251225_153045\probe.mrc
- outputs\session_20251225_153045\result_additive.mrc

----------------------------------------------------------------------

Session completed: 2025-12-25 15:31:08
======================================================================
```

### 日志级别

- `[INFO]`: 一般信息
- `[PROGRESS]`: 处理进度
- `[WARNING]`: 警告信息
- `[ERROR]`: 错误信息

## 使用场景示例

### 场景 1：每日研究工作

**需求**: 每天处理多个图像，按日期组织结果

**配置**:
```json
{
  "paths": {
    "session_folder_format": "%Y%m%d"
  }
}
```

**结果**:
```
outputs/
├── 20251224/    ← 12月24日所有处理
│   ├── original.mrc
│   ├── result_001.mrc
│   ├── result_002.mrc
│   └── ...
└── 20251225/    ← 12月25日所有处理
    ├── original.mrc
    ├── result_001.mrc
    └── ...
```

### 场景 2：批量处理同一图像

**需求**: 用不同参数测试同一图像，优化参数

**配置**:
```json
{
  "paths": {
    "session_folder_format": "test_%Y%m%d_%H%M%S"
  }
}
```

**操作流程**:
1. 加载图像
2. 设置参数组 1 → 处理 → 生成 `test_20251225_100000/`
3. 设置参数组 2 → 处理 → 生成 `test_20251225_101500/`
4. 修改参数组 3 → 处理 → 生成 `test_20251225_103000/`
5. 比较各结果文件夹的图像

### 场景 3：长期项目存储

**需求**: 将所有结果存储在专用磁盘

**配置**:
```json
{
  "paths": {
    "default_output": "E:\\STEM_Projects\\2025\\Results",
    "auto_create_session_folder": true
  }
}
```

**结果**:
```
E:\STEM_Projects\2025\Results\
├── session_20251225_100000/
├── session_20251225_120000/
├── session_20251226_093000/
└── ...
```

## 常见问题

### Q: 如何找到最新处理的结果？

**A**: 文件夹按时间排序，最后的是最新的：

1. 打开 `outputs/` 文件夹
2. 按日期排序（最新的在最后）
3. 或按时间戳排序（`session_YYYYMMDD_HHMMSS`）

### Q: 可以更改已有会话的名称吗？

**A**: 可以，直接重命名文件夹：

```
session_20251225_153045/  →  my_experiment_001/
```

软件不会重命名，所以可以自由管理。

### Q: 如何删除旧会话？

**A**: 直接删除对应的会话文件夹：

```
outputs/session_20251225_153045/  → 删除
```

不会影响其他会话和新文件的创建。

### Q: 处理失败后文件在哪里？

**A**: 即使处理失败，会话文件夹和部分文件可能已创建：

- 检查最近的 `session_YYYYMMDD_HHMMSS/` 文件夹
- 查看 `log.txt` 了解失败原因
- 检查是否有 `parameters.json`（部分保存）

### Q: 可以指定绝对路径吗？

**A**: 可以，在配置文件中使用完整的绝对路径：

```json
{
  "paths": {
    "default_output": "E:\\Data\\Results",
    "auto_create_session_folder": true
  }
}
```

### Q: 网络路径支持吗？

**A**: 支持，使用 UNC 路径：

```json
{
  "paths": {
    "default_output": "\\\\server\\share\\STEM_Results"
  }
}
```

注意：网络路径需要正确的访问权限。

### Q: 日志文件太大怎么办？

**A**: 可以删除旧日志，或配置文件系统自动清理：

1. 手动删除：删除对应会话的 `log.txt`
2. 定期清理：删除旧的整个会话文件夹

### Q: 如何备份所有结果？

**A**: 整个 `outputs/` 文件夹备份：

```bash
# 使用 Windows 内置工具
# 右键点击 outputs/ → 发送到 → 压缩(zipped)文件夹

# 或使用命令行
powershell Compress-Archive -Path outputs -DestinationPath outputs_backup.zip
```

## 高级技巧

### 技巧 1：使用符号链接（Windows 10+）

在多个位置访问同一输出目录：

```powershell
# 创建符号链接
New-Item -ItemType SymbolicLink -Path "C:\Users\<用户名>\Desktop\STEM_Results" -Target "E:\STEM_Data\outputs"
```

### 技巧 2：自动化文件整理

创建批处理脚本移动旧会话：

```batch
@echo off
set /a DAYS=30

forfiles /p "outputs\" /d -%DAYS% /c "cmd /c echo Moving @file... & move \"@file\" \"outputs\\archive\\""
```

### 技巧 3：导出参数列表

提取所有会话的参数到 CSV：

```python
import json
import os
import csv

# 创建CSV文件
with open('all_parameters.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['session', 'voltage', 'defocus', 'iterations', 'algorithm'])

    # 遍历所有会话文件夹
    for session_dir in os.listdir('outputs'):
        param_file = os.path.join('outputs', session_dir, 'parameters.json')
        if os.path.exists(param_file):
            with open(param_file, 'r') as f:
                params = json.load(f)
                data = params.get('parameters', {})
                writer.writerow([
                    session_dir,
                    data.get('voltage_kv', ''),
                    data.get('defocus_nm', ''),
                    data.get('iterations', ''),
                    data.get('algorithm', '')
                ])
```

### 技巧 4：监控输出文件夹

使用 Python 监控新会话创建：

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SessionHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory and 'session_' in event.src_path:
            print(f"新会话创建: {event.src_path}")

observer = Observer()
observer.schedule(SessionHandler(), 'outputs', recursive=False)
observer.start()
```

## 技术支持

如需更多帮助：

- **文档**: [README.md](README.md)
- **配置指南**: [CONFIG.md](CONFIG.md)
- **安装指南**: [INSTALL.md](INSTALL.md)
- **打包指南**: [PACKAGING_WINDOWS.md](PACKAGING_WINDOWS.md)
- **GitHub Issues**: [提交问题](https://github.com/chenguisen/deconvolution-stem/issues)

---

版本: 1.0.0
更新: 2025-12-25
