# Installation Guide

This guide provides detailed instructions for installing the HAADF-STEM Deconvolution toolkit on various operating systems.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Install](#quick-install)
- [Detailed Installation](#detailed-installation)
  - [Linux](#linux)
  - [macOS](#macos)
  - [Windows](#windows)
- [Dependencies](#dependencies)
- [Troubleshooting](#troubleshooting)
- [Development Setup](#development-setup)

## System Requirements

### Software

- **Python**: 3.9 or later (3.10 or 3.11 recommended)
- **pip**: Python package manager (included with Python)
- **Git**: For cloning the repository (optional)

### Hardware

- **Memory**: Minimum 4 GB, 8 GB or more recommended
- **Storage**: At least 1 GB free space
- **CPU**: Multi-core processor supported (Numba auto-uses multi-core)

### Supported Operating Systems

- Linux (Ubuntu, Fedora, CentOS, etc.)
- macOS (10.15 Catalina and later)
- Windows 10/11

## Quick Install

If Python is already set up:

```bash
# 1. Clone the repository
git clone https://github.com/chenguisen/deconvolution-stem.git
cd deconvolution-stem

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the program
python deconvolution_gui.py
```

## Detailed Installation

### Linux

#### Install Python

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**Fedora/CentOS:**
```bash
sudo dnf install python3 python3-pip python3-venv
```

**Arch Linux:**
```bash
sudo pacman -S python python-pip python-virtualenv
```

#### Install system build dependencies

Some packages require compilation:

```bash
# Ubuntu/Debian
sudo apt install build-essential gfortran

# Fedora
sudo dnf install gcc gcc-c++ gfortran

# CentOS
sudo yum groupinstall "Development Tools"
sudo yum install gfortran
```

#### Create virtual environment and install

```bash
# Clone the repository
git clone https://github.com/chenguisen/deconvolution-stem.git
cd deconvolution-stem

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Run the program
python deconvolution_gui.py
```

### macOS

#### Install Python

**Using Homebrew (recommended):**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.10
```

**Or download from official installer:**
Download from https://www.python.org/downloads/

#### Install dependencies

```bash
# Clone the repository
git clone https://github.com/chenguisen/deconvolution-stem.git
cd deconvolution-stem

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Run the program
python deconvolution_gui.py
```

#### Notes

- macOS may require Xcode command-line tools: `xcode-select --install`
- If compilation errors occur, ensure Xcode is up to date

### Windows

#### Install Python

1. Visit https://www.python.org/downloads/
2. Download Python 3.9, 3.10, or 3.11 installer
3. Run the installer — **Important: check "Add Python to PATH"**
4. Complete installation

#### Install Visual C++ Build Tools (optional)

Some packages require compilation:

```powershell
# Run PowerShell as Administrator:
winget install Microsoft.VisualStudio.2022.BuildTools
```

#### Clone or download the repository

**Using Git:**
```powershell
git clone https://github.com/chenguisen/deconvolution-stem.git
cd deconvolution-stem
```

**Or download ZIP:**
1. Visit https://github.com/chenguisen/deconvolution-stem
2. Click "Code" → "Download ZIP"
3. Extract to a local directory

#### Create virtual environment and install

```powershell
# Open Command Prompt or PowerShell, enter the project directory
cd deconvolution-stem

# Create virtual environment
python -m venv venv

# Activate virtual environment
# PowerShell:
venv\Scripts\Activate.ps1
# or Command Prompt:
venv\Scripts\activate.bat

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Run the program
python deconvolution_gui.py
```

#### Windows PowerShell execution policy

If you see "execution of scripts is disabled":

```powershell
# Run PowerShell as Administrator:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Dependencies

### Required

| Package | Purpose | Dependencies |
|---------|---------|--------------|
| PyQt6 | GUI framework | None |
| numpy | Numerical computing | None |
| scipy | Scientific computing | numpy |
| matplotlib | Data visualization | numpy |
| mrcfile | MRC file I/O | numpy |

### Optional

| Package | Purpose | Notes |
|---------|---------|-------|
| numba | Performance acceleration | JIT compilation, significantly speeds up computation |
| scikit-image | Image processing | Additional image processing algorithms |
| tqdm | Progress bar | Terminal progress display for CLI tools |

### Minimal Installation

For basic functionality only:

```bash
pip install PyQt6 numpy scipy matplotlib mrcfile
```

## Troubleshooting

### Issue 1: Old pip version

**Error**: `WARNING: You are using pip version X, however version Y is available.`

**Solution**:
```bash
python -m pip install --upgrade pip
```

### Issue 2: Permission errors

**Error**: `Permission denied` or `Access denied`

**Solution**:
- On Linux/macOS: Use a virtual environment (recommended) instead of `sudo`
- On Windows: Run terminal as Administrator

### Issue 3: Compilation errors

**Error**: `Microsoft Visual C++ 14.0 is required` or similar

**Solution**:
- Windows: Install Visual C++ Build Tools
- Linux: Install `build-essential` and `gfortran`
- macOS: Install Xcode command-line tools

### Issue 4: PyQt6 installation fails

**Solution**:
```bash
# Try pre-built wheels
pip install PyQt6 --prefer-binary

# Or use conda as alternative
conda install pyqt
```

### Issue 5: numpy/scipy version conflicts

**Solution**:
```bash
# Clean old versions
pip uninstall numpy scipy

# Reinstall
pip install numpy scipy
```

### Issue 6: mrcfile import error

**Error**: `ImportError: No module named 'mrcfile'`

**Solution**:
```bash
pip install mrcfile
```

### Issue 7: Virtual environment activation fails

**Linux/macOS**: Ensure `python3-venv` is installed
```bash
# Ubuntu/Debian
sudo apt install python3-venv

# Fedora
sudo dnf install python3-virtualenv
```

**Windows**: Use the correct activation script
```powershell
# PowerShell
venv\Scripts\Activate.ps1

# CMD
venv\Scripts\activate.bat
```

## Development Setup

### Install development tools

```bash
# Activate virtual environment first, then:
pip install pytest pylint black flake8 mypy
```

### Run tests

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_pipeline.py

# Generate coverage report
pytest --cov=stem_deconv --cov-report=html
```

### Code formatting

```bash
# Format with Black
black stem_deconv/ *.py

# Check quality with Pylint
pylint stem_deconv/
```

## Verify Installation

Run the following to verify:

```bash
# Check Python version
python --version

# Test imports
python -c "import numpy, scipy, matplotlib, PyQt6; print('All imports successful!')"

# Launch GUI
python deconvolution_gui.py
```

If the GUI starts successfully, installation is complete!

## Uninstallation

### Uninstall packages

```bash
pip uninstall -y PyQt6 numpy scipy matplotlib mrcfile numba scikit-image tqdm
```

### Remove virtual environment

```bash
deactivate  # if activated
rm -rf venv  # Linux/macOS
# or on Windows:
rmdir /s venv
```

### Delete project

```bash
cd ..
rm -rf deconvolution-stem  # Linux/macOS
rmdir /s deconvolution-stem  # Windows
```

## Next Steps

After installation, refer to [README.md](README.md) for usage instructions.

For issues, please submit a report at [GitHub Issues](https://github.com/chenguisen/deconvolution-stem/issues).
