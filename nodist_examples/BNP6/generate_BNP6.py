#!/usr/bin/env python3
from pySecDec.loop_integral import loop_package
import pySecDec as psd

if __name__ == "__main__":

    # massless non-planar 6-propagator box

    li = psd.loop_integral.LoopIntegralFromGraph(
    internal_lines = [[0,[1,2]],[0,[1,3]],[0,[1,4]],[0,[4,5]],[0,[3,5]],[0,[2,5]]],
    external_lines = [['p1',1],['p2',2],['p3',3],['p4',4]],

    replacement_rules = [
                            ('p1*p1', 0),
                            ('p2*p2', 0),
                            ('p3*p3', 0),
                            ('p4*p4', 0),
                            ('p1*p2', 's/2'),
                            ('p2*p3', 't/2'),
                            ('p1*p3', '(-s-t)/2'),
                            ('p3*p4', 's/2'),
                            ('p1*p4', 't/2'),
                            ('p2*p4', '(-s-t)/2')
                        ]

    )


    Mandelstam_symbols = ['s','t']
    #mass_symbols = ['m1sq','m2sq']


    loop_package(

    name = 'BNP6',

    loop_integral = li,

    real_parameters = Mandelstam_symbols,
    #complex_parameters = mass_symbols,

    # the highest order of the final epsilon expansion --> change this value to whatever you think is appropriate
    requested_order = 0,

    # the optimization level to use in FORM (can be 0, 1, 2, 3)
    form_optimization_level = 2,

    # the WorkSpace parameter for FORM
    form_work_space = '1G',

    # the method to be used for the sector decomposition
    # valid values are ``iterative`` or ``geometric`` or ``geometric_ku``
    decomposition_method = 'iterative',

    split = True

    )
