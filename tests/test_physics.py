"""Физические проверки с независимыми ориентирами и реалистичной геометрией."""
import unittest
from dataclasses import replace
import numpy as np
from scipy.integrate import quad, dblquad
from physical_pendulum.config import DEFAULT
from physical_pendulum.model import simulate
from physical_pendulum.theory import exact_period, exact_free_angle, linear_angle


class GeometryTests(unittest.TestCase):
    def test_inertia_by_mass_integration(self):
        p = DEFAULT
        # Независимое интегрирование r_perp² dm по цилиндру и блоку.
        rod_long = quad(lambda z: p.rod_mass/p.rod_length*z*z, 0, p.rod_length)[0]
        rod_cross = dblquad(lambda phi, r: p.rod_mass/(np.pi*p.rod_radius**2)
                            *r**3*np.cos(phi)**2, 0, p.rod_radius,
                            lambda r: 0, lambda r: 2*np.pi)[0]
        block = dblquad(lambda z, x: p.bob_mass/(p.bob_width*p.bob_height)
                        *(x*x+z*z), -p.bob_width/2, p.bob_width/2,
                        lambda x: p.bob_distance-p.bob_height/2,
                        lambda x: p.bob_distance+p.bob_height/2)[0]
        self.assertAlmostEqual(p.inertia, rod_long+rod_cross+block, delta=1e-13)

    def test_mass_scaling_does_not_change_free_period(self):
        p = DEFAULT
        heavier = replace(p, rod_mass=2*p.rod_mass, bob_mass=2*p.bob_mass)
        self.assertAlmostEqual(p.period, heavier.period, places=13)

    def test_invalid_geometry(self):
        for args in ({'rod_length': 0}, {'bob_mass': -1}, {'gravity': float('nan')},
                     {'bob_distance': .5}, {'amplitude_half_life': 0}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                replace(DEFAULT, **args)


class DynamicsTests(unittest.TestCase):
    def test_equilibrium_stays_at_rest(self):
        s = simulate(DEFAULT, 0, 3)
        np.testing.assert_array_equal(s.angle, 0)
        np.testing.assert_array_equal(s.energy, 0)
        with self.assertRaises(ValueError):
            simulate(DEFAULT, .1, .01).period

    def test_small_angle_period(self):
        s = simulate(DEFAULT, 1e-3, 10*DEFAULT.period)
        self.assertLess(abs(s.period/DEFAULT.period-1), 1e-7)

    def test_period_against_independent_quadrature(self):
        p = DEFAULT
        for degrees in (5, 60, 120, 170):
            a = np.deg2rad(degrees)
            k = np.sin(a/2)
            integral = quad(lambda u: 1/np.sqrt(1-k*k*np.sin(u)**2), 0, np.pi/2,
                            epsabs=1e-12, epsrel=1e-12)[0]
            reference = 4*integral/p.frequency
            s = simulate(p, a, 6*reference, samples=1001)
            with self.subTest(degrees=degrees):
                self.assertLess(abs(s.period/reference-1), 2e-8)
                self.assertLess(s.balance_error, 1e-8)

    def test_full_trajectory_against_exact_solution(self):
        p = DEFAULT
        for degrees in (30, -60, 150):
            a = np.deg2rad(degrees)
            s = simulate(p, a, 10*exact_period(p,a))
            self.assertLess(np.max(np.abs(s.angle-exact_free_angle(p,s.time,a))), 2e-7)

    def test_nonzero_initial_velocity_and_energy(self):
        p = DEFAULT
        s = simulate(p, 0, 10, velocity=0.4)
        amplitude = 2*np.arcsin(np.sqrt((.5*p.inertia*.4**2)/(2*p.gravity*p.first_moment)))
        self.assertLess(abs(s.period/exact_period(p,amplitude)-1), 1e-8)
        self.assertLess(s.balance_error, 1e-8)

    def test_damped_energy_balance_and_monotonicity(self):
        p = DEFAULT
        for degrees in (5, 60):
            s = simulate(p, np.deg2rad(degrees), 60, damping=p.damping)
            self.assertLess(s.balance_error, 1e-8)
            self.assertLess(np.max(np.diff(s.energy)), 1e-10*s.energy[0])
            self.assertGreaterEqual(np.min(np.diff(s.heat)), -1e-12)
            self.assertLess(s.energy[-1]/s.energy[0], .08)

    def test_damped_linear_limit_and_half_life(self):
        p = DEFAULT
        a = np.deg2rad(1)
        s = simulate(p, a, 60, damping=p.damping)
        reference = linear_angle(p,s.time,a,damping=p.damping)
        self.assertLess(np.max(np.abs(s.angle-reference))/a, .001)
        mask = s.peak_times > .01
        fitted = -np.polyfit(s.peak_times[mask],np.log(s.peak_angles[mask]),1)[0]
        self.assertLess(abs(np.log(2)/fitted/p.amplitude_half_life-1), 1e-4)

    def test_realistic_bob_positions(self):
        for distance in (.15,.25,.35,.40):
            p = replace(DEFAULT,bob_distance=distance)
            s = simulate(p,np.deg2rad(5),8*p.period)
            self.assertLess(abs(s.period/exact_period(p,np.deg2rad(5))-1),1e-8)

    def test_convergence_when_tolerance_tightens(self):
        p = DEFAULT
        a = np.deg2rad(120)
        errors=[]
        for tol in (1e-4,1e-9):
            s=simulate(p,a,20*exact_period(p,a),rtol=tol,atol=tol/100,max_step=p.period)
            errors.append(np.max(np.abs(s.angle-exact_free_angle(p,s.time,a))))
        self.assertLess(errors[1],errors[0]/1000)

    def test_invalid_solver_parameters(self):
        for args in ({'duration':0},{'damping':-1},{'angle':float('inf')},
                     {'samples':1},{'max_step':0},{'rtol':0}):
            kw=dict(angle=.1,duration=2)
            kw.update(args)
            with self.subTest(args=args), self.assertRaises(ValueError):
                simulate(DEFAULT,**kw)
        for a in (np.pi, float('nan')):
            with self.assertRaises(ValueError):
                exact_period(DEFAULT,a)


if __name__ == '__main__':
    unittest.main()
