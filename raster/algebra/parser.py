import numpy
from pyparsing import (
    Forward, Group, Keyword, Literal, ParseException, ParserElement, Regex, Word, alphanums, alphas, infixNotation,
    oneOf, opAssoc, replaceWith
)

from django.contrib.gis.gdal import GDALRaster
from raster.algebra import const
from raster.algebra.evaluators import (
    EvalAdd, EvalAnd, EvalComparison, EvalConstant, EvalExp, EvalFunction, EvalMult, EvalNot, EvalNull, EvalOr,
    EvalUnary, EvalVariable
)
from raster.const import ALGEBRA_PIXEL_TYPE_GDAL, ALGEBRA_PIXEL_TYPE_NUMPY
from raster.exceptions import RasterAlgebraException

# Packratting makes infixNotation parsers much faster
ParserElement.enablePackrat()


class FormulaParser(object):
    """
    Deconstruct mathematical algebra expressions and convert those into
    callable funcitons.

    This formula parser was inspired by the fourFun pyparsing example and also
    benefited from additional substantial contributions by Paul McGuire.
    """

    def __init__(self):
        """
        Setup the Backus Normal Form (BNF) parser logic.
        """
        # Set an empty formula attribute
        self.formula = None

        # The data dictionary holds the values on which to evaluate the formula.
        self.data = {}

        # Instantiate blank parser for BNF construction
        self.bnf = Forward()

        # Expression for parenthesis, which are suppressed in the atoms
        # after matching.
        lpar = Literal("(").suppress()
        rpar = Literal(")").suppress()

        # Expression for mathematical constants: Euler number and Pi
        e = Keyword(const.EULER).setParseAction(replaceWith(numpy.e), EvalConstant)
        pi = Keyword(const.PI).setParseAction(replaceWith(numpy.pi), EvalConstant)

        # Prepare operator expressions
        addop = oneOf(const.ADDOP)
        multop = oneOf(const.MULTOP)
        eqop = oneOf(const.EQUOP)
        sizeeqop = oneOf(const.SIZEEQOP)
        sizeop = oneOf(const.SIZEOP)
        powop = oneOf(const.POWOP)
        unary = oneOf(const.UNOP)
        andop = oneOf(const.ANDOP)
        orop = oneOf(const.OROP)
        notop = oneOf(const.NOTOP)

        # Expression for null values
        null = Keyword(const.NULL).setParseAction(EvalNull)

        # Expression for floating point numbers, allowing for
        # scientific notation.
        number = Regex(r'[+-]?\d+(\.\d*)?([Ee][+-]?\d+)?').setParseAction(EvalConstant)

        # Variables are alphanumeric strings that represent keys in the input
        # data dictionary.
        variable = Word(alphas, alphanums + '_').setParseAction(self.get_variable_data, EvalVariable)

        # Functional calls
        function = Group(Word(alphas, alphanums + "_$") + lpar + self.bnf + rpar)
        function.setParseAction(EvalFunction)

        # True and false keywords
        true_exp = Keyword(const.TRUE).setParseAction(replaceWith(True), EvalConstant)
        false_exp = Keyword(const.FALSE).setParseAction(replaceWith(False), EvalConstant)

        # Arithmetic atom - a single element is either a number, function,
        # math constant or variable.
        arith_atom = number | function | null | true_exp | false_exp | pi | e | variable

        # Arithmetic expression as subelement
        # The order the operators in this list matters due to "<=" being caught by "<".
        arith_expr = infixNotation(
            arith_atom,
            [
                (unary, 1, opAssoc.RIGHT, EvalUnary),
                (powop, 2, opAssoc.LEFT, EvalExp),
                (multop, 2, opAssoc.LEFT, EvalMult),
                (addop, 2, opAssoc.LEFT, EvalAdd),
                (eqop, 2, opAssoc.LEFT, EvalComparison),
                (sizeeqop, 2, opAssoc.LEFT, EvalComparison),
                (sizeop, 2, opAssoc.LEFT, EvalComparison),
            ]
        )

        # The order of the operators matters, see comment above
        comp_expr = Group(arith_expr + (eqop | sizeeqop | sizeop | andop | orop) + arith_expr).setParseAction(EvalComparison)
        bool_term = true_exp | false_exp | comp_expr
        bool_expr = infixNotation(
            bool_term,
            [
                (notop, 1, opAssoc.RIGHT, EvalNot),
                (andop, 2, opAssoc.LEFT, EvalAnd),
                (orop, 2, opAssoc.LEFT, EvalOr)
            ]
        )

        self.bnf <<= bool_expr | arith_expr

    def get_variable_data(self, *args):
        var = args[-1][0]
        if var not in self.variable_map:
            raise RasterAlgebraException('Found an undeclared variable "{0}" in formula.'.format(var))
        return self.variable_map[var]

    def set_formula(self, formula):
        """
        Stores the input formula as the one to evaluate on.
        """
        self.formula = formula

    def evaluate(self, data={}, formula=None):
        """
        Evaluate the input data using the current formula expression stack.
        """
        if formula:
            self.set_formula(formula)

        if not self.formula:
            raise RasterAlgebraException('Formula not specified.')

        # Make sure all data is in numpy format
        for k, v in data.items():
            if not isinstance(v, numpy.ndarray):
                data[k] = numpy.array(v)

        self.variable_map = data

        # Populate the expression stack
        parsed = self.bnf.parseString(self.formula, parseAll=True)[0]

        # Evaluate stack
        return parsed.eval()


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
        result = self.evaluate(data_arrays, formula)

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
