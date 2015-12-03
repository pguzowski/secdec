"""Unit tests for the algebra module"""

from .algebra import *
import sympy as sp
import unittest

class TestPolynomial(unittest.TestCase):
    def test_init(self):
        # Proper instantiation
        Polynomial([(0,1),(1,0),(2,1)],['A','B','C'])

        # exponents should be integer
        self.assertRaisesRegexp(TypeError, "(e|E)xpolist.*integer", Polynomial, [(0,1.5),(1,0),(2,1)], ['A','B','C'])

        # Length mismatch between coeffs and expolist
        self.assertRaisesRegexp(AssertionError, "same length", Polynomial, [(0,1),(1,0),(2,1)], ['A','B','C','D'])

        # entries of expolist have variable length
        self.assertRaisesRegexp(AssertionError, "expolist.*same length", Polynomial, [(0,1,2),(1,0),(2,1)], ['A','B','C'])

    def test_string_form(self):
        polynomial1 = Polynomial([(0,1),(1,0),(2,1),(0,0)],['A','B','C','D'])
        string_polynomial1 = " + (A)*x1 + (B)*x0 + (C)*x0**2*x1 + (D)"
        self.assertEqual(str(polynomial1), string_polynomial1)
        self.assertEqual(repr(polynomial1), string_polynomial1)

        polynomial2 = Polynomial([(0,1),(1,0),(2,1),(0,0)],['A','B','C','D'], polysymbols='z')
        string_polynomial2 = string_polynomial1.replace('x','z')
        self.assertEqual(str(polynomial2), string_polynomial2)
        self.assertEqual(repr(polynomial2), string_polynomial2)

        polynomial3 = Polynomial([(0,1),(1,0),(2,1),(0,0)],['A','B','C','D'], polysymbols=['x','y'])
        string_polynomial3 = string_polynomial1.replace('x0','x').replace('x1','y')
        self.assertEqual(str(polynomial3), string_polynomial3)
        self.assertEqual(repr(polynomial3), string_polynomial3)

    def test_copy(self):
        from sympy import symbols
        A, Afoo = symbols('A Afoo')

        polynomial1 = Polynomial([(0,1),(1,0),(2,1),(0,0)],['A','B','C','D'])
        polynomial2 = polynomial1.copy()

        self.assertEqual(str(polynomial1), str(polynomial2))

        polynomial1.expolist[0,0] = 5
        self.assertEqual(polynomial1.expolist[0,0],5)
        self.assertEqual(polynomial2.expolist[0,0],0)

        polynomial1.coeffs[0] = Afoo
        self.assertEqual(polynomial1.coeffs[0],Afoo)
        self.assertEqual(polynomial2.coeffs[0],A)

    def test_has_constant_term(self):
        self.assertTrue(Polynomial([(0,1),(1,0),(2,1),(0,0)],['A','B','C','D']).has_constant_term())
        self.assertTrue(Polynomial([(0,1),(0,0),(1,0),(2,1),(4,0)],['A','B','C','D',1]).has_constant_term())

        self.assertFalse(Polynomial([(0,1),(1,0),(2,1),(4,0)],['A','B','C','D']).has_constant_term())
        self.assertFalse(Polynomial([(0,1),(2,1),(4,0)],['A','B','D']).has_constant_term())

    def test_becomes_zero_for(self):
        self.assertTrue(Polynomial([(0,1,1,0),(2,1,0,5)],['A','B']).becomes_zero_for([1,0]))
        self.assertTrue(Polynomial([(0,1),(0,1),(1,5),(0,1),(4,4)],['A','B','C','D',1]).becomes_zero_for([1]))

        self.assertFalse(Polynomial([(0,1),(1,0),(2,1),(4,0)],['A','B','C','D']).becomes_zero_for([1]))
        self.assertFalse(Polynomial([(0,1,0,1),(2,1,0,5),(0,0,3,5)],['A','B','C']).becomes_zero_for([1,0]))

    def test_derive(self):
        from sympy import sympify
        polynomial = Polynomial([(2,1),(0,1)],['A', 'B'])

        derivative_0 = sympify( str(polynomial.derive(0)) )
        target_derivative_0 = sympify('2*A*x0*x1')
        self.assertEqual( (derivative_0 - target_derivative_0).simplify() , 0 )

        derivative_1 = sympify( str(polynomial.derive(1)) )
        target_derivative_1 = sympify('A*x0**2 + B')
        self.assertEqual( (derivative_1 - target_derivative_1).simplify() , 0 )

class TestFormerSNCPolynomial(unittest.TestCase):
    def setUp(self):
        self.p0 = Polynomial([(0,1),(1,0),(1,1)],[1,1,3])
        self.p1 = Polynomial([(1,1),(1,1),(2,1)],[1,1,2])
        self.p2 = Polynomial([(0,0),(1,0),(1,1)],[5,6,7])

    def test_init(self):
        self.assertRaisesRegexp(AssertionError, "coeffs.*one.dimensional", Polynomial, [(0,3),(1,2)],[[1,4],[2,3]])
        Polynomial([(1,2),(1,0),(2,1)], [1,2,3])

    def test_combine(self):
        polynomial = Polynomial([[1,2],[1,2],[2,2]  ,  [2,1],[2,1],[3,1]  ,  [2,2],[2,2],[3,2]], [1,1,2  ,  1,1,2  ,  3,3,6])
        polynomial.combine()
        self.assertEqual( (sp.sympify(str(polynomial)) - sp.sympify(" + (2)*x0*x1**2 + (8)*x0**2*x1**2 + (2)*x0**2*x1 + (2)*x0**3*x1 + (6)*x0**3*x1**2")).simplify() , 0)

        # should have minimal number of terms
        self.assertEqual(len(polynomial.coeffs), 5)
        self.assertEqual(polynomial.expolist.shape, (5,2))

    def test_mul(self):
        self.assertRaisesRegexp(AssertionError, "Number of varibales must be equal for both factors in \*", lambda: self.p0 * Polynomial([(0,0,3)],[4]))

        poly = Polynomial([(0,2),(1,0)],[1,'C'])
        intprod = 5 * poly
        self.assertEqual( (sp.sympify(str(intprod)) - sp.sympify(' + (5)*x1**2 + (5*C)*x0')).simplify() , 0)
        # should have minimal number of terms
        self.assertEqual(len(intprod.coeffs), 2)
        self.assertEqual(intprod.expolist.shape, (2,2))

        prod = self.p0 * self.p1

        #                              expolist    coefficient
        target_prod_expolist = np.array([[1,2],   #     1
        #                                [1,2],   #     1
                                         [2,2],   #     2
                                         [2,1],   #     1
        #                                [2,1],   #     1
                                         [3,1],   #     2
        #                                [2,2],   #     3
        #                                [2,2],   #     3
                                         [3,2]])  #     6

        target_prod_coeffs = np.array([2,  8  ,  2,  2  ,      6])


        # the order of the terms does not matter but for array comparison, it must be fixed
        sortkey_target = argsort_2D_array(target_prod_expolist)
        sorted_target_prod_expolist = target_prod_expolist[sortkey_target]
        sorted_target_prod_coeffs = target_prod_coeffs[sortkey_target]

        sortkey_prod = argsort_2D_array(prod.expolist)
        sorted_prod_expolist = prod.expolist[sortkey_prod]
        sorted_prod_coeffs = prod.coeffs[sortkey_prod]

        np.testing.assert_array_equal(sorted_prod_expolist, sorted_target_prod_expolist)
        np.testing.assert_array_equal(sorted_prod_coeffs, sorted_target_prod_coeffs)

    def test_add(self):
        self.assertRaisesRegexp(AssertionError, "Number of varibales must be equal for both polynomials in \+", lambda: self.p0 + Polynomial([(0,0,3)],[4]))

        self.assertEqual( str(10 + Polynomial([(1,0)],[1])) , ' + (10) + (1)*x0' )
        self.assertEqual( str(10 + Polynomial([(0,0),(1,0)],[2,1])) , ' + (12) + (1)*x0' )

        polysum = self.p0 + self.p2
        self.assertEqual( (sp.sympify(str(polysum)) - sp.sympify(" + (1)*x1 + (7)*x0 + (10)*x0*x1 + (5)")).simplify() , 0)

        # should have minimal number of terms
        self.assertEqual(len(polysum.coeffs), 4)
        self.assertEqual(polysum.expolist.shape, (4,2))


    def test_negation(self):
        neg_p2 = - self.p2
        np.testing.assert_array_equal(neg_p2.coeffs, -self.p2.coeffs)
        np.testing.assert_array_equal(neg_p2.expolist, self.p2.expolist)

    def test_subtract(self):
        polysum = self.p0 + self.p2
        polysum -= self.p2
        self.assertEqual(str(polysum),str(self.p0))

    def test_sympy_binding(self):
        from sympy import symbols
        a,b = symbols('a b')

        p = Polynomial([(1,0),(0,1)],[a,b])
        p_squared = p * p
        self.assertEqual(str(p), ' + (a)*x0 + (b)*x1')
        self.assertEqual( (sp.sympify(str(p_squared)) - sp.sympify(' + (a**2)*x0**2 + (2*a*b)*x0*x1 + (b**2)*x1**2')).simplify() , 0)

        # should have minimal number of terms
        self.assertEqual(len(p_squared.coeffs), 3)
        self.assertEqual(p_squared.expolist.shape, (3,2))

        p_sum = p_squared + Polynomial([(1,1),(0,1)],[a,b])
        self.assertEqual( (sp.sympify(str(p_sum)) - sp.sympify(' + (a**2)*x0**2 + (2*a*b + a)*x0*x1 + (b**2)*x1**2 + (b)*x1')).simplify() , 0)

        # should have minimal number of terms
        self.assertEqual(len(p_sum.coeffs), 4)
        self.assertEqual(p_sum.expolist.shape, (4,2))


    def test_empty_expolist(self):
        polynomial = Polynomial([(0,1),(1,0),(2,1),(0,0)],[0,0,0,0])
        polynomial.combine()
        self.assertGreater(len(polynomial.expolist), 0)
        self.assertGreater(len(polynomial.coeffs), 0)

        np.testing.assert_array_equal(polynomial.expolist, [[0,0]])
        np.testing.assert_array_equal(polynomial.coeffs, [0])

    def test_creation_from_expression(self):
        from sympy import symbols, sympify
        x,y, a,b,c = symbols('x y a b c')
        polynomial_expression = a*x + b*y + c*x**2*y

        poly1 = Polynomial.from_expression(polynomial_expression, [x,y])
        poly2 = Polynomial.from_expression('a*x + b*y + c*x**2*y', ['x','y'])

        self.assertEqual((sympify(str(poly1)) - polynomial_expression).simplify(), 0)
        self.assertEqual((sympify(str(poly2)) - polynomial_expression).simplify(), 0)

        self.assertRaisesRegexp(TypeError, "\'x\*y\' is not.*symbol", Polynomial.from_expression, 'a*x + b*y + c*x**2*y', [x,x*y])
        self.assertRaisesRegexp(TypeError, "polysymbols.*at least one.*symbol", Polynomial.from_expression, 'a*x + b*y + c*x**2*y', [])

class TestExponentiatedPolynomial(unittest.TestCase):
    def test_init(self):
        ExponentiatedPolynomial([(1,2),(1,0),(2,1)], ['x',2,3])
        ExponentiatedPolynomial([(1,2),(1,0),(2,1)], ['x',2,3], exponent='A + eps')

    def test_string_form(self):
        polynomial1 = ExponentiatedPolynomial([(1,2),(1,0),(2,1)], ['x',2,3], polysymbols='y')
        string_polynomial1 = ' + (x)*y0*y1**2 + (2)*y0 + (3)*y0**2*y1'
        # if exponent is one, do not show it
        self.assertEqual(str(polynomial1), string_polynomial1)
        self.assertEqual(repr(polynomial1), string_polynomial1)

        polynomial2 = ExponentiatedPolynomial([(1,2),(1,0),(2,1)], ['x',2,3], polysymbols='y', exponent='A + eps')
        string_polynomial2 = '( + (x)*y0*y1**2 + (2)*y0 + (3)*y0**2*y1)**(A + eps)'
        self.assertEqual(str(polynomial2), string_polynomial2)
        self.assertEqual(repr(polynomial2), string_polynomial2)

    def test_copy(self):
        polynomial1 = ExponentiatedPolynomial([(0,1),(1,0),(2,1),(0,0)],['A','B','C','D'],exponent='eps')
        polynomial2 = polynomial1.copy()

        self.assertEqual(str(polynomial1), str(polynomial2))
        self.assertEqual(polynomial1.exponent, polynomial2.exponent)

    def test_derive(self):
        from sympy import sympify, symbols
        A, B = symbols('A B')
        polynomial = ExponentiatedPolynomial([(2,1),(0,0)],[A, B],exponent=sympify('a + b*eps'))

        derivative_0 = sympify( str(polynomial.derive(0)) )
        target_derivative_0 = sympify('(a + b*eps)*(A*x0**2*x1 + B)**(a + b*eps - 1) * (2*A*x0*x1)')
        self.assertEqual( (derivative_0 - target_derivative_0).simplify() , 0 )

        derivative_1 = sympify( str(polynomial.derive(1)) )
        target_derivative_1 = sympify('(a + b*eps)*(A*x0**2*x1 + B)**(a + b*eps - 1) * (A*x0**2)')
        self.assertEqual( (derivative_1 - target_derivative_1).simplify() , 0 )


        polynomial = ExponentiatedPolynomial([(2,1),(0,0)],[A, B],exponent=Polynomial.from_expression('a + b*x0',['x0','x1']))
        derivative_0 = sympify( str(polynomial.derive(0)) )
        target_derivative_0 = sympify('(a + b*x0)*(A*x0**2*x1 + B)**(a + b*x0 - 1) * (2*A*x0*x1)   +   (A*x0**2*x1 + B)**(a + b*x0)*b*log(A*x0**2*x1 + B)')
        self.assertEqual( (derivative_0 - target_derivative_0).simplify() , 0 )

class TestProduct(unittest.TestCase):
    def test_init(self):
        p0 = Polynomial([(0,1),(1,0),(2,1)],['A','B','C'])
        p1 = Polynomial([(8,1),(1,5),(2,1)],['D','E','F'])
        p2 = Polynomial([(1,0,1),(2,1,0),(0,2,1)],['G','H','I'])

        # mismatch in number of parameters
        self.assertRaisesRegexp(TypeError, 'same number of variables.*all.*factors', Product,p0,p2)

        self.assertRaisesRegexp(AssertionError, 'at least one factor', Product)

        # Proper instantiation
        prod = Product(p0,p1)

        # made a copy?
        self.assertEqual(prod.factors[0].expolist[0,0],0)
        self.assertEqual(p0.expolist[0,0],0)
        prod.factors[0].expolist[0,0] = 5
        self.assertEqual(prod.factors[0].expolist[0,0],5)
        self.assertEqual(p0.expolist[0,0],0)

    def test_copy(self):
        p0 = Polynomial([(0,1),(1,0),(2,1)],['A','B','C'])
        p1 = Polynomial([(8,1),(1,5),(2,1)],['D','E','F'])

        orig = Product(p0,p1)
        copy = orig.copy()

        self.assertEqual(orig.factors[0].expolist[0,0],0)
        self.assertEqual(copy.factors[0].expolist[0,0],0)
        orig.factors[0].expolist[0,0] = 5
        self.assertEqual(orig.factors[0].expolist[0,0],5)
        self.assertEqual(copy.factors[0].expolist[0,0],0)

    def test_derive(self):
        from sympy import sympify, symbols
        A, B = symbols('A B')
        polynomial = ExponentiatedPolynomial([(2,1),(0,0)],[A, B],exponent=sympify('a + b*eps'))

        derivative_0 = polynomial.derive(0)
        derivative_0_1 = sympify( str(derivative_0.derive(1)) )
        target_derivative_0_1 = sympify('(a + b*eps)*(a + b*eps - 1)*(A*x0**2*x1 + B)**(a + b*eps - 2) * (A*x0**2) * (2*A*x0*x1) + (a + b*eps)*(A*x0**2*x1 + B)**(a + b*eps - 1) * (2*A*x0)')
        self.assertEqual( (derivative_0_1 - target_derivative_0_1).simplify() , 0 )

    def test_string_form(self):
        p0 = ExponentiatedPolynomial([(0,1)],['A'],exponent='exponent')
        p1 = Polynomial([(8,1),(1,5),(2,1)],['B','C','D'])
        prod = Product(p0,p1)
        string_prod = '(( + (A)*x1)**(exponent)) * ( + (B)*x0**8*x1 + (C)*x0*x1**5 + (D)*x0**2*x1)'

        self.assertEqual(str(prod), string_prod)
        self.assertEqual(repr(prod), string_prod)

class TestSum(unittest.TestCase):
    def test_init(self):
        p0 = Polynomial([(0,1),(1,0),(2,1)],['A','B','C'])
        p1 = Polynomial([(8,1),(1,5),(2,1)],['D','E','F'])
        p2 = Polynomial([(1,0,1),(2,1,0),(0,2,1)],['G','H','I'])

        # mismatch in number of parameters
        self.assertRaisesRegexp(TypeError, 'same number of variables.*all.*summands', Sum,p0,p2)

        self.assertRaisesRegexp(AssertionError, 'at least one summand', Sum)

        # Proper instantiation
        psum = Sum(p0,p1)

        # made a copy?
        self.assertEqual(psum.summands[0].expolist[0,0],0)
        self.assertEqual(p0.expolist[0,0],0)
        psum.summands[0].expolist[0,0] = 5
        self.assertEqual(psum.summands[0].expolist[0,0],5)
        self.assertEqual(p0.expolist[0,0],0)

    def test_copy(self):
        p0 = Polynomial([(0,1),(1,0),(2,1)],['A','B','C'])
        p1 = Polynomial([(8,1),(1,5),(2,1)],['D','E','F'])

        orig = Sum(p0,p1)
        copy = orig.copy()

        self.assertEqual(orig.summands[0].expolist[0,0],0)
        self.assertEqual(copy.summands[0].expolist[0,0],0)
        orig.summands[0].expolist[0,0] = 5
        self.assertEqual(orig.summands[0].expolist[0,0],5)
        self.assertEqual(copy.summands[0].expolist[0,0],0)

    def test_string_form(self):
        p0 = ExponentiatedPolynomial([(0,1)],['A'],exponent='exponent')
        p1 = Polynomial([(8,1),(1,5),(2,1)],['B','C','D'])
        sum = Sum(p0,p1)
        string_sum = '(( + (A)*x1)**(exponent)) + ( + (B)*x0**8*x1 + (C)*x0*x1**5 + (D)*x0**2*x1)'

        self.assertEqual(str(sum), string_sum)
        self.assertEqual(repr(sum), string_sum)

    def test_derive(self):
        from sympy import symbols, sympify
        A, B = symbols('A B')

        p0 = ExponentiatedPolynomial([(0,1)],[A])
        p1 = ExponentiatedPolynomial([(2,1)],[B])
        psum = Sum(p0,p1)

        derivative_0 = sympify( psum.derive(0) )
        target_derivative_0 = sympify( '2*B*x0*x1' )
        self.assertEqual( (derivative_0 - target_derivative_0).simplify() , 0 )

class TestLogOfPolynomial(unittest.TestCase):
    def test_string_form(self):
        p0 = LogOfPolynomial([(0,1),(1,0),(2,1)],['A','B','C'])
        str_p0 = 'log( + (A)*x1 + (B)*x0 + (C)*x0**2*x1)'

        self.assertEqual(str(p0),str_p0)
        self.assertEqual(repr(p0),str_p0)

    def test_construct_from_expression(self):
        p1 = LogOfPolynomial.from_expression('D*x0**8*x1 + E*x0*x1**5 + F*x0*x0*x1',['x0','x1'])
        str_p1 = 'log( + (D)*x0**8*x1 + (E)*x0*x1**5 + (F)*x0**2*x1)'
        sympy_p1 = sp.sympify(str_p1)

        self.assertEqual(str(p1),repr(p1))
        self.assertEqual( sp.sympify(repr(p1)) - sympy_p1 , 0 )

    def test_derive(self):
        expr = LogOfPolynomial([(2,1),(0,1)],['A', 'B'])

        derivative_0 = expr.derive(0)
        sympified_derivative_0 = sp.sympify( str(derivative_0) )
        target_derivative_0 = sp.sympify('1/(A*x0**2*x1 + B*x1) * 2*A*x0*x1')
        self.assertEqual( (sympified_derivative_0 - target_derivative_0).simplify() , 0 )
        self.assertEqual(type(derivative_0), Product)
        self.assertEqual(len(derivative_0.factors), 2)
        self.assertEqual(type(derivative_0.factors[0]), ExponentiatedPolynomial)

        derivative_1 = sp.sympify( str(expr.derive(1)) )
        target_derivative_1 = sp.sympify('1/(A*x0**2*x1 + B*x1) * (A*x0**2 + B)')
        self.assertEqual( (derivative_1 - target_derivative_1).simplify() , 0 )

class TestInsertion(unittest.TestCase):
    def test_insert_value_polynomial(self):
        poly = Polynomial([(0,0),(1,0),(0,1),(0,2)],['A','B','C','D'])
        replaced_poly = replace(poly,index=1,value=sp.sympify('1/2'))
        self.assertEqual( sp.sympify(str(replaced_poly)) - sp.sympify('A + B*x0 + C/2 + D/4') , 0 )

    def test_insert_value_polynomial_product(self):
        poly0 = Polynomial([(0,0),(1,0),(0,1),(0,2)],['A','B','C','D'])
        poly1 = Polynomial([(0,0),(5,0)],['E',1])
        prod = Product(poly0,poly1)
        replaced_prod = replace(prod,index=1,value=0)
        self.assertEqual( (sp.sympify(str(replaced_prod)) - sp.sympify('(A + B*x0) * (E + x0**5)')).simplify() , 0 )

    def test_insert_value_polynomial_sum(self):
        poly0 = Polynomial([(0,0),(1,0),(0,1),(0,2)],['A','B','C','D'])
        poly1 = Polynomial([(0,0),(5,0)],['E',1])
        prod = Sum(poly0,poly1)
        replaced_prod = replace(prod,index=1,value=0)
        self.assertEqual( (sp.sympify(str(replaced_prod)) - sp.sympify('A + B*x0 + E + x0**5')).simplify() , 0 )

    def test_insert_in_exponent(self):
        exponent = Polynomial([(0,0),(5,0)],['E',1])
        poly1 = ExponentiatedPolynomial([(0,0),(1,0),(0,1),(0,2)],['A','B','C','D'],exponent)
        replaced = replace(poly1,index=0,value=0)
        self.assertEqual( (sp.sympify(str(replaced)) - sp.sympify('(A + C*x1 + D*x1**2)**(E)')).simplify() , 0 )

    def test_error(self):
        self.assertRaisesRegexp(TypeError, 'Can.*only.*Polynomial.*not.*int', replace, 3, 2, 1)
