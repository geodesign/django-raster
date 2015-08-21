import numpy

from django.test import TestCase
from raster.formulas import FormulaParser

parser = FormulaParser()


class FormulaParserTests(TestCase):

    def assertFormulaResult(self, formula, expVal, data={}):
        val = parser.evaluate_formula(formula, data)
        self.assertTrue((val == numpy.array(expVal)).all())

    def test_formula_parser_without_vars(self):
        self.assertFormulaResult("9", 9)
        self.assertFormulaResult("-9", -9)
        self.assertFormulaResult("--9", 9)
        self.assertFormulaResult("-E", -numpy.e)
        self.assertFormulaResult("9 + 3 + 6", 9 + 3 + 6)
        self.assertFormulaResult("9 + 3 / 11", 9 + 3.0 / 11)
        self.assertFormulaResult("(9 + 3)", (9 + 3))
        self.assertFormulaResult("(9+3) / 11", (9 + 3.0) / 11)
        self.assertFormulaResult("9 - 12 - 6", 9 - 12 - 6)
        self.assertFormulaResult("9 - (12 - 6)", 9 - (12 - 6))
        self.assertFormulaResult("2*3.14159", 2 * 3.14159)
        self.assertFormulaResult("3.1415926535*3.1415926535 / 10", 3.1415926535 * 3.1415926535 / 10)
        self.assertFormulaResult("PI * PI / 10", numpy.pi * numpy.pi / 10)
        self.assertFormulaResult("PI*PI/10", numpy.pi * numpy.pi / 10)
        self.assertFormulaResult("PI^2", numpy.pi ** 2)
        self.assertFormulaResult("round(PI^2)", round(numpy.pi ** 2))
        self.assertFormulaResult("6.02E23 * 8.048", 6.02E23 * 8.048)
        self.assertFormulaResult("e / 3", numpy.e / 3)
        self.assertFormulaResult("sin(PI/2)", numpy.sin(numpy.pi / 2))
        self.assertFormulaResult("int(E)", int(numpy.e))
        self.assertFormulaResult("int(-E)", int(-numpy.e))
        self.assertFormulaResult("round(E)", round(numpy.e))
        self.assertFormulaResult("round(-E)", round(-numpy.e))
        self.assertFormulaResult("E^PI", numpy.e ** numpy.pi)
        self.assertFormulaResult("2^3^2", 2 ** 3 ** 2)
        self.assertFormulaResult("2^3+2", 2 ** 3 + 2)
        self.assertFormulaResult("2^9", 2 ** 9)
        self.assertFormulaResult("sign(-2)", -1)
        self.assertFormulaResult("sign(0)", 0)
        self.assertFormulaResult("sign(0.1)", 1)
        self.assertFormulaResult("exp(0)", numpy.e)
        self.assertFormulaResult("log(1)", 0)
        self.assertFormulaResult("99999", 99999)

    def test_formula_parser_with_vars(self):
        data = {
            "x": numpy.array([1.2, 0, -1.2]),
            "y": numpy.array([0, 1, 0])
        }
        self.assertFormulaResult("sin(x)", numpy.sin(data['x']), data)
        self.assertFormulaResult("x == 0", [0, 1, 0], data)
        self.assertFormulaResult("x > 0", [1, 0, 0], data)
        self.assertFormulaResult("x < 0", [0, 0, 1], data)
        self.assertFormulaResult("x >= 1", [1, 0, 0], data)
        self.assertFormulaResult("x >= 1.2", [1, 0, 0], data)
        self.assertFormulaResult("x <= 0", [0, 1, 1], data)
        self.assertFormulaResult("x <= 1", [0, 1, 1], data)
        self.assertFormulaResult("(x >= 0)*(x <= 0)", [0, 1, 0], data)
        self.assertFormulaResult("(x >= 0)&(x <= 0)", [0, 1, 0], data)
        self.assertFormulaResult("(x > 1)+(x >= 0)", [1, 1, 0], data)
        self.assertFormulaResult("(x > 1)|(x >= 0)", [1, 1, 0], data)
        self.assertFormulaResult("x + x", [2.4, 0, -2.4], data)
        self.assertFormulaResult("x - x", [0, 0, 0], data)
        self.assertFormulaResult("x * x", [1.2 * 1.2, 0, -1.2 * -1.2], data)
        self.assertFormulaResult("x / (x + y)", [1, 0, 1], data)
        self.assertFormulaResult("x * 99999 + 0.5*y)", [1.2 * 99999, 0.5, -1.2 * 99999], data)
