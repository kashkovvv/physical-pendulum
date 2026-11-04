"""Воспроизводимые вычислительные эксперименты М5."""
from dataclasses import asdict, replace
import csv
import json
from pathlib import Path
import platform
import numpy as np
import scipy
from .config import DEFAULT
from .model import simulate
from .theory import exact_period, exact_free_angle, linear_angle


AMPLITUDES = (1, 5, 15, 30, 60, 90, 120, 150, 170)


def run_experiments(model=DEFAULT):
    free = simulate(model, np.deg2rad(60), 20 * model.period)
    small = simulate(model, np.deg2rad(5), 60, damping=model.damping, samples=6001)
    large = simulate(model, np.deg2rad(60), 60, damping=model.damping, samples=6001)
    periods = []
    for degrees in AMPLITUDES:
        a = np.deg2rad(degrees)
        theory = exact_period(model, a)
        s = simulate(model, a, 6 * theory, samples=1001)
        periods.append(dict(amplitude_deg=degrees, numerical_s=s.period, theory_s=theory,
                            relative_error=abs(s.period / theory - 1),
                            excess_percent=100 * (theory / model.period - 1),
                            inferred_g=model.gravity * (model.period / s.period)**2,
                            energy_error=s.balance_error))
    positions = []
    for distance in (0.15, 0.25, 0.35, 0.40):
        p = replace(model, bob_distance=distance)
        a = np.deg2rad(5)
        s = simulate(p, a, 8 * p.period, samples=1001)
        positions.append(dict(distance_m=distance, inertia_kg_m2=p.inertia,
                              equivalent_length_m=p.equivalent_length,
                              numerical_s=s.period, theory_s=exact_period(p, a)))
    convergence = []
    a = np.deg2rad(120)
    for tolerance in (1e-4, 1e-6, 1e-8, 1e-10):
        s = simulate(model, a, 20 * exact_period(model, a), rtol=tolerance,
                     atol=tolerance / 100, max_step=model.period, samples=4001)
        convergence.append(dict(rtol=tolerance, nfev=s.evaluations,
                                relative_period_error=abs(s.period / exact_period(model, a) - 1),
                                max_angle_error_rad=float(np.max(np.abs(s.angle - exact_free_angle(model, s.time, a)))),
                                energy_error=s.balance_error))
    mask = small.peak_times > 0.01
    beta_fit = -float(np.polyfit(small.peak_times[mask], np.log(small.peak_angles[mask]), 1)[0])
    linear = linear_angle(model, small.time, np.deg2rad(5), damping=model.damping)
    metrics = dict(inertia_kg_m2=model.inertia, rod_inertia_kg_m2=model.rod_inertia,
                   bob_inertia_kg_m2=model.bob_inertia, mass_kg=model.mass,
                   center_of_mass_m=model.center_of_mass, equivalent_length_m=model.equivalent_length,
                   small_angle_period_s=model.period, damping_N_m_s=model.damping,
                   beta_s_inverse=model.beta, beta_fit_s_inverse=beta_fit,
                   quality_factor=model.frequency / (2 * model.beta),
                   damped_period_linear_s=2 * np.pi / np.sqrt(model.frequency**2 - model.beta**2),
                   damped_period_measured_s=small.period,
                   free_energy_error=free.balance_error,
                   free_exact_angle_error_rad=float(np.max(np.abs(free.angle - exact_free_angle(model, free.time, np.deg2rad(60))))),
                   damped_balance_error=small.balance_error,
                   large_damped_balance_error=large.balance_error,
                   damped_linear_max_error_deg=float(np.rad2deg(np.max(np.abs(small.angle-linear)))))
    return dict(model=model, free=free, small=small, large=large, periods=periods,
                positions=positions, convergence=convergence, metrics=metrics)


def save_experiments(data, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ('periods', 'positions', 'convergence'):
        with (directory / f'{name}.csv').open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[name][0]))
            writer.writeheader()
            writer.writerows(data[name])
    for name in ('free', 'small', 'large'):
        s = data[name]
        np.savetxt(directory / f'{name}.csv', np.column_stack([s.time, s.angle, s.velocity,
                   s.kinetic, s.potential, s.energy, s.heat]), delimiter=',',
                   header='time_s,angle_rad,velocity_rad_s,kinetic_J,potential_J,energy_J,heat_J', comments='')
    payload = dict(parameters=asdict(data['model']), metrics=data['metrics'],
                   versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
                   integration=dict(method='DOP853', rtol=1e-10, atol=1e-12,
                                    max_step_s=data['model'].period/30),
                   damping_note='Время полузатухания 30 с - предположение, не измерение PASCO.')
    (directory / 'summary.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
