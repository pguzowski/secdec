"""This file defines the Polynomial class"""

import numpy as np
import sympy as sp

class Polynomial(object):
    '''
    Container class for polynomials.
    Store a polynomial as list of lists counting the powers of
    the variables. For example the polynomial "x1**2 + x1*x2" is
    stored as [[2,0],[1,1]].

    Coefficients are stored in a separate list of strings, e.g.
    "A*x0**2 + B*x0*x1" <-> [[2,0],[1,1]] and ["A","B"].

    :param expolist:
        iterable of iterables;
        The variable's powers for each term.

    :param coeffs:
        1d array-like with numerical or sympy-symbolic
        (see http://www.sympy.org/) content, e.g. [x,1,2]
        where x is a sympy symbol;
        The coefficients of the polynomial.

    :param polysymbols:
        iterable or string, optional;
        The symbols to be used for the polynomial variables
        when converted to string. If a string is passed, the
        variables will be consecutively numbered.

        For example: expolist=[[2,0],[1,1]] coeffs=["A","B"]
         * polysymbols='x' (default) <-> "A*x0**2 + B*x0*x1"
         * polysymbols=['x','y']     <-> "A*x**2 + B*x*y"

    '''
    def __init__(self, expolist, coeffs, polysymbols='x'):
        self.expolist = np.array(expolist)
        assert len(self.expolist.shape) == 2, 'All entries in `expolist` must have the same length'
        if not np.issubdtype(self.expolist.dtype, np.integer):
            raise TypeError('All entries in `expolist` must be integer.')
        self.coeffs = np.array(coeffs)
        assert len(self.expolist) == len(self.coeffs), \
            '`expolist` (length %i) and `coeffs` (length %i) must have the same length.' %(len(self.expolist),len(self.coeffs))
        assert len(self.coeffs.shape) == 1, '`coeffs` must be one-dimensional'
        if not np.issubdtype(self.coeffs.dtype, np.number):
            self.coeffs = np.array([coeff.copy() if isinstance(coeff,Polynomial) else sp.sympify(coeff) for coeff in self.coeffs])
        self.number_of_variables = self.expolist.shape[1]
        if isinstance(polysymbols, str):
            self.polysymbols=[polysymbols + str(i) for i in range(self.number_of_variables)]
        else:
            self.polysymbols=list(polysymbols)

    @staticmethod
    def from_expression(expression, polysymbols):
        '''
        Alternative constructor.
        Construct the polynomial from an algebraic expression.

        :param expression:
            string or sympy expression;
            The algebraic representation of the polynomial, e.g.
            "5*x1**2 + x1*x2"

        :param polysymbols:
            iterable of strings or sympy symbols;
            The symbols to be interpreted as the polynomial variables,
            e.g. "['x1','x2']".

        '''
        polysymbols = list(polysymbols)

        if not polysymbols:
            raise TypeError("`polysymbols` must contain at least one symbol")

        expression, polysymbols = sp.sympify((expression, polysymbols))

        for symbol in polysymbols:
            if not symbol.is_Symbol:
                raise TypeError("'%s' is not a symbol" % symbol)

        sympy_poly = sp.poly(expression, polysymbols)
        expolist = sympy_poly.monoms()
        coeffs = sympy_poly.coeffs()
        return Polynomial(expolist, coeffs, polysymbols)


    def __repr__(self):
        outstr = ''
        for coeff,expolist in zip(self.coeffs,self.expolist):
            outstr += (" + (%s)" % coeff)
            for i,(power,symbol) in enumerate(zip(expolist,self.polysymbols)):
                if power == 0:
                    continue
                elif power == 1:
                    outstr += "*%s" % symbol
                else:
                    outstr += "*%s**%i" %(symbol,power)
        return outstr

    __str__ = __repr__

    def copy(self):
        "Return a copy of a :class:`.Polynomial` or a subclass."
        return type(self)(self.expolist, self.coeffs, self.polysymbols)

    def has_constant_term(self):
        '''
        Return True if the polynomial can be written as:

        .. math::
            const + ...

        Otherwise, return False.

        '''
        return (self.expolist == 0).all(axis=1).any()

    def becomes_zero_for(self, zero_params):
        '''
        Return True if the polynomial becomes zero if the
        parameters passed in `zero_params` are set to zero.
        Otherwise, return False.

        :param zero_params:
            iterable of integers;
            The indices of the parameters to be checked.

        '''
        return (self.expolist > 0)[:,tuple(zero_params)].any(axis=1).all()

    def derive(self, index):
        '''
        Generate the derivative by the parameter indexed `index`.

        :param index:
            integer;
            The index of the paramater to derive by.

        '''
        # derivative(... * x**k) = ... * k * x**(k-1) = ... * <additional_coeff_factor> * x**(k-1)
        additional_coeff_factors = self.expolist[:,index]
        new_coeffs = [old_coeff*new_factor for old_coeff,new_factor in zip(self.coeffs,additional_coeff_factors)]
        new_expolist = self.expolist.copy()
        new_expolist[:,index] -= 1

        outpoly = Polynomial(new_expolist, new_coeffs, self.polysymbols)
        outpoly.combine() # simplify
        return outpoly

    def __add__(self, other):
        'addition operator'
        return self._sub_or_add(other, False)

    def __sub__(self, other):
        'subtraction operator'
        return self._sub_or_add(other, True)

    def _sub_or_add(self, other, sub):
        '''
        Function that implements addition and subtraction.
        The coefficients of `other` are negated if `sub`
        is `True`.

        '''
        if  type(other) is Polynomial:
            assert self.number_of_variables == other.number_of_variables, 'Number of varibales must be equal for both polynomials in +'

            sum_expolist = np.vstack([self.expolist, other.expolist])
            sum_coeffs = np.hstack([self.coeffs, -other.coeffs if sub else other.coeffs])

            result = Polynomial(sum_expolist, sum_coeffs, self.polysymbols)
            result.combine()
            return result

        elif np.issubdtype(type(other), np.number) or isinstance(other, sp.Expr):
            new_expolist = np.vstack([[0]*self.number_of_variables, self.expolist])
            new_coeffs = np.append(other, self.coeffs)
            outpoly = Polynomial(new_expolist, new_coeffs, self.polysymbols)
            outpoly.combine()
            return outpoly

        else:
            return NotImplemented

    def __mul__(self, other):
        'multiplication operator'
        if  type(other) is Polynomial:
            assert self.number_of_variables == other.number_of_variables, 'Number of varibales must be equal for both factors in *'

            product_expolist = np.vstack([other.expolist + term for term in self.expolist])
            product_coeffs = np.hstack([other.coeffs * term for term in self.coeffs])

            result = Polynomial(product_expolist, product_coeffs, self.polysymbols)
            result.combine()
            return result

        elif np.issubdtype(type(other), np.number) or isinstance(other, sp.Expr):
            new_coeffs = self.coeffs * other
            return Polynomial(self.expolist, new_coeffs, self.polysymbols)

        else:
            return NotImplemented

    __rmul__ = __mul__
    __radd__ = __add__
    __rsub__ = __sub__

    def __neg__(self):
        'arithmetic negation "-self"'
        return Polynomial(self.expolist, [-coeff for coeff in self.coeffs], self.polysymbols)

    def combine(self):
        '''
        Combine terms that have the same exponents of
        the variables.

        '''
        for i in range(len(self.coeffs)):
            # do not have to consider terms with zero coefficient
            if self.coeffs[i] == 0: continue
            # search `self.expolist` for the same term
            same_exponents = np.where( (self.expolist[i+1:] == self.expolist[i]).all(axis=1) )
            # add all these coefficients together
            self.coeffs[i] += np.sum(self.coeffs[i+1:][same_exponents])
            # mark other terms for removal by setting coefficients to zero
            self.coeffs[i+1:][same_exponents] = 0

        # remove terms with zero coefficient
        zero_coeffs = np.where(self.coeffs == 0)
        self.coeffs = np.delete(self.coeffs, zero_coeffs)
        self.expolist = np.delete(self.expolist, zero_coeffs ,axis=0)

        # need to have at least one term
        if len(self.coeffs) == 0:
            self.coeffs = np.array([0])
            self.expolist = np.array([[0]*self.number_of_variables])

class ExponentiatedPolynomial(Polynomial):
    '''
    Like :class:`.Polynomial`, but with a global exponent.
    :math:`polynomial^{exponent}`

    :param expolist:
        iterable of iterables;
        The variable's powers for each term.

    :param coeffs:
        iterable;
        The coefficients of the polynomial.

    :param exponent:
        object, optional;
        The global exponent.

    :param polysymbols:
        iterable or string, optional;
        The symbols to be used for the polynomial variables
        when converted to string. If a string is passed, the
        variables will be consecutively numbered.

        For example: expolist=[[2,0],[1,1]] coeffs=["A","B"]
         * polysymbols='x' (default) <-> "A*x0**2 + B*x0*x1"
         * polysymbols=['x','y']     <-> "A*x**2 + B*x*y"

    '''
    def __init__(self, expolist, coeffs, exponent=1, polysymbols='x'):
        Polynomial.__init__(self, expolist, coeffs, polysymbols)
        if np.issubdtype(type(exponent), np.number) or isinstance(exponent,Polynomial):
            self.exponent = exponent
        else:
            self.exponent = sp.sympify(exponent)

    def _NotImplemented(self,*args,**kwargs):
        return NotImplemented

    __mul__ = __rmul__ = __add__ = __radd__ = __sub__ = __rsub__ = __neg__ = _NotImplemented

    def __repr__(self):
        if self.exponent == 1:
            return super(ExponentiatedPolynomial, self).__repr__()
        else:
            return '(' + super(ExponentiatedPolynomial, self).__repr__() \
                       + ')**(%s)' % self.exponent
    __str__ = __repr__

    def derive(self, index):
        '''
        Generate the derivative by the parameter indexed `index`.

        :param index:
            integer;
            The index of the paramater to derive by.

        '''
        # derive an expression of the form "poly**exponent"
        # chain rule:
        #   --> factor0 = "poly**(exponent-1)"

        # simplification: (...)**0 = 1
        # do not need factor 0 in that case
        new_exponent = self.exponent - 1
        if new_exponent == 0:
            factor0 = None
        else:
            factor0 = ExponentiatedPolynomial(self.expolist,
                                              self.coeffs,
                                              new_exponent,
                                              self.polysymbols)

        #   --> factor1 = "derivative(poly) * exponent"
        #   --> derivative(... * x**k) = ... * k * x**(k-1) = ... * <additional_coeff_factor> * x**(k-1)
        additional_coeff_factors = self.expolist[:,index] * self.exponent
        new_coeffs = [old_coeff*new_factor for old_coeff,new_factor in zip(self.coeffs,additional_coeff_factors)]
        new_expolist = self.expolist.copy()
        new_expolist[:,index] -= 1
        factor1 = ExponentiatedPolynomial(new_expolist,
                                          new_coeffs,
                                          polysymbols=self.polysymbols)
        # simplify
        factor1.combine()

        if factor0 is None:
            return factor1
        else:
            return PolynomialProduct(factor0, factor1)

    def copy(self):
        "Return a copy of a :class:`.Polynomial` or a subclass."
        return type(self)(self.expolist, self.coeffs, self.exponent, self.polysymbols)

class PolynomialSum(object):
    r'''
    Sum of polynomials.
    Store one or polynomials :math:`p_i` to be interpreted as
    product :math:`\sum_i p_i`.

    .. hint::
        This class is particularly useful when used with instances
        of :class:`ExponentiatedPolynomial`.

    :param summands:
        arbitrarily many instances of :class:`.Polynomial`;
        The summands :math:`p_i`.

    :math:`p_i` can be accessed with ``self.summands[i]``.

    Example:

    .. code-block:: python

        p = PolynomialSum(p0, p1)
        p0 = p.summands[0]
        p1 = p.summands[1]

    '''
    def __init__(self,*summands):
        self.summands = [summand.copy() for summand in summands]
        assert self.summands, 'Must have at least one summand'

        self.number_of_variables = self.summands[0].number_of_variables

        for summand in self.summands:
            if summand.number_of_variables != self.number_of_variables:
                raise TypeError('Must have the same number of variables for all summands.')

    def __repr__(self):
        stringified_summands = []
        for summand in self.summands:
            stringified_summands.append( '(' + str(summand) + ')' )
        return ' + '.join(stringified_summands)

    __str__ = __repr__

    def simplify(self):
        '''
        If one or more of ``self.summands`` is a
        :class:`PolynomialSum`, replace it by its summands.
        If only one summand is present, return that summand.
        Remove zero from sums.

        '''
        changed = True
        while changed:
            changed = False
            old_summands = self.summands
            self.summands = []
            for summand in old_summands:
                if isinstance(summand, PolynomialProduct):
                    summand = summand.simplify()
                if isinstance(summand, PolynomialSum):
                    changed = True
                    self.summands.extend(summand.summands)
                elif isinstance(summand, Polynomial):
                    if (summand.coeffs == 0).all():
                        changed = True
                        zero = summand
                    else:
                        self.summands.append(summand)
                else:
                    self.summands.append(summand)
        if len(self.summands) == 1:
            return self.summands[0]
        elif len(self.summands) == 0:
            return zero
        else:
            return self

    def copy(self):
        "Return a copy of a :class:`.PolynomialSum`."
        return PolynomialSum(*self.summands)

    def derive(self, index):
        '''
        Generate the derivative by the parameter indexed `index`.

        :param index:
            integer;
            The index of the paramater to derive by.

        '''
        # derivative(p1 + p2 + ...) = derivative(p1) + derivative(p2) + ...
        return PolynomialSum(*(summand.derive(index) for summand in self.summands)).simplify()

class PolynomialProduct(object):
    r'''
    Product of polynomials.
    Store one or polynomials :math:`p_i` to be interpreted as
    product :math:`\prod_i p_i`.

    :param factors:
        arbitrarily many instances of :class:`.Polynomial`;
        The factors :math:`p_i`.

    :math:`p_i` can be accessed with ``self.factors[i]``.

    Example:

    .. code-block:: python

        p = PolynomialProduct(p0, p1)
        p0 = p.factors[0]
        p1 = p.factors[1]


    '''
    def __init__(self,*factors):
        self.factors = [factor.copy() for factor in factors]
        assert self.factors, 'Must have at least one factor'

        self.number_of_variables = self.factors[0].number_of_variables

        for factor in self.factors:
            if factor.number_of_variables != self.number_of_variables:
                raise TypeError('Must have the same number of variables for all factors.')

    def __repr__(self):
        stringified_factors = []
        for factor in self.factors:
            stringified_factors.append( '(' + str(factor) + ')' )
        return ' * '.join(stringified_factors)

    __str__ = __repr__

    def copy(self):
        "Return a copy of a :class:`.PolynomialProduct`."
        return PolynomialProduct(*self.factors)

    def simplify(self):
        '''
        If one or more of ``self.factors`` is a
        :class:`PolynomialProduct`, replace it by its factors.
        If only one factor is present, return that factor.
        Remove factors of one and zero.

        '''
        changed = True
        while changed:
            changed = False
            old_factors = self.factors
            self.factors = []
            for factor in old_factors:
                if isinstance(factor, PolynomialSum):
                    factor = factor.simplify()
                if isinstance(factor, PolynomialProduct):
                    changed = True
                    self.factors.extend(factor.factors)
                elif isinstance(factor, Polynomial):
                    if (factor.expolist == 0).all() and (factor.coeffs == 1).all():
                        # do not need to append unity except there is no other factor
                        if self.factors:
                            changed = True
                        else:
                            self.factors.append(factor)
                    elif (factor.coeffs == 0).all():
                        factor.combine()
                        self.factors = [factor]
                        break
                    else:
                        self.factors.append(factor)
                else:
                    self.factors.append(factor)
        if len(self.factors) == 1:
            return self.factors[0]
        else:
            return self

    def derive(self, index):
        '''
        Generate the derivative by the parameter indexed `index`.

        :param index:
            integer;
            The index of the paramater to derive by.

        '''
        # product rule: derivative(p1 * p2 * ...) = derivative(p1) * p2 * ... + p1 * derivative(p2) * ...
        summands = []
        factors = list(self.factors) # copy
        for i,factor in enumerate(self.factors):
            factors[i] = factor.derive(index)
            summands.append(PolynomialProduct(*factors).simplify())
            factors[i] = factor
        return PolynomialSum(*summands).simplify()

def replace(expression, index, value):
    '''
    Replace a polynomial variable by a number or
    a symbol.
    The entries in all ``expolist`` of the underlying
    :class:`.Polynomial` are set to zero. The coefficients
    are modified according to `value` and the powers
    indicated in the ``expolist``.

    :param expression:
        PolynomialProduct, PolynomialSum, or Polynomial;
        The expression to replace the variable.

    :param index:
        integer;
        The index of the variable to be replaced.

    :param value:
        number of sympy expression;
        The value to insert for the chosen variable.

    '''
    if isinstance(expression,Polynomial):
        outpoly = expression.copy()
        powers = expression.expolist[:,index]
        outpoly.coeffs *= value**powers
        outpoly.expolist[:,index] = 0
        outpoly.combine()
        return outpoly
    elif isinstance(expression, PolynomialProduct):
        outfactors = []
        for factor in expression.factors:
            outfactors.append(replace(factor,index,value))
        return PolynomialProduct(*outfactors)
    elif isinstance(expression, PolynomialSum):
        outsummands = []
        for summand in expression.summands:
            outsummands.append(replace(summand,index,value))
        return PolynomialSum(*outsummands)
    else:
        raise NotImplementedError('Can only operate on `Polynomial`, `PolynomialProduct`, and `PolynomialSum`, not `%s`' % type(expression))
