"""
This module implements the main program - the function
:func:`.make_package`.

"""

from __future__ import print_function
from ..metadata import version, git_id
from ..misc import sympify_symbols, rangecomb
from ..algebra import _Expression, Expression, Polynomial, \
                      ExponentiatedPolynomial, Pow, Product, \
                      ProductRule, DerivativeTracker, Function, \
                      Sum
from .. import decomposition
from ..matrix_sort import iterative_sort, Pak_sort
from ..subtraction import integrate_pole_part
from ..expansion import expand_singular, expand_Taylor, expand_sympy
from ..misc import lowest_order
from .template_parser import parse_template_file, parse_template_tree
from itertools import chain
from time import strftime
from re import match
import numpy as np
import sympy as sp
import sys, os

# The only public object this module provides is the function `make_package`.
# The module is organized in multiple sections dedicated to specific tasks
# to be addressed while writing the c++ package.
# To find the main function `make_package`, it is easiest to full-text search
# for "def make_package(".

_sympy_one = sp.sympify(1)

# ----------------------------------- parse input -----------------------------------
def _parse_expressions(expressions, polysymbols, target_type, name_of_make_argument_being_parsed):
    '''
    Convert `polynomials` from string or sympy expression
    to :class:`_Expression` or :class:`ExponentiatedPolynomial`.
    If a polynomial in `polynomials` is already of that type,
    check that the `polysymbols` are correct.
    Return the parsed polynomials and their names.

    Note: `target_type` may only be :class:`_Expression` or
          :class:`ExponentiatedPolynomial`.

    '''
    parsed = []
    for expression in expressions:
        if isinstance(expression, _Expression):
            if expression.symbols != polysymbols:
                raise ValueError('"%s" (in `%s`) depends on the wrong `symbols` (is: %s, should be: %s). Try passing it as string or sympy expression.' \
                                 % (expression, name_of_make_argument_being_parsed, expression.symbols, polysymbols))
        if target_type is ExponentiatedPolynomial:
            if type(expression) == ExponentiatedPolynomial:
                expression.exponent = sp.sympify(str(expression.exponent))
                expression.coeffs = np.array([ sp.sympify(str(coeff)) for coeff in expression.coeffs ])
            elif type(expression) == Polynomial:
                expression = ExponentiatedPolynomial(expression.expolist,
                                                     np.array([ sp.sympify(str(coeff)) for coeff in expression.coeffs ]),
                                                     _sympy_one, # exponent
                                                     polysymbols, copy=False)
            else:
                expression = sp.sympify(str(expression))
                if expression.is_Pow:
                    assert len(expression.args) == 2
                    expression_base = Polynomial.from_expression(expression.args[0], polysymbols)
                    expression_exponent = sp.sympify(str(expression.args[1]))
                    expression = ExponentiatedPolynomial(expression_base.expolist,
                                                         expression_base.coeffs,
                                                         expression_exponent, polysymbols, copy=False)
                else:
                    expression = Polynomial.from_expression(expression, polysymbols)
                    expression = ExponentiatedPolynomial(expression.expolist,
                                                         expression.coeffs,
                                                         _sympy_one, # exponent
                                                         polysymbols, copy=False)
        elif target_type is _Expression:
            if not isinstance(expression, _Expression):
                expression, functions = Expression(expression, polysymbols, follow_functions=True)
        else:
            raise RuntimeError('`_parse_expressions` is only implemented for `target_type`s in %s, not for %s. (raised while parsing `%s`)' \
                                % (set([_Expression, ExponentiatedPolynomial]), target_type, name_of_make_argument_being_parsed))
        parsed.append(expression if target_type is ExponentiatedPolynomial else (expression,functions))
    return parsed

def _validate(name):
    '''
    Check validity of `name` for usage in FORM,
    c++, and the file system.
    Restrictions are as follows:
     o FORM: no underscores
     o FORM, c++: the first character must be
       in [A-Z, a-z]; i.e. no leading numbers
     o all: no special characters; i.e. only
       characters from the set [A-Z, a-z, 0-9]
     o `name` must not begin with "SecDecInternal"

    '''
    if match(r'^[A-Z,a-z]+[A-Z,a-z,0-9]*$', name) is None:
        raise NameError('"%s" cannot be used as symbol' % name)
    if name.startswith('SecDecInternal'):
        raise NameError('Symbol names must not start with "SecDecInternal"')

def _convert_input(name, integration_variables, regulators,
                   requested_orders, polynomials_to_decompose, polynomial_names,
                   other_polynomials, prefactor, remainder_expression, functions,
                   real_parameters, complex_parameters, form_optimization_level,
                   form_work_space, form_insertion_depth, contour_deformation_polynomial,
                   decomposition_method):
    'Get the data types right.'

    # parse symbols
    integration_variables = sympify_symbols(list(integration_variables), 'All `integration_variables` must be symbols.')
    regulators = sympify_symbols(list(regulators), 'All `regulators` must be symbols.')
    polynomial_names = sympify_symbols(list(polynomial_names), 'All `polynomial_names` must be symbols.')
    real_parameters= sympify_symbols(list(real_parameters), 'All `real_parameters` must be symbols.')
    complex_parameters = sympify_symbols(list(complex_parameters), 'All `complex_parameters` must be symbols.')
    functions = list(functions); sympify_symbols(functions, 'All `functions` must be symbols.'); functions = set(str(f) for f in functions)
    if contour_deformation_polynomial is not None:
        contour_deformation_polynomial = sympify_symbols([contour_deformation_polynomial], '`contour_deformation_polynomial` must be a symbol.')[0]

    # check validity of symbol names and `name`
    for symbol in chain(integration_variables, regulators, polynomial_names, real_parameters, complex_parameters, functions,
                        [contour_deformation_polynomial] if contour_deformation_polynomial is not None else []):
        _validate( str(symbol) )

    # define the symbols of the different classes of `_Expression`s
    symbols_polynomials_to_decompose = integration_variables + regulators
    symbols_remainder_expression = integration_variables + regulators + polynomial_names
    all_symbols = symbols_other_polynomials = integration_variables + regulators + polynomial_names

    # check format of `requested_orders` --> must be 1d and have the length as `regulators`
    requested_orders = np.array(requested_orders)
    assert len(requested_orders.shape) == 1, '`requested_orders` has the wrong shape. (is %s; should be (%i,))' % (requested_orders.shape,len(regulators))
    assert requested_orders.shape[0] == len(regulators), 'The length of `requested_orders` (%i) must match the length of `regulators` (%i)' % (len(requested_orders),len(regulators))

    # parse expressions
    polynomials_to_decompose = _parse_expressions(polynomials_to_decompose, symbols_polynomials_to_decompose, ExponentiatedPolynomial, 'polynomials_to_decompose')
    other_polynomials = _parse_expressions(other_polynomials, symbols_other_polynomials, ExponentiatedPolynomial, 'other_polynomials')
    remainder_expression, function_calls = _parse_expressions([remainder_expression], symbols_remainder_expression, _Expression, 'remainder_expression')[0]

    # the exponents be polynomials in the regulators
    for poly in polynomials_to_decompose + other_polynomials:
        try:
            Polynomial.from_expression(poly.exponent, regulators)
        except Exception as error:
            error.args = tuple(['The exponents of the `polynomials_to_decompose` and the `other_polynomials` must be polynomials in the regulators. Error while checking: "%s"' % poly] + [arg for arg in error.args])
            raise
        exponent = Polynomial.from_expression(poly.exponent, integration_variables)
        assert (exponent.expolist == 0).all(), 'The exponents of the `polynomials_to_decompose` and the `other_polynomials` must not depend on the `integration_variables`. Error while checking: "%s"' % poly

    # convert ``prefactor`` to sympy expression
    prefactor = sp.sympify(prefactor)

    # convert ``requested_orders`` to numpy array
    requested_orders = np.array(requested_orders)

    # convert ``form_insertion_depth`` to integer and check nonnegativity
    assert form_insertion_depth == int(form_insertion_depth), '`form_insertion_depth` must be an integer.'
    assert form_insertion_depth >= 0, '`form_insertion_depth` must not be negative.'

    return (name, integration_variables, regulators,
            requested_orders, polynomials_to_decompose, polynomial_names,
            other_polynomials, prefactor, remainder_expression, functions, function_calls,
            real_parameters, complex_parameters, form_optimization_level,
            form_work_space, form_insertion_depth, contour_deformation_polynomial,
            decomposition_method, symbols_polynomials_to_decompose, symbols_other_polynomials,
            symbols_remainder_expression, all_symbols)


# ---------------------------------- decomposition ----------------------------------
_decomposition_strategies = dict(
                                    iterative=           dict(
                                                                 primary=decomposition.iterative.primary_decomposition,
                                                                 secondary=decomposition.iterative.iterative_decomposition
                                                             ),
                                    geometric=           dict(
                                                                 primary=lambda x: [decomposition.geometric.Cheng_Wu(x)],
                                                                 secondary=decomposition.geometric.geometric_decomposition # TODO: allow the user to set the path to normaliz
                                                             ),
                                    iterative_no_primary=dict(
                                                                 primary=lambda x: [x], # no primary decomposition
                                                                 secondary=decomposition.iterative.iterative_decomposition
                                                             )
                                )


# -------------------------------- template parsing ---------------------------------
def _parse_global_templates(name, regulators, polynomial_names,
                            real_parameters, complex_parameters, form_optimization_level,
                            form_work_space, form_insertion_depth, requested_orders,
                            contour_deformation_polynomial, sector_container_type):
    '''
    Create the `target_directory` (given by `name`) and return the two
    optional arguments passed to :func:`parse_template_tree`.

    '''
    # initialize template replacements
    template_replacements = dict(
                                     name = name,
                                     number_of_real_parameters = len(real_parameters),
                                     real_parameters = _make_FORM_list(real_parameters),
                                     names_of_real_parameters = _make_cpp_list(real_parameters),
                                     number_of_complex_parameters = len(complex_parameters),
                                     complex_parameters = _make_FORM_list(complex_parameters),
                                     names_of_complex_parameters = _make_cpp_list(complex_parameters),
                                     have_complex_parameters = len(complex_parameters) > 0,
                                     number_of_regulators = len(regulators),
                                     regulators = _make_FORM_list(regulators),
                                     names_of_regulators = _make_cpp_list(regulators),
                                     polynomial_names = _make_FORM_list(regulators),
                                     form_optimization_level = form_optimization_level,
                                     form_work_space = form_work_space,
                                     form_insertion_depth = form_insertion_depth,
                                     contour_deformation = int(contour_deformation_polynomial is not None),
                                     requested_orders = _make_FORM_list(requested_orders),
                                     sector_container_type = sector_container_type,
                                     pySecDec_version = version,
                                     python_version = sys.version,
                                     pySecDec_git_id = git_id,
                                     date_time = strftime("%a %d %b %Y %H:%M")
                                )

    # configure template parser
    file_renamings = {
                          # replace "name" by the name of the integral
                          'name' : name,

                          # the files below are specific for each sector --> do not parse globally
                          'contour_deformation.h' : None,
                          'sector.h' : None,

                          # "integrands.cpp", "name.hpp", "prefactor.cpp", and "functions.hpp" can only be written after the decomposition is completed
                          'integrands.cpp' : None,
                          'name.hpp' : None,
                          'prefactor.cpp' : None,
                          'functions.hpp' : None
                     }

    # the files below are only relevant for contour deformation --> do not parse if deactivated
    if contour_deformation_polynomial is None:
        for filename in ['contour_deformation.h','write_contour_deformation.frm', 'contour_deformation_functions.hpp']:
            file_renamings[filename] = None

    # get path to the directory with the template files (path relative to directory with this file: "./templates/")
    template_sources = os.path.join(os.path.split(os.path.abspath(__file__))[0],'templates')

    # initialize the target directory with the sector independent files
    parse_template_tree(template_sources, name, template_replacements, file_renamings)

    # return parser options
    return template_sources, template_replacements, file_renamings


# --------------------------------- write FORM code ---------------------------------
def _make_FORM_list(python_list):
    '''
    Convert a python list to a string to be used
    in FORM like a list.

    Example: ``['a', 'b', 'c'] --> 'a,b,c'``

    '''
    return ','.join(str(item) for item in python_list)

def _make_FORM_definition(name, expression):
    r'''
    Write the following line for the insertion
    in FORM:

    #define `name` "`expression`"

    Sample output:
    #define f " + (3)*y*z + (1)*x^2"

    '''
    return '#define %s "%s"\n' % \
    (
        name,
        str(expression).replace('**','^')
    )

def _make_FORM_function_definition(name, expression, args, limit):
    '''
    Split an `expression` whose string representation
    exceeds the `limit` of characters. Return a FORM
    procedure "defineReplacementExpression`name`"
    that defines `expression` as local expression
    named ``replacement``.

    :param name:
        string;
        The name of the expression. It is part of the
        name of the resulting FORM procedure
        "defineReplacementExpression`name`".

    :param expression:
        :class:`pySecDec.algebra._Expression`;
        The expression to be split.

    :param args:
        iterable of sympy symbols or None;
        The arguments of the function.

    :param limit:
        integer;
        The maximum number of characters in each
        subexpression.

    '''
    if args is None:
        FORM_args_left_hand_side = FORM_args_right_hand_side = ''
    else:
        FORM_args_left_hand_side = '(' + _make_FORM_list(str(arg)+'?' for arg in args) + ')'
        FORM_args_right_hand_side = '(' + _make_FORM_list(str(arg) for arg in args) + ')'
    codelines = []

    def recursion(name, expression):
        str_expression = str(expression)

        if len(str_expression) <= limit: # no need to split
            codelines.append( "  Id %s = %s;" % (name+FORM_args_left_hand_side,str_expression) )
            return

        if type(expression) == ProductRule:
            expression = expression.to_sum()

        if type(expression) == Sum:
            name_next_level = 'SecDecInternalfDUMMY'+name+'Part'
            codelines.append(
                "  Id %s = %s;" % (
                    name+FORM_args_left_hand_side,
                    '+'.join( name_next_level+str(i)+FORM_args_right_hand_side for i in range(len(expression.summands)) )
                )
            )
            for i,summand in enumerate(expression.summands):
                recursion(name_next_level+str(i), summand)
            return

        if type(expression) == Product:
            name_next_level = 'SecDecInternalfDUMMY'+name+'Part'
            codelines.append(
                "  Id %s = %s;" % (
                    name+FORM_args_left_hand_side,
                    '*'.join( name_next_level+str(i)+FORM_args_right_hand_side for i in range(len(expression.factors)) )
                )
            )
            for i,factor in enumerate(expression.factors):
                recursion(name_next_level+str(i), factor)
            return

        # rescue: print warning and write unsplit expression
        print( 'WARNING: Could not split "%s" (not implemented for %s)' % (name,type(expression)) )
        codelines.append( "  Id %s = %s;" % (name+FORM_args_left_hand_side,str_expression) )
        return

    recursion(name, expression)
    codelines.append('') # empty line
    return "\n".join(codelines)

def _make_FORM_shifted_orders(positive_powers):
    r'''
    Write FORM code that defines the preprocessor
    variables
    `shiftedRegulator`regulatorIndex'PowerOrder`shiftedOrderIndex''.

    '''
    codelines = []
    orders_index = 0
    for multiindex in positive_powers:
        orders_index += 1
        regulator_index = 0
        for regulator_power in multiindex:
            regulator_index += 1
            codelines.append( '#define shiftedRegulator%iPowerOrder%i "%i"' % (regulator_index,orders_index,regulator_power) )
    return '\n'.join(codelines)

def _derivative_muliindex_to_name(basename, multiindex):
    '''
    Convert a derivative multiindex as returned by
    :meth:`pySecDec.algebra.DerivativeTracker.compute_derivatives`
    to the form ``d...d<basename>d<index>...d<index>``.

    Example:

    >>> _derivative_muliindex_to_name('f', (1,2,1))
    ddddfd0d1d1d2

    '''
    prefix = 'd' * sum(multiindex)
    suffix = ''.join(('d' + str(i)) * depth for i,depth in enumerate(multiindex))
    return prefix + basename + suffix

# define the internal names to be used in FORM
internal_prefix = 'SecDecInternal'
FORM_names = dict(
    cal_I=internal_prefix+'CalI',
    cast_polynomial=internal_prefix+'PolynomialToDecompose',
    other_polynomial=internal_prefix+'OtherPolynomial',
    remainder_expression=internal_prefix+'RemainderExpression',
    contourdef_transform=internal_prefix+'ContourdefDeformation',
    contourdef_Jacobian=internal_prefix+'ContourdefJacobian',
    deformed_variable=internal_prefix+'Deformed',
    deformation_parameter_i=internal_prefix+'Lambda%i',
    end_point_parameter=internal_prefix+'Mu',
    additional_deformation_factor=internal_prefix+'AdditionalDeformationFactor',
    ExpMinusMuOverX=internal_prefix+'ExpMinusMuOverX',
    XExpMinusMuOverX=internal_prefix+'XExpMinusMuOverX',
    label_contour_deformation_transform=internal_prefix+'LabelTransformation',
    label_contour_deformation_Jacobian_matrix_index_i=internal_prefix+'LabelJacobianMatrixI',
    label_contour_deformation_Jacobian_matrix_index_j=internal_prefix+'LabelJacobianMatrixJ'
)

def _make_FORM_Series_initilization(min_orders, max_orders, sector_ID, contour_deformation):
    '''
    Write the c++ code that initilizes the container class
    (``Series<Series<...<Series<IntegrandContainer>>...>``).

    '''
    assert len(min_orders) == len(max_orders)
    last_regulator_index = len(min_orders) - 1

    def multiindex_to_cpp_order(multiindex):
        '(-1,3,2,-4) --> n1_3_2_n4'
        snippets = []
        for order in multiindex:
            snippets.append(str(order).replace('-','n'))
        return '_'.join(snippets)

    current_orders = np.array(min_orders) # use as nonlocal variable in `recursion`
    def recursion(regulator_index):
        if regulator_index < last_regulator_index:
            outstr_body_snippets = []
            outstr_head = '{%i,%i,{' % (min_orders[regulator_index],max_orders[regulator_index])
            for this_regulator_order in range(min_orders[regulator_index],max_orders[regulator_index]+1):
                current_orders[regulator_index] = this_regulator_order
                outstr_body_snippets.append( recursion(regulator_index + 1) )
            outstr_tail = '},true}'
            return ''.join( (outstr_head, ','.join(outstr_body_snippets), outstr_tail) )
        else: # regulator_index == last_regulator_index; i.e. processing last regulator
            outstr_head = '{%i,%i,{{' % (min_orders[regulator_index],max_orders[regulator_index])
            outstr_body_snippets = []
            for this_regulator_order in range(min_orders[regulator_index],max_orders[regulator_index]+1):
                current_orders[regulator_index] = this_regulator_order
                if contour_deformation:
                    outstr_body_snippets.append(
                        '''%(sector_ID)i,sector_%(sector_ID)i_order_%(cpp_order)s_numIV,sector_%(sector_ID)i_order_%(cpp_order)s_integrand,
                           sector_%(sector_ID)i_order_%(cpp_order)s_contour_deformation_polynomial,
                           sector_%(sector_ID)i_order_%(cpp_order)s_maximal_allowed_deformation_parameters''' \
                        % dict(sector_ID=sector_ID,cpp_order=multiindex_to_cpp_order(current_orders))
                    )
                else:
                    outstr_body_snippets.append(
                        '%(sector_ID)i,sector_%(sector_ID)i_order_%(cpp_order)s_numIV,sector_%(sector_ID)i_order_%(cpp_order)s_integrand' \
                        % dict(sector_ID=sector_ID,cpp_order=multiindex_to_cpp_order(current_orders))
                    )
            outstr_tail = '}},true}'
            return ''.join( (outstr_head, '},{'.join(outstr_body_snippets), outstr_tail) )

    return recursion(0)


# ---------------------------------- write c++ code ---------------------------------
def _make_cpp_list(python_list):
    '''
    Convert a python list to a string to be used
    in c++ initializer list for a vector.

    Example: ``['a', 'b', 'c'] --> '"a","b","c"'``

    '''
    return '"' + '","'.join(str(item) for item in python_list) + '"'

def _make_prefactor_function(expanded_prefactor, real_parameters, complex_parameters):
    regulators = expanded_prefactor.polysymbols
    last_regulator_index = len(regulators) - 1

    def recursion(regulator_index,expression):
        orders = expression.expolist[:,regulator_index]
        min_order = orders.min()
        max_order = orders.max()
        if regulator_index < last_regulator_index:
            outstr_body_snippets = []
            outstr_head = '{%i,%i,{' % (min_order,max_order)
            for coeff in expression.coeffs:
                outstr_body_snippets.append( recursion(regulator_index + 1, coeff) )
            outstr_tail = '},true}' if expression.truncated else '},false}'
            return ''.join( (outstr_head, ','.join(outstr_body_snippets), outstr_tail) )
        else: # regulator_index == last_regulator_index; i.e. processing last regulator
            outstr_head = '{%i,%i,{{' % (min_order,max_order)
            outstr_body_snippets = []
            for coeff in expression.coeffs:
                outstr_body_snippets.append( str(coeff.evalf(20)) )
            outstr_tail = '}},true}' if expression.truncated else '}},false}'
            return ''.join( (outstr_head, '},{'.join(outstr_body_snippets), outstr_tail) )

    parameter_definitions = []
    parameter_undefs = []
    for real_or_complex in ('real','complex'):
        for i,p in enumerate(eval(real_or_complex+'_parameters')):
            parameter_definitions.append('#define %s %s_parameters.at(%i)' % (p,real_or_complex,i))
            parameter_undefs.append('#undef %s' % p)
    parameter_definitions = '\n'.join(parameter_definitions)
    parameter_undefs = '\n'.join(parameter_undefs)

    code = parameter_definitions + '\nreturn ' + recursion(0,expanded_prefactor) + ';\n' + parameter_undefs
    return code.replace('\n', '\n        ')

def _make_CXX_function_declaration(function_name, number_of_arguments):
    '''
    Write the declaration of a c++ function with
    name `function_name` and `number_of_arguments`
    arguments. The function's return type is set
    to "integrand_return_t". The argument types
    are templated.

    '''
    if number_of_arguments == 0:
        return '    integrand_return_t ' + function_name + '();\n'

    template_arguments = ', '.join('typename T%i' % i for i in range(number_of_arguments))
    arguments = ', '.join('T%i arg%i' % (i,i) for i in range(number_of_arguments))
    return '    template<' + template_arguments + '>\n    integrand_return_t ' + function_name + '(' + arguments + ');\n'


# --------------------------------- algebra helper ---------------------------------
class NoDerivativeAtZeroFunction(Function):
    '''
    Symbolic function with the additional property
    that the function and all derivatives vanish at zero.

    '''
    def __init__(self, symbol, *arguments, **kwargs):
        super(NoDerivativeAtZeroFunction, self).__init__(symbol, *arguments, **kwargs)

    def replace(expression, index, value, remove=False):
        if value == 0:
            return Polynomial(np.zeros([1,expression.number_of_variables], dtype=int), np.array([0]), expression.symbols, copy=False)
        else:
            return super(NoDerivativeAtZeroFunction, expression).replace(index, value, remove)

    def simplify(self):
        super(NoDerivativeAtZeroFunction, self).simplify()
        for i,arg in enumerate(self.arguments):
            if type(arg) is Polynomial and len(arg.coeffs) == 1 and arg.coeffs[0] == 1 and (arg.expolist == 0).all():
                return Polynomial(np.zeros([1,len(arg.polysymbols)], dtype=int), np.array([0]), arg.polysymbols, copy=False)
        return self

class RealPartFunction(Function):
    '''
    Symbolic function that takes exactly one argument
    and with the additional property that the
    derivative commutes to the inside.

    '''
    def __init__(self, symbol, *arguments, **kwargs):
        assert len(arguments) == 1, 'A `RealPartFunction` takes exactly one argument'
        super(RealPartFunction, self).__init__(symbol, *arguments, **kwargs)

    def derive(self, index):
        return RealPartFunction(self.symbol, self.arguments[0].derive(index), copy=False)


# ---------------------------------- main function ----------------------------------
def make_package(name, integration_variables, regulators, requested_orders,
                 polynomials_to_decompose, polynomial_names=[], other_polynomials=[],
                 prefactor=1, remainder_expression=1, functions=[], real_parameters=[],
                 complex_parameters=[], form_optimization_level=2, form_work_space='500M',
                 form_insertion_depth=5, contour_deformation_polynomial=None,
                 decomposition_method='iterative_no_primary'):
    r'''
    Decompose, subtract and expand an expression.
    Return it as c++ package.

    .. seealso::
        In order to decompose a loop integral,
        use the function
        :func:`pySecDec.loop_integral.loop_package`.

    :param name:
        string;
        The name of the c++ namepace and the output
        directory.

    :param integration_variables:
        iterable of strings or sympy symbols;
        The variables that are to be integrated from
        0 to 1.

    :param regulators:
        iterable of strings or sympy symbols;
        The UV/IR regulators of the integral.

    :param requested_orders:
        iterable of integers;
        Compute the expansion in the regulators to these
        orders.

    :param polynomials_to_decompose:
        iterable of strings or sympy expressions or
        :class:`pySecDec.algebra.ExponentiatedPolynomial`
        or :class:`pySecDec.algebra.Polynomial`;
        The polynomials to be decomposed.

    :param polynomial_names:
        iterable of strings;
        Assign symbols for the `polynomials_to_decompose`.
        These can be referenced in the `other_polynomials`;
        see `other_polynomials` for details.

    :param other_polynomials:
        iterable of strings or sympy expressions or
        :class:`pySecDec.algebra.ExponentiatedPolynomial`
        or :class:`pySecDec.algebra.Polynomial`;
        Additional polynomials where no decomposition is
        attempted.
        The symbols defined in `polynomial_names`
        can be used to reference the
        `polynomials_to_decompose`. This is particularly
        useful when computing loop integrals where the
        "numerator" can depend on the first and second
        Symanzik polynomials.

        Example (1-loop bubble with numerator):

        >>> polynomials_to_decompose = ["(x0 + x1)**(2*eps - 4)",
        ...                             "(-p**2*x0*x1)**(-eps))"]
        >>> polynomial_names = ["U", "F"]
        >>> other_polynomials = ["""   (eps - 1)*s*U**2
        ...                          + (eps - 2)*F
        ...                          - (eps - 1)*2*s*x0*U
        ...                          + (eps - 1)*s*x0**2"""]

        .. seealso::
            :mod:`pySecDec.loop_integral`

        Note that the `polynomial_names` refer to the
        `polynomials_to_decompose` **without** their
        exponents.

    :param prefactor:
        string or sympy expression,
        optional;
        A factor that does not depend on the integration
        variables.

    :param remainder_expression:
        string or sympy expression or
        :class:`pySecDec.algebra._Expression`, optional;
        An additional factor.

        Dummy function must be provided with all arguments,
        e.g. ``remainder_expression='exp(eps)*f(x0,x1)'``.
        In addition, all dummy function must be listed
        in `functions`.

        The `polynomial_names` can be used like in
        `other_polynomials`. In particular, they go
        **without** arguments, e.g.
        ``remainder_expression='exp(g(U,F))'``.

    :param functions:
        iterable of strings or sympy symbols, optional;
        Function symbols occuring in `remainder_expression`,
        e.g.``['f']``.

        .. note::
            The power function `pow` and the logarithm
            `log` are already defined by default. The
            `log` uses the nonstandard continuation
            from a negative imaginary part on the negative
            real axis (e.g. ``log(-1) = -i*pi``).

    :param real_parameters:
        iterable of strings or sympy symbols, optional;
        Symbols to be interpreted as real variables.

    :param complex_parameters:
        iterable of strings or sympy symbols, optional;
        Symbols to be interpreted as complex variables.

    :param form_optimization_level:
        integer out of the interval [0,3], optional;
        The optimization level to be used in FORM.
        Default: ``2``.

    :param form_work_space:
        string, optional;
        The FORM WorkSpace. Default: ``'500M'``.

    :param form_insertion_depth:
        nonnegative integer, optional;
        How deep FORM should try to resolve nested function
        calls. Default: ``5``.

    :param contour_deformation_polynomial:
        string or sympy symbol, optional;
        The name of the polynomial in `polynomial_names`
        that is to be continued to the complex plane
        according to a :math:`- i\delta` prescription.
        For loop integrals, this is the second Symanzik
        polynomial ``F``.
        If not provided, no code for contour deformation
        is created.

    :param decomposition_method:
        string, optional;
        The strategy to decompose the polynomials. The
        following strategies are available:

        * 'iterative_no_primary' (default)
        * 'iterative'
        * 'geometric'

        'iterative' and 'geometric' are only valid for
        loop integrals. An end user should always use
        the default 'iterative_no_primary' here.
        In order to compute loop integrals, please use the
        function :func:`pySecDec.loop_integral.loop_package`.

    '''
    # convert input data types to the data types we need
    name, integration_variables, regulators, \
    requested_orders, polynomials_to_decompose, polynomial_names, \
    other_polynomials, prefactor, remainder_expression, functions, \
    function_calls, real_parameters, complex_parameters, \
    form_optimization_level, form_work_space, form_insertion_depth, \
    contour_deformation_polynomial, decomposition_method, \
    symbols_polynomials_to_decompose, symbols_other_polynomials, \
    symbols_remainder_expression, all_symbols = \
    _convert_input(name, integration_variables, regulators,
                   requested_orders, polynomials_to_decompose, polynomial_names,
                   other_polynomials, prefactor, remainder_expression, functions,
                   real_parameters, complex_parameters, form_optimization_level,
                   form_work_space, form_insertion_depth, contour_deformation_polynomial,
                   decomposition_method)

    # construct the c++ type of the integrand container class
    # for two regulators, the resulting code should read:
    # "secdecutil::Series<secdecutil::Series<SectorContainerWith[out]Deformation>>"
    if contour_deformation_polynomial is None:
        sector_container_type = 'secdecutil::Series<' * len(regulators) + 'secdecutil::SectorContainerWithoutDeformation<real_t,complex_t,integrand_return_t>' + '>' * len(regulators)
    else:
        sector_container_type = 'secdecutil::Series<' * len(regulators) + 'secdecutil::SectorContainerWithDeformation<real_t,complex_t>' + '>' * len(regulators)

    # configure the template parser and parse global files
    template_sources, template_replacements, file_renamings = \
        _parse_global_templates(
        name, regulators, polynomial_names,
        real_parameters, complex_parameters, form_optimization_level,
        form_work_space, form_insertion_depth, requested_orders,
        contour_deformation_polynomial, sector_container_type
    )

    # get the highest poles from the ``prefactor``
    highest_prefactor_pole_orders = -np.array([lowest_order(prefactor, regulator) for regulator in regulators])

    # compute the required expansion order accounting for the prefactor
    required_orders = requested_orders + highest_prefactor_pole_orders

    # get the decomposition routines
    strategy = _decomposition_strategies[decomposition_method]

    # define the `Polynomial` "x0 + x1 + x2 + ..." to keep track of the transformations
    transformations = Polynomial(np.identity(len(integration_variables), dtype=int), [1]*len(integration_variables), integration_variables)

    # make a copy of the `integration_variables` for later reference
    all_integration_variables = list(integration_variables)

    # intialize the c++ declarations of the `functions`
    function_declarations = set()

    # print message how to implement the dummy functions if applicable
    if functions:
        print(
                 "Declarations of the `functions` and their required derivatives are provided\n" + \
                 "in the file 'src/functions.hpp'. Please refer to that file for further\n" + \
                 "instructions."
             )

    # hide ``regulators`` and ``polynomial_names`` from decomposition
    polynomials_to_decompose_hidden_regulators = []
    polynomials_to_decompose_hide_containers = []
    for poly in polynomials_to_decompose:
        poly, hidden = decomposition.hide(poly, len(regulators))
        polynomials_to_decompose_hidden_regulators.append(poly)
        polynomials_to_decompose_hide_containers.append(hidden)
    other_polynomials_hidden_regulators_and_names = []
    other_polynomials_name_hide_containers = []
    other_polynomials_regulator_hide_containers = []
    for poly in other_polynomials:
        poly, hidden = decomposition.hide(poly, len(polynomial_names))
        other_polynomials_name_hide_containers.append(hidden)
        poly, hidden = decomposition.hide(poly, len(regulators))
        other_polynomials_regulator_hide_containers.append(hidden)
        other_polynomials_hidden_regulators_and_names.append(poly)

    # initialize the decomposition
    initial_sector = decomposition.Sector(polynomials_to_decompose_hidden_regulators, other_polynomials_hidden_regulators_and_names + [transformations])

    # initialize the counter
    sector_index = 0

    # initialize the global lowest orders
    lowest_orders = requested_orders.copy()

    # define the imaginary unit
    imaginary_unit = sp.sympify('I')

    # we must backwards traverse the `polynomial_names` --> create the reversed list once and for all
    reversed_polynomial_names = list(polynomial_names) # copy
    reversed_polynomial_names.reverse()

    if contour_deformation_polynomial is not None:
        # get the index of the `contour_deformation_polynomial` in `polynomial_names`
        str_contour_deformation_polynomial = str(contour_deformation_polynomial)
        contour_deformation_polynomial_index = 0
        while str(polynomial_names[contour_deformation_polynomial_index]) != str_contour_deformation_polynomial:
            contour_deformation_polynomial_index += 1
            if len(polynomial_names) <= contour_deformation_polynomial_index:
                raise IndexError('Could not find the `contour_deformation_polynomial` "%s" in `polynomial_names`.' % str_contour_deformation_polynomial)

        # define labels for simultaneous optimization in FORM
        FORM_label_contour_deformation_transform = sp.sympify(FORM_names['label_contour_deformation_transform'])
        FORM_label_contour_deformation_Jacobian_matrix_index_i = sp.sympify(FORM_names['label_contour_deformation_Jacobian_matrix_index_i'])
        FORM_label_contour_deformation_Jacobian_matrix_index_j = sp.sympify(FORM_names['label_contour_deformation_Jacobian_matrix_index_j'])

    def parse_exponents_and_coeffs(sector, symbols_polynomials_to_decompose, symbols_other_polynomials, include_last_other):
        #  - in ``sector.cast``
        for product in sector.cast:
            mono, poly = product.factors
            mono.exponent = Polynomial.from_expression(mono.exponent, symbols_polynomials_to_decompose)
            poly.exponent = Polynomial.from_expression(poly.exponent, symbols_polynomials_to_decompose)
            mono.coeffs = np.array([Expression(coeff, symbols_polynomials_to_decompose) for coeff in mono.coeffs])
            poly.coeffs = np.array([Expression(coeff, symbols_polynomials_to_decompose) for coeff in poly.coeffs])

        #  - in ``sector.other``
        for poly in sector.other if include_last_other else sector.other[:-1]: # [:-1] due to the `transformations`
            poly.exponent = Polynomial.from_expression(poly.exponent, symbols_other_polynomials)
            poly.coeffs = np.array([Expression(coeff, symbols_polynomials_to_decompose) for coeff in poly.coeffs])

    # investigate if we can take advantage of sector symmetries
    # We can simplify due to symmetries if the `remainder_expression`
    # does explicitly not depend on any integration variable (implicit
    # dependence via `polynomial_names` is OK).
    use_symmetries = True
    for i,_ in enumerate(integration_variables):
        derivative = remainder_expression.derive(i).simplify()
        if not ( type(derivative) is Polynomial and np.array_equal(derivative.coeffs, [0]) and (derivative.expolist == 0).all() ):
            use_symmetries = False
            break
    remainder_expression_is_trivial = use_symmetries

    # Check that either the primary decomposition or the `remainder_expression` is trivial.
    # Note that the primary decomposition is specialized for loop integrals.
    if not remainder_expression_is_trivial and decomposition_method != 'iterative_no_primary':
        raise NotImplementedError('The primary decomposition is only implemented for loop integrals. Please perform the primary decomposition yourself and choose ``decomposition_method="iterative_no_primary"``.')

    if use_symmetries:
        # can investigate sector symmetries
        # we do not need `transformations` in that case --> remove from `initial_sector`
        initial_sector.other.pop()

        # run primary decomposition and squash symmetry-equal sectors (using both implemented strategies)
        primary_sectors = strategy['primary'](initial_sector)
        primary_sectors = decomposition.squash_symmetry_redundant_sectors(primary_sectors, iterative_sort)
        primary_sectors = decomposition.squash_symmetry_redundant_sectors(primary_sectors, Pak_sort)

        # rename the `integration_variables` in all `primary_sectors` --> must have the same names in all primary sectors
        symbols_primary_sectors = primary_sectors[0].Jacobian.polysymbols
        for sector in primary_sectors:
            sector.Jacobian.polysymbols = list(symbols_primary_sectors) # copy
            for prod in sector.cast:
                for factor in prod.factors:
                    factor.polysymbols = list(symbols_primary_sectors) # copy
            for poly in sector.other:
                poly.polysymbols = list(symbols_primary_sectors) # copy

        # give one primary sector as representative for the global initialization
        primary_sectors_to_consider = [primary_sectors[0]]

    else: # if we cannot take advantage of symmetries
        primary_sectors_to_consider = strategy['primary'](initial_sector)

    for primary_sector in primary_sectors_to_consider:

        # primary decomposition removes one integration parameter --> redefine `integration_variables` and the symbols of the different classes of `_Expression`s
        integration_variables = list(primary_sector.Jacobian.polysymbols) # make a copy
        symbols_polynomials_to_decompose = symbols_other_polynomials = integration_variables + regulators
        symbols_remainder_expression = integration_variables + regulators + polynomial_names
        all_symbols = integration_variables + regulators + polynomial_names

        # define `integration_variables` in the template system
        template_replacements['number_of_integration_variables'] = len(integration_variables)
        template_replacements['integration_variables'] = _make_FORM_list(integration_variables)

        # get the indices of the `integration_variables`, the `regulators`, and the `polynomial_names` in the polysymbols
        integration_variable_indices = list(range(len(integration_variables)))
        regulator_indices = [i + len(integration_variables) for i in range(len(regulators))]

        # define "elementary" `_Expression`s such as ``x = Polynomial.from_expression('x', polysymbols)`` for all x
        elementary_monomials = []
        for i, symbol in enumerate(symbols_polynomials_to_decompose):
            expolist = np.zeros([1,len(symbols_polynomials_to_decompose)], dtype=int)
            expolist[:,i] = 1
            elementary_monomials.append( Polynomial(expolist, np.array([1]), symbols_polynomials_to_decompose, copy=False) )

        if contour_deformation_polynomial is not None:
            symbolic_deformed_variable_names = [FORM_names['deformed_variable'] + str(original_varname) for original_varname in integration_variables]

            # Need all first and second derivatives of the `contour_deformation_polynomial`.
            # Since the `contour_deformation_polynomial` is left symbolic they are equal for every subsector after primary decomposition.
            symbolic_contour_deformation_polynomial = Function(str_contour_deformation_polynomial, *elementary_monomials)
            symbolic_contour_deformation_polynomial = DerivativeTracker(symbolic_contour_deformation_polynomial)

            # compute the deformation of the integration parameters and its Jacobian matrix (see e.g. section 3.2 in arXiv:1601.03982):
            # ``z_k({x_k}) = x_k - i * lambda_k * x_k*exp(-mu/x_k) * (1-x_k)exp(-mu/(1-x_k)) * Re(dF_dx_k)``, where "dF_dx_k" denotes the derivative of ``F`` by ``x_k``
            # Remark: The determinant of the Jacobian matrix is calculated numerically.
            deformation_parameters = [sp.symbols(FORM_names['deformation_parameter_i'] % i) for i in range(len(integration_variables))]
            end_point_parameter = Polynomial(np.zeros([1,len(symbols_polynomials_to_decompose)]), np.array([sp.symbols(FORM_names['end_point_parameter'])]), symbols_polynomials_to_decompose, copy=False)
            deformed_integration_parameters = [
                                                     Sum(
                                                         elementary_monomials[k],
                                                         Product(
                                                            -imaginary_unit * deformation_parameters[k] * \
                                                            NoDerivativeAtZeroFunction(FORM_names['XExpMinusMuOverX'], end_point_parameter, elementary_monomials[k]),
                                                            NoDerivativeAtZeroFunction(FORM_names['XExpMinusMuOverX'], end_point_parameter, (1 - elementary_monomials[k])),
                                                            RealPartFunction('SecDecInternalRealPart', symbolic_contour_deformation_polynomial.derive(k), copy=False),
                                                         copy=False),
                                                     copy=False)
                                                     for k in range(len(integration_variables))
                                              ]

            # define the `symbolic_deformed_variables` to be inserted FORM
            symbolic_deformed_variables = [ Function(deformed_name, *elementary_monomials[:len(integration_variables)]) for deformed_name in symbolic_deformed_variable_names ]
            symbolic_deformed_variables.extend( (regulator for regulator in elementary_monomials[len(integration_variables):]) )

            contourdef_Jacobian = np.empty((len(integration_variables), len(integration_variables)), dtype=object)
            for i in range(len(integration_variables)):
                for j in range(len(integration_variables)):
                    contourdef_Jacobian[i,j] = deformed_integration_parameters[i].simplify().derive(j)

            # define the FORM procedure that inserts the deformed integration variables
            insert_deformed_integration_variables_procedure = ''.join(
                _make_FORM_function_definition(
                    'SecDecInternalDeformed' + str(integration_variable), deformed_integration_parameters[idx], integration_variables, limit=10**6
                ).replace('**','^')
                for idx,integration_variable in enumerate(integration_variables)
            )

            # define a procedure that defines the Jacobian matrix as labelled global expression in FORM
            contourdef_Jacobian_expression = Sum(
                                                   *(
                                                        FORM_label_contour_deformation_Jacobian_matrix_index_i ** (i + 1) * \
                                                        FORM_label_contour_deformation_Jacobian_matrix_index_j ** (j + 1) * \
                                                        contourdef_Jacobian[i,j]
                                                        for i in range(len(integration_variables))
                                                        for j in range(len(integration_variables))
                                                    ),
                                                    copy = False
                                                )
            insert_contourdef_Jacobian_procedure = ''.join(
                _make_FORM_function_definition('SecDecInternalContourdefJacobian', contourdef_Jacobian_expression, args=integration_variables, limit=10**6)
            )

        # insert the `polynomials_to_decompose` as dummy functions into `other_polynomials` and `remainder_expression`
        # we want to remove them from the symbols --> traverse backwards and pop the last of the `polysymbols`
        # redefine ``all_symbols`` and ``symbols_remainder_expression``
        all_symbols = symbols_remainder_expression = integration_variables + regulators
        this_primary_sector_remainder_expression = remainder_expression
        for i in range(len(other_polynomials)):
            poly = primary_sector.other[i]
            decomposition.unhide(poly, other_polynomials_name_hide_containers[i])
            for poly_name in reversed_polynomial_names:
                poly = poly.replace(-1, poly_name(*all_symbols), remove=True)
            primary_sector.other[i] = poly
        for poly_name in reversed_polynomial_names:
            this_primary_sector_remainder_expression = this_primary_sector_remainder_expression.replace(-1, poly_name(*all_symbols), remove=True)

        # If there is a nontrivial primary decomposition, remove the integration variable also from the `remainder_expression`
        for i,var in enumerate(all_integration_variables):
            if var not in integration_variables:
                this_primary_sector_remainder_expression = this_primary_sector_remainder_expression.replace(i,1,remove=True)
                break

        # we later need ``1`` packed into specific types
        polynomial_one = Polynomial(np.zeros([1,len(all_symbols)], dtype=int), np.array([1]), all_symbols, copy=False)
        pole_part_initializer = Pow(polynomial_one, -polynomial_one)

        # define symbols for the `polynomials_to_decompose` and the `other_polynomials --> shorter expressions and faster in python
        symbolic_other_polynomials = [
                                         Pow(
                                             Function(FORM_names['other_polynomial'] + str(i), *(elementary_monomials if contour_deformation_polynomial is None else symbolic_deformed_variables)),
                                             Expression(primary_sector.other[i].exponent, symbols_polynomials_to_decompose),
                                             copy = False
                                         )
                                         for i in range(len(other_polynomials))
                                     ]
        names_other_polynomials = [FORM_names['other_polynomial'] + str(i) for i in range(len(other_polynomials))]
        symbolic_polynomials_to_decompose = []
        names_polynomials_to_decompose = []
        for i in range(len(polynomials_to_decompose)):
            try:
                poly_name = str(polynomial_names[i])
            except IndexError:
                poly_name = FORM_names['cast_polynomial'] + str(i)
            symbolic_polynomials_to_decompose.append(
                Pow(
                    Function(poly_name, *(elementary_monomials if contour_deformation_polynomial is None else symbolic_deformed_variables)),
                    Expression(primary_sector.cast[i].factors[1].exponent, symbols_polynomials_to_decompose),
                    copy = False
                )
            )
            names_polynomials_to_decompose.append(poly_name)

        if use_symmetries:
            # search for symmetries throughout the secondary decomposition
            secondary_sectors = []
            for primary_sector in primary_sectors:
                secondary_sectors.extend( strategy['secondary'](primary_sector) )
            # find symmetries using both implemented strategies
            secondary_sectors = decomposition.squash_symmetry_redundant_sectors(secondary_sectors, iterative_sort)
            secondary_sectors = decomposition.squash_symmetry_redundant_sectors(secondary_sectors, Pak_sort)
        else:
            parse_exponents_and_coeffs(primary_sector, symbols_polynomials_to_decompose, symbols_other_polynomials, use_symmetries)
            secondary_sectors = strategy['secondary'](primary_sector)

        for sector in secondary_sectors:
            sector_index += 1

            if use_symmetries:
                # If we use symmetries, we still have to parse the `exponents` and `coeffs`.
                parse_exponents_and_coeffs(sector, symbols_polynomials_to_decompose, symbols_other_polynomials, use_symmetries)
            else:
                # If we do not use symmetries, we have to take care of `transformations`
                # extract ``this_transformation``
                this_transformation = sector.other.pop() # remove transformation from ``sector.other``

            # unhide the regulator
            #  - in the Jacobian
            Jacobian = sector.Jacobian
            Jacobian.number_of_variables += len(regulators)
            Jacobian.polysymbols += regulators
            Jacobian.expolist = np.hstack([Jacobian.expolist, np.zeros([len(Jacobian.coeffs),len(regulators)], dtype=int)])

            #  - in ``sector.cast``
            for product,hidden_regulators in zip(sector.cast,polynomials_to_decompose_hide_containers):
                mono, poly = product.factors
                mono.number_of_variables += len(regulators)
                mono.polysymbols += regulators
                mono.expolist = np.hstack([mono.expolist, np.zeros([1,len(regulators)], dtype=int)])
                decomposition.unhide(poly, hidden_regulators)

            #  - in ``sector.other``
            for poly, hide_container in zip(sector.other, other_polynomials_regulator_hide_containers):
                hide_container.coeffs = poly.coeffs # coeffs had been hidden in `other_polynomials_name_hide_containers` --> do not overwrite
                decomposition.unhide(poly, hide_container)


            # insert the monomials of the `polynomial_names` into ``sector.other`` ``<symbol> --> xi**pow_i * <symbol>``
            # ``[:,:-len(regulators)]`` is the part of the expolist that contains only the powers of the `integration_variables` but not of the `regulators`;
            #     i.e. it excludes the powers of the regulators from the modification
            for poly, hidden_name in zip(sector.other, other_polynomials_name_hide_containers):
                for i,(polyname,prod) in enumerate(zip(polynomial_names,sector.cast)):
                    mono,_ = prod.factors
                    poly.expolist[:,:-len(regulators)] += np.einsum('i,k->ik', hidden_name.expolist[:,i], mono.expolist[0,:-len(regulators)])

            # factorize polynomials in ``sector.other``
            for i,to_factorize in enumerate(sector.other):
                to_factorize = sector.other[i] = Product(ExponentiatedPolynomial(np.zeros([1,len(all_symbols)], dtype=int), np.array([1]), to_factorize.exponent.copy(), all_symbols, copy=False), to_factorize)
                decomposition.refactorize(to_factorize)

            # subtraction needs type `ExponentiatedPolynomial` for all factors in its monomial part
            Jacobian = ExponentiatedPolynomial(Jacobian.expolist, Jacobian.coeffs, polysymbols=Jacobian.polysymbols, exponent=polynomial_one, copy=False)

            if use_symmetries:
                # `remainder_expression` does not depend on the integration variables in that case --> nothing to transform here
                symbolic_remainder_expression = this_primary_sector_remainder_expression
            else:
                # Apply ``this_transformation`` and the contour deformaion (if applicable) to
                # the `remainder_expression` BEFORE taking derivatives.
                # Introduce a symbol for the `remainder_expression` and insert in FORM.
                symbolic_remainder_expression_arguments = []
                for expovec, coeff in zip(this_transformation.expolist, this_transformation.coeffs):
                    expovec = np.hstack([expovec, [0]*len(regulators)])
                    symbolic_remainder_expression_arguments.append( Polynomial([expovec], [coeff], symbols_other_polynomials) )
                symbolic_remainder_expression_arguments += elementary_monomials[-len(regulators):]
                symbolic_remainder_expression = Function(FORM_names['remainder_expression'], *symbolic_remainder_expression_arguments)

            # initialize the product of monomials for the subtraction
            monomial_factors = list(chain([Jacobian], (prod.factors[0] for prod in sector.cast), (prod.factors[0] for prod in sector.other)))
            monomials = Product(*monomial_factors, copy=False)

            if contour_deformation_polynomial is not None:
                # Apply the deformation ``z_k({x_k}) = x_k - i * lambda_k * x_k*exp(-mu/x_k) * (1-x_k)exp(-mu/(1-x_k)) * Re(dF_dx_k)`` to the monomials.
                # Split as ``z_k({x_k}) = monomials[k] * <something in remainder_expression>``
                # where ``monomials[k] = x_k``; i.e. unchanged
                # and where ``<something in remainder_expression> = 1 - i * lambda_k * exp(-mu/x_k) * (1-x_k)exp(-mu/(1-x_k)) * Re(dF_dx_k)``.
                # That amounts to multiplying ``<something in remainder_expression> ** <exponent_of_monomial>`` to `remainder_expression`
                additional_deformation_factors = []
                monomial_powers = np.zeros(len(integration_variables), dtype=object)
                for factor in monomial_factors:
                    for k,exponent in enumerate(factor.expolist[0,:len(integration_variables)]):
                        monomial_powers[k] += factor.exponent*exponent
                for k,power in enumerate(monomial_powers):
                    additional_deformation_factors.append \
                    (
                        Pow(
                               Sum(
                                      polynomial_one,
                                      Product(
                                                 -imaginary_unit * deformation_parameters[k] * \
                                                 NoDerivativeAtZeroFunction(FORM_names['ExpMinusMuOverX'], end_point_parameter, elementary_monomials[k]),
                                                 NoDerivativeAtZeroFunction(FORM_names['XExpMinusMuOverX'], end_point_parameter, (1 - elementary_monomials[k])),
                                                 RealPartFunction('SecDecInternalRealPart', symbolic_contour_deformation_polynomial.derive(k), copy=False),
                                                 copy=False
                                             ),
                                  copy=False
                                  ),
                              power, copy=False
                           )
                    )
                additional_deformation_factor = Product(*additional_deformation_factors, copy=False)
            derivative_tracking_symbolic_remainder_expression = DerivativeTracker(symbolic_remainder_expression)

            # define `DerivativeTracker` for the symbolic polynomials
            derivative_tracking_symbolic_polynomials_to_decompose = [DerivativeTracker(f) for f in symbolic_polynomials_to_decompose]
            derivative_tracking_symbolic_other_polynomials = [DerivativeTracker(f) for f in symbolic_other_polynomials]

            # define ``cal_I``, the part of the integrand that does not lead to poles
            # use the derivative tracking dummy functions for the polynomials --> faster
            cal_I = Product(derivative_tracking_symbolic_remainder_expression, *chain(derivative_tracking_symbolic_polynomials_to_decompose, derivative_tracking_symbolic_other_polynomials), copy=False)

            # multiply Jacobian determinant to `cal_I`
            if contour_deformation_polynomial is not None:
                symbolic_contourdef_Jacobian = NoDerivativeAtZeroFunction(FORM_names['contourdef_Jacobian'], *elementary_monomials[:len(integration_variables)])
                symbolic_additional_deformation_factor = DerivativeTracker( Function(FORM_names['additional_deformation_factor'], *elementary_monomials) )
                cal_I = Product(symbolic_contourdef_Jacobian, symbolic_additional_deformation_factor, cal_I)

            # it is faster to use a dummy function for ``cal_I`` and substitute back in FORM
            # symbolic cal_I wrapped in a `DerivativeTracker` to keep track of derivatives
            symbolic_cal_I = DerivativeTracker(Function(FORM_names['cal_I'], *elementary_monomials))

            # initialize the Product to be passed to `integrate_pole_part` (the subtraction) and subtract
            subtraction_initializer = Product(monomials, pole_part_initializer, symbolic_cal_I, copy=False)
            subtracted = integrate_pole_part(subtraction_initializer, *integration_variable_indices)

            # intialize expansion
            pole_parts = [s.factors[1].simplify() for s in subtracted]
            regular_parts = [Product( *([s.factors[0]] + s.factors[2:]), copy=False ) for s in subtracted]

            # expand poles
            integrand_summands = []
            for i,(regular,singular) in enumerate(zip(regular_parts, pole_parts)):
                # must expand every term to the requested order plus the highest pole it multiplies
                # We calculated the highest pole order of the prefactor (variable ``highest_prefactor_pole_orders``) above.
                # In addition, we have to take the poles of the current term into account.
                singular_expanded = expand_singular(Product(singular, copy=False), regulator_indices, required_orders)

                highest_poles_current_term = - singular_expanded.expolist[:,regulator_indices].min(axis=0)
                expansion_orders = required_orders + highest_poles_current_term
                regular_expanded = expand_Taylor(regular, regulator_indices, expansion_orders)

                if i == 0: # first iteration; ``highest_poles_current_sector`` not yet set
                    highest_poles_current_sector = highest_poles_current_term
                else:
                    highest_poles_current_sector = np.maximum(highest_poles_current_sector, highest_poles_current_term)

                integrand_summands.append( Product(singular_expanded,regular_expanded,copy=False) )

            integrand = Sum(*integrand_summands, copy=False)

            # update the global lowest
            lowest_orders = np.minimum(lowest_orders, -highest_poles_current_sector)

            # initialize the CFunctions for FORM
            all_functions = []

            # compute the required derivatives
            cal_I_derivatives = {}
            other_derivatives = {}

            ordered_cal_I_derivative_names = [] # python dictionaries are unordered but some insertions depend on others --> need an ordering
            ordered_other_derivative_names = [] # python dictionaries are unordered but some insertions depend on others --> need an ordering
            def update_derivatives(basename, derivative_tracker, full_expression, derivatives=other_derivatives, ordered_derivative_names=ordered_other_derivative_names):
                derivatives[basename] = full_expression # include undifferentiated expression
                ordered_derivative_names.append(basename)
                all_functions.append(basename) # define the symbol as CFunction in FORM
                for multiindex,expression in derivative_tracker.compute_derivatives(full_expression).items():
                    name = _derivative_muliindex_to_name(basename, multiindex)
                    derivatives[name] = expression
                    ordered_derivative_names.append(name)
                    all_functions.append(name) # define the symbol as CFunction in FORM

            #  - for cal_I
            update_derivatives(basename=FORM_names['cal_I'], derivative_tracker=symbolic_cal_I, full_expression=cal_I,
                               derivatives=cal_I_derivatives, ordered_derivative_names=ordered_cal_I_derivative_names)

            #  - for the `remainder_expression`
            update_derivatives(basename=FORM_names['remainder_expression'],
                               derivative_tracker=derivative_tracking_symbolic_remainder_expression,
                               full_expression=this_primary_sector_remainder_expression)

            #  - for the additional factors
            if contour_deformation_polynomial is not None:
                update_derivatives(
                    FORM_names['additional_deformation_factor'], # basename
                    symbolic_additional_deformation_factor, # derivative tracker
                    additional_deformation_factor # full_expression
                )

            #  - for the polynomials (`other_polynomials` first since they can reference `polynomials_to_decompose`)
            for prod, tracker, basename in chain(
                zip(sector.other, derivative_tracking_symbolic_other_polynomials, names_other_polynomials),
                zip(sector.cast , derivative_tracking_symbolic_polynomials_to_decompose, names_polynomials_to_decompose)
            ):
                _, expression = prod.factors
                expression.exponent = 1 # exponent is already part of the `tracker`
                update_derivatives(
                    basename=basename, # name as defined in `polynomial_names` or dummy name
                    derivative_tracker=tracker,
                    full_expression=expression
                )

            #  - for the contour deformation polynomial
            if contour_deformation_polynomial is not None:
                full_expression = sector.cast[contour_deformation_polynomial_index].factors[1]
                full_expression.exponent = 1 # exponent is already part of the `tracker`
                update_derivatives(
                    str_contour_deformation_polynomial, # basename
                    symbolic_contour_deformation_polynomial, # derivative tracker
                    full_expression
                )


            # determine which derivatives of the user input ``functions`` are needed and
            # generate the corresponding c++ "function_declarations"
            for call in function_calls:
                number_of_arguments = call.number_of_arguments
                derivative_symbols = call.derivative_symbols
                functions.update(derivative_symbols)
                for derivative_symbol in derivative_symbols:
                    function_declarations.add( _make_CXX_function_declaration(derivative_symbol, number_of_arguments) )
            all_functions.extend(functions)

            # generate the function definitions for the insertion in FORM
            FORM_cal_I_definitions = ''.join(
                _make_FORM_function_definition(name, cal_I_derivatives[name], all_symbols, limit=10**6).replace('**','^')
                for name in ordered_cal_I_derivative_names
            )
            FORM_function_definitions = ''.join(
                _make_FORM_function_definition(name, other_derivatives[name], all_symbols, limit=10**6).replace('**','^')
                for name in ordered_other_derivative_names
            )

            # generate list over all occuring orders in the regulators
            regulator_powers = list( rangecomb(np.zeros_like(required_orders), required_orders + highest_poles_current_sector) )
            number_of_orders = len(regulator_powers)

            # generate the definitions of the FORM preprocessor variables "shiftedRegulator`regulatorIndex'PowerOrder`shiftedOrderIndex'"
            regulator_powers = _make_FORM_shifted_orders(regulator_powers)

            # parse template file "sector.h"
            template_replacements['functions'] = _make_FORM_list(all_functions)
            template_replacements['insert_cal_I_procedure'] = FORM_cal_I_definitions
            template_replacements['insert_other_procedure'] = FORM_function_definitions
            template_replacements['integrand_definition_procedure'] = _make_FORM_function_definition('SecDecInternalsDUMMYIntegrand', integrand, args=None, limit=10**6)
            template_replacements['sector_container_initializer'] = _make_FORM_Series_initilization(-highest_poles_current_sector, required_orders, sector_index, contour_deformation_polynomial is not None)
            template_replacements['highest_regulator_poles'] = _make_FORM_list(highest_poles_current_sector)
            template_replacements['regulator_powers'] = regulator_powers
            template_replacements['number_of_orders'] = number_of_orders
            parse_template_file(os.path.join(template_sources, 'codegen', 'sector.h'), # source
                                os.path.join(name,             'codegen', 'sector%i.h' % sector_index), # dest
                                template_replacements)

            if contour_deformation_polynomial is not None:
                # parse template file "contour_deformation.h"
                template_replacements['deformed_integration_variable_names'] = _make_FORM_list(symbolic_deformed_variable_names)
                template_replacements['contour_deformation_polynomial'] = contour_deformation_polynomial
                template_replacements['insert_deformed_integration_variables_procedure'] = insert_deformed_integration_variables_procedure
                template_replacements['insert_contourdef_Jacobian_procedure'] = insert_contourdef_Jacobian_procedure
                template_replacements['deformation_parameters'] = _make_FORM_list(deformation_parameters)
                parse_template_file(os.path.join(template_sources, 'codegen', 'contour_deformation.h'), # source
                                    os.path.join(name,             'codegen', 'contour_deformation_sector%i.h' % sector_index), # dest
                                    template_replacements)

    # expand the `prefactor` to the required orders
    required_prefactor_orders = requested_orders - lowest_orders
    expanded_prefactor = expand_sympy(prefactor, regulators, required_prefactor_orders)

    # pack the `prefactor` into c++ function that returns a nested `Series`
    # and takes the `real_parameters` and the `complex_parameters`
    prefactor_type = 'secdecutil::Series<' * len(regulators) + 'secdecutil::UncorrelatedDeviation<integrand_return_t' + '>' * (len(regulators) + 1)
    prefactor_function_body = _make_prefactor_function(expanded_prefactor, real_parameters, complex_parameters)

    # define the return type of "make_integrands"
    make_integrands_return_t = 'std::vector<' + 'secdecutil::Series<' * len(regulators) + \
                               'secdecutil::IntegrandContainer<integrand_return_t, real_t const * const' + \
                               '>' * (len(regulators) + 2)

    # parse the template files "integrands.cpp", "name.hpp", "prefactor.cpp", and "functions.hpp"
    template_replacements['function_declarations'] = '\n'.join(function_declarations)
    template_replacements['make_integrands_return_t'] = make_integrands_return_t
    template_replacements['prefactor_type'] = prefactor_type
    template_replacements['prefactor_function_body'] = prefactor_function_body
    template_replacements['number_of_sectors'] = sector_index
    template_replacements['lowest_orders'] = _make_FORM_list(lowest_orders)
    template_replacements['highest_orders'] = _make_FORM_list(required_orders)
    template_replacements['lowest_prefactor_orders'] = _make_FORM_list(-highest_prefactor_pole_orders)
    template_replacements['highest_prefactor_orders'] = _make_FORM_list(required_prefactor_orders)
    template_replacements['sector_includes'] = ''.join( '#include "sector_%i.hpp"\n' % i for i in range(1,sector_index+1) )
    template_replacements['sectors_initializer'] = ','.join( 'integrand_of_sector_%i' % i for i in range(1,sector_index+1) )
    parse_template_file(os.path.join(template_sources, 'src', 'integrands.cpp'), # source
                        os.path.join(name,             'src', 'integrands.cpp'), # dest
                        template_replacements)
    parse_template_file(os.path.join(template_sources, 'name.hpp'), # source
                        os.path.join(name,            name + '.hpp'), # dest
                        template_replacements)
    parse_template_file(os.path.join(template_sources, 'src', 'prefactor.cpp'), # source
                        os.path.join(name,             'src', 'prefactor.cpp'), # dest
                        template_replacements)
    parse_template_file(os.path.join(template_sources, 'src', 'functions.hpp'), # source
                        os.path.join(name,             'src', 'functions.hpp'), # dest
                        template_replacements)

    # return the replacements in the template files
    return template_replacements
