#!/usr/bin/env python
"""Minimal pipeline test for dec_stem_for_computer.

Verifies that all three deconvolution algorithms run successfully on synthetic data
and produce valid outputs (correct shape, no NaN, not all-constant).
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stem_deconv.physics import calculate_ctf, calculate_probe, calculate_wavelength
from stem_deconv.core import (
    richardson_lucy_additive,
    richardson_lucy_multiplicative,
    fista_deconvolution,
)


def make_synthetic_image(size=256, n_columns=16):
    """Generate a synthetic HAADF-STEM image: Gaussian atom columns + Poisson noise."""
    rng = np.random.default_rng(42)
    x = np.linspace(0, size - 1, size)
    y = np.linspace(0, size - 1, size)
    xx, yy = np.meshgrid(x, y)

    image = np.zeros((size, size), dtype=np.float32)
    spacing = size / n_columns
    sigma = 3.0
    amp = 1000.0

    for i in range(n_columns):
        for j in range(n_columns):
            cx = (i + 0.5) * spacing
            cy = (j + 0.5) * spacing
            image += amp * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * sigma**2))

    noisy = rng.poisson(image).astype(np.float32)
    return noisy


def check_result(result, name, check_nonneg=True):
    """Validate deconvolution output."""
    assert result.shape == (256, 256), f"{name}: wrong shape {result.shape}"
    assert not np.any(np.isnan(result)), f"{name}: contains NaN"
    assert not np.any(np.isinf(result)), f"{name}: contains Inf"
    assert np.std(result) > 1e-6, f"{name}: output is nearly constant"
    if check_nonneg:
        assert np.min(result) >= 0, f"{name}: negative values"
    return True


def main():
    print("=" * 60)
    print("dec_stem_for_computer — Pipeline Test")
    print("=" * 60)

    # --- Setup ---
    print("\n[1/4] Generating synthetic data (256x256, 16x16 Gaussian columns + Poisson noise)...")
    image = make_synthetic_image()
    pixel_size = 0.01  # nm
    print(f"      Shape: {image.shape}, Range: [{image.min():.1f}, {image.max():.1f}]")

    # --- Probe ---
    print("\n[2/4] Computing probe function...")
    voltage = 300.0  # kV
    cs3 = 0.5  # mm
    cs5 = 0.0  # mm
    defocus = -44.0  # nm
    obj_aperture = 16.0  # mrad

    ctf = calculate_ctf(image.shape, pixel_size, voltage,
                        cs3, cs5, defocus, obj_aperture / 1000.0)
    probe = calculate_probe(ctf)
    wavelength_nm = calculate_wavelength(voltage)
    print(f"      Wavelength: {wavelength_nm*1000:.3f} pm")
    print(f"      Probe shape: {probe.shape}")

    # --- Deconvolution ---
    print("\n[3/4] Running deconvolution algorithms...")
    passed = 0
    failed = 0

    # Test 1: RL Additive
    name = "RL Additive"
    try:
        result = richardson_lucy_additive(image, probe, iterations=10,
                                          lambda_reg=0.002, reg_type="TV",
                                          boundary_handling=True)
        check_result(result, name, check_nonneg=False)
        print(f"      [PASS] {name} — shape={result.shape}, range=[{result.min():.2f}, {result.max():.2f}]")
        passed += 1
    except Exception as e:
        print(f"      [FAIL] {name}: {e}")
        failed += 1

    # Test 2: RL Multiplicative + TV
    name = "RL Multiplicative + TV"
    try:
        result = richardson_lucy_multiplicative(
            image, probe, iterations=15,
            lambda_reg=0.002, reg_type="TV",
            pixel_size=pixel_size, wavelength=wavelength_nm,
            acceleration=True, boundary_handling=True,
            residual_stopping=True,
        )
        check_result(result, name, check_nonneg=True)
        print(f"      [PASS] {name} — shape={result.shape}, range=[{result.min():.2f}, {result.max():.2f}]")
        passed += 1
    except Exception as e:
        print(f"      [FAIL] {name}: {e}")
        failed += 1

    # Test 3: FISTA-TV
    name = "FISTA-TV"
    try:
        result = fista_deconvolution(image, probe, iterations=15,
                                     lambda_reg=0.005, boundary_handling=True)
        check_result(result, name, check_nonneg=False)
        print(f"      [PASS] {name} — shape={result.shape}, range=[{result.min():.2f}, {result.max():.2f}]")
        passed += 1
    except Exception as e:
        print(f"      [FAIL] {name}: {e}")
        failed += 1

    # --- Summary ---
    print(f"\n[4/4] Results: {passed} passed, {failed} failed out of 3")
    print("=" * 60)

    if failed > 0:
        print("SOME TESTS FAILED")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
