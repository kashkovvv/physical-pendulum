"""Независимые теоретические ориентиры для численного решения."""
import numpy as np
from scipy.special import ellipk, ellipj


def exact_period(model, amplitude):
    """Период либраций; ellipk принимает параметр m = k², не модуль k."""
    if not np.isfinite(amplitude) or not 0 <= abs(amplitude) < np.pi:
        raise ValueError("Для периода необходимо |амплитуда| < pi")
    return 4 * ellipk(np.sin(amplitude / 2)**2) / model.frequency


def exact_free_angle(model, time, amplitude):
    """Точное нелинейное решение при omega(0)=0 и |theta(0)|<pi."""
    exact_period(model, amplitude)
    k = np.sin(amplitude / 2)
    m = k * k
    sn = ellipj(ellipk(m) - model.frequency * np.asarray(time), m)[0]
    return 2 * np.arcsin(np.clip(k * sn, -1, 1))


def linear_angle(model, time, angle, velocity=0.0, damping=0.0):
    """Линейное решение с правильной начальной скоростью, слабое трение."""
    beta = damping / (2 * model.inertia)
    if not 0 <= beta < model.frequency:
        raise ValueError("Формула применима только к колебательному режиму")
    wd = np.sqrt(model.frequency**2 - beta**2)
    t = np.asarray(time)
    return np.exp(-beta * t) * (angle * np.cos(wd * t) + (velocity + beta * angle) / wd * np.sin(wd * t))
