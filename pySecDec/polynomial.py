"""This file defines the Polynomial class"""

import numpy as np

class Polynomial(object):
    '''
    Container class for polynomials.
    Store a polynomial as list of lists counting the powers of
    the variables. For example the monomial "x1^2 + x1*x2" is
    stored as [[2,0],[1,1]].

    Coefficients are stored in a separate list of strings, e.g.
    "A*x1^2 + B*x1*x2" <-> [[2,0],[1,1]] and ["A","B"].

    :param expolist:
        iterable of iterables;
        The variable's powers for each term.

    :param coeffs:
        iterable of strings;
        The symbolic coefficients of the polynomial.

    '''
    def __init__(self, expolist, coeffs):
        self.expolist = np.array(expolist)
        assert len(self.expolist.shape) == 2, 'All entries in `expolist` must have the same length'
        if not np.issubdtype(self.expolist.dtype, np.integer):
            raise TypeError('All entries in `expolist` must be integer.')
        self.coeffs = list(coeffs)
        assert len(self.expolist) == len(self.coeffs), \
            '`expolist` (length %i) and `coeffs` (length %i) must have the same length.' %(len(self.expolist),len(self.coeffs))
        self.number_of_variables = self.expolist.shape[1]

    def __repr__(self):
        from .configure import _powsymbol, _coeffs_in_parentheses
        outstr = ''
        for coeff,expolist in zip(self.coeffs,self.expolist):
            if coeff != '':
                if _coeffs_in_parentheses:
                    outstr += (" + (%s)" % coeff).replace('**',_powsymbol)
                else:
                    outstr += (" + %s" % coeff).replace('**',_powsymbol)
            else:           outstr += " + 1"
            for i,power in enumerate(expolist):
                outstr += "*x%i%s%i" %(i,_powsymbol,power)

        return outstr

    __str__ = __repr__

    def copy(self):
        "Return a copy of a :class:`.Polynomial`."
        return Polynomial(self.expolist, self.coeffs)

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

class SNCPolynomial(Polynomial):
    '''
    "Symbolic or Numerical Coefficiented Polynomial"
    Like :class:`.Polynomial`, but with numerical coefficients
    (`coeffs`). The coefficients are stored in a numpy array.

    :param expolist:
        iterable of iterables;
        The variable's powers for each term.

    :param coeffs:
        1d array-like with numerical or sympy-symbolic
        (see http://www.sympy.org/) content, e.g. [x,1,2]
        where x is a sympy symbol;
        The coefficients of the polynomial.

    '''
    def __init__(self, expolist, coeffs):
        Polynomial.__init__(self, expolist, coeffs)
        self.coeffs = np.array(coeffs)
        assert len(self.coeffs.shape) == 1, '`coeffs` must be one-dimensional'

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
        if  type(other) is not SNCPolynomial:
            return NotImplemented

        assert self.number_of_variables == other.number_of_variables, 'Number of varibales must be equal for both polynomials in +'

        sum_expolist = np.vstack([self.expolist, other.expolist])
        sum_coeffs = np.hstack([self.coeffs, -other.coeffs if sub else other.coeffs])

        result = SNCPolynomial(sum_expolist, sum_coeffs)
        result.combine()
        return result

    def __mul__(self, other):
        'multiplication operator'
        if  type(other) is not SNCPolynomial:
            return NotImplemented

        assert self.number_of_variables == other.number_of_variables, 'Number of varibales must be equal for both factors in *'

        product_expolist = np.vstack([other.expolist + term for term in self.expolist])
        product_coeffs = np.hstack([other.coeffs * term for term in self.coeffs])

        result = SNCPolynomial(product_expolist, product_coeffs)
        result.combine()
        return result

    def __neg__(self):
        'arithmetic negation "-self"'
        return SNCPolynomial(self.expolist, [-coeff for coeff in self.coeffs])

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

        self.number_of_variables = self.factors[0].expolist.shape[1]

        for factor in self.factors:
            if factor.expolist.shape[1] != self.number_of_variables:
                raise TypeError('Must have the same number of variables for all factors.')

    def copy(self):
        "Return a copy of a :class:`.PolynomialProduct`."
        return PolynomialProduct(*self.factors)
