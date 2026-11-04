"""Запуск: python -m physical_pendulum [--no-show] [--output PATH]."""
import argparse
from datetime import datetime
from pathlib import Path
from .experiments import run_experiments, save_experiments


def main():
    parser = argparse.ArgumentParser(description='М5: физический маятник, расчёты и графики')
    parser.add_argument('--no-show', action='store_true', help='Сохранить графики без окон')
    parser.add_argument('--output', type=Path, help='Папка результатов')
    args = parser.parse_args()
    if args.no_show:
        import matplotlib
        matplotlib.use('Agg')
    from .plots import create_figures
    import matplotlib.pyplot as plt
    out = args.output or Path('results') / datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')
    data = run_experiments()
    save_experiments(data, out)
    figures = create_figures(data)
    for name, fig in figures.items():
        fig.savefig(out / f'{name}.png', dpi=180)
    m = data['metrics']
    print(f"Момент инерции: {m['inertia_kg_m2']:.9f} кг·м²")
    print(f"Период малых колебаний: {m['small_angle_period_s']:.6f} с")
    print(f"Ошибка сохранения энергии: {m['free_energy_error']:.3e}")
    print(f"Ошибка баланса с трением: {m['damped_balance_error']:.3e}")
    print(f"Результаты: {out.resolve()}")
    if not args.no_show and plt.get_backend().lower() != 'agg':
        plt.show()
    plt.close('all')


if __name__ == '__main__':
    main()
