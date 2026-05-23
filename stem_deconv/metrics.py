"""
metrics.py -- Quantitative evaluation metrics for deconvolution quality

Provides SNR, SSIM, MSE, and FRC computation. These metrics require
ground truth data (e.g., from simulations) and are not applicable
to experimental images without a reference.

Author: Chen Guisen
"""

import numpy as np
from scipy.ndimage import uniform_filter
from typing import Tuple, Optional


def signal_to_noise_ratio(
    ground_truth: np.ndarray,
    restored: np.ndarray,
) -> float:
    """
    Compute Signal-to-Noise Ratio in dB.

    SNR = 10 * log10( ||GT||_2^2 / ||restored - GT||_2^2 )

    Args:
        ground_truth: Ground truth image (float).
        restored: Restored/deconvolved image (float).

    Returns:
        SNR in dB.
    """
    signal_power = np.sum(np.abs(ground_truth) ** 2)
    noise_power = np.sum(np.abs(restored - ground_truth) ** 2)
    if noise_power < 1e-15:
        return float('inf')
    return float(10.0 * np.log10(signal_power / noise_power))


def mean_squared_error(
    ground_truth: np.ndarray,
    restored: np.ndarray,
) -> float:
    """
    Compute Mean Squared Error (MSE).

    MSE = (1/N) * sum_i (restored_i - GT_i)^2

    Args:
        ground_truth: Ground truth image.
        restored: Restored image.

    Returns:
        MSE value.
    """
    return float(np.mean((restored - ground_truth) ** 2))


def structural_similarity_index(
    ground_truth: np.ndarray,
    restored: np.ndarray,
    K1: float = 0.01,
    K2: float = 0.03,
    L: Optional[float] = None,
) -> float:
    """
    Compute Structural Similarity Index (SSIM) between two images.

    Implements the Wang-Bovik SSIM with defaults K1=0.01, K2=0.03,
    matching the description in the paper.

    Args:
        ground_truth: Ground truth image.
        restored: Restored image.
        K1, K2: SSIM stability constants.
        L: Dynamic range. If None, computed as max(GT) - min(GT).

    Returns:
        SSIM value (float between -1 and 1).
    """
    if L is None:
        L = float(np.max(ground_truth) - np.min(ground_truth))
    if L < 1e-10:
        L = 1.0

    C1 = (K1 * L) ** 2
    C2 = (K2 * L) ** 2

    gt = ground_truth.astype(np.float64)
    re = restored.astype(np.float64)

    window_size = 11
    mu_gt = uniform_filter(gt, size=window_size)
    mu_re = uniform_filter(re, size=window_size)

    sigma_gt_sq = uniform_filter(gt ** 2, size=window_size) - mu_gt ** 2
    sigma_re_sq = uniform_filter(re ** 2, size=window_size) - mu_re ** 2
    sigma_gt_re = uniform_filter(gt * re, size=window_size) - mu_gt * mu_re

    ssim_map = ((2.0 * mu_gt * mu_re + C1) * (2.0 * sigma_gt_re + C2)) / \
               ((mu_gt ** 2 + mu_re ** 2 + C1) * (sigma_gt_sq + sigma_re_sq + C2) + 1e-15)

    return float(np.mean(ssim_map))


def fourier_ring_correlation(
    ground_truth: np.ndarray,
    restored: np.ndarray,
    pixel_size: Optional[float] = None,
    bit_threshold: float = 0.5,
    return_curve: bool = False,
):
    """
    Compute Fourier Ring Correlation (FRC) between two images.

    Uses the 1/2-bit threshold criterion (van Heel & Schatz, 2005).

    Args:
        ground_truth: Ground truth image.
        restored: Restored image.
        pixel_size: Pixel size in nm for frequency axis. If None, use pixel units.
        bit_threshold: FRC threshold (default: 0.5 for 1/2-bit criterion).
        return_curve: If True, return (resolution, frequencies, frc_values).

    Returns:
        If return_curve is False: resolution in nm (or pixel units if pixel_size is None).
        If return_curve is True: tuple (resolution, frequencies, frc_values).
    """
    ny, nx = ground_truth.shape
    center = (ny // 2, nx // 2)

    f_gt = np.fft.fftshift(np.fft.fft2(ground_truth))
    f_re = np.fft.fftshift(np.fft.fft2(restored))

    y, x = np.indices((ny, nx))
    r = np.sqrt((y - center[0]) ** 2 + (x - center[1]) ** 2).astype(int)
    max_r = min(ny, nx) // 2

    frc_values = np.zeros(max_r)
    frequencies = np.arange(max_r)

    for ring in range(max_r):
        mask = r == ring
        if np.sum(mask) == 0:
            continue
        numerator = np.abs(np.sum(f_gt[mask] * np.conj(f_re[mask])))
        denom_gt = np.sum(np.abs(f_gt[mask]) ** 2)
        denom_re = np.sum(np.abs(f_re[mask]) ** 2)
        denominator = np.sqrt(denom_gt * denom_re)
        if denominator > 1e-15:
            frc_values[ring] = numerator / denominator

    indices_above = np.where(frc_values > bit_threshold)[0]
    if len(indices_above) == 0:
        resolution_index = 0
    else:
        resolution_index = indices_above[-1]

    if pixel_size is not None:
        freq = resolution_index / (max_r * pixel_size * 2.0) if max_r > 0 else 0
        resolution = 1.0 / freq if freq > 0 else float('inf')
    else:
        resolution = float(resolution_index)

    if return_curve:
        return resolution, frequencies, frc_values
    return float(resolution)
