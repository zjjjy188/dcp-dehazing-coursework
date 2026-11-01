"""复现 ngydc/dehazing-dark-channel，并实现计算加速与可消融的改进。"""
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import minimum_filter, uniform_filter


@dataclass(frozen=True)
class Config:
    window: int = 15
    radius: int = 40
    omega: float = 0.95
    t0: float = 0.1
    eps: float = 0.001 / 255**2  # 与原版 0..255 引导图的正则项等效
    robust_airlight: bool = False
    bright_protection: float = 0.0


def validate(image, cfg):
    image = np.asarray(image, dtype=np.float64)
    if image.ndim != 3 or image.shape[2] != 3 or min(image.shape[:2]) < 1:
        raise ValueError('输入必须是非空 RGB 图像')
    if not np.isfinite(image).all() or image.min() < 0 or image.max() > 1:
        raise ValueError('像素必须是 0 到 1 之间的有限数值')
    if cfg.window < 1 or cfg.window % 2 != 1 or cfg.radius < 1:
        raise ValueError('暗通道窗口必须为正奇数，引导滤波半径必须大于零')
    if not (0 < cfg.t0 <= 1 and 0 < cfg.omega <= 1 and cfg.eps > 0 and 0 <= cfg.bright_protection <= 1):
        raise ValueError('去雾参数超出有效范围')
    return image


def dark_channel(image, window=15):
    # 最小值可先在颜色通道归约，再进行空间最小滤波，边界与上游 edge 一致。
    return minimum_filter(image.min(axis=2), size=window, mode='nearest')


def airlight(image, dark, robust=False):
    flat = image.reshape(-1, 3)
    count = max(1, int(dark.size * 0.01))
    # 使用同一排序，保证与原版候选像素相同（包括暗通道并列值）。
    candidates = flat[np.argsort(-dark.ravel())[:count]]
    if robust:
        # 从最亮的四分之一候选取中位数，减弱单个异常亮点的影响。
        brightness = candidates.mean(axis=1)
        selected = candidates[np.argsort(-brightness)[:max(1, count // 4)]]
        value = np.median(selected, axis=0)
    else:
        value = candidates.max(axis=0)
    return np.maximum(value, 1 / 255)


def guided_filter(guide, src, radius=40, eps=1e-3):
    """彩色引导滤波，截断边界归一化与原版一致，批量求解 3×3 方程。"""
    size = 2 * radius + 1
    count = uniform_filter(np.ones(src.shape), size=size, mode='constant')

    def mean(x):
        kernel = (size, size) + (1,) * (x.ndim - 2)
        denominator = count[(...,) + (None,) * (x.ndim - 2)]
        return uniform_filter(x, size=kernel, mode='constant') / denominator

    mean_i, mean_p = mean(guide), mean(src)
    cov_ip = mean(guide * src[..., None]) - mean_i * mean_p[..., None]
    covariance = mean(guide[..., :, None] * guide[..., None, :]) - mean_i[..., :, None] * mean_i[..., None, :]
    covariance += eps * np.eye(3)
    a = np.linalg.solve(covariance, cov_ip[..., None])[..., 0]
    b = mean_p - np.sum(a * mean_i, axis=2)
    return np.sum(mean(a) * guide, axis=2) + mean(b)


def dehaze(image, cfg=Config(), details=False):
    image = validate(image, cfg)
    dark = dark_channel(image, cfg.window)
    atmosphere = airlight(image, dark, cfg.robust_airlight)
    normalized_dark = dark_channel(image / atmosphere, cfg.window)
    transmission = 1 - cfg.omega * normalized_dark
    transmission = guided_filter(image, transmission, cfg.radius, cfg.eps)
    if cfg.bright_protection:
        # 低饱和、高亮区域的暗通道先验容易失效，适当提高透射率下限。
        maximum, minimum = image.max(axis=2), image.min(axis=2)
        saturation = (maximum - minimum) / np.maximum(maximum, 1e-8)
        weight = np.clip((minimum - 0.55) / 0.4, 0, 1) * (1 - saturation)
        floor = cfg.t0 + cfg.bright_protection * weight
    else:
        floor = cfg.t0
    transmission = np.clip(np.maximum(transmission, floor), cfg.t0, 1)
    result = np.clip((image - atmosphere) / transmission[..., None] + atmosphere, 0, 1)
    return (result, {'dark': dark, 'transmission': transmission, 'airlight': atmosphere}) if details else result
