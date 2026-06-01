# Configuration Guide

This document details the parameter configuration for the HAADF-STEM Deconvolution toolkit.

## Table of Contents

- [Microscope Parameters](#microscope-parameters)
- [Deconvolution Parameters](#deconvolution-parameters)
- [Advanced Aberration Parameters](#advanced-aberration-parameters)
- [Post-Processing Parameters](#post-processing-parameters)
- [Display Parameters](#display-parameters)
- [Recommended Parameter Values](#recommended-parameter-values)
- [Parameter Tuning Strategy](#parameter-tuning-strategy)
- [Troubleshooting](#troubleshooting)

## Microscope Parameters

### Voltage

**Unit**: kV

**Description**: Accelerating voltage of the electron microscope.

**Common values**:
- 80 kV: Suitable for low-voltage TEM
- 200 kV: Standard TEM
- 300 kV: High-resolution TEM (most common)
- 1000 kV: Ultra-high voltage TEM

**Effect**: Higher voltage yields shorter electron wavelength and better resolution, but may increase sample damage.

### Cs3 (Third-order Spherical Aberration)

**Unit**: mm

**Description**: Third-order spherical aberration coefficient, one of the primary aberration terms.

**Typical values**:
- Without Cs corrector: 0.5 - 3.0 mm
- With Cs corrector: < 0.1 mm
- Modern TEM: typically < 1.0 mm

**Effect**: Larger Cs reduces resolution. Cs correction significantly improves resolution.

### Cs5 (Fifth-order Spherical Aberration)

**Unit**: mm

**Description**: Fifth-order spherical aberration coefficient, typically much smaller than Cs3.

**Typical values**: 0.0 - 0.5 mm

**Effect**: Mainly affects high-angle scattering; can be set to 0 for most images.

### Defocus

**Unit**: nm

**Description**: Objective lens defocus distance. Positive values indicate overfocus, negative values indicate underfocus.

**Typical values**:
- Underfocus: -10 to -100 nm (most common)
- Overfocus: +10 to +100 nm
- Scherzer focus: Slightly positive (for phase contrast)

**Effect**:
- Underfocus enhances contrast but may introduce artifacts
- Overfocus blurs the image
- Excessive defocus causes CTF oscillations

**Recommendation**: Use the Fourier transform of the image to observe the CTF and choose a defocus where the first CTF zero is at a reasonable position.

### Objective Aperture

**Unit**: mrad

**Description**: The collection angle of the objective aperture, determining the semi-angle of the probe.

**Typical values**:
- 8 - 12 mrad: Low angle, high penetration
- 12 - 20 mrad: Standard setting (common)
- 20 - 30 mrad: High angle, high resolution

**Effect**:
- Larger aperture yields smaller probe and better resolution
- However, high angles may cause probe tailing and increase computational complexity

### Pixel Size

**Unit**: nm

**Description**: The physical size corresponding to each image pixel, typically read automatically from MRC file metadata.

**Calculation**:
```
Pixel Size = Camera Pixel Size × Magnification / 1000
```

**Effect**: Smaller pixel size gives higher digital resolution but larger data volume.

## Deconvolution Parameters

### Iterations

**Range**: 1 - 100

**Description**: Number of deconvolution algorithm iterations.

**Recommended values**:
- Quick preview: 5 - 10 iterations
- Standard processing: 15 - 30 iterations
- High quality: 30 - 50 iterations
- Not recommended beyond 100 iterations

**Effect**:
- Too few iterations: insufficient deconvolution, blurry result
- Too many iterations: noise amplification, possible artifacts

**Selection guide**:
1. Start with 10 iterations
2. Observe the result
3. Gradually increase to find the optimal balance

### Lambda (RL Regularization Parameter)

**Range**: 0.0001 - 1.0

**Description**: Regularization parameter for the Richardson-Lucy algorithm, controlling image smoothness.

**Recommended values**:
- 0.001 - 0.01: Sharp image, may have noise
- 0.01 - 0.05: Balanced setting (common)
- 0.05 - 0.1: Smooth image, less noise

**Effect**:
- Small λ: Sharp image but noise amplification
- Large λ: Smooth image but detail loss

**Selection guide**:
- High SNR images: λ = 0.001 - 0.01
- Low SNR images: λ = 0.01 - 0.1
- Try different values to find the optimum

### Lambda (FISTA Regularization Parameter)

**Range**: 0.0001 - 1.0

**Description**: L1 regularization parameter for the FISTA algorithm.

**Recommended values**: 0.005 - 0.05

**Effect**: Similar to RL λ, but FISTA uses L1 regularization, better suited for sparse data.

### Regularization Type

**Options**:
- **TV (Total Variation)**: Total variation regularization
  - Advantage: Preserves sharp edges
  - Disadvantage: May produce blocky artifacts
  - Suitable for: Images with sharp edges
- **L2 (L2 Norm)**: Smooth regularization
  - Advantage: Naturally smooth
  - Disadvantage: May blur edges
  - Suitable for: Noise-dominated images

**Recommendation**: Use TV by default; switch to L2 if blocky artifacts appear.

### Boundary Handling

**Options**: True / False

**Description**: Whether to process image boundaries to reduce artifacts.

**Recommendation**: **True** (always enable)

**Effect**:
- True: Reduced boundary artifacts, slightly more computation
- False: Possible ring artifacts at boundaries, faster computation

## Advanced Aberration Parameters

These parameters are typically used for high-resolution imaging and can be set to 0 for general images.

### A2 Aberration (Second-order)

**Amplitude**: nm
**Angle**: rad

Description: Second-order aberration, including astigmatism, etc.

### A3 Aberration (Third-order)

**Amplitude**: nm
**Angle**: rad

Description: Third-order aberration, including coma, etc.

### B2 Aberration

**Amplitude**: nm
**Angle**: rad

Description: Specific aberration component.

### Focal Spread

**Unit**: nm

**Description**: Statistical distribution width of the focal point, used for partial coherence modeling.

**Typical values**: 2 - 10 nm

### Convergence Angle

**Unit**: rad

**Description**: Convergence angle of the electron beam.

**Typical values**: 0.005 - 0.02 rad

## Post-Processing Parameters

### Apply Wiener Filter

**Options**: True / False

**Description**: Apply Wiener filtering to suppress high-frequency noise.

**Recommendation**: **True** (recommended)

**Effect**:
- True: Reduced noise, improved SNR
- False: Preserves raw deconvolution result

### Use P-spline Filter

**Options**: True / False

**Description**: Use P-spline filtering as an alternative to traditional radial Wiener filtering.

**Recommendation**: False (unless specific frequency response is needed)

**Difference**:
- Radial Wiener: Radially symmetric, simple and fast
- P-spline: Directional frequency response control, more flexible

### P-spline Lambda

**Range**: 1 - 10000

**Description**: Smoothing strength for the P-spline filter.

**Recommended values**: 100 - 1000

**Effect**:
- Small value: Weaker smoothing
- Large value: Stronger smoothing

### Information Limit

**Unit**: 1/nm or 1/Å (spatial frequency)

**Description**: The information limit frequency of the microscope; frequencies above this are filtered out.

**Options**: "Auto" or a specific value

**Recommendation**: **Auto** (automatic estimation)

**Auto-estimation**: Automatically determines the cutoff frequency based on the probe's amplitude spectrum.

## Display Parameters

### Space

**Options**:
- **Real Space**: Real-space image display
- **Frequency Space**: Fourier space (frequency domain) display

**Description**: Toggle between spatial domains for image display.

**Usage**:
- Real space: Observe image structure and details
- Frequency domain: Observe CTF, probe shape, frequency components

### Mode (Display Mode)

**Options**:
- **Linear**: Linear display (raw data)
- **Power**: Power spectrum (amplitude squared)
- **Log**: Logarithmic display (dynamic range compression)

**Description**: Controls the image display mode.

**Usage**:
- Linear: Suitable for real-space images
- Power: Suitable for frequency-domain analysis
- Log: Suitable for displaying both high and low frequency information simultaneously

### Colormap

**Options**: gray, viridis, plasma, inferno, magma, jet, hot, cool

**Description**: Select the color mapping scheme for images.

**Recommendation**:
- gray: Scientific analysis (monochrome, objective)
- viridis: Perceptually uniform, suitable for all audiences
- plasma/inferno/magma: Rich colors, suitable for presentations
- jet: Traditional heat map (not recommended for analysis)

## Recommended Parameter Values

### 300 kV Microscope (Common Configuration)

```
Voltage:        300 kV
Cs3:            0.5 mm
Cs5:            0.0 mm
Defocus:       -44 nm
Obj. Aperture:  16 mrad
Pixel Size:     0.05 - 0.2 nm

Iterations:     15 - 25
Lambda (RL):    0.002 - 0.005
Reg. Type:      TV
Boundary:       True

Wiener:         True
P-spline:       False
Info Limit:     Auto
```

### 200 kV Microscope

```
Voltage:        200 kV
Cs3:            1.0 mm
Cs5:            0.0 mm
Defocus:       -50 nm
Obj. Aperture:  15 mrad
Pixel Size:     0.05 - 0.2 nm

Iterations:     20 - 30
Lambda (RL):    0.003 - 0.008
Reg. Type:      TV
Boundary:       True
```

### Low SNR Images

```
Iterations:     10 - 15 (avoid noise amplification)
Lambda (RL):    0.01 - 0.05 (strong regularization)
Reg. Type:      L2 (smoother)
Wiener:         True (post-processing denoising)
```

### High SNR Images

```
Iterations:     25 - 40 (fully leverage data)
Lambda (RL):    0.001 - 0.005 (weak regularization)
Reg. Type:      TV (edge preservation)
Wiener:         False (preserve detail)
```

## Parameter Tuning Strategy

### Step 1: Determine CTF Parameters

1. View the raw image in the frequency domain
2. Observe CTF oscillations
3. Adjust Defocus so the first zero is at a reasonable position

### Step 2: Set Basic Deconvolution Parameters

1. Iterations = 15
2. Lambda = 0.002
3. Reg. Type = TV
4. Boundary = True

### Step 3: Iterative Optimization

1. Examine the deconvolution result
2. If blurry: Increase iterations
3. If noisy: Decrease iterations or increase λ

### Step 4: Fine Tuning

1. If edge artifacts appear: Switch to L2 regularization
2. If blocky artifacts appear: Switch to L2 or increase λ
3. If high-frequency noise is present: Enable Wiener filtering

## Troubleshooting

### Issue: Result is still blurry

**Possible causes**:
- Too few iterations
- λ too large
- Incorrect CTF parameters

**Solutions**:
- Increase iterations to 30-50
- Decrease λ to 0.001-0.002
- Verify Voltage, Cs3, and Defocus values

### Issue: Visible noise

**Possible causes**:
- Too many iterations
- λ too small
- Noisy input image

**Solutions**:
- Reduce iterations to 10-15
- Increase λ to 0.01-0.05
- Enable Wiener post-filtering
- Use L2 regularization

### Issue: Ring artifacts

**Possible causes**:
- Incorrect CTF parameters
- Boundary handling disabled

**Solutions**:
- Check and correct the Defocus value
- Ensure Boundary Handling = True

### Issue: Blocky texture near edges

**Possible causes**:
- TV regularization too strong

**Solutions**:
- Switch to L2 regularization
- Or decrease the TV λ value

### Issue: Abnormal frequency-domain image

**Possible causes**:
- Incorrect Pixel Size

**Solutions**:
- Check MRC file metadata
- Manually set the correct Pixel Size

## References

- HAADF-STEM imaging principles
- Deconvolution algorithm theory
- Electron microscope parameter manuals

For more information, refer to [README.md](README.md) or submit an [Issue](https://github.com/chenguisen/deconvolution-stem/issues).
