"""Тесты численного решения уравнения колебаний."""

from math import radians
import unittest

import numpy as np

from physical_pendulum.config import DEFAULT_INTEGRATION, DEFAULT_PENDULUM
from physical_pendulum.pendulum import (
    PendulumModel,
    fit_decay_rate_1_s,
    measure_period,
)
from physical_pendulum.theory import (
    exact_period_s,
    small_angle_angle_rad,
    small_angle_period_s,
)


# Малая амплитуда для сравнения с гармоническим решением, град.
SMALL_AMPLITUDE_DEG: float = 1.0

# Большая амплитуда для сравнения с точной формулой периода, град.
LARGE_AMPLITUDE_DEG: float = 120.0

# Продолжительность расчётов в тестах, с.
DURATION_S: float = 10.0

# Продолжительность расчёта с трением, с.
DAMPED_DURATION_S: float = 30.0

# Допустимое отличие периода при 1° от T0 (поправка A²/16 ≈ 1,9·10⁻⁵).
SMALL_PERIOD_RELATIVE_TOLERANCE: float = 3.0e-5

# Допустимое отличие угла при 1° от A cos(ω0 t), доля амплитуды.
SMALL_ANGLE_RELATIVE_TOLERANCE: float = 1.0e-3

# Допустимое отличие периода от точной формулы.
EXACT_PERIOD_RELATIVE_TOLERANCE: float = 1.0e-8

# Допустимое изменение энергии без трения и ошибка баланса E + Q.
ENERGY_RELATIVE_TOLERANCE: float = 1.0e-10

# Допустимый рост энергии за шаг вывода при трении, доля E0.
ENERGY_GROWTH_TOLERANCE: float = 1.0e-12

# Допустимое отличие найденного коэффициента затухания от β.
DECAY_RATE_RELATIVE_TOLERANCE: float = 1.0e-2


class PendulumModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model: PendulumModel = PendulumModel(DEFAULT_PENDULUM, DEFAULT_INTEGRATION)

    def test_rejects_invalid_input(self) -> None:
        for amplitude, duration in ((0.0, 1.0), (np.pi, 1.0), (0.1, 0.0),
                                    (float("nan"), 1.0), (0.1, float("inf"))):
            with self.subTest(amplitude=amplitude, duration=duration):
                with self.assertRaises(ValueError):
                    self.model.simulate(amplitude, duration)

    def test_small_oscillations_match_harmonic_solution(self) -> None:
        amplitude = radians(SMALL_AMPLITUDE_DEG)
        result = self.model.simulate(amplitude, DURATION_S)
        expected_period = small_angle_period_s(DEFAULT_PENDULUM)
        self.assertAlmostEqual(
            result.period_s, expected_period,
            delta=SMALL_PERIOD_RELATIVE_TOLERANCE * expected_period,
        )
        harmonic = small_angle_angle_rad(DEFAULT_PENDULUM, result.time_s, amplitude)
        deviation = float(np.max(np.abs(result.angle_rad - harmonic)))
        self.assertLess(deviation, SMALL_ANGLE_RELATIVE_TOLERANCE * amplitude)

    def test_large_amplitude_period_matches_exact_formula(self) -> None:
        amplitude = radians(LARGE_AMPLITUDE_DEG)
        result = self.model.simulate(amplitude, DURATION_S)
        expected = exact_period_s(DEFAULT_PENDULUM, amplitude)
        self.assertAlmostEqual(
            result.period_s, expected, delta=EXACT_PERIOD_RELATIVE_TOLERANCE * expected
        )

    def test_energy_is_conserved_without_friction(self) -> None:
        result = self.model.simulate(radians(LARGE_AMPLITUDE_DEG), DURATION_S)
        self.assertLess(result.energy_relative_error, ENERGY_RELATIVE_TOLERANCE)
        self.assertEqual(float(np.max(result.dissipated_energy_j)), 0.0)

    def test_energy_balance_with_friction(self) -> None:
        result = self.model.simulate(radians(10.0), DAMPED_DURATION_S, damped=True)
        initial = float(result.energy_j[0])
        self.assertLess(result.balance_relative_error, ENERGY_RELATIVE_TOLERANCE)
        self.assertLess(float(np.max(np.diff(result.energy_j))),
                        ENERGY_GROWTH_TOLERANCE * initial)
        self.assertLess(float(result.energy_j[-1]), 0.5 * initial)

    def test_peaks_decay_with_theoretical_rate(self) -> None:
        result = self.model.simulate(radians(5.0), DAMPED_DURATION_S, damped=True)
        expected = DEFAULT_PENDULUM.decay_rate_1_s
        self.assertAlmostEqual(
            fit_decay_rate_1_s(result), expected,
            delta=DECAY_RATE_RELATIVE_TOLERANCE * expected,
        )


class MeasurePeriodTests(unittest.TestCase):
    def test_measures_period_of_sine(self) -> None:
        time_s = np.linspace(0.0, 10.0, 10_001)
        self.assertAlmostEqual(measure_period(time_s, np.sin(2.0 * time_s)), np.pi)

    def test_requires_two_crossings(self) -> None:
        time_s = np.linspace(0.0, 1.0, 101)
        with self.assertRaises(ValueError):
            measure_period(time_s, np.cos(time_s))


if __name__ == "__main__":
    unittest.main()
