#!/usr/bin/env python3

import sympy as sp

if __name__ == "__main__":

    # load c++ library
    from pySecDec.integral_interface import DistevalLibrary
    name = 'twoloop_EBR_first_order_s' #name of directory
    loop_integral = DistevalLibrary('{0}/disteval/{0}.json'.format(name))

    # integrate
    #s_energies = [1, 1.5, 2, 4, 10, 100]
    s_energies = [3]
    for x in s_energies:
        str_result = loop_integral(parameters={'s' : x, 'mwsq' : 0.78, 'mzsq' : 1.0, 'mtsq' : 0.00038}, verbose=True)
