from __future__ import unicode_literals

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
        if data and isinstance(expVal, (list, tuple, numpy.ndarray)) and any(numpy.array(numpy.isnan(expVal))):
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
        self.assertFormulaResult("!TRUE", False)
        self.assertFormulaResult("!1", False)
        self.assertFormulaResult("!-1", False)
        self.assertFormulaResult("!2", False)
        self.assertFormulaResult("2 * 3 * 4 * 5", 2 * 3 * 4 * 5)
        self.assertFormulaResult("2 + 3 + 4 + 5", 2 + 3 + 4 + 5)
        self.assertFormulaResult("(2 + 3 * 6) * ((2 + 3 * (3 * 4 + 1)) + 4 + 5)", 1000)
        self.assertFormulaResult("INF > 0", True)
        self.assertFormulaResult("INF < 0", False)
        self.assertFormulaResult("-INF > 0", False)
        self.assertFormulaResult("~300", 300)

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
            "a_1_a": numpy.array([1, 2, 3]),
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
        self.assertFormulaResult("INF < x", [False, False, False])
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
        self.assertFormulaResult("b & c", [True, False, False])
        self.assertFormulaResult("b | c", [True, False, True])
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
        # Alphanumeric variable name with underscore
        self.assertFormulaResult("-a_1_a", -d['a_1_a'])
        # Formula with Linebreaks and white space
        self.assertFormulaResult("\n x \n + \r y \r +     z", d['x'] + d['y'] + d['z'])
        # Long formulas mixing logical with numerical expressions
        self.assertFormulaResult('x*(x>1)', d['x'] * (d['x'] > 1))
        self.assertFormulaResult(
            '(b>0) & (a > 1) & (c < 1) & (d > 0)',
            (d['b'] > 0) & (d['a'] > 1) & (d['c'] < 1) & (d['a'] > 0)
        )
        self.assertFormulaResult(
            '(a*b)*((b>0) & (a > 1)) + 99*a*(b <=0)',
            d['a'] * d['b'] * ((d['b'] > 0) & (d['a'] > 0)) + 99 * d['a'] * (d['b'] <= 0)
        )
        self.assertFormulaResult(
            'x*(x>1) + 2*y + 3*z*(z==78)',
            d['x'] * (d['x'] > 1) + 2 * d['y'] + 3 * d['z'] * (d['z'] == 78),
        )
        self.assertFormulaResult('a*(a<=1)+(a>1)', d['a'] * (d['a'] <= 1) + (d['a'] > 1))
        self.assertFormulaResult("~a", d['a'])

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
        # Null value propagation in formula
        self.assertFormulaResult("unmasked * (masked != NULL) + 99 * (masked == NULL)", [99, 99, 3])
        # Fill operator removes null values
        self.assertFormulaResult("~masked == NULL", [False, False, False])

    def test_masked_array_result(self):
        data = {
            'x': numpy.ma.masked_array([1, 2, 3], mask=[True, False, False], fill_value=99),
            'y': numpy.ma.masked_array([1, 2, 3], mask=[False, True, False], fill_value=100),
        }
        result = self.parser.evaluate(data, 'x + y')
        self.assertTrue(numpy.ma.is_masked(result))
        self.assertEqual(
            result.compressed().tolist(),
            (data['x'] + data['y']).compressed().tolist()
        )

    def test_fill_operator_result(self):
        data = {
            'x': numpy.ma.masked_array([1, 2, 3], mask=[True, False, False], fill_value=99),
            'y': numpy.ma.masked_array([1, 2, 3], mask=[False, True, False], fill_value=100),
        }
        result = self.parser.evaluate(data, '~x + y')
        self.assertEqual(
            result.compressed().tolist(),
            (data['x'].filled() + data['y']).compressed().tolist()
        )
        result = self.parser.evaluate(data, '~x + ~y')
        self.assertEqual(
            result.tolist(),
            (data['x'].filled() + data['y'].filled()).tolist()
        )
        result = self.parser.evaluate(data, '~x + (~y == NULL)')
        self.assertEqual(
            result.tolist(),
            (data['x'].filled()).tolist()
        )

    def test_re_evaluation(self):
        self.parser.set_formula('+x')
        self.assertEqual(self.parser.evaluate({'x': 1}), 1)
        self.assertEqual(self.parser.evaluate({'x': 2}), 2)
        self.parser.set_formula('-x')
        self.assertEqual(self.parser.evaluate({'x': 3}), -3)
        self.assertEqual(self.parser.evaluate({'x': 4}), -4)

    def test_statistics_functions(self):
        d = self.data = {'x': numpy.random.rand(10), 'y': range(3)}
        self.assertFormulaResult('min(x)', numpy.min(d['x']))
        self.assertFormulaResult('max(x)', numpy.max(d['x']))
        self.assertFormulaResult('mean(x)', numpy.mean(d['x']))
        self.assertFormulaResult('median(x)', numpy.median(d['x']))
        self.assertFormulaResult('std(x)', numpy.std(d['x']))
        self.assertFormulaResult('y * min(x)', numpy.arange(3) * numpy.min(d['x']))

    def test_keyword_variable_exception(self):
        msg = 'Invalid variable name found: "del".'
        with self.assertRaisesMessage(RasterAlgebraException, msg):
            self.parser.evaluate({'del': [1]}, 'del')

    def test_invalid_variables(self):
        d = self.data = {
            '_no': range(5),
            'no_': range(5),
            '__no__': range(5),
            '__': range(5),
        }
        for key, val in d.items():
            msg = 'Invalid variable name found: "{}".'.format(key)
            with self.assertRaisesMessage(RasterAlgebraException, msg):
                self.parser.evaluate({key: val}, key)
