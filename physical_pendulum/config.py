"""Геометрия PASCO ME-9821 и явно отделённые допущения, все величины в СИ."""
from dataclasses import dataclass
from math import isfinite, log, pi, sqrt


@dataclass(frozen=True)
class Pendulum:
    """Цилиндрический стержень и прямоугольный груз; ось поперёк стержня.

    Размеры и массы из PASCO ME-9821. Положение груза, ориентация блока,
    идеальная геометрия, g и время полузатухания задаются в модели.
    """
    rod_length: float = 0.417
    rod_radius: float = 0.002
    rod_mass: float = 0.001
    bob_mass: float = 0.100
    bob_width: float = 0.028
    bob_height: float = 0.028
    bob_depth: float = 0.015
    bob_distance: float = 0.350
    gravity: float = 9.80665
    amplitude_half_life: float = 30.0

    def __post_init__(self):
        for name, value in vars(self).items():
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name}: требуется положительное конечное число")
        if not self.bob_height / 2 <= self.bob_distance <= self.rod_length - self.bob_height / 2:
            raise ValueError("Груз должен целиком помещаться вдоль стержня")

    @property
    def mass(self):
        return self.rod_mass + self.bob_mass

    @property
    def first_moment(self):
        return self.rod_mass * self.rod_length / 2 + self.bob_mass * self.bob_distance

    @property
    def center_of_mass(self):
        return self.first_moment / self.mass

    @property
    def rod_inertia(self):
        return self.rod_mass * (self.rod_length**2 / 3 + self.rod_radius**2 / 4)

    @property
    def bob_inertia(self):
        return self.bob_mass * (self.bob_distance**2 + (self.bob_width**2 + self.bob_height**2) / 12)

    @property
    def inertia(self):
        return self.rod_inertia + self.bob_inertia

    @property
    def equivalent_length(self):
        return self.inertia / self.first_moment

    @property
    def frequency(self):
        """Собственная угловая частота, рад/с."""
        return sqrt(self.gravity / self.equivalent_length)

    @property
    def period(self):
        return 2 * pi / self.frequency

    @property
    def beta(self):
        return log(2) / self.amplitude_half_life

    @property
    def damping(self):
        """Коэффициент вязкого момента b, Н·м·с; не паспортное измерение."""
        return 2 * self.inertia * self.beta


DEFAULT = Pendulum()
