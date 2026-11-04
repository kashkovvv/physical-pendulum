"""Тесты теоретических формул."""

from math import pi, radians, sqrt
import unittest

import numpy as np

from physical_pendulum.config import DEFAULT_PENDULUM
from physical_pendulum.theory import (
    damped_envelope_rad,
    damped_period_s,
    exact_period_s,
    series_period_s,
    small_angle_period_s,
)


# Контрольный период малых колебаний, с.
EXPECTED_SMALL_ANGLE_PERIOD_S: float = 1.26597

# Абсолютная погрешность сравнения контрольного периода, с.
PERIOD_TOLERANCE_S: float = 1.0e-5

# Допустимое отличие ряда от точной формулы при 20° (следующий член ~A⁶).
SERIES_RELATIVE_TOLERANCE: float = 1.0e-6

# Точное значение T(90°)/T0 = 2K(1/2)/π.
RIGHT_ANGLE_PERIOD_RATIO: float = 1.180340599


class TheoryTests(unittest.TestCase):
    def test_small_angle_period(self) -> None:
        p = DEFAULT_PENDULUM
        torque = p.mass_kg * p.gravity_m_s2 * p.center_of_mass_m
        period = small_angle_period_s(p)
        self.assertAlmostEqual(period, 2.0 * pi * sqrt(p.inertia_kg_m2 / torque))
        self.assertAlmostEqual(
            period, EXPECTED_SMALL_ANGLE_PERIOD_S, delta=PERIOD_TOLERANCE_S
        )

    def test_exact_period_limits(self) -> None:
        p = DEFAULT_PENDULUM
        t0 = small_angle_period_s(p)
        self.assertAlmostEqual(exact_period_s(p, 1.0e-6) / t0, 1.0)
        self.assertAlmostEqual(
            exact_period_s(p, radians(90.0)) / t0, RIGHT_ANGLE_PERIOD_RATIO
        )

    def test_series_matches_exact_period_at_moderate_amplitude(self) -> None:
        amplitude = radians(20.0)
        exact = exact_period_s(DEFAULT_PENDULUM, amplitude)
        self.assertAlmostEqual(
            series_period_s(DEFAULT_PENDULUM, amplitude), exact,
            delta=SERIES_RELATIVE_TOLERANCE * exact,
        )

    def test_damping_formulas(self) -> None:
        p = DEFAULT_PENDULUM
        envelope = damped_envelope_rad(p, np.array((p.amplitude_half_life_s,)), 1.0)
        self.assertAlmostEqual(float(envelope[0]), 0.5)
        self.assertGreater(damped_period_s(p), small_angle_period_s(p))


if __name__ == "__main__":
    unittest.main()
