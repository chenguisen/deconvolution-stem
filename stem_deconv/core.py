import numpy as np
from scipy.ndimage import gaussian_filter
from .utils import fft2, ifft2, fftshift, ifftshift
from .regularization import total_variation_gradient, tikhonov_miller_regularization

def richardson_lucy_additive(image, probe, iterations, lambda_reg=0, reg_type="None", alpha=1.0, boundary_handling=True):
    """
    Richardson-Lucy Additive Deconvolution.
    """
    # Save original dimensions for cropping after deconvolution
    orig_h, orig_w = image.shape[:2]

    # Boundary Handling: zero-pad to next power of 2 for FFT efficiency
    if boundary_handling:
        ny_next = 1 << (image.shape[0] - 1).bit_length()
        nx_next = 1 << (image.shape[1] - 1).bit_length()
        pad_y = ny_next - image.shape[0]
        pad_x = nx_next - image.shape[1]
        image = np.pad(image, ((0, pad_y), (0, pad_x)), mode='constant')
        probe = np.pad(probe, ((0, pad_y), (0, pad_x)), mode='constant')

    # Initialize object estimate with the image
    object_data = image.astype(np.float32)
    
    # C++: Probe is spatial domain, centered (from CalProbe -> IFFT -> Rearrange)
    # But RL function takes `fftwf_complex * probe`.
    # And does `m_math.FlipMatrix(probe_flip, probe)` (spatial flip)
    # Then `FFT(probe)` and `FFT(probe_flip)`.
    # Note: C++ FFT expects corner-zero. If probe is centered, FFT result has phase shift.
    # But `probe` passed to RL is likely centered.
    # Let's assume we work with centered spatial images throughout.
    
    probe_spatial = np.abs(probe).astype(np.float32)
    
    # Normalize probe
    probe_sum = np.sum(probe_spatial)
    if probe_sum != 0:
        probe_spatial /= probe_sum
    
    # C++ FlipMatrix: y[i] = x[N-i] (Circular flip)
    # This keeps index 0 at 0.
    # np.flip flips 0 to N-1.
    # np.roll(np.flip(x), 1) gives circular flip.
    probe_flip_spatial = np.roll(np.flip(np.flip(probe_spatial, 0), 1), (1, 1), (0, 1))
    
    # FFTs
    # C++ uses FFTW_FORWARD (unnormalized).
    # We use scipy.fft.fft2 (unnormalized).
    probe_fft = fft2(probe_spatial)
    probe_flip_fft = fft2(probe_flip_spatial)
    
    # Scale factor for IFFT
    # C++ does IFFT (unnormalized) then Scale(1/N).
    # scipy.fft.ifft2 is normalized (1/N).
    # So ifft2(fft2(x)) == x. Matches C++.
    
    for i in range(iterations):
        # 1. Convolve Object with Probe: O * P
        obj_fft = fft2(object_data)
        blurred_fft = obj_fft * probe_fft
        blurred = np.real(fftshift(ifft2(blurred_fft)))
        
        # 2. Calculate Ratio: I / (O * P)
        denom = np.maximum(blurred, 1e-9)
        ratio = image / denom
        
        # 3. Convolve Ratio with Flipped Probe: Ratio * P_flip
        ratio_fft = fft2(ratio)
        gradient_fft = ratio_fft * probe_flip_fft
        gradient = np.real(fftshift(ifft2(gradient_fft)))
        
        # 4. Update Step
        # C++: tempImage = gradient
        # tempImage = tempImage - 1
        update_term = gradient - 1.0
        
        # Regularization
        if reg_type == "TV":
            # Standard TV: Add lambda * curvature (smoothing)
            # curvature = div(grad/|grad|)
            curv = total_variation_gradient(object_data)
            update_term = update_term + lambda_reg * curv
            
        elif reg_type == "TM":
            # Standard TM: Add lambda * Laplacian (smoothing)
            # But TM usually minimizes ||grad u||^2 + ||u-f||^2
            # Gradient descent: u_new = u_old + (f - u) + lambda * Laplacian u
            # RL Additive: u_new = u_old + (Ratio - 1) + lambda * Laplacian u
            # So we add lambda * Laplacian.
            
            # Note: C++ TM implementation was weird (1 - 2*lambda*div).
            # We use standard Laplacian here.
            # lap = tikhonov_miller_regularization(object_data, pixel_size=1.0) # pixel_size not passed to RL Additive currently?
            # Assuming pixel_size=1.0 for now or we need to update signature.
            # Additive RL signature doesn't have pixel_size.
            
            # update_term = update_term + lambda_reg * lap
            pass # Not implemented for Additive in C++ strictly speaking, or requires pixel_size/wavelength
            
        # Apply alpha
        update_term = update_term * alpha
        
        # Update Object
        object_data = object_data + update_term
        
        # Resolution Limit (Optional, based on C++ code)
        # ...
        
    if boundary_handling:
        object_data = object_data[:orig_h, :orig_w]

    return object_data

def _compute_entropy(image):
    """Compute Shannon entropy of normalized pixel intensity distribution."""
    p = image / (image.sum() + 1e-10)
    return -np.sum(p * np.log(p + 1e-10))


def _compute_sharpness(image):
    """
    Compute image sharpness as variance of discrete Laplacian.

    Physical meaning: during good RL-TV deconvolution, TV regularization
    suppresses noise and smooths uniform regions, decreasing Laplacian
    variance. When overconvolution begins, noise amplification increases
    Laplacian variance again. The minimum marks the optimal trade-off
    between feature recovery and noise suppression.
    """
    lap = (4 * image
           - np.roll(image, 1, 0) - np.roll(image, -1, 0)
           - np.roll(image, 1, 1) - np.roll(image, -1, 1))
    return float(np.var(lap))


def _compute_hp_residual_norm(image, blurred_with_bg, sigma=3.0):
    """
    Compute norm of high-pass filtered residual.

    r = I - (O*P + B)
    r_hp = r - gauss(r, sigma)  -- suppress smooth background variation
    return ||r_hp||

    Physical meaning: during RL deconvolution, the unfiltered residual is
    dominated by smooth background changes (from TV regularization). The
    high-pass filter isolates structural details in the residual that vanish
    upon convergence. When the improvement rate of ||r_hp|| declines past its
    peak, further iterations yield diminishing returns.
    """
    residual = image - blurred_with_bg
    residual_low = gaussian_filter(residual, sigma, mode='reflect')
    residual_high = residual - residual_low
    return float(np.linalg.norm(residual_high))


def richardson_lucy_multiplicative(image, probe, iterations, lambda_reg=0, reg_type="None", pixel_size=1.0, wavelength=1.0, acceleration=False, boundary_handling=True, damping_threshold=None, background_level=0.0, entropy_stopping=False, entropy_window=5, entropy_patience=3, entropy_rel_tol=5e-3, entropy_grad_tol=None, entropy_min_iterations=10, sharpness_stopping=False, sharpness_patience=2, sharpness_rel_tol=0.005, sharpness_min_iterations=10, residual_stopping=False, residual_sigma=3.0, residual_rel_tol=0.85, residual_patience=3, residual_min_iterations=5, return_info=False):
    """
    Richardson-Lucy Multiplicative Deconvolution.
    Supports Biggs-Andrews acceleration, Damping, and Background handling.

    Args:
        damping_threshold (float): Threshold (in sigma) for damped RL.
                                   If set, suppresses noise amplification in flat regions.
        background_level (float): Estimated background level to subtract/model during deconvolution.
                                  RL assumes Poisson noise on (Signal + Background).
        entropy_stopping (bool): Enable early stopping via entropy plateau detection.
        entropy_window (int): Window size for entropy change detection.
        entropy_patience (int): Consecutive windows below threshold before declaring convergence.
        entropy_rel_tol (float): Relative entropy change threshold.
        entropy_grad_tol (float or None): If set, enables combined entropy+TV-gradient criterion.
        entropy_min_iterations (int): Minimum iterations before entropy stopping.
        return_info (bool): If True, return (result, info_dict).
    """
    # Save original dimensions for cropping after deconvolution
    orig_h, orig_w = image.shape[:2]

    # Boundary Handling: zero-pad to next power of 2 for FFT efficiency
    if boundary_handling:
        ny_next = 1 << (image.shape[0] - 1).bit_length()
        nx_next = 1 << (image.shape[1] - 1).bit_length()
        pad_y = ny_next - image.shape[0]
        pad_x = nx_next - image.shape[1]
        image = np.pad(image, ((0, pad_y), (0, pad_x)), mode='constant')
        probe = np.pad(probe, ((0, pad_y), (0, pad_x)), mode='constant')

    object_data = image.astype(np.float32)
    probe_spatial = np.abs(probe).astype(np.float32)
    
    # Normalize probe to preserve energy (sum = 1)
    # This is critical for Richardson-Lucy, especially with background modeling
    probe_sum = np.sum(probe_spatial)
    if probe_sum != 0:
        probe_spatial /= probe_sum
    
    probe_flip_spatial = np.roll(np.flip(np.flip(probe_spatial, 0), 1), (1, 1), (0, 1))
    
    probe_fft = fft2(probe_spatial)
    probe_flip_fft = fft2(probe_flip_spatial)
    
    # Entropy stopping state (always initialized for return_info)
    _info = {}
    _hp_norm_history = []

    # Acceleration variables (Biggs-Andrews vector extrapolation)
    if acceleration:
        g_tm1 = object_data.copy()  # O_{n-1}
        g_tm2 = object_data.copy()  # O_{n-2}
        alpha_acc = 0.0
        delta_tm1 = None  # Delta_{n-1} = O_{n-1} - O_{n-2}

    for i in range(iterations):
        # Prediction step for acceleration
        if acceleration and i > 1:
            # Biggs-Andrews vector extrapolation (Biggs & Andrews, 1997)
            # delta_n = O_n - O_{n-1} (current minus previous)
            delta_n = object_data - g_tm1

            # alpha_n = <Delta_n, Delta_{n-1}> / <Delta_{n-1}, Delta_{n-1}>
            dot_product = np.sum(delta_n * delta_tm1)
            norm_delta_tm1 = np.sum(delta_tm1 * delta_tm1) + 1e-10
            alpha_acc = dot_product / norm_delta_tm1

            # Clamp alpha to [0, 1] for stability (damping)
            alpha_acc = max(0.0, min(1.0, alpha_acc))

            prediction = object_data + alpha_acc * delta_n
            prediction = np.maximum(prediction, 0)  # Positivity constraint
            current_estimate = prediction
        else:
            current_estimate = object_data

        # 1. O * P + Background
        obj_fft = fft2(current_estimate)
        blurred = np.real(fftshift(ifft2(obj_fft * probe_fft)))
        
        # Add background to the model prediction
        blurred_with_bg = blurred + background_level
        blurred_with_bg[blurred_with_bg < 1e-9] = 1e-9 # Avoid division by zero
        
        # 2. I / (O * P + B)
        ratio = image / blurred_with_bg
        
        # Damping (White 1994)
        if damping_threshold is not None:
            # Calculate local noise threshold based on Poisson statistics
            # sigma = sqrt(Model)
            # We want to suppress updates if |Data - Model| < N * sigma
            # |Ratio - 1| = |Data/Model - 1| = |Data - Model| / Model
            # So we check if |Ratio - 1| < N * sigma / Model = N / sqrt(Model)
            
            # Avoid div by zero in sqrt
            model_mag = blurred_with_bg
            model_mag = np.maximum(model_mag, 1e-9)
            
            local_threshold = damping_threshold / np.sqrt(model_mag)
            
            mask_damp = np.abs(ratio - 1.0) < local_threshold
            ratio[mask_damp] = 1.0
        
        # 3. Ratio * P_flip
        gradient = np.real(fftshift(ifft2(fft2(ratio) * probe_flip_fft)))
        
        # 4. Update
        if reg_type == "TV":
            # Multiplicative TV: O_new = O_old * Gradient / (1 - lambda * curv)
            curv = total_variation_gradient(current_estimate)
            divisor = 1.0 - lambda_reg * curv
            # Ensure divisor is positive to prevent sign flipping and division by zero
            divisor = np.maximum(divisor, 1e-6)
            
            new_object = current_estimate * gradient / divisor
            
        elif reg_type == "TM":
            # Multiplicative TM
            tm_term = tikhonov_miller_regularization(current_estimate, lambda_reg, pixel_size, wavelength)
            divisor = tm_term
            # Ensure divisor is positive
            divisor = np.maximum(divisor, 1e-6)
            
            new_object = current_estimate * gradient / divisor
            
        else:
            new_object = current_estimate * gradient
            
        if acceleration:
            delta_tm1 = object_data - g_tm1  # save before updating
            g_tm1 = object_data.copy()
            object_data = new_object
        else:
            object_data = new_object

        # Entropy stopping criterion
        if entropy_stopping:
            if i == 0:
                entropy_history = []
                _patience_counter = 0
                _tv_norm_history = []
                _info = {}

            current_entropy = _compute_entropy(object_data)
            entropy_history.append(current_entropy)

            if entropy_grad_tol is not None and reg_type == "TV":
                _tv_norm_history.append(np.mean(np.abs(curv)))

            if i >= entropy_window:
                # Relative entropy change over window
                delta_rel = abs(current_entropy - entropy_history[i - entropy_window]) / (abs(current_entropy) + 1e-10)

                converged_flag = delta_rel < entropy_rel_tol

                # Combined with TV gradient norm stability
                if entropy_grad_tol is not None and reg_type == "TV":
                    tv_window = _tv_norm_history[i - entropy_window:i + 1]
                    tv_std_rel = np.std(tv_window) / (np.mean(tv_window) + 1e-10)
                    converged_flag = converged_flag and (tv_std_rel < entropy_grad_tol)

                if converged_flag and i >= entropy_min_iterations:
                    _patience_counter += 1
                    if _patience_counter >= entropy_patience:
                        _info = {
                            "iterations_performed": i + 1,
                            "entropy_final": float(current_entropy),
                            "entropy_history": entropy_history,
                            "converged": True,
                            "stop_reason": "entropy_plateau",
                        }
                        break
                else:
                    _patience_counter = 0

        # Sharpness stopping criterion
        if sharpness_stopping:
            if i == 0:
                sharpness_history = []
                _sharpness_increase_counter = 0
                _best_object = object_data.copy()
                _best_iteration = 0
                _info = {}

            current_sharpness = _compute_sharpness(object_data)
            sharpness_history.append(current_sharpness)

            if i == 0:
                _min_sharpness = current_sharpness

            if current_sharpness < _min_sharpness:
                _min_sharpness = current_sharpness
                _best_object = object_data.copy()
                _best_iteration = i

            if i >= sharpness_min_iterations:
                # Detect if sharpness has passed its minimum and is increasing
                # (signals onset of overconvolution / noise amplification)
                if current_sharpness > _min_sharpness * (1.0 + sharpness_rel_tol):
                    _sharpness_increase_counter += 1
                    if _sharpness_increase_counter >= sharpness_patience:
                        # Roll back to the result at minimum sharpness
                        object_data = _best_object
                        _info = {
                            "iterations_performed": _best_iteration + 1,
                            "sharpness_final": float(_min_sharpness),
                            "sharpness_history": sharpness_history,
                            "sharpness_min": float(_min_sharpness),
                            "converged": True,
                            "stop_reason": "sharpness_rollback",
                        }
                        break
                else:
                    _sharpness_increase_counter = 0

        # Residual stopping criterion (HP-filtered residual improvement rate with rollback)
        if residual_stopping:
            if i == 0:
                _hp_norm_prev = None
                _max_improvement = 0.0
                _best_object_residual = object_data.copy()
                _best_iteration_residual = 0
                _residual_decline_counter = 0
                _info = {}

            hp_norm = _compute_hp_residual_norm(image, blurred_with_bg, residual_sigma)
            _hp_norm_history.append(hp_norm)

            if i > 0:
                improvement = _hp_norm_prev - hp_norm

                if improvement > _max_improvement:
                    _max_improvement = improvement
                    _best_object_residual = object_data.copy()
                    _best_iteration_residual = i

                if i >= residual_min_iterations:
                    if improvement < _max_improvement * residual_rel_tol:
                        _residual_decline_counter += 1
                        if _residual_decline_counter >= residual_patience:
                            object_data = _best_object_residual
                            _info = {
                                "iterations_performed": _best_iteration_residual + 1,
                                "hp_residual_history": _hp_norm_history,
                                "hp_improvement_max": float(_max_improvement),
                                "converged": True,
                                "stop_reason": "residual_rollback",
                            }
                            break
                    else:
                        _residual_decline_counter = 0

            _hp_norm_prev = hp_norm

    if boundary_handling:
        object_data = object_data[:orig_h, :orig_w]

    if return_info:
        if not _info:
            _info = {
                "iterations_performed": iterations,
                "entropy_final": float(_compute_entropy(object_data)) if entropy_stopping else None,
                "entropy_history": entropy_history if entropy_stopping else [],
                "sharpness_final": float(_compute_sharpness(object_data)) if sharpness_stopping else None,
                "sharpness_history": sharpness_history if sharpness_stopping else [],
                "hp_residual_history": _hp_norm_history if residual_stopping else [],
                "converged": False,
                "stop_reason": "max_iterations",
            }
        return object_data, _info
    return object_data


def _chambolle_tv_denoise(u, weight, num_iter=25):
    """
    Chambolle's projection algorithm for TV denoising (Chambolle, JMIV 2004).

    Solves: min_u 0.5 * ||u - f||_2^2 + weight * TV(u)

    Dual formulation: u = f - weight * div(p), where |p| <= 1 pointwise.
    Iterates p in the dual space, then reconstructs the primal.

    Args:
        u (np.ndarray): Input image f (the proximal input).
        weight (float): Regularization weight (step_size * lambda_reg).
        num_iter (int): Number of dual iterations.

    Returns:
        np.ndarray: Denoised image.
    """
    f = u.astype(np.float64)
    f_over_weight = f / weight
    epsilon = 1e-8
    px = np.zeros_like(f)
    py = np.zeros_like(f)
    tau = 0.249  # Step size (< 1/4 ensures convergence for 2D)

    for _ in range(num_iter):
        # Backward divergence of p (with Neumann boundary: p_{-1}=0)
        # div_p[i,j] = px[i,j] - px[i,j-1] (for j>0), px[i,0] for j=0
        #             + py[i,j] - py[i-1,j] (for i>0), py[0,j] for i=0
        div_p = np.zeros_like(f)
        div_p[:, 0] = px[:, 0]
        div_p[:, 1:] = px[:, 1:] - px[:, :-1]
        div_p[0, :] += py[0, :]
        div_p[1:, :] += py[1:, :] - py[:-1, :]

        # Forward gradient of (div(p) - f/weight)
        # grad_x[i,j] = tmp[i,j+1] - tmp[i,j], with Neumann: last diff = -tmp[:,-1]
        tmp = div_p - f_over_weight
        grad_x = np.zeros_like(f)
        grad_y = np.zeros_like(f)
        grad_x[:, :-1] = tmp[:, 1:] - tmp[:, :-1]
        grad_x[:, -1] = -tmp[:, -1]
        grad_y[:-1, :] = tmp[1:, :] - tmp[:-1, :]
        grad_y[-1, :] = -tmp[-1, :]

        # Dual update with projection onto |p| <= 1
        px = (px + tau * grad_x) / (1.0 + tau * np.sqrt(grad_x**2 + grad_y**2 + epsilon))
        py = (py + tau * grad_y) / (1.0 + tau * np.sqrt(grad_x**2 + grad_y**2 + epsilon))

    # Reconstruct: u = f - weight * div(p)
    div_final = np.zeros_like(f)
    div_final[:, 0] = px[:, 0]
    div_final[:, 1:] = px[:, 1:] - px[:, :-1]
    div_final[0, :] += py[0, :]
    div_final[1:, :] += py[1:, :] - py[:-1, :]

    return f - weight * div_final


def fista_deconvolution(image, probe, iterations, lambda_reg=0.001, boundary_handling=True):
    """
    Fast Iterative Shrinkage-Thresholding Algorithm (FISTA) for TV regularization.
    Minimizes ||Ax - b||^2 + lambda * TV(x)
    """
    # Save original dimensions for cropping after deconvolution
    orig_h, orig_w = image.shape[:2]

    # Boundary Handling: zero-pad to next power of 2 for FFT efficiency
    if boundary_handling:
        ny_next = 1 << (image.shape[0] - 1).bit_length()
        nx_next = 1 << (image.shape[1] - 1).bit_length()
        pad_y = ny_next - image.shape[0]
        pad_x = nx_next - image.shape[1]
        image = np.pad(image, ((0, pad_y), (0, pad_x)), mode='constant')
        probe = np.pad(probe, ((0, pad_y), (0, pad_x)), mode='constant')

    # A is convolution with probe
    # A^T is convolution with flipped probe
    
    x = image.astype(np.float32)
    y = x.copy()
    t = 1.0
    
    probe_spatial = np.abs(probe).astype(np.float32)
    
    # Normalize probe
    probe_sum = np.sum(probe_spatial)
    if probe_sum != 0:
        probe_spatial /= probe_sum
        
    probe_flip_spatial = np.roll(np.flip(np.flip(probe_spatial, 0), 1), (1, 1), (0, 1))
    
    probe_fft = fft2(probe_spatial)
    probe_flip_fft = fft2(probe_flip_spatial)
    
    # Lipschitz constant estimation (max eigenvalue of A^T A)
    # For convolution, it's max(|FFT(probe)|^2)
    L = np.max(np.abs(probe_fft)**2)
    if L == 0: L = 1.0
    step_size = 1.0 / L
    
    for k in range(iterations):
        # Gradient descent step on data fidelity: x - step * A^T (Ax - b)
        # Ax
        Ax_fft = fft2(y) * probe_fft
        Ax = np.real(fftshift(ifft2(Ax_fft)))
        
        # Residual Ax - b
        residual = Ax - image
        
        # A^T (Residual)
        grad_fft = fft2(residual) * probe_flip_fft
        grad = np.real(fftshift(ifft2(grad_fft)))
        
        x_next = y - step_size * grad

        # TV Proximal operator via Chambolle's projection algorithm
        # prox_{lambda_reg * step_size * TV}(x_next)
        x_next = _chambolle_tv_denoise(x_next, weight=lambda_reg * step_size, num_iter=20)
        
        # FISTA Momentum update
        t_next = (1.0 + np.sqrt(1.0 + 4.0 * t**2)) / 2.0
        y = x_next + ((t - 1.0) / t_next) * (x_next - x)
        
        x = x_next
        t = t_next
        
    if boundary_handling:
        x = x[:orig_h, :orig_w]

    return x
