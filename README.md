# HAADF-STEM Image Deconvolution

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-CC%20BY--NC%204.0-blue.svg)](LICENSE)

A Python toolkit for HAADF-STEM (High-Angle Annular Dark-Field Scanning Transmission Electron Microscopy) image deconvolution, providing a complete graphical user interface and command-line tools.

## Features

- **Modern GUI** - PyQt6-based user-friendly interface
- **Multiple deconvolution algorithms**
  - Richardson-Lucy Additive algorithm
  - Richardson-Lucy Multiplicative algorithm — supports Biggs-Andrews acceleration and damping control
  - FISTA (Fast Iterative Shrinkage-Thresholding Algorithm) — with Total Variation regularization
- **Full microscope parameter configuration**
  - Accelerating voltage
  - Spherical aberration (Cs3, Cs5)
  - Defocus
  - Objective aperture
  - Advanced aberration parameters (A2, A3, B2, etc.)
- **Real-time probe preview**
- **Multi-view display**
  - Real-space / Frequency domain
  - Linear / Power spectrum / Log scale
  - Multiple color maps
- **Multiple color themes**
  - Professional Blue
  - Dark Mode
  - Light Clean
  - Nature Green
  - Sunset Orange
- **Advanced post-processing and filtering**
  - Radial Wiener filter
  - P-spline filter — for complex background estimation
  - Radial difference filter
- **Automated stopping criteria** (RL Multiplicative, configurable in GUI)
  - Residual-based stopping — detects signal extraction to noise fitting transition
  - Entropy plateau detection — monitors information entropy stabilization
  - Sharpness minimum detection — detects U-shaped sharpness curve minimum
- **MRC file format support**

## System Requirements

- Python 3.9 or later
- Operating systems: Linux, macOS, Windows

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/chenguisen/deconvolution-stem.git
cd deconvolution-stem
```

### 2. Create a virtual environment (recommended)

```bash
# Using venv
python -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### Dependency overview

| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | >=6.0.0 | GUI framework |
| numpy | >=1.20.0 | Numerical computing |
| scipy | >=1.7.0 | Scientific computing |
| matplotlib | >=3.5.0 | Data visualization |
| mrcfile | >=1.4.0 | MRC file I/O |
| numba | >=0.56.0 | Performance acceleration (optional) |
| scikit-image | >=0.19.0 | Image processing (optional) |
| tqdm | >=4.62.0 | Progress bar (optional) |

## Usage

### Graphical Interface (recommended)

Launch the GUI application:

```bash
python deconvolution_gui.py
```

#### GUI Workflow:

1. **Select image file** - Click "Browse..." to choose an MRC-format image
2. **Set output path** - Specify the result save directory
3. **Configure microscope parameters** - Set voltage, spherical aberration, defocus, etc.
4. **Choose algorithm** - Select a deconvolution algorithm:
   - Richardson-Lucy Additive: suitable for most cases
   - Richardson-Lucy Multiplicative: for images with large intensity variations, supports acceleration and damping
   - FISTA: for scenarios requiring sparse constraints and TV regularization
5. **Adjust parameters** - Set iteration count, regularization parameter, stopping criteria, boundary handling, etc.
6. **Select post-processing** - Optionally apply Wiener / P-spline / Radial difference filtering
7. **Preview probe** - Click "Preview Probe" to visualize the generated probe function
8. **Start processing** - Click "Start Processing" to begin deconvolution
9. **View results** - Inspect the probe, original data, and results across three tabs
10. **Save results** - Click "Save Results" to save the deconvolved image

#### Theme Switching

Switch interface themes via the `🎨 Theme` menu.

#### Display Controls

Each image display area provides three controls:

- **Space**: Select Real Space or Frequency Space
- **Mode**: Select Linear, Power spectrum, or Log display
- **Colormap**: Choose a color mapping scheme

### Command-Line Usage

For batch processing or automation workflows:

```bash
python run_deconv.py
```

**Note**: The default example requires modification of image path and parameters. Configure parameters inside `run_deconv.py`.

#### Key Parameters

- `image_path`: Input MRC file path
- `output_path`: Output file path
- `voltage`: Accelerating voltage (kV)
- `cs3`: Third-order spherical aberration (mm)
- `cs5`: Fifth-order spherical aberration (mm)
- `defocus`: Defocus (nm)
- `obj_aperture`: Objective aperture (mrad)
- `iterations`: Number of deconvolution iterations
- `lambda_reg`: Regularization parameter
- `reg_type`: Regularization type ("TV" or "L2")

### Result Comparison

Compare results from different algorithms using:

```bash
python compare_results.py
```

## Deconvolution Algorithms

### Richardson-Lucy Additive

Applies the additive RL model for HAADF-STEM images. Suitable for most use cases.

**Features**:
- Numerically stable
- Good convergence
- Suitable for general images

### Richardson-Lucy Multiplicative

Multiplicative RL algorithm with TV regularization and automated stopping criteria. Suitable for images with large intensity variations.

**Features**:
- TV regularization (spatially adaptive edge preservation)
- Multiplicative constraint with natural non-negativity preservation
- Biggs-Andrews vector extrapolation acceleration (data-dependent step size, clamped to [0, 1])
- Damping control to suppress noise amplification in flat regions
- Three automated stopping criteria: residual-based, entropy plateau, sharpness minimum
- Automatic rollback to the best iterate upon stopping

### FISTA

Fast Iterative Shrinkage-Thresholding Algorithm with Total Variation regularization and Chambolle dual projection proximal operator.

**Features**:
- Nesterov acceleration (momentum extrapolation)
- Chambolle dual projection algorithm for TV proximal operator
- Strong edge-preserving denoising (TV regularization)
- Suitable for very low SNR and Gaussian-noise-dominated images

## Post-Processing

### Radial Wiener Filter

Suppresses high-frequency noise and improves SNR.

### P-spline Filter

Advanced filtering based on P-splines, providing better complex background estimation and frequency response control.

**Parameters**:
- `P-spline Lambda`: Spline smoothing parameter
- `Information Limit`: Information cutoff frequency (can be auto-estimated)

### Radial Difference Filter

Enhances structural information by subtracting the radial average background.

## File Structure

```
deconvolution-stem/
├── deconvolution_gui.py      # GUI main program
├── run_deconv.py             # Command-line tool
├── compare_results.py        # Result comparison tool
├── test_damping.py           # Damping parameter testing
├── config_manager.py         # Configuration management
├── session_logger.py         # Session logging
├── requirements.txt          # Dependency list
├── tests/                    # Tests
│   └── test_pipeline.py      # Pipeline integration test
├── testdata/                 # Test data
├── stem_deconv/              # Core algorithm library
│   ├── core.py               # Deconvolution algorithms (RL, RL-TV, FISTA-TV)
│   ├── physics.py            # Electron optics and probe computation (CTF)
│   ├── postprocess.py        # Filtering and post-processing
│   ├── regularization.py     # Regularization methods (TV, Tikhonov-Miller)
│   ├── io.py                 # MRC/DM3 file I/O
│   ├── display.py            # Image display and spectrum visualization
│   ├── metrics.py            # Quantitative metrics (SNR, SSIM, MSE, FRC)
│   └── utils.py              # FFT utility functions
```

## FAQ

### Q: How do I obtain microscope parameters?

A: These parameters are typically provided by the microscope manufacturer, can be read from image file metadata, or found in the instrument manual.

### Q: How should I choose the number of iterations?

A: Generally 10-30 iterations are sufficient. Excessive iterations may lead to noise amplification. Try different values to find the optimum.

### Q: How do I adjust the regularization parameter λ?

A: Smaller λ produces sharper images but more noise; larger λ produces smoother images. Start with a range of 0.001–0.01.

### Q: Why is boundary handling needed?

A: Due to the periodic boundary assumption of the Fourier transform, artifacts may appear at image boundaries. Boundary handling reduces these artifacts.

## Contributing

Issues and Pull Requests are welcome!

## License

Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)

This license permits sharing and adaptation of the material for non-commercial purposes, provided appropriate attribution is given. Commercial use requires prior written permission from the copyright holder.

See the [LICENSE](LICENSE) file for details.

## Contact

For questions or suggestions:
- GitHub Issues: https://github.com/chenguisen/deconvolution-stem/issues

## Changelog

### v1.2.1 (2026-05)
- GUI: Independent control of three stopping criteria (residual, entropy plateau, sharpness minimum)
- GUI: Added radial difference filter option
- P-spline filter can be enabled independently, no longer tied to Wiener master switch
- All post-processing filters can be used in combination
- Cleaned up dead code in postprocess.py; migrated scipy.fftpack to scipy.fft

### v1.2.0 (2026-05)
- Enhanced Biggs-Andrews vector extrapolation acceleration (data-dependent step size)
- Implemented Chambolle dual projection algorithm for FISTA-TV proximal operator
- Added three automated stopping criteria: residual, entropy plateau, sharpness minimum
- Added `metrics.py` module (SNR, SSIM, MSE, FRC quantitative evaluation)
- Updated FFT zero-padding default strategy to next power of two
- Updated dependencies: Python 3.9+, PyQt6, scikit-image 0.19+
- Code aligned with CPC journal paper description

### v1.1.0 (2026-02)
- Added FISTA algorithm with TV regularization
- Added Biggs-Andrews acceleration and damping control for RL multiplicative
- Added P-spline filter and radial difference filter
- Optimized GUI and advanced parameter settings

### v1.0.0 (2025-12-25)
- Initial release
- Complete GUI
- Three deconvolution algorithms
- Multi-theme support
- Real-time probe preview
- Post-processing capabilities
