"""Входные параметры модели физического маятника."""

from dataclasses import dataclass
from math import isfinite, log, pi, sqrt


# Тело маятника: графитовый стержень и латунный груз на его нижнем конце.
# Ось подвеса проходит через верхний конец стержня.
# Длина стержня, м.
ROD_LENGTH_M: float = 0.417

# Радиус стержня, м.
ROD_RADIUS_M: float = 0.002

# Плотность графита, кг/м^3.
ROD_DENSITY_KG_M3: float = 1_600.0

# Плотность латуни, кг/м^3.
BOB_DENSITY_KG_M3: float = 8_500.0

# Размер груза поперёк стержня в плоскости качания, м.
BOB_WIDTH_M: float = 0.028

# Размер груза вдоль стержня, м.
BOB_HEIGHT_M: float = 0.028

# Размер груза вдоль оси подвеса, м.
BOB_DEPTH_M: float = 0.015

# Ускорение свободного падения, м/с^2.
GRAVITY_M_S2: float = 9.806_65

# Время, за которое амплитуда уменьшается вдвое из-за трения, с.
AMPLITUDE_HALF_LIFE_S: float = 30.0


# Начальные условия и продолжительность расчётов.
# Маятник отпускается без начальной скорости с отклонения на амплитуду.
# Амплитуда колебаний при малых углах, град.
SMALL_AMPLITUDE_DEG: float = 5.0

# Амплитуда колебаний при больших углах, град.
LARGE_AMPLITUDE_DEG: float = 60.0

# Продолжительность расчёта свободных колебаний, с.
FREE_DURATION_S: float = 30.0

# Амплитуды для изучения зависимости периода от амплитуды, град.
PERIOD_AMPLITUDES_DEG: tuple[float, ...] = (
    5.0, 10.0, 20.0, 30.0, 45.0, 60.0, 90.0, 120.0, 150.0,
)

# Продолжительность каждого расчёта периода, с.
PERIOD_DURATION_S: float = 15.0

# Амплитуда затухающих колебаний, град.
DAMPED_AMPLITUDE_DEG: float = 10.0

# Продолжительность расчёта затухающих колебаний, с.
DAMPED_DURATION_S: float = 90.0


# Настройки численного решения уравнения движения.
# Относительная погрешность интегрирования.
RELATIVE_TOLERANCE: float = 1.0e-10

# Абсолютная погрешность угла, рад, и угловой скорости, рад/с.
ABSOLUTE_TOLERANCE: float = 1.0e-12

# Максимальный шаг интегрирования, с.
MAXIMUM_STEP_S: float = 0.01

# Шаг сетки, на которой сохраняется решение, с.
OUTPUT_STEP_S: float = 0.001


# Настройки графиков.
# Длительность участка, который показан на графиках угла, с.
PLOT_WINDOW_S: float = 6.0

# Разрешение сохраняемых рисунков, точек на дюйм.
FIGURE_DPI: int = 150


@dataclass(frozen=True)
class PendulumParameters:
    """Размеры и массы тела, g и трение в единицах СИ."""

    rod_length_m: float = ROD_LENGTH_M
    rod_radius_m: float = ROD_RADIUS_M
    rod_density_kg_m3: float = ROD_DENSITY_KG_M3
    bob_density_kg_m3: float = BOB_DENSITY_KG_M3
    bob_width_m: float = BOB_WIDTH_M
    bob_height_m: float = BOB_HEIGHT_M
    bob_depth_m: float = BOB_DEPTH_M
    gravity_m_s2: float = GRAVITY_M_S2
    amplitude_half_life_s: float = AMPLITUDE_HALF_LIFE_S

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if not isfinite(value) or value <= 0.0:
                raise ValueError(f"{name}: ожидалось конечное положительное число")
        if self.bob_height_m > self.rod_length_m:
            raise ValueError("Груз должен помещаться на стержне")

    @property
    def rod_mass_kg(self) -> float:
        """Масса стержня m_ст = ρπR²L, кг."""
        return self.rod_density_kg_m3 * pi * self.rod_radius_m**2 * self.rod_length_m

    @property
    def bob_mass_kg(self) -> float:
        """Масса груза m_гр = ρ·(w·h·s - πR²h), кг.

        Стержень проходит сквозь груз, поэтому из объёма бруска вычитается
        отверстие под стержень длиной h.
        """
        block = self.bob_width_m * self.bob_height_m * self.bob_depth_m
        hole = pi * self.rod_radius_m**2 * self.bob_height_m
        return self.bob_density_kg_m3 * (block - hole)

    @property
    def mass_kg(self) -> float:
        """Масса маятника, кг."""
        return self.rod_mass_kg + self.bob_mass_kg

    @property
    def bob_distance_m(self) -> float:
        """Расстояние от оси до центра груза a = L - h/2, м."""
        return self.rod_length_m - self.bob_height_m / 2.0

    @property
    def center_of_mass_m(self) -> float:
        """Расстояние от оси до центра масс d, м."""
        first_moment = (
            self.rod_mass_kg * self.rod_length_m / 2.0
            + self.bob_mass_kg * self.bob_distance_m
        )
        return first_moment / self.mass_kg

    @property
    def inertia_kg_m2(self) -> float:
        """Момент инерции относительно оси (теорема Штейнера), кг·м²."""
        rod = self.rod_mass_kg * (
            self.rod_length_m**2 / 3.0 + self.rod_radius_m**2 / 4.0
        )
        bob = self.bob_mass_kg * (
            self.bob_distance_m**2
            + (self.bob_width_m**2 + self.bob_height_m**2) / 12.0
        )
        return rod + bob

    @property
    def natural_frequency_rad_s(self) -> float:
        """Частота малых колебаний ω0 = √(mgd/I), рад/с."""
        torque = self.mass_kg * self.gravity_m_s2 * self.center_of_mass_m
        return sqrt(torque / self.inertia_kg_m2)

    @property
    def decay_rate_1_s(self) -> float:
        """Коэффициент затухания β = ln2 / t½, 1/с."""
        return log(2.0) / self.amplitude_half_life_s

    @property
    def damping_n_m_s(self) -> float:
        """Коэффициент вязкого трения в оси b = 2Iβ, Н·м·с."""
        return 2.0 * self.inertia_kg_m2 * self.decay_rate_1_s


@dataclass(frozen=True)
class IntegrationParameters:
    """Настройки solve_ivp и сетки вывода."""

    relative_tolerance: float = RELATIVE_TOLERANCE
    absolute_tolerance: float = ABSOLUTE_TOLERANCE
    maximum_step_s: float = MAXIMUM_STEP_S
    output_step_s: float = OUTPUT_STEP_S

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if not isfinite(value) or value <= 0.0:
                raise ValueError(f"{name}: ожидалось конечное положительное число")
        if self.relative_tolerance >= 1.0:
            raise ValueError("Относительная погрешность должна быть меньше единицы")


# Параметры маятника по умолчанию.
DEFAULT_PENDULUM: PendulumParameters = PendulumParameters()

# Настройки интегрирования по умолчанию.
DEFAULT_INTEGRATION: IntegrationParameters = IntegrationParameters()
