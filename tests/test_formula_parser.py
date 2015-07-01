import numpy

from django.test import TestCase
from raster.formulas import FormulaParser


class FormulaParserTests(TestCase):
    def parse_formula(self, formula, expVal, data={}):
        parser = FormulaParser()
        val = parser.eval_formula(formula, data)
        self.assertTrue((val == numpy.array(expVal)).all())

    def test_formula_parser_without_vars(self):
        self.parse_formula("9", 9)
        self.parse_formula("-9", -9)
        self.parse_formula("--9", 9)
        self.parse_formula("-E", -numpy.e)
        self.parse_formula("9 + 3 + 6", 9 + 3 + 6)
        self.parse_formula("9 + 3 / 11", 9 + 3.0 / 11)
        self.parse_formula("(9 + 3)", (9 + 3))
        self.parse_formula("(9+3) / 11", (9 + 3.0) / 11)
        self.parse_formula("9 - 12 - 6", 9 - 12 - 6)
        self.parse_formula("9 - (12 - 6)", 9 - (12 - 6))
        self.parse_formula("2*3.14159", 2 * 3.14159)
        self.parse_formula("3.1415926535*3.1415926535 / 10", 3.1415926535 * 3.1415926535 / 10)
        self.parse_formula("PI * PI / 10", numpy.pi * numpy.pi / 10)
        self.parse_formula("PI*PI/10", numpy.pi * numpy.pi / 10)
        self.parse_formula("PI^2", numpy.pi ** 2)
        self.parse_formula("round(PI^2)", round(numpy.pi ** 2))
        self.parse_formula("6.02E23 * 8.048", 6.02E23 * 8.048)
        self.parse_formula("e / 3", numpy.e / 3)
        self.parse_formula("sin(PI/2)", numpy.sin(numpy.pi / 2))
        self.parse_formula("trunc(E)", int(numpy.e))
        self.parse_formula("trunc(-E)", int(-numpy.e))
        self.parse_formula("round(E)", round(numpy.e))
        self.parse_formula("round(-E)", round(-numpy.e))
        self.parse_formula("E^PI", numpy.e ** numpy.pi)
        self.parse_formula("2^3^2", 2 ** 3 ** 2)
        self.parse_formula("2^3+2", 2 ** 3 + 2)
        self.parse_formula("2^9", 2 ** 9)
        self.parse_formula("sgn(-2)", -1)
        self.parse_formula("sgn(0)", 0)
        self.parse_formula("sgn(0.1)", 1)

    def test_formula_parser_with_vars(self):
        data = {
            "x": numpy.array([1.2, 0, -1.2]),
            "y": numpy.array([0, 1, 0])
        }
        self.parse_formula("sin(x)", numpy.sin(data['x']), data)
        self.parse_formula("x == 0", [0, 1, 0], data)
        self.parse_formula("x > 0", [1, 0, 0], data)
        self.parse_formula("x < 0", [0, 0, 1], data)
        self.parse_formula("x >= 1", [1, 0, 0], data)
        self.parse_formula("x >= 1.2", [1, 0, 0], data)
        self.parse_formula("x <= 0", [0, 1, 1], data)
        self.parse_formula("x <= 1", [0, 1, 1], data)
        self.parse_formula("(x >= 0)*(x <= 0)", [0, 1, 0], data)
        self.parse_formula("(x >= 0)&(x <= 0)", [0, 1, 0], data)
        self.parse_formula("(x > 1)+(x >= 0)", [1, 1, 0], data)
        self.parse_formula("(x > 1)|(x >= 0)", [1, 1, 0], data)
        self.parse_formula("x + x", [2.4, 0, -2.4], data)
        self.parse_formula("x - x", [0, 0, 0], data)
        self.parse_formula("x * x", [1.2 * 1.2, 0, -1.2 * -1.2], data)
        self.parse_formula("x / (x + y)", [1, 0, 1], data)
