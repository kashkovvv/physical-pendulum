"""Графики по уже рассчитанным результатам."""

from math import cos, radians, sin

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Arc, Polygon

from .config import PLOT_WINDOW_S, PendulumParameters
from .pendulum import ExperimentResults, PendulumResult, find_peaks
from .theory import (
    damped_energy_j,
    damped_envelope_rad,
    exact_period_s,
    series_period_s,
    small_angle_angle_rad,
    small_angle_period_s,
)


# Цвета: численное решение, теория и вспомогательные линии.
NUMERIC_COLOR: str = "#2a62c9"
THEORY_COLOR: str = "#d9622b"
GUIDE_COLOR: str = "#6b6b6b"
SECOND_COLOR: str = "#1b8a5a"
ROD_COLOR: str = "#333333"
BOB_COLOR: str = "#c9a23a"

# Угол наклона маятника на схеме, град.
SKETCH_ANGLE_DEG: float = 20.0

# Наибольшая амплитуда на кривых теоретического периода, град.
CURVE_MAX_AMPLITUDE_DEG: float = 160.0


# Заголовки окон с рисунками при запуске программы.
FIGURE_TITLES: dict[str, str] = {
    "geometry": "Рис. 1. Схема маятника",
    "free": "Рис. 2. Свободные колебания без трения",
    "period": "Рис. 3. Зависимость периода от амплитуды",
    "damped": "Рис. 4. Затухающие колебания",
}


def create_pendulum_figures(results: ExperimentResults) -> dict[str, Figure]:
    """Создать все рисунки: схему, свободные колебания, период и затухание."""
    return {
        "geometry": _plot_geometry(results.pendulum),
        "free": _plot_free(results),
        "period": _plot_period(results),
        "damped": _plot_damped(results),
    }


def _format_axis(axis: Axes, x_label: str, y_label: str) -> None:
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.grid(alpha=0.25)


def _comma(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _draw_body(
    axis: Axes, pendulum: PendulumParameters, angle_rad: float
) -> tuple[float, float]:
    """Нарисовать стержень и груз, отклонённые на угол; вернуть центр масс."""
    along = np.array((sin(angle_rad), -cos(angle_rad)))
    across = np.array((cos(angle_rad), sin(angle_rad)))

    def point(distance: float, offset: float = 0.0) -> tuple[float, float]:
        x, y = distance * along + offset * across
        return float(x), float(y)

    length = pendulum.rod_length_m
    half_width = pendulum.bob_width_m / 2.0
    top = length - pendulum.bob_height_m
    axis.plot(*zip(point(0.0), point(length)), color=ROD_COLOR, lw=3, zorder=2,
              solid_capstyle="butt")
    axis.add_patch(Polygon(
        [point(top, -half_width), point(top, half_width),
         point(length, half_width), point(length, -half_width)],
        closed=True, facecolor=BOB_COLOR, edgecolor="black", lw=0.8, zorder=3,
    ))
    axis.plot(0.0, 0.0, "o", color="black", ms=7, zorder=4)
    center = point(pendulum.center_of_mass_m)
    axis.plot(*center, "o", color=THEORY_COLOR, ms=7, mec="white", mew=1.2,
              zorder=5)
    return center


def _plot_geometry(pendulum: PendulumParameters) -> Figure:
    figure, (size_axis, swing_axis) = plt.subplots(
        1, 2, figsize=(7, 5), layout="constrained"
    )
    length = pendulum.rod_length_m

    # Слева: равновесие и размеры, отложенные от оси вниз.
    _draw_body(size_axis, pendulum, 0.0)
    for distance, offset, label in (
        (length, 0.06, "L"),
        (pendulum.bob_distance_m, 0.11, "a"),
        (pendulum.center_of_mass_m, 0.16, "d"),
    ):
        size_axis.plot((0.0, offset + 0.01), (-distance, -distance),
                       ":", color=GUIDE_COLOR, lw=0.8)
        size_axis.annotate("", xy=(offset, -distance), xytext=(offset, 0.0),
                           arrowprops={"arrowstyle": "<->", "color": GUIDE_COLOR})
        size_axis.text(offset + 0.005, -distance / 2.0,
                       f"{label} = {_comma(100 * distance)} см",
                       rotation=90, ha="left", va="center", fontsize=10)
    size_axis.plot((0.0, 0.17), (0.0, 0.0), ":", color=GUIDE_COLOR, lw=0.8)
    size_axis.text(-0.015, 0.0, "ось O", ha="right", va="center")
    size_axis.text(-0.025, -pendulum.center_of_mass_m, "центр масс",
                   ha="right", va="center", color=THEORY_COLOR)
    size_axis.text(-0.025, -pendulum.bob_distance_m - 0.03,
                   "груз " + _comma(1e3 * pendulum.bob_mass_kg, 2) + " г",
                   ha="right", va="center")
    size_axis.text(-0.015, -length / 2.0, "стержень", ha="right", va="center")
    size_axis.set_title("Равновесие: размеры тела")
    size_axis.set_xlim(-0.16, 0.24)

    # Справа: отклонённый маятник, сила тяжести и плечо d·sinθ.
    angle = radians(SKETCH_ANGLE_DEG)
    center_x, center_y = _draw_body(swing_axis, pendulum, angle)
    swing_axis.plot((0.0, 0.0), (0.0, -1.05 * length), "--",
                    color=GUIDE_COLOR, lw=1)
    swing_axis.add_patch(Arc((0.0, 0.0), 0.16, 0.16, theta1=270.0,
                             theta2=270.0 + SKETCH_ANGLE_DEG, color=NUMERIC_COLOR,
                             lw=1.5))
    swing_axis.text(0.012, -0.1, "θ", color=NUMERIC_COLOR, fontsize=14)
    swing_axis.annotate("", xy=(center_x, center_y - 0.09),
                        xytext=(center_x, center_y),
                        arrowprops={"arrowstyle": "-|>", "color": THEORY_COLOR,
                                    "lw": 2})
    swing_axis.text(center_x + 0.01, center_y - 0.08, "mg", color=THEORY_COLOR,
                    fontsize=12)
    swing_axis.plot((0.0, center_x), (center_y, center_y), color=SECOND_COLOR,
                    lw=2)
    swing_axis.text(center_x / 2.0, center_y + 0.01, "d·sinθ", color=SECOND_COLOR,
                    ha="center", va="bottom")
    swing_axis.text(0.015, 0.0, "ось O", va="center")
    swing_axis.set_title("Отклонение на угол θ")
    swing_axis.set_xlim(-0.1, 0.3)

    for axis in (size_axis, swing_axis):
        axis.set_aspect("equal")
        axis.set_ylim(-1.15 * length, 0.04)
        axis.set_axis_off()
    return figure


def _plot_free(results: ExperimentResults) -> Figure:
    figure, axes = plt.subplots(3, 1, figsize=(9, 8.5), layout="constrained")
    pendulum = results.pendulum
    for axis, run in zip(axes[:2], (results.small, results.large)):
        shown = run.time_s <= PLOT_WINDOW_S
        time = run.time_s[shown]
        theory = small_angle_angle_rad(pendulum, time, run.amplitude_rad)
        axis.plot(time, np.degrees(run.angle_rad[shown]), color=NUMERIC_COLOR,
                  lw=2, label="численное решение")
        axis.plot(time, np.degrees(theory), "--", color=THEORY_COLOR, lw=1.5,
                  label="A cos(ω₀t)")
        axis.set_title(f"Амплитуда {np.degrees(run.amplitude_rad):.0f}°")
        _format_axis(axis, "Время, с", "Угол, град")
        axis.legend(loc="upper right")

    for run, color in ((results.small, NUMERIC_COLOR), (results.large, SECOND_COLOR)):
        initial = float(run.energy_j[0])
        error = np.maximum.accumulate(np.abs(run.energy_j - initial) / initial)
        axes[2].semilogy(run.time_s[1:], error[1:], color=color, lw=2,
                         label=f"A = {np.degrees(run.amplitude_rad):.0f}°")
    axes[2].set_title(
        "Относительная погрешность энергии δE без трения"
    )
    _format_axis(axes[2], "Время, с", r"$\delta E = \max\,|E - E_0|\,/\,E_0$")
    axes[2].legend(loc="lower right")
    return figure


def _plot_period(results: ExperimentResults) -> Figure:
    figure, axis = plt.subplots(figsize=(9, 5), layout="constrained")
    pendulum = results.pendulum
    curve_deg = np.linspace(1.0, CURVE_MAX_AMPLITUDE_DEG, 300)
    exact = [exact_period_s(pendulum, radians(value)) for value in curve_deg]
    series = [series_period_s(pendulum, radians(value)) for value in curve_deg]
    axis.axhline(small_angle_period_s(pendulum), color=GUIDE_COLOR, lw=1,
                 label="T₀ (малые колебания)")
    axis.plot(curve_deg, series, "--", color=THEORY_COLOR, lw=1.5,
              label="ряд T₀(1 + A²/16 + 11A⁴/3072)")
    axis.plot(curve_deg, exact, color=THEORY_COLOR, lw=2,
              label="точная формула (4/ω₀)K(sin²(A/2))")
    axis.plot(results.period_amplitudes_deg, results.periods_s, "o",
              color=NUMERIC_COLOR, ms=8, mec="white", label="численный расчёт")
    axis.set_title("Зависимость периода от амплитуды")
    _format_axis(axis, "Амплитуда A, град", "Период T, с")
    axis.legend(loc="upper left")
    return figure


def _plot_damped(results: ExperimentResults) -> Figure:
    figure = plt.figure(figsize=(10, 8), layout="constrained")
    grid = figure.add_gridspec(2, 2)
    angle_axis = figure.add_subplot(grid[0, :])
    peak_axis = figure.add_subplot(grid[1, 0])
    energy_axis = figure.add_subplot(grid[1, 1])
    pendulum = results.pendulum
    run: PendulumResult = results.damped
    amplitude_deg = np.degrees(run.amplitude_rad)
    envelope = np.degrees(damped_envelope_rad(pendulum, run.time_s, run.amplitude_rad))

    angle_axis.plot(run.time_s, np.degrees(run.angle_rad), color=NUMERIC_COLOR,
                    lw=0.7, label="численное решение θ(t)")
    angle_axis.plot(run.time_s, envelope, "--", color=THEORY_COLOR, lw=2,
                    label=r"теория: $\pm A\,e^{-\beta t}$")
    angle_axis.plot(run.time_s, -envelope, "--", color=THEORY_COLOR, lw=2)
    angle_axis.set_title(f"Колебания с трением, начальный угол {amplitude_deg:.0f}°")
    _format_axis(angle_axis, "Время, с", "Угол, град")
    angle_axis.legend(loc="upper right")

    peak_time, peak_angle = find_peaks(run.time_s, run.angle_rad)
    peak_axis.semilogy(peak_time, np.degrees(peak_angle), "o", color=NUMERIC_COLOR,
                       ms=4, label="максимумы численного решения")
    peak_axis.semilogy(run.time_s, envelope, color=THEORY_COLOR, lw=2,
                       label=r"теория $A\,e^{-\beta t}$, "
                       f"β = {pendulum.decay_rate_1_s:.4f} 1/с")
    ticks = [value for value in (1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)
             if value <= amplitude_deg]
    peak_axis.set_yticks(ticks, [f"{value:g}" for value in ticks])
    peak_axis.minorticks_off()
    peak_axis.set_title("Амплитуда (логарифмическая шкала)")
    _format_axis(peak_axis, "Время, с", "Амплитуда, град")
    peak_axis.legend(loc="upper right", fontsize=8)

    millijoule = 1.0e3
    initial_energy = float(run.energy_j[0])
    energy_axis.plot(run.time_s, millijoule * run.energy_j, color=NUMERIC_COLOR,
                     lw=1.5, label="энергия E (расчёт)")
    energy_axis.plot(run.time_s,
                     millijoule * damped_energy_j(pendulum, run.time_s,
                                                  initial_energy),
                     "--", color=THEORY_COLOR, lw=2,
                     label=r"теория: $E_0\,e^{-2\beta t}$")
    energy_axis.plot(run.time_s,
                     millijoule * (run.energy_j + run.dissipated_energy_j),
                     color=SECOND_COLOR, lw=2, label="E + Q (Q — теплота трения)")
    energy_axis.set_title("Энергия маятника")
    _format_axis(energy_axis, "Время, с", "Энергия, мДж")
    energy_axis.set_ylim(bottom=0.0)
    energy_axis.legend(loc="center right", fontsize=8)
    return figure
