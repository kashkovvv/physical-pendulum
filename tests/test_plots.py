"""Проверка построения рисунков."""

import unittest

import matplotlib
import numpy as np

matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402

from physical_pendulum.config import (  # noqa: E402
    DEFAULT_INTEGRATION,
    DEFAULT_PENDULUM,
)
from physical_pendulum.pendulum import run_experiments  # noqa: E402
from physical_pendulum.plots import create_pendulum_figures  # noqa: E402


class PlotsTests(unittest.TestCase):
    def test_creates_all_figures_with_data(self) -> None:
        results = run_experiments(DEFAULT_PENDULUM, DEFAULT_INTEGRATION)
        figures = create_pendulum_figures(results)
        try:
            self.assertEqual(set(figures), {"geometry", "free", "period", "damped"})
            period_axis = figures["period"].axes[0]
            points = np.asarray(period_axis.lines[-1].get_xydata())
            self.assertEqual(len(points), len(results.periods_s))
            for name, figure in figures.items():
                with self.subTest(figure=name):
                    self.assertTrue(figure.axes)
        finally:
            for figure in figures.values():
                plt.close(figure)


if __name__ == "__main__":
    unittest.main()
