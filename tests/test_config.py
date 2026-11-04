"""Тесты параметров маятника и момента инерции."""

import unittest
from dataclasses import fields, replace
from collections.abc import Callable
from math import cos, log, pi

from scipy.integrate import tplquad

from physical_pendulum.config import (
    DEFAULT_INTEGRATION,
    DEFAULT_PENDULUM,
    IntegrationParameters,
    PendulumParameters,
)


# Допустимая относительная погрешность сравнения с прямым интегрированием.
INTEGRAL_RELATIVE_TOLERANCE: float = 1.0e-9

# Недопустимые значения параметров.
INVALID_VALUES: tuple[float, ...] = (0.0, -1.0, float("nan"), float("inf"))


# Подынтегральная функция от координат x (поперёк стержня) и z (вдоль него), м.
Integrand = Callable[[float, float], float]


def rod_integral(function: Integrand) -> float:
    """Интеграл ∫ρ·f(x, z) dV по стержню в цилиндрических координатах."""
    p = DEFAULT_PENDULUM

    def integrand(r: float, phi: float, z: float) -> float:
        return p.rod_density_kg_m3 * function(r * cos(phi), z) * r

    value, _ = tplquad(
        integrand, 0.0, p.rod_length_m, 0.0, 2.0 * pi, 0.0, p.rod_radius_m
    )
    return float(value)


def bob_integral(function: Integrand) -> float:
    """Интеграл ∫ρ·f(x, z) dV по однородному грузу-параллелепипеду."""
    p = DEFAULT_PENDULUM
    density = p.bob_mass_kg / (p.bob_width_m * p.bob_height_m * p.bob_depth_m)

    def integrand(x: float, _y: float, z: float) -> float:
        return density * function(x, z)

    value, _ = tplquad(
        integrand,
        p.rod_length_m - p.bob_height_m, p.rod_length_m,
        -p.bob_depth_m / 2.0, p.bob_depth_m / 2.0,
        -p.bob_width_m / 2.0, p.bob_width_m / 2.0,
    )
    return float(value)


def body_integral(function: Integrand) -> float:
    """Интеграл по всему маятнику."""
    return rod_integral(function) + bob_integral(function)


class PendulumParametersTests(unittest.TestCase):
    def test_rejects_invalid_numeric_values(self) -> None:
        for parameter_field in fields(PendulumParameters):
            for invalid_value in INVALID_VALUES:
                with self.subTest(field=parameter_field.name, value=invalid_value):
                    with self.assertRaises(ValueError):
                        replace(
                            DEFAULT_PENDULUM, **{parameter_field.name: invalid_value}
                        )

    def test_requires_bob_on_rod(self) -> None:
        with self.assertRaises(ValueError):
            replace(DEFAULT_PENDULUM, bob_height_m=2.0 * DEFAULT_PENDULUM.rod_length_m)

    def test_rod_mass_from_density(self) -> None:
        expected = rod_integral(lambda x, z: 1.0)
        self.assertAlmostEqual(
            DEFAULT_PENDULUM.rod_mass_kg, expected,
            delta=INTEGRAL_RELATIVE_TOLERANCE * expected,
        )

    def test_center_of_mass_matches_integration(self) -> None:
        expected = body_integral(lambda x, z: z) / body_integral(lambda x, z: 1.0)
        self.assertAlmostEqual(
            DEFAULT_PENDULUM.center_of_mass_m, expected,
            delta=INTEGRAL_RELATIVE_TOLERANCE * expected,
        )

    def test_inertia_matches_integration(self) -> None:
        expected = body_integral(lambda x, z: x**2 + z**2)
        self.assertAlmostEqual(
            DEFAULT_PENDULUM.inertia_kg_m2, expected,
            delta=INTEGRAL_RELATIVE_TOLERANCE * expected,
        )

    def test_damping_gives_half_life(self) -> None:
        p = DEFAULT_PENDULUM
        decay = p.damping_n_m_s / (2.0 * p.inertia_kg_m2)
        self.assertAlmostEqual(decay * p.amplitude_half_life_s, log(2.0))


class IntegrationParametersTests(unittest.TestCase):
    def test_rejects_invalid_numeric_values(self) -> None:
        for parameter_field in fields(IntegrationParameters):
            for invalid_value in INVALID_VALUES:
                with self.subTest(field=parameter_field.name, value=invalid_value):
                    with self.assertRaises(ValueError):
                        replace(
                            DEFAULT_INTEGRATION, **{parameter_field.name: invalid_value}
                        )

    def test_requires_relative_tolerance_below_one(self) -> None:
        with self.assertRaises(ValueError):
            replace(DEFAULT_INTEGRATION, relative_tolerance=1.0)


if __name__ == "__main__":
    unittest.main()
