"""Численное решение уравнения колебаний физического маятника."""

from dataclasses import dataclass
from math import isfinite, radians

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from .config import (
    DAMPED_AMPLITUDE_DEG,
    DAMPED_DURATION_S,
    FREE_DURATION_S,
    LARGE_AMPLITUDE_DEG,
    PERIOD_AMPLITUDES_DEG,
    PERIOD_DURATION_S,
    SMALL_AMPLITUDE_DEG,
    IntegrationParameters,
    PendulumParameters,
)


@dataclass(frozen=True)
class PendulumResult:
    """История движения маятника в единицах СИ."""

    time_s: NDArray[np.float64]
    angle_rad: NDArray[np.float64]
    angular_velocity_rad_s: NDArray[np.float64]
    energy_j: NDArray[np.float64]
    dissipated_energy_j: NDArray[np.float64]

    @property
    def amplitude_rad(self) -> float:
        """Начальное отклонение, рад."""
        return float(self.angle_rad[0])

    @property
    def energy_relative_error(self) -> float:
        """Наибольшее отклонение max|E - E0|/E0."""
        initial = float(self.energy_j[0])
        return float(np.max(np.abs(self.energy_j - initial))) / initial

    @property
    def balance_relative_error(self) -> float:
        """Наибольшее отклонение max|E + Q - E0|/E0 с учётом теплоты Q."""
        initial = float(self.energy_j[0])
        total = self.energy_j + self.dissipated_energy_j
        return float(np.max(np.abs(total - initial))) / initial

    @property
    def period_s(self) -> float:
        """Средний период по переходам угла через ноль снизу вверх, с."""
        return measure_period(self.time_s, self.angle_rad)


class PendulumModel:
    """Модель качания тела вокруг горизонтальной оси: Iθ'' = -mgd·sinθ - bθ'."""

    def __init__(
        self, pendulum: PendulumParameters, integration: IntegrationParameters
    ) -> None:
        self.pendulum: PendulumParameters = pendulum
        self.integration: IntegrationParameters = integration

    def simulate(
        self, amplitude_rad: float, duration_s: float, damped: bool = False
    ) -> PendulumResult:
        """Решить уравнение движения при θ(0) = A, ω(0) = 0."""
        if not isfinite(amplitude_rad) or not 0.0 < amplitude_rad < np.pi:
            raise ValueError("Амплитуда должна лежать между 0 и π")
        if not isfinite(duration_s) or duration_s <= 0.0:
            raise ValueError("Продолжительность должна быть положительной")

        inertia = self.pendulum.inertia_kg_m2
        torque = (
            self.pendulum.mass_kg
            * self.pendulum.gravity_m_s2
            * self.pendulum.center_of_mass_m
        )
        damping = self.pendulum.damping_n_m_s if damped else 0.0

        def derivatives(
            _time_s: float, state: NDArray[np.float64]
        ) -> NDArray[np.float64]:
            # Состояние: угол, угловая скорость и выделившаяся теплота Q.
            angle, velocity, _heat = state
            acceleration = (-torque * np.sin(angle) - damping * velocity) / inertia
            return np.array((velocity, acceleration, damping * velocity**2))

        steps = round(duration_s / self.integration.output_step_s)
        time_s = np.linspace(0.0, steps * self.integration.output_step_s, steps + 1)
        solution = solve_ivp(
            fun=derivatives,
            t_span=(0.0, float(time_s[-1])),
            y0=np.array((amplitude_rad, 0.0, 0.0)),
            method="DOP853",
            t_eval=time_s,
            rtol=self.integration.relative_tolerance,
            atol=self.integration.absolute_tolerance,
            max_step=self.integration.maximum_step_s,
        )
        if not solution.success:
            raise RuntimeError(f"Ошибка численного решения: {solution.message}")

        angle, velocity, heat = solution.y
        # U = mgd(1 - cos θ) = 2mgd·sin²(θ/2): во второй записи нет вычитания
        # близких чисел, поэтому при малых углах меньше ошибка округления.
        potential = 2.0 * torque * np.sin(angle / 2.0) ** 2
        energy = 0.5 * inertia * velocity**2 + potential
        return PendulumResult(
            time_s=solution.t,
            angle_rad=angle,
            angular_velocity_rad_s=velocity,
            energy_j=energy,
            dissipated_energy_j=heat,
        )


def upward_crossings_s(
    time_s: NDArray[np.float64], angle_rad: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Моменты перехода угла через ноль снизу вверх (линейная интерполяция), с."""
    index = np.nonzero((angle_rad[:-1] < 0.0) & (angle_rad[1:] >= 0.0))[0]
    fraction = -angle_rad[index] / (angle_rad[index + 1] - angle_rad[index])
    return time_s[index] + fraction * (time_s[index + 1] - time_s[index])


def measure_period(
    time_s: NDArray[np.float64], angle_rad: NDArray[np.float64]
) -> float:
    """Средний интервал между переходами через ноль в одну сторону, с."""
    crossings = upward_crossings_s(time_s, angle_rad)
    if crossings.size < 2:
        raise ValueError("Слишком короткий расчёт: меньше одного полного периода")
    return float(np.mean(np.diff(crossings)))


def find_peaks(
    time_s: NDArray[np.float64], angle_rad: NDArray[np.float64]
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Времена и значения положительных максимумов угла."""
    inner = angle_rad[1:-1]
    index = 1 + np.nonzero(
        (inner > angle_rad[:-2]) & (inner >= angle_rad[2:]) & (inner > 0.0)
    )[0]
    return time_s[index], angle_rad[index]


def fit_decay_rate_1_s(result: PendulumResult) -> float:
    """Коэффициент затухания по наклону ln(амплитуды) от времени, 1/с."""
    peak_time_s, peak_angle_rad = find_peaks(result.time_s, result.angle_rad)
    slope, _intercept = np.polyfit(peak_time_s, np.log(peak_angle_rad), 1)
    return -float(slope)


@dataclass(frozen=True)
class ExperimentResults:
    """Результаты всех расчётов задания."""

    pendulum: PendulumParameters
    small: PendulumResult
    large: PendulumResult
    period_amplitudes_deg: tuple[float, ...]
    periods_s: tuple[float, ...]
    damped: PendulumResult


def run_experiments(
    pendulum: PendulumParameters, integration: IntegrationParameters
) -> ExperimentResults:
    """Выполнить расчёты свободных, затухающих колебаний и периода от амплитуды."""
    model = PendulumModel(pendulum, integration)
    periods = tuple(
        model.simulate(radians(amplitude), PERIOD_DURATION_S).period_s
        for amplitude in PERIOD_AMPLITUDES_DEG
    )
    return ExperimentResults(
        pendulum=pendulum,
        small=model.simulate(radians(SMALL_AMPLITUDE_DEG), FREE_DURATION_S),
        large=model.simulate(radians(LARGE_AMPLITUDE_DEG), FREE_DURATION_S),
        period_amplitudes_deg=PERIOD_AMPLITUDES_DEG,
        periods_s=periods,
        damped=model.simulate(
            radians(DAMPED_AMPLITUDE_DEG), DAMPED_DURATION_S, damped=True
        ),
    )
