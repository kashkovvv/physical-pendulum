"""Запуск расчётов физического маятника: python -m physical_pendulum."""

from dataclasses import asdict
from datetime import datetime
import json
from math import degrees, radians
from pathlib import Path

from matplotlib import pyplot as plt

from .config import (
    DEFAULT_INTEGRATION,
    DEFAULT_PENDULUM,
    FIGURE_DPI,
)
from .pendulum import fit_decay_rate_1_s, run_experiments
from .plots import FIGURE_TITLES, create_pendulum_figures
from .theory import (
    damped_period_s,
    exact_period_s,
    series_period_s,
    small_angle_period_s,
)


def main() -> None:
    pendulum = DEFAULT_PENDULUM
    results = run_experiments(pendulum, DEFAULT_INTEGRATION)

    print("Тело маятника")
    print(f"  Масса стержня: {1e3 * pendulum.rod_mass_kg:.3f} г")
    print(f"  Масса маятника: {1e3 * pendulum.mass_kg:.3f} г")
    print(f"  Расстояние до центра масс d: {100 * pendulum.center_of_mass_m:.3f} см")
    print(f"  Момент инерции I: {pendulum.inertia_kg_m2:.6e} кг·м²")
    print(f"  Период малых колебаний T0: {small_angle_period_s(pendulum):.6f} с")

    print()
    print("Свободные колебания без трения")
    for run in (results.small, results.large):
        print(
            f"  A = {degrees(run.amplitude_rad):.0f}°: период {run.period_s:.6f} с, "
            f"max|E - E0|/E0 = {run.energy_relative_error:.1e}"
        )

    print()
    print("Период от амплитуды: расчёт, ряд, точная формула")
    for amplitude, period in zip(results.period_amplitudes_deg, results.periods_s):
        angle = radians(amplitude)
        print(
            f"  {amplitude:5.0f}°: {period:.6f} с, "
            f"{series_period_s(pendulum, angle):.6f} с, "
            f"{exact_period_s(pendulum, angle):.6f} с"
        )
    damped = results.damped
    print()
    print("Затухающие колебания")
    print(f"  Коэффициент трения b: {pendulum.damping_n_m_s:.3e} Н·м·с")
    print(f"  β теория: {pendulum.decay_rate_1_s:.5f} 1/с")
    print(f"  β по максимумам: {fit_decay_rate_1_s(damped):.5f} 1/с")
    print(
        f"  Период: {damped.period_s:.6f} с, "
        f"теория Td = {damped_period_s(pendulum):.6f} с"
    )
    print(f"  max|E + Q - E0|/E0 = {damped.balance_relative_error:.1e}")

    figures = create_pendulum_figures(results)
    generated_at = datetime.now().astimezone()
    output = Path("results") / generated_at.strftime(
        "%Y-%m-%d_%H-%M-%S_%f"
    )
    output.mkdir(parents=True, exist_ok=True)
    print("\nРисунки:")
    for name, figure in figures.items():
        figure.savefig(output / f"{name}.png", dpi=FIGURE_DPI)
        manager = figure.canvas.manager
        if manager is not None:
            manager.set_window_title(FIGURE_TITLES[name])
        print(f"  {FIGURE_TITLES[name]} ({name}.png)")
    parameters = {
        "generated_at": generated_at.isoformat(timespec="microseconds"),
        "pendulum": asdict(pendulum),
        "integration": asdict(DEFAULT_INTEGRATION),
    }
    with (output / "parameters.json").open("w", encoding="utf-8") as stream:
        json.dump(parameters, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"\nРисунки и параметры сохранены в {output}")

    if plt.get_backend().lower() != "agg":
        plt.show()
    plt.close("all")


if __name__ == "__main__":
    main()
