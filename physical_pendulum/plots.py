"""Графики для программы и отчёта; единицы указаны на каждой оси."""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from .theory import exact_period, exact_free_angle, linear_angle


plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.grid': True, 'grid.alpha': .22, 'figure.dpi': 120})


def create_figures(data):
    p = data['model']
    figures = {}
    fig, ax = plt.subplots(figsize=(8, 4.5), layout='constrained')
    ax.add_patch(Rectangle((-p.rod_radius, -p.rod_length), 2*p.rod_radius, p.rod_length, color='#4c6580'))
    ax.add_patch(Rectangle((-p.bob_width/2, -p.bob_distance-p.bob_height/2), p.bob_width, p.bob_height, color='#d89732'))
    ax.add_patch(Circle((0, 0), .004, color='#163c56'))
    ax.scatter([0], [-p.center_of_mass], c='#be3650', zorder=5)
    ax.annotate('Ось O', (0, 0), (.04, -.01))
    ax.annotate('Центр масс', (0, -p.center_of_mass), (.05, -.28), arrowprops={'arrowstyle':'->'})
    ax.text(.05, -.12, f'Стержень: {p.rod_length*100:.1f} см; {p.rod_mass*1000:g} г\nГруз: {p.bob_mass*1000:g} г\na = {p.bob_distance*100:g} см')
    ax.set(xlim=(-.07, .30), ylim=(-.45, .04), aspect='equal', xlabel='x, м', ylabel='y, м', title='Выбранная геометрия в положении равновесия')
    figures['geometry'] = fig

    s = data['free']
    fig, axs = plt.subplots(2, 2, figsize=(9, 6), layout='constrained')
    mask = s.time < 6*p.period
    axs[0,0].plot(s.time[mask], np.rad2deg(s.angle[mask]), label='Численно')
    axs[0,0].plot(s.time[mask], np.rad2deg(exact_free_angle(p, s.time[mask], np.deg2rad(60))), '--', label='Точное решение')
    axs[0,0].set(xlabel='t, с', ylabel='θ, град', title='Свободные колебания, 60°')
    axs[0,0].legend()
    axs[0,1].plot(np.rad2deg(s.angle), s.velocity)
    axs[0,1].set(xlabel='θ, град', ylabel='ω, рад/с', title='Фазовая траектория')
    for values, label in [(s.kinetic,'Кинетическая'), (s.potential,'Потенциальная'), (s.energy,'Полная')]:
        axs[1,0].plot(s.time[mask], values[mask], label=label)
    axs[1,0].set(xlabel='t, с', ylabel='Энергия, Дж')
    axs[1,0].legend(fontsize=8)
    axs[1,1].plot(s.time, (s.energy-s.energy[0])/s.energy[0])
    axs[1,1].set(xlabel='t, с', ylabel='(E − E₀) / E₀', title='Погрешность сохранения энергии')
    figures['free'] = fig

    rows = data['periods']
    x = np.linspace(0, 175, 350)
    fig, axs = plt.subplots(1, 2, figsize=(9,4), layout='constrained')
    axs[0].plot(x, [exact_period(p,np.deg2rad(v)) for v in x], label='Эллиптический интеграл')
    axs[0].scatter([r['amplitude_deg'] for r in rows], [r['numerical_s'] for r in rows], color='#d89732', label='Численное решение', zorder=3)
    axs[0].axhline(p.period, ls='--', color='gray', label='Малые углы')
    axs[0].set(xlabel='Амплитуда, град', ylabel='Период, с')
    axs[0].legend(fontsize=8)
    axs[1].semilogy([r['amplitude_deg'] for r in rows], [max(r['relative_error'],1e-16) for r in rows], 'o-')
    axs[1].set(xlabel='Амплитуда, град', ylabel='|Tчисл / Tтеор − 1|', title='Ошибка относительно точной теории')
    figures['period'] = fig

    s = data['small']
    fig, axs = plt.subplots(2, 2, figsize=(9,6), layout='constrained')
    lin = linear_angle(p, s.time, np.deg2rad(5), damping=p.damping)
    axs[0,0].plot(s.time, np.rad2deg(s.angle), lw=.9, label='Нелинейная модель')
    axs[0,0].plot(s.time, np.rad2deg(lin), '--', lw=.7, label='Линейная теория')
    axs[0,0].set(xlabel='t, с', ylabel='θ, град', title='Затухание при начальном угле 5°')
    axs[0,0].legend(fontsize=8)
    axs[0,1].semilogy(s.peak_times, np.rad2deg(s.peak_angles), 'o', ms=3, label='Максимумы решения')
    axs[0,1].semilogy(s.time, 5*np.exp(-p.beta*s.time), label='5 exp(−βt)')
    axs[0,1].set(xlabel='t, с', ylabel='Амплитуда, град', title='Огибающая')
    axs[0,1].legend(fontsize=8)
    axs[1,0].plot(s.time, s.energy/s.energy[0], label='E / E₀')
    axs[1,0].plot(s.time, s.heat/s.energy[0], label='Q / E₀')
    axs[1,0].plot(s.time, (s.energy+s.heat)/s.energy[0], label='(E + Q) / E₀')
    axs[1,0].set(xlabel='t, с', ylabel='Доля начальной энергии')
    axs[1,0].legend(fontsize=8)
    axs[1,1].plot(s.time, (s.energy+s.heat-s.energy[0])/s.energy[0])
    axs[1,1].set(xlabel='t, с', ylabel='(E + Q − E₀) / E₀', title='Проверка баланса с трением')
    figures['damping'] = fig

    s = data['large']
    fig, axs = plt.subplots(1, 2, figsize=(9,4), layout='constrained')
    axs[0].plot(s.time, np.rad2deg(s.angle), lw=.8)
    axs[0].set(xlabel='t, с', ylabel='θ, град', title='Затухание при начальном угле 60°')
    axs[1].plot(s.crossings[1:], np.diff(s.crossings), 'o-', ms=3, label='Период между пересечениями')
    axs[1].axhline(data['metrics']['damped_period_linear_s'], ls='--', color='gray', label='Линейная теория')
    axs[1].set(xlabel='t, с', ylabel='Локальный период, с', title='Период уменьшается с амплитудой')
    axs[1].legend(fontsize=8)
    figures['large_damping'] = fig

    fig, axs = plt.subplots(1, 2, figsize=(9,4), layout='constrained')
    rows = data['positions']
    axs[0].plot([r['distance_m'] for r in rows], [r['theory_s'] for r in rows], label='Теория, 5°')
    axs[0].scatter([r['distance_m'] for r in rows], [r['numerical_s'] for r in rows], color='#d89732', label='Расчёт')
    axs[0].set(xlabel='Расстояние до груза a, м', ylabel='Период, с')
    axs[0].legend()
    rows = data['periods']
    axs[1].plot([r['amplitude_deg'] for r in rows], [100*(r['inferred_g']/p.gravity-1) for r in rows], 'o-')
    axs[1].set(xlabel='Амплитуда, град', ylabel='Ошибка определения g, %', title='Если использовать формулу малых углов')
    figures['practical'] = fig

    fig, ax = plt.subplots(figsize=(8,4), layout='constrained')
    rows = data['convergence']
    for key, label in [('energy_error','Энергия'), ('relative_period_error','Период'), ('max_angle_error_rad','Угол, рад')]:
        ax.loglog([r['rtol'] for r in rows], [r[key] for r in rows], 'o-', label=label)
    ax.invert_xaxis()
    ax.set(xlabel='Относительный допуск интегратора', ylabel='Максимальная ошибка', title='Сходимость: 120°, 20 периодов')
    ax.legend()
    figures['convergence'] = fig
    return figures
