"""PSNR 与 11×11 高斯窗口 RGB SSIM，输入范围为 0..1。"""
import numpy as np
from scipy.ndimage import gaussian_filter


def psnr(reference, output):
    mse = np.mean((reference - output)**2)
    return float(-10 * np.log10(max(float(mse), 1e-15)))


def ssim(reference, output):
    def smooth(x):
        return gaussian_filter(x, sigma=(1.5, 1.5, 0), truncate=3.5, mode='reflect')
    ux, uy = smooth(reference), smooth(output)
    vx, vy = smooth(reference**2) - ux**2, smooth(output**2) - uy**2
    covariance = smooth(reference * output) - ux * uy
    values = ((2 * ux * uy + .01**2) * (2 * covariance + .03**2)) / ((ux**2 + uy**2 + .01**2) * (vx + vy + .03**2))
    return float(values[5:-5, 5:-5].mean())
