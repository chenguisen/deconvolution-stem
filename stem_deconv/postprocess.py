import numpy as np
from scipy.fft import dct, idct
from .utils import fft2, ifft2, fftshift, ifftshift

def whittaker_smooth_2d(data, lambda_val, order=2):
    """
    2D Whittaker-Eilers smoother using Discrete Cosine Transform (DCT).
    Minimizes: S = ||y - z||^2 + lambda * (||D_x z||^2 + ||D_y z||^2)
    """
    rows, cols = data.shape
    
    # 1. DCT of data
    Y = dct(dct(data, axis=0, norm='ortho', type=2), axis=1, norm='ortho', type=2)
    
    # 2. Eigenvalues of penalty matrix
    i = np.arange(rows)
    j = np.arange(cols)
    w_row = (2 * (1 - np.cos(i * np.pi / rows))) ** order
    w_col = (2 * (1 - np.cos(j * np.pi / cols))) ** order
    
    # 3. Filter in DCT domain
    Gamma = 1 + lambda_val * (w_row.reshape(-1, 1) + w_col.reshape(1, -1))
    Z = Y / Gamma
    
    # 4. Inverse DCT
    z = idct(idct(Z, axis=0, norm='ortho', type=2), axis=1, norm='ortho', type=2)
    
    return z

def get_gaussian_kernel_1d_from_2d(kernel_size, sigma):
    """
    Mimic C++ GetGaussianKernel (2D) and collapse to 1D.
    The C++ code convolves a 1D radial profile (treated as Nx1) with a 2D kernel.
    This is effectively convolving with the projection of the 2D kernel.
    """
    center = kernel_size // 2
    param = 1.0 / (2.0 * sigma * sigma)
    kernel_2d = np.zeros((kernel_size, kernel_size))
    
    for i in range(kernel_size):
        for j in range(kernel_size):
            dist_sq = (i - center)**2 + (j - center)**2
            kernel_2d[i, j] = (1.0 / np.pi * param) * np.exp(-dist_sq * param)
            
    # Normalize
    kernel_2d /= np.sum(kernel_2d)
    
    # Collapse to 1D
    kernel_1d = np.sum(kernel_2d, axis=0) 
    return kernel_1d

def rotation_average(data, kernel_size=3, fwhm_val=8.0):
    """
    Calculate the radially averaged profile of the data and smooth it.
    Mimics C++ rotationAverage function.
    
    Args:
        data: 2D input array (usually Magnitude spectrum).
        kernel_size: Size of the smoothing kernel (default 3).
        fwhm_val: FWHM for sigma calculation (default 8.0, from C++ code).
                  Note: C++ comments say 'in Angstrom', but the value is used 
                  directly in kernel generation for the pixel-based radial array.
                  So it acts as a smoothing factor of ~3.4 bins.
    """
    rows, cols = data.shape
    center = (rows//2, cols//2)
    y, x = np.indices((rows, cols))
    r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
    r_int = r.astype(int)
    max_r = min(rows, cols) // 2
    
    # Binning
    # Only consider r < max_r
    mask = r_int < max_r
    r_valid = r_int[mask]
    data_valid = data[mask]
    
    # Calculate radial average
    tbin = np.bincount(r_valid, weights=data_valid, minlength=max_r)
    nr = np.bincount(r_valid, minlength=max_r)
    
    radial_profile = np.zeros_like(tbin, dtype=np.float32)
    np.divide(tbin, nr, out=radial_profile, where=nr!=0)
    
    # Smoothing
    sigma = fwhm_val / 2.355
    kernel_1d = get_gaussian_kernel_1d_from_2d(kernel_size, sigma)
    
    radial_profile_smoothed = np.convolve(radial_profile, kernel_1d, mode='same')
    
    # Map back to 2D
    # Use fancy indexing
    r_int_clipped = np.clip(r_int, 0, len(radial_profile_smoothed)-1)
    background = radial_profile_smoothed[r_int_clipped]
    
    # Explicitly zero out r >= max_r to match C++
    background[r_int >= max_r] = 0
    
    return background

def radial_wiener_filter(image, pixel_size, information_limit=None):
    """
    Apply a Radial Wiener Filter to the image.
    
    Uses the C++ implementation logic:
    1. Calculate Magnitude Spectrum |F|.
    2. Estimate Background B using smoothed Radial Average of |F|.
    3. Filter W = (|F|^2 - B^2) / |F|^2.
    
    Args:
        image (np.ndarray): Input image (real).
        pixel_size (float): Pixel size (in real space units).
        information_limit (float): Frequency limit ratio (0.0 to 1.0) relative to Nyquist.
                                   Default is 0.5 (50% of Nyquist) if None.
                                   Frequencies beyond this limit are zeroed out 
                                   BEFORE background estimation.
    
    Returns:
        np.ndarray: Filtered image.
    """
    rows, cols = image.shape
    
    # 1. FFT
    img_fft = fft2(image.astype(np.complex64))
    img_fft_shifted = fftshift(img_fft)
    
    # 2. Masking
    # Default to 0.5 (50%) if not provided, as per user request.
    limit_ratio = information_limit if information_limit is not None else 0.5
    
    center = (rows//2, cols//2)
    y, x = np.indices((rows, cols))
    r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
    
    # Nyquist radius is min(rows, cols) / 2
    nyquist_r = min(rows, cols) / 2.0
    r_limit = limit_ratio * nyquist_r
    
    mask = r <= r_limit
    img_fft_shifted *= mask
        
    # 3. Magnitude and Background
    magnitude = np.abs(img_fft_shifted)
    background_mag = rotation_average(magnitude)
    
    # 4. Power Calculation
    power_spectrum = magnitude**2
    background_power = background_mag**2
    
    # Mask center of background (C++ sets center 2x2 to 0 to keep low freq)
    # "Sets the mask keep the lowest frequency component in the mask"
    cy, cx = rows//2, cols//2
    shift = 2
    background_power[cy-shift:cy+2, cx-shift:cx+2] = 0
    
    # 5. Construct Filter
    # W = (P - B) / P
    wiener_filter = np.zeros_like(power_spectrum)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        numerator = power_spectrum - background_power
        # Threshold at 0
        numerator[numerator < 0] = 0
        
        wiener_filter = numerator / power_spectrum
        wiener_filter[power_spectrum == 0] = 0
        
    # 6. Apply Filter
    filtered_fft = img_fft_shifted * wiener_filter
    
    # 7. IFFT
    filtered_image = np.abs(ifft2(ifftshift(filtered_fft)))
    
    return filtered_image

def whittaker_smooth_2d_iterative(data, lambda_val, order=2, max_iter=10, tol=1e-3):
    """
    Iterative 2D Whittaker smoother for background estimation (Asymmetric / Robust).
    Uses a sigma-clipping approach to ignore positive outliers (peaks) while 
    fitting the mean of the noise floor.
    """
    # Work in Log space to handle dynamic range
    # Add small epsilon to avoid log(0)
    epsilon = 1e-10
    log_data = np.log(data + epsilon)
    
    z = log_data.copy()
    w_data = log_data.copy()
    
    for it in range(max_iter):
        z_prev = z.copy()
        
        # 1. Smooth the current working data
        z = whittaker_smooth_2d(w_data, lambda_val, order=order)
        
        # 2. Update working data: Sigma Clipping
        # Calculate residuals
        resid = log_data - z
        
        # Estimate noise sigma from the negative residuals (valleys)
        # This avoids the influence of the massive Bragg peaks
        # Assuming symmetric noise distribution around the background in log space
        # sigma ~ sqrt(mean(resid[resid < 0]^2))
        neg_resid = resid[resid < 0]
        if len(neg_resid) > 0:
            sigma = np.sqrt(np.mean(neg_resid**2))
        else:
            sigma = 1.0 # Fallback
            
        # Clip positive outliers (peaks)
        # Replace values > z + 2.5*sigma with z
        # This effectively "erases" the peaks
        mask_peaks = resid > (2.5 * sigma)
        
        w_data = log_data.copy()
        w_data[mask_peaks] = z[mask_peaks]
        
        # Check convergence
        diff = np.linalg.norm(z - z_prev) / (np.linalg.norm(z_prev) + 1e-10)
        if diff < tol:
            break
            
    # Convert back to linear space
    background = np.exp(z)
    return background

def p_spline_wiener_filter(image, pixel_size, lambda_val=100.0, order=2, information_limit=None):
    """
    Apply a Wiener Filter using P-spline based background estimation.
    
    This method estimates the 2D background of the Fourier Magnitude Spectrum 
    using a fast 2D penalized least squares smoother (Whittaker-Eilers smoother).
    It uses an iterative "clipping" approach to robustly estimate the background 
    in the presence of strong Bragg peaks (structure information).
    
    Reference: 
    "Fast and compact smoothing on large multidimensional grids", 
    P.H.C. Eilers et al., Computational Statistics and Data Analysis 50 (2006) 61-76.
    
    Args:
        image (np.ndarray): Input image.
        pixel_size (float): Pixel size.
        lambda_val (float): Smoothing parameter. Higher = smoother background.
        order (int): Order of penalty (2 = curvature).
        information_limit (float): Frequency limit ratio (0.0 to 1.0). Default 0.5.
    """
    rows, cols = image.shape
    
    # 1. FFT
    img_fft = fft2(image.astype(np.complex64))
    img_fft_shifted = fftshift(img_fft)
    
    # 2. Masking
    limit_ratio = information_limit if information_limit is not None else 0.5
    
    center = (rows//2, cols//2)
    y, x = np.indices((rows, cols))
    r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
    
    nyquist_r = min(rows, cols) / 2.0
    r_limit = limit_ratio * nyquist_r
    
    # We do NOT mask the input to the background estimator with zeros, 
    # because log(0) is bad. We will apply the mask at the end.
    # However, we should ignore the high freq noise in the estimation if possible.
    # But P-spline works on the full grid.
    # Let's just use the full magnitude for estimation, it should be fine.
    
    magnitude = np.abs(img_fft_shifted)
    
    # 3. Background Estimation using 2D P-spline (Iterative/Robust)
    # We smooth the Magnitude spectrum in Log space.
    
    background_mag = whittaker_smooth_2d_iterative(magnitude, lambda_val, order=order)
    
    # 4. Power Calculation
    power_spectrum = magnitude**2
    background_power = background_mag**2
    
    # Mask center of background (preserve low freq)
    cy, cx = rows//2, cols//2
    shift = 2
    background_power[cy-shift:cy+2, cx-shift:cx+2] = 0
    
    # 5. Construct Filter
    # W = (P - B) / P
    wiener_filter = np.zeros_like(power_spectrum)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        numerator = power_spectrum - background_power
        numerator[numerator < 0] = 0
        
        wiener_filter = numerator / power_spectrum
        wiener_filter[power_spectrum == 0] = 0
        
    # 6. Apply Information Limit Mask
    mask = r <= r_limit
    wiener_filter *= mask
    
    # 7. Apply Filter
    filtered_fft = img_fft_shifted * wiener_filter
    
    # 8. IFFT
    filtered_image = np.abs(ifft2(ifftshift(filtered_fft)))
    
    return filtered_image

def radial_difference_filter(image, pixel_size, information_limit=None):
    """
    Apply a Radial Difference Filter (Background Subtraction).
    
    Logic:
    1. Calculate Magnitude |F|.
    2. Estimate Background B using smoothed Radial Average of |F|.
    3. Filter W = (|F| - B) / |F|.
    
    Args:
        information_limit (float): Frequency limit ratio (0.0 to 1.0). Default 0.5.
    """
    rows, cols = image.shape
    
    # 1. FFT
    img_fft = fft2(image.astype(np.complex64))
    img_fft_shifted = fftshift(img_fft)
    
    # 2. Masking
    limit_ratio = information_limit if information_limit is not None else 0.5
    
    center = (rows//2, cols//2)
    y, x = np.indices((rows, cols))
    r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
    
    nyquist_r = min(rows, cols) / 2.0
    r_limit = limit_ratio * nyquist_r
    
    mask = r <= r_limit
    img_fft_shifted *= mask

    magnitude = np.abs(img_fft_shifted)
    
    # 3. Background
    background_mag = rotation_average(magnitude)
    
    # 4. Filter
    # W = (Mag - Back) / Mag
    wiener_filter = np.zeros_like(magnitude)
    
    with np.errstate(divide='ignore', invalid='ignore'):
        numerator = magnitude - background_mag
        numerator[numerator < 0] = 0
        
        wiener_filter = numerator / magnitude
        wiener_filter[magnitude == 0] = 0
        
    filtered_fft = img_fft_shifted * wiener_filter
    
    filtered_image = np.abs(ifft2(ifftshift(filtered_fft)))
    
    return filtered_image
