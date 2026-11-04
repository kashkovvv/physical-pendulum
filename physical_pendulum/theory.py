"""Теоретические формулы для сравнения с численным решением."""

from math import pi, sin, sqrt

import numpy as np
from numpy.typing import NDArray
from scipy.special import ellipk

from .config import PendulumParameters


def small_angle_period_s(pendulum: PendulumParameters) -> float:
    """Период малых колебаний T0 = 2π√(I/(mgd)), с."""
    return 2.0 * pi / pendulum.natural_frequency_rad_s


def series_period_s(pendulum: PendulumParameters, amplitude_rad: float) -> float:
    """Период по ряду T0(1 + A²/16 + 11A⁴/3072), с."""
    correction = 1.0 + amplitude_rad**2 / 16.0 + 11.0 * amplitude_rad**4 / 3072.0
    return small_angle_period_s(pendulum) * correction


def exact_period_s(pendulum: PendulumParameters, amplitude_rad: float) -> float:
    """Точный период через полный эллиптический интеграл K, с."""
    parameter = sin(amplitude_rad / 2.0) ** 2
    return 4.0 * float(ellipk(parameter)) / pendulum.natural_frequency_rad_s


def small_angle_angle_rad(
    pendulum: PendulumParameters, time_s: NDArray[np.float64], amplitude_rad: float
) -> NDArray[np.float64]:
    """Решение для малых углов θ = A cos(ω0 t), рад."""
    return amplitude_rad * np.cos(pendulum.natural_frequency_rad_s * time_s)


def damped_envelope_rad(
    pendulum: PendulumParameters, time_s: NDArray[np.float64], amplitude_rad: float
) -> NDArray[np.float64]:
    """Огибающая затухающих колебаний A·exp(-βt), рад."""
    return amplitude_rad * np.exp(-pendulum.decay_rate_1_s * time_s)


def damped_period_s(pendulum: PendulumParameters) -> float:
    """Период малых затухающих колебаний 2π/√(ω0² - β²), с."""
    omega = pendulum.natural_frequency_rad_s
    return 2.0 * pi / sqrt(omega**2 - pendulum.decay_rate_1_s**2)


def damped_energy_j(
    pendulum: PendulumParameters, time_s: NDArray[np.float64], initial_energy_j: float
) -> NDArray[np.float64]:
    """Энергия малых затухающих колебаний E0·exp(-2βt), Дж.

    Энергия пропорциональна квадрату амплитуды, поэтому убывает вдвое
    быстрее амплитуды.
    """
    return initial_energy_j * np.exp(-2.0 * pendulum.decay_rate_1_s * time_s)
