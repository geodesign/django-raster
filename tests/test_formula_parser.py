import numpy

from django.test import TestCase
from raster.algebra.parser import FormulaParser
from raster.exceptions import RasterAlgebraException


class FormulaParserTests(TestCase):

    def setUp(self):
        self.parser = FormulaParser()

    def assertFormulaResult(self, formula, expVal, data={}):
        # Get data from test object if not passed as an argument
        if hasattr(self, 'data'):
            data = self.data

        # Evaluate
        val = self.parser.evaluate(data, formula)

        # Drop nan values
        if data and any(numpy.isnan(expVal)):
            val = val[numpy.logical_not(numpy.isnan(val))]
            expVal = expVal[numpy.logical_not(numpy.isnan(expVal))]

        # Assert non nan values are as expected
        if isinstance(val, numpy.ndarray):
            val = val.tolist()
        if isinstance(expVal, numpy.ndarray):
            expVal = expVal.tolist()

        self.assertEqual(val, expVal)

        # Check that nan values are the same
        self.assertTrue(numpy.array_equal(numpy.isnan(expVal), numpy.isnan(val)))

    def test_formula_parser_without_vars(self):
        self.assertFormulaResult("9", 9)
        self.assertFormulaResult("-9", -9)
        self.assertFormulaResult("--9", 9)
        self.assertFormulaResult("+9 - 8", 1)
        self.assertFormulaResult("9 + 3 + 6", 9 + 3 + 6)
        self.assertFormulaResult("9 + 3 / 11", 9 + 3.0 / 11)
        self.assertFormulaResult("(9 + 3)", (9 + 3))
        self.assertFormulaResult("(9 + 3) / 11", (9 + 3.0) / 11)
        self.assertFormulaResult("9 - 12 - 6", 9 - 12 - 6)
        self.assertFormulaResult("9 - (12 - 6)", 9 - (12 - 6))
        self.assertFormulaResult("2 * 3.14159", 2 * 3.14159)
        self.assertFormulaResult("3.1415926535 * 3.1415926535 / 10", 3.1415926535 * 3.1415926535 / 10)
        self.assertFormulaResult("PI * PI / 10", numpy.pi * numpy.pi / 10)
        self.assertFormulaResult("PI * PI / 10", numpy.pi * numpy.pi / 10)
        self.assertFormulaResult("PI^2", numpy.pi ** 2)
        self.assertFormulaResult("round(PI^2)", round(numpy.pi ** 2))
        self.assertFormulaResult("6.02E23 * 8.048", 6.02E23 * 8.048)
        self.assertFormulaResult("6.02e23 * 8.048", 6.02E23 * 8.048)
        self.assertFormulaResult("sin(PI / 2)", numpy.sin(numpy.pi / 2))
        self.assertFormulaResult("cos(PI / 5)", numpy.cos(numpy.pi / 5))
        self.assertFormulaResult("-E", -numpy.e)
        self.assertFormulaResult("int(E)", int(numpy.e))
        self.assertFormulaResult("int(-E)", int(-numpy.e))
        self.assertFormulaResult("round(E)", round(numpy.e))
        self.assertFormulaResult("round(-E)", round(-numpy.e))
        self.assertFormulaResult("E^PI", numpy.e ** numpy.pi)
        self.assertFormulaResult("2^1^3^2", 2 ** 1 ** 3 ** 2)
        self.assertFormulaResult("2^0", 1)
        self.assertFormulaResult("2^3^(2 + 1)", 2 ** 3 ** 3)
        self.assertFormulaResult("2^3 + 2", 2 ** 3 + 2)
        self.assertFormulaResult("2^9", 2 ** 9)
        self.assertFormulaResult("sign(-2)", -1)
        self.assertFormulaResult("sign(0)", 0)
        self.assertFormulaResult("sign(0.1)", 1)
        self.assertFormulaResult("exp(0)", 1)
        self.assertFormulaResult("exp(1)", numpy.e)
        self.assertFormulaResult("log(1)", 0)
        self.assertFormulaResult("TRUE", True)
        self.assertFormulaResult("FALSE", False)
        self.assertFormulaResult("FALSE | TRUE", True)
        self.assertFormulaResult("TRUE & TRUE", True)
        self.assertFormulaResult("TRUE & FALSE", False)
        self.assertFormulaResult("2 > 1", True)
        self.assertFormulaResult("2 >= 1", True)
        self.assertFormulaResult("2 < 1", False)
        self.assertFormulaResult("2 <= 1", False)
        self.assertFormulaResult("1 == 1", True)
        self.assertFormulaResult("1 != 2", True)
        self.assertFormulaResult("!1", False)
        self.assertFormulaResult("!-1", False)
        self.assertFormulaResult("!2", False)

    def test_formula_parser_with_vars(self):
        d = self.data = {
            "a": numpy.array([2, 4, 6]),
            "b": numpy.array([True, False, True]),
            "c": numpy.array([True, False, False]),
            "d": [2, 4, 6],
            "x": numpy.array([1.2, 0, -1.2]),
            "y": numpy.array([0, 1, 0]),
            "z": numpy.array([-5, 78, 912]),
            "u": numpy.array([2, 4, 6]),
            "A": numpy.array([1E5, 2.3e4]),
            "e": numpy.array([2, 11e3]),
            "aLongVariable": numpy.array([1, 2, 3]),
            "A1A": numpy.array([1, 2, 3]),
        }
        self.assertFormulaResult("-x", -d['x'])
        self.assertFormulaResult("sin(x)", numpy.sin(d['x']))
        self.assertFormulaResult("cos(x)", numpy.cos(d['x']))
        self.assertFormulaResult("tan(x)", numpy.tan(d['x']))
        self.assertFormulaResult("log(a)", numpy.log(d['a']))
        self.assertFormulaResult("abs(x)", numpy.abs(d['x']))
        self.assertFormulaResult("round(x)", numpy.round(d['x']))
        self.assertFormulaResult("sign(x)", numpy.sign(d['x']))
        self.assertFormulaResult("x == 0", [0, 1, 0])
        self.assertFormulaResult("x > 0", [1, 0, 0])
        self.assertFormulaResult("x < 0", [0, 0, 1])
        self.assertFormulaResult("x >= 1.0", [1, 0, 0])
        self.assertFormulaResult("x >= 1.2", [1, 0, 0])
        self.assertFormulaResult("x <= 0", [0, 1, 1])
        self.assertFormulaResult("x <= 1", [0, 1, 1])
        self.assertFormulaResult("(x >= 0) & (x <= 0)", [0, 1, 0])
        self.assertFormulaResult("(x > 1) | (x >= 0)", [1, 1, 0])
        self.assertFormulaResult("x + x", [2.4, 0, -2.4])
        self.assertFormulaResult("x - x", [0, 0, 0])
        self.assertFormulaResult("x * x", [1.2 * 1.2, 0, -1.2 * -1.2])
        self.assertFormulaResult("x + y", d['x'] + d['y'])
        self.assertFormulaResult("x / (x + y)", [1, 0, 1])
        self.assertFormulaResult("x * 99999 + 0.5 * y", [1.2 * 99999, 0.5, -1.2 * 99999])
        self.assertFormulaResult("x + y + z + a", d['x'] + d['y'] + d['z'] + d['a'])
        self.assertFormulaResult("a ^ 2", [4, 16, 36])
        self.assertFormulaResult("!b", [False, True, False])
        self.assertFormulaResult("b & c", [True, False, False])
        self.assertFormulaResult("b | c", [True, False, True])
        self.assertFormulaResult("b | !c", [True, True, True])
        self.assertFormulaResult("b == TRUE", [True, False, True])
        self.assertFormulaResult("(b == TRUE) & (c == FALSE)", [False, False, True])
        self.assertFormulaResult("(b == TRUE) | (c == FALSE)", [True, True, True])
        self.assertFormulaResult("d", d['d'])
        # Mix euler number, scientific notation and variable called e
        self.assertFormulaResult("E * 1e5 * e", numpy.e * 1e5 * d['e'])
        # Nested expressions can be evaluated
        self.assertFormulaResult(
            "((a * 2) + (x * 3)) * 6",
            [(2 * 2 + 1.2 * 3) * 6, (4 * 2 + 0 * 3) * 6, (6 * 2 + -1.2 * 3) * 6]
        )
        # Formula is case sensitive
        self.assertFormulaResult("-A", -d['A'])
        # Long variable name is accepted
        self.assertFormulaResult("-aLongVariable", -d['aLongVariable'])
        # Alphanumeric variable name
        self.assertFormulaResult("-A1A", -d['A1A'])
        # Formula with Linebreaks and white space
        self.assertFormulaResult("\n x \n + \r y \r +     z", d['x'] + d['y'] + d['z'])
        # Long formulas mixing logical with numerical expressions
        self.assertFormulaResult('x*(x>1)', d['x'] * (d['x'] > 1))
        self.assertFormulaResult(
            'x*(x>1) + 2*y + 3*z*(z==78)',
            d['x'] * (d['x'] > 1) + 2 * d['y'] + 3 * d['z'] * (d['z'] == 78),
        )
        self.assertFormulaResult('a*(a<=1)+(a>1)', d['a'] * (d['a'] <= 1) + (d['a'] > 1))

    def test_formula_parser_with_unknown_vars(self):
        # Unknown variable raises error
        msg = 'Found an undeclared variable "not_a_var" in formula.'
        with self.assertRaisesMessage(RasterAlgebraException, msg):
            self.parser.evaluate({}, "3 * not_a_var")

    def test_formula_parser_without_formula(self):
        # Unknown variable raises error
        msg = 'Formula not specified.'
        with self.assertRaisesMessage(RasterAlgebraException, msg):
            self.parser.evaluate({})

    def test_with_null_comparison(self):
        mask = [True, True, False]
        self.data = {
            "masked": numpy.ma.masked_array([1, 2, 3], mask=mask),
            "unmasked": numpy.array([1, 2, 3]),
        }
        self.assertFormulaResult('masked == NULL', mask)
        self.assertFormulaResult('masked != NULL', [not x for x in mask])
        self.assertFormulaResult('NULL == masked', mask)
        self.assertFormulaResult('unmasked == NULL', [False, False, False])
        msg = 'NULL can only be used with "==" or "!=" operators.'
        with self.assertRaisesMessage(RasterAlgebraException, msg):
            self.assertFormulaResult('masked >= NULL', mask)
