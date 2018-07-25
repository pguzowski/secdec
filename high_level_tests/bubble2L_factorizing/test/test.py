from __future__ import print_function
from pySecDec.integral_interface import IntegralLibrary
import sympy as sp
import unittest

class CheckLib(unittest.TestCase):
    def setUp(self):
        # load c++ library
        self.lib = IntegralLibrary('../bubble2L_factorizing/bubble2L_factorizing_pylink.so')

        # set global options
        self.maxeval = 10**6
        self.epsrel = 1e-7
        self.epsabs = 1e-15

        self.target_result_without_prefactor = \
        {
              -1: 1.0/9.0 + 0.0j
        }

        self.target_prefactor = \
        {
              -1: 1.0/4.0 + 0.0j
        }

    def check_integral(self, computed_series, target_series, epsrel, epsabs, order_min, order_max):
        # convert result to sympy expressions
        computed_series = sp.sympify(  computed_series.replace(',','+I*').replace('+/-','*value+error*')  )

        for order in range(order_min, order_max+1):
            value = complex( computed_series.coeff('eps',order).coeff('value') )
            error = complex( computed_series.coeff('eps',order).coeff('error') )

            # check that the uncertainties are reasonable
            self.assertLessEqual(error.real, abs(2*epsrel * target_series[order].real))
            if target_series[order].imag != 0.0:
                self.assertLessEqual(error.imag, abs(2*epsrel * target_series[order].imag))

            # check that the desired uncertainties are reached
            self.assertLessEqual(error.real, abs(epsrel * value.real) )
            if target_series[order].imag == 0.0:
                self.assertLessEqual(error.imag, epsabs)
            else:
                self.assertLessEqual(error.imag, abs(epsrel * value.imag) )

            # check integral value
            self.assertAlmostEqual(  value.real, target_series[order].real, delta=epsrel*abs(target_series[order].real)  )
            if target_series[order].imag == 0.0:
                self.assertAlmostEqual(  value.imag, target_series[order].imag, delta=epsabs  )
            else:
                self.assertAlmostEqual(  value.imag, target_series[order].imag, delta=epsrel*abs(target_series[order].imag)  )

    def check_prefactor(self, computed_series, target_series, order_min, order_max):
        # convert result to sympy expressions
        computed_series = sp.sympify(  computed_series.replace(',','+I*')  )

        for order in range(order_min, order_max+1):
            value = complex( computed_series.coeff('eps',order) )

            # check value
            self.assertAlmostEqual(  value.real, target_series[order].real  )
            self.assertAlmostEqual(  value.imag, target_series[order].imag  )

    def check_Cuhre(self, es12):
        # choose integrator
        self.lib.use_Cuhre(epsrel=self.epsrel, maxeval=self.maxeval, epsabs=self.epsabs, real_complex_together=True, flags=0)

        # integrate
        str_integral_without_prefactor, str_prefactor, str_integral_with_prefactor = self.lib([es12])

        # check integral
        self.check_integral(str_integral_without_prefactor, self.target_result_without_prefactor, self.epsrel, self.epsabs, order_min=-1, order_max=-1)

        # check prefactor
        self.check_prefactor(str_prefactor, self.target_prefactor, order_min=-1, order_max=-1)

    def test_Cuhre_Euclidean(self):
        self.check_Cuhre(-1.)

    def test_Cuhre_physical(self):
        self.check_Cuhre(1.)

if __name__ == '__main__':
    unittest.main()
