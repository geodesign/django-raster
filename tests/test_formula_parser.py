import numpy

from django.test import TestCase
from raster.formulas import FormulaParser


class FormulaParserTests(TestCase):

    def assertFormulaResult(self, formula, expVal, data={}):
        parser = FormulaParser()

        val = parser.evaluate_formula(formula, data)

        # Drop nan values
        if data and any(numpy.isnan(expVal)):
            val = val[numpy.logical_not(numpy.isnan(val))]
            expVal = expVal[numpy.logical_not(numpy.isnan(expVal))]

        # Assert non nan values are as expected
        self.assertTrue((numpy.array(val) == expVal).all())

        # Check that nan values are the same
        self.assertTrue(numpy.array_equal(numpy.isnan(expVal), numpy.isnan(val)))

    def test_formula_parser_without_vars(self):
        self.assertFormulaResult("9", 9)
        self.assertFormulaResult("-9", -9)
        self.assertFormulaResult("--9", 9)
        self.assertFormulaResult("-E", -numpy.e)
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
        self.assertFormulaResult("e / 3", numpy.e / 3)
        self.assertFormulaResult("sin(PI / 2)", numpy.sin(numpy.pi / 2))
        self.assertFormulaResult("cos(PI / 5)", numpy.cos(numpy.pi / 5))
        self.assertFormulaResult("int(E)", int(numpy.e))
        self.assertFormulaResult("int(-E)", int(-numpy.e))
        self.assertFormulaResult("round(E)", round(numpy.e))
        self.assertFormulaResult("round(-E)", round(-numpy.e))
        self.assertFormulaResult("E^PI", numpy.e ** numpy.pi)
        self.assertFormulaResult("2^3^2", 2 ** 3 ** 2)
        self.assertFormulaResult("2^3 + 2", 2 ** 3 + 2)
        self.assertFormulaResult("2^9", 2 ** 9)
        self.assertFormulaResult("sign(-2)", -1)
        self.assertFormulaResult("sign(0)", 0)
        self.assertFormulaResult("sign(0.1)", 1)
        self.assertFormulaResult("exp(0)", numpy.e)
        self.assertFormulaResult("log(1)", 0)
        self.assertFormulaResult("0 | 1", 1)
        self.assertFormulaResult("1 & 1", 1)
        self.assertFormulaResult("1 & 0", 0)
        self.assertFormulaResult("2 > 1", True)
        self.assertFormulaResult("2 >= 1", True)
        self.assertFormulaResult("2 < 1", False)
        self.assertFormulaResult("2 <= 1", False)
        self.assertFormulaResult("1 == 1", True)
        self.assertFormulaResult("1 != 2", True)
        self.assertFormulaResult("!1", False)

    def test_formula_parser_with_vars(self):
        data = {
            "a": numpy.array([2, 4, 6]),
            "b": numpy.array([True, False, True]),
            "c": numpy.array([True, False, False]),
            "x": numpy.array([1.2, 0, -1.2]),
            "y": numpy.array([0, 1, 0]),
            "z": numpy.array([-5, 78, 912]),
            "u": numpy.array([2, 4, 6]),
            "A": numpy.array([1E5]),
        }
        self.assertFormulaResult("-x", -data['x'], data)
        self.assertFormulaResult("sin(x)", numpy.sin(data['x']), data)
        self.assertFormulaResult("cos(x)", numpy.cos(data['x']), data)
        self.assertFormulaResult("tan(x)", numpy.tan(data['x']), data)
        self.assertFormulaResult("log(a)", numpy.log(data['a']), data)
        self.assertFormulaResult("abs(x)", numpy.abs(data['x']), data)
        self.assertFormulaResult("round(x)", numpy.round(data['x']), data)
        self.assertFormulaResult("sign(x)", numpy.sign(data['x']), data)
        self.assertFormulaResult("x == 0", [0, 1, 0], data)
        self.assertFormulaResult("x > 0", [1, 0, 0], data)
        self.assertFormulaResult("x < 0", [0, 0, 1], data)
        self.assertFormulaResult("x >= 1.0", [1, 0, 0], data)
        self.assertFormulaResult("x >= 1.2", [1, 0, 0], data)
        self.assertFormulaResult("x <= 0", [0, 1, 1], data)
        self.assertFormulaResult("x <= 1", [0, 1, 1], data)
        self.assertFormulaResult("(x >= 0) * (x <= 0)", [0, 1, 0], data)
        self.assertFormulaResult("(x >= 0) & (x <= 0)", [0, 1, 0], data)
        self.assertFormulaResult("(x > 1) + (x >= 0)", [1, 1, 0], data)
        self.assertFormulaResult("(x > 1) | (x >= 0)", [1, 1, 0], data)
        self.assertFormulaResult("x + x", [2.4, 0, -2.4], data)
        self.assertFormulaResult("x - x", [0, 0, 0], data)
        self.assertFormulaResult("x * x", [1.2 * 1.2, 0, -1.2 * -1.2], data)
        self.assertFormulaResult("x / (x + y)", [1, 0, 1], data)
        self.assertFormulaResult("x * 99999 + 0.5 * y)", [1.2 * 99999, 0.5, -1.2 * 99999], data)
        self.assertFormulaResult("x + y + z + a)", data['x'] + data['y'] + data['z'] + data['a'], data)
        self.assertFormulaResult("a ^ 2)", [4, 16, 36], data)
        self.assertFormulaResult("!b", [False, True, False], data)
        self.assertFormulaResult("b & c", [True, False, False], data)
        self.assertFormulaResult("b | c", [True, False, True], data)
        self.assertFormulaResult("b | !c", [True, True, True], data)
        # Nested expressions can be evaluated
        self.assertFormulaResult(
            "((a * 2) + (x * 3)) * 6",
            [(2 * 2 + 1.2 * 3) * 6, (4 * 2 + 0 * 3) * 6, (6 * 2 + -1.2 * 3) * 6],
            data
        )
        # Formula is case sensitive
        self.assertFormulaResult("-A", -data['A'], data)

        # This is not desired behavior, should be changed in formula parser
        # to raise error or accept multi character words.
        self.assertFormulaResult("aaa", data['a'], data)
