import operator
from functools import reduce

import numpy
from pyparsing import (
    CaselessLiteral, Combine, Forward, Literal, Optional, ParseException, Word, ZeroOrMore, alphanums, alphas, nums
)

from django.contrib.gis.gdal import GDALRaster

from .const import ALGEBRA_PIXEL_TYPE_GDAL, ALGEBRA_PIXEL_TYPE_NUMPY


class FormulaParser(object):
    """
    Deconstruct mathematical algebra expressions and convert those into
    callable funcitons.

    Adopted from: http://pyparsing.wikispaces.com/file/view/fourFn.py
    """
    # Map function names to numpy functions
    numpy_functions = {
        "sin": numpy.sin,
        "cos": numpy.cos,
        "tan": numpy.tan,
        "log": numpy.log,
        "exp": numpy.exp,
        "abs": numpy.abs,
        "int": numpy.int,
        "round": numpy.round,
        "sign": numpy.sign,
    }

    # Map operator symbols to arithmetic operations in numpy
    numpy_operators = {
        "+": numpy.add,
        "-": numpy.subtract,
        "*": numpy.multiply,
        "/": numpy.divide,
        "^": numpy.power,
        "==": numpy.equal,
        "!=": numpy.not_equal,
        ">": numpy.greater,
        ">=": numpy.greater_equal,
        "<": numpy.less,
        "<=": numpy.less_equal,
        "|": numpy.logical_or,
        "&": numpy.logical_and,
    }

    numpy_unary_operators = {
        "unary !": numpy.logical_not,
        "unary -": numpy.negative,
    }

    # Additive operators
    addop = ("+", "-", "==")

    # Exponential operator
    expop = ("^", )

    # Unary operators
    unary = {"-": "unary -", "!": "unary !"}

    # Multiplicative operators. The order the operators in this list
    # matters due to "<=" being caught by "<".
    multop = ("*", "/", "!=", "<=", ">=", "<", ">", "|", "&")

    # Euler number and pi
    euler = 'E'
    pi = 'PI'

    def __init__(self):
        """
        Setup the Backus Normal Form (BNF) parser logic.
        """
        # The data dictionary holds the values on which to evaluate the formula.
        self.data = {}

        # The list holding parsed expressions used for evaluation of the formula.
        self.expr_stack = []

        # Instantiate blank parser for BNF construction
        self.bnf = Forward()

        # Expression for parenthesis, which are suppressed in the atoms
        # after matching.
        lpar = Literal("(").suppress()
        rpar = Literal(")").suppress()

        # Expression for mathematical constants: Euler number and Pi
        e = Literal(self.euler)
        pi = Literal(self.pi)

        # Prepare operator expressions
        addop = reduce(operator.or_, (Literal(x) for x in self.addop))
        multop = reduce(operator.or_, (Literal(x) for x in self.multop))
        expop = reduce(operator.or_, (Literal(x) for x in self.expop))
        unary = reduce(operator.add, (Optional(x) for x in self.unary.keys()))

        # Expression for floating point numbers, allowing for
        # scientific notation.
        number = Combine(
            Word("+-" + nums, nums) +
            Optional(Literal('.') + Optional(Word(nums))) +
            Optional(CaselessLiteral('e') + Word("+-" + nums, nums))
        )

        # Variables are alphanumeric strings that represent keys in the input
        # data dictionary.
        variable = Word(alphanums)

        # Functional calls
        function = Word(alphas, alphas + nums + "_$") + lpar + self.bnf + rpar

        # Atom core - a single element is either a math constant,
        # a function or a variable.
        atom_core = function | pi | e | number | variable

        # Atom subelement between parenthesis
        atom_subelement = lpar + self.bnf.suppress() + rpar

        # In atoms, pi and e need to be before the letters for it to be found
        atom = (
            unary + atom_core.setParseAction(self.push_first) | atom_subelement
        ).setParseAction(self.push_unary_operator)

        # By defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of
        # left-to-right that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor << atom + ZeroOrMore((expop + factor).setParseAction(self.push_first))

        term = factor + ZeroOrMore((multop + factor).setParseAction(self.push_first))
        self.bnf << term + ZeroOrMore((addop + term).setParseAction(self.push_first))

    def push_first(self, strg, loc, toks):
        self.expr_stack.append(toks[0])

    def push_unary_operator(self, strg, loc, toks):
        """
        Set custom flag for unary operators.
        """
        if toks and toks[0] in self.unary:
            self.expr_stack.append(self.unary[toks[0]])

    def evaluate_stack(self, stack):
        """
        Evaluate a stack element.
        """
        op = stack.pop()

        if op in self.numpy_unary_operators:
            return self.numpy_unary_operators[op](self.evaluate_stack(stack))
        elif op in self.numpy_operators.keys():
            op2 = self.evaluate_stack(stack)
            op1 = self.evaluate_stack(stack)
            return self.numpy_operators[op](op1, op2)
        elif op in self.numpy_functions:
            return self.numpy_functions[op](self.evaluate_stack(stack))
        elif op == self.euler:
            return numpy.e
        elif op == self.pi:
            return numpy.pi
        elif op in self.data:
            return self.data[op]
        else:
            try:
                return numpy.array(op, dtype=ALGEBRA_PIXEL_TYPE_NUMPY)
            except ValueError:
                raise ParseException('Found an undeclared variable in formula.')

    def parse_formula(self, formula):
        """
        Parse a string formula into a BNF expression.
        """
        # Clean formula before parsing
        formula = self.clean_formula(formula)

        # Reset expression stack
        self.expr_stack = []

        # Use bnf to parse the string
        self.bnf.parseString(formula)

    def clean_formula(self, formula):
        """
        Remove any white space and line breaks from formula.
        """
        return formula.replace(' ', '').replace('\n', '').replace('\r', '')

    def evaluate(self, data=None):
        """
        Evaluate the input data using the current formula expression stack.
        """
        # Make sure a formula has been parsed before evaluating
        if self.expr_stack == []:
            raise ParseException('Please specify a formula to evaluate.')

        # Update dataset
        if data:
            self.data = data

        # Evaluate stack on data
        self.result = self.evaluate_stack(self.expr_stack)

        return self.result

    def evaluate_formula(self, formula, data={}):
        """
        Set formula and evaluate in one call.
        """
        self.parse_formula(formula)
        return self.evaluate(data)


class RasterAlgebraParser(FormulaParser):
    """
    Compute raster algebra expressions using the FormulaParser class.
    """

    def evaluate_raster_algebra(self, data, formula, check_aligned=False):
        """
        Evaluate a raster algebra expression on a set of rasters. All input
        rasters need to be strictly aligned (same size, geotransform and srid).

        The input raster list will be zipped into a dictionary using the input
        names. The resulting dictionary will be used as input data for formula
        evaluation. If the check_aligned flag is set, the input rasters are
        compared to make sure they are aligned.
        """
        # Check that all input rasters are aligned
        if check_aligned:
            self.check_aligned(list(data.values()))

        # Construct list of numpy arrays holding raster pixel data
        data_arrays = {
            key: numpy.ma.masked_values(rast.bands[0].data().ravel(), rast.bands[0].nodata_value)
            for key, rast in data.items()
        }

        # Evaluate formula on raster data
        result = self.evaluate_formula(formula, data_arrays)

        # Reference first original raster for constructing result
        orig = list(data.values())[0]
        orig_band = orig.bands[0]

        # Convert to default number type
        result = result.astype(ALGEBRA_PIXEL_TYPE_NUMPY)

        # Return GDALRaster holding results
        return GDALRaster({
            'datatype': ALGEBRA_PIXEL_TYPE_GDAL,
            'driver': 'MEM',
            'width': orig.width,
            'height': orig.height,
            'nr_of_bands': 1,
            'srid': orig.srs.srid,
            'origin': orig.origin,
            'scale': orig.scale,
            'skew': orig.skew,
            'bands': [{
                'nodata_value': orig_band.nodata_value,
                'data': result
            }],
        })

    def check_aligned(self, rasters):
        """
        Assert that all input rasters are properly aligned.
        """
        if not len(set([x.srs.srid for x in rasters])) == 1:
            raise ParseException('Raster aligment check failed: SRIDs not all the same')

        gt = rasters[0].geotransform
        if any([gt != rast.geotransform for rast in rasters[1:]]):
            raise ParseException('Raster aligment check failed: geotransform arrays are not all the same')
