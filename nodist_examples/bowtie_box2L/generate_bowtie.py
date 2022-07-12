#!/usr/bin/env python3
from pySecDec.loop_integral import loop_package
import pySecDec as psd

if __name__ == "__main__":

    li = psd.loop_integral.LoopIntegralFromGraph(
    internal_lines = [[0,[3,4]],[0,[4,5]],[0,[3,6]],['msq',[1,5]],['msq',[1,6]],['msq',[2,5]],['msq',[2,6]]],
    external_lines = [['p1',1],['p2',2],['p3',3],['p4',4]],

    replacement_rules = [
                            ('p1*p1', 0),
                            ('p2*p2', 0),
                            ('p3*p3', 0),
                            ('p4*p4', 0),
                            ('p1*p2', 's/2'),
                            ('p2*p3', 't/2'),
                            ('p1*p3', '-s/2-t/2'),
                            ('p3*p4', 's/2'),
                            ('p1*p4', 't/2'),
                            ('p2*p4', '-s/2-t/2')
                        ]

    )


    Mandelstam_symbols = ['s','t']
    mass_symbols = ['msq']


    loop_package(

    name = 'bowtie',

    loop_integral = li,

    real_parameters = Mandelstam_symbols+mass_symbols,
    #complex_parameters = mass_symbols,

    # the highest order of the final epsilon expansion --> change this value to whatever you think is appropriate
    requested_orders = [0],

    # the optimization level to use in FORM (can be 0, 1, 2, 3)
    form_optimization_level = 2,

    # the WorkSpace parameter for FORM
    form_work_space = '1G',

    # the method to be used for the sector decomposition
    # valid values are ``iterative`` or ``geometric`` or ``geometric_ku``
    decomposition_method = 'geometric',

    )
