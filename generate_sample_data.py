#!/usr/bin/env python
"""Generate sample deconvolution output data for CPC distribution.

Produces synthetic HAADF-STEM data, runs all three algorithms, and saves
results as MRC files under a samples/ directory.
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stem_deconv.physics import calculate_ctf, calculate_probe, calculate_wavelength
from stem_deconv.core import (
    richardson_lucy_additive,
    richardson_lucy_multiplicative,
    fista_deconvolution,
)
from stem_deconv.io import save_mrc


def make_synthetic_image(size=256, n_columns=16, seed=42):
    """Generate a synthetic HAADF-STEM image: Gaussian atom columns + Poisson noise."""
    rng = np.random.default_rng(seed)
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


def main():
    print("=" * 60)
    print("Generating sample deconvolution data")
    print("=" * 60)

    # Setup
    pixel_size = 0.01  # nm
    voltage = 300.0    # kV
    cs3 = 0.5          # mm
    cs5 = 0.0          # mm
    defocus = -44.0    # nm
    obj_aperture = 16.0  # mrad

    # Output directory
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
    os.makedirs(out_dir, exist_ok=True)
    print(f"Output directory: {out_dir}")

    # Generate synthetic data
    print("\n[1/5] Generating synthetic data (256x256, 16x16 Gaussian columns + Poisson noise)...")
    image = make_synthetic_image()
    save_mrc(os.path.join(out_dir, "input.mrc"), image, pixel_size)
    print(f"      Saved: input.mrc ({image.shape}, range [{image.min():.1f}, {image.max():.1f}])")

    # Compute probe
    print("\n[2/5] Computing probe function...")
    ctf = calculate_ctf(image.shape, pixel_size, voltage,
                        cs3, cs5, defocus, obj_aperture / 1000.0)
    probe = calculate_probe(ctf)
    wavelength_nm = calculate_wavelength(voltage)
    save_mrc(os.path.join(out_dir, "probe.mrc"), np.abs(probe), pixel_size)
    print(f"      Saved: probe.mrc ({probe.shape})")

    # RL Additive
    print("\n[3/5] Running RL Additive (20 iterations, λ=0.002, TV)...")
    result_rla = richardson_lucy_additive(image, probe, iterations=20,
                                          lambda_reg=0.002, reg_type="TV",
                                          boundary_handling=True)
    save_mrc(os.path.join(out_dir, "output_rl_additive.mrc"), result_rla, pixel_size)
    print(f"      Saved: output_rl_additive.mrc (range [{result_rla.min():.2f}, {result_rla.max():.2f}])")

    # RL Multiplicative + TV
    print("\n[4/5] Running RL Multiplicative + TV (15 iterations, λ=0.002, acceleration)...")
    result_rlm = richardson_lucy_multiplicative(
        image, probe, iterations=15,
        lambda_reg=0.002, reg_type="TV",
        pixel_size=pixel_size, wavelength=wavelength_nm,
        acceleration=True, boundary_handling=True,
        residual_stopping=True,
    )
    save_mrc(os.path.join(out_dir, "output_rl_multiplicative.mrc"), result_rlm, pixel_size)
    print(f"      Saved: output_rl_multiplicative.mrc (range [{result_rlm.min():.2f}, {result_rlm.max():.2f}])")

    # FISTA-TV
    print("\n[5/5] Running FISTA-TV (15 iterations, λ=0.005)...")
    result_fista = fista_deconvolution(image, probe, iterations=15,
                                       lambda_reg=0.005, boundary_handling=True)
    save_mrc(os.path.join(out_dir, "output_fista.mrc"), result_fista, pixel_size)
    print(f"      Saved: output_fista.mrc (range [{result_fista.min():.2f}, {result_fista.max():.2f}])")

    print("\n" + "=" * 60)
    print("All sample data generated successfully in samples/")
    print("=" * 60)


if __name__ == "__main__":
    main()
