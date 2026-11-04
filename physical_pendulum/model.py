"""Интегрирование нелинейного уравнения и баланса энергии методом DOP853."""
from dataclasses import dataclass
import numpy as np
from scipy.integrate import solve_ivp


@dataclass
class Motion:
    time: np.ndarray
    angle: np.ndarray
    velocity: np.ndarray
    heat: np.ndarray
    kinetic: np.ndarray
    potential: np.ndarray
    crossings: np.ndarray
    peak_times: np.ndarray
    peak_angles: np.ndarray
    evaluations: int

    @property
    def energy(self):
        return self.kinetic + self.potential

    @property
    def period(self):
        if len(self.crossings) < 2:
            raise ValueError("Недостаточно пересечений для измерения периода")
        return float(np.mean(np.diff(self.crossings)))

    @property
    def balance_error(self):
        scale = max(float(self.energy[0]), np.finfo(float).tiny)
        return float(np.max(np.abs(self.energy + self.heat - self.energy[0])) / scale)


def simulate(model, angle, duration, velocity=0.0, damping=0.0,
             rtol=1e-10, atol=1e-12, max_step=None, samples=4001):
    """Q'=b*omega². Нули theta с одинаковым направлением дают полный период.

    samples задаёт только вывод, не внутренний шаг интегратора.
    """
    for name, value in [('angle', angle), ('velocity', velocity), ('damping', damping),
                        ('duration', duration), ('rtol', rtol), ('atol', atol)]:
        if not np.isfinite(value):
            raise ValueError(f"{name}: требуется конечное число")
    if duration <= 0 or damping < 0 or not 0 < rtol < 1 or atol <= 0:
        raise ValueError("Некорректные длительность, трение или допуски")
    if not isinstance(samples, int) or samples < 2:
        raise ValueError("samples должно быть целым числом >= 2")
    step = model.period / 30 if max_step is None else max_step
    if not np.isfinite(step) or step <= 0:
        raise ValueError("max_step должен быть положительным")

    def rhs(t, y):
        theta, omega, _ = y
        return [omega, -model.frequency**2 * np.sin(theta) - damping / model.inertia * omega,
                damping * omega**2]

    def crossing(t, y):
        return y[0]

    crossing.direction = -1

    def peak(t, y):
        return y[1]

    peak.direction = -1
    result = solve_ivp(rhs, (0, duration), [angle, velocity, 0.0], method='DOP853',
                       rtol=rtol, atol=atol, max_step=step,
                       t_eval=np.linspace(0, duration, samples), events=(crossing, peak))
    if not result.success:
        raise RuntimeError(result.message)
    theta, omega, heat = result.y
    peaks = result.y_events[1]
    return Motion(result.t, theta, omega, heat,
                  0.5 * model.inertia * omega**2,
                  2 * model.gravity * model.first_moment * np.sin(theta / 2)**2,
                  result.t_events[0], result.t_events[1],
                  peaks[:, 0] if len(peaks) else np.array([]), result.nfev)
