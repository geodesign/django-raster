from __future__ import unicode_literals

import keyword
import operator
from functools import reduce

import numpy
from pyparsing import Forward, Keyword, Literal, Optional, Regex, Word, ZeroOrMore, alphanums, delimitedList, oneOf

from django.contrib.gis.gdal import GDALRaster
from django.utils import six
from raster.algebra import const
from raster.exceptions import RasterAlgebraException


class FormulaParser(object):
    """
    Deconstruct mathematical algebra expressions and convert those into
    callable funcitons.


    Deconstruct mathematical algebra expressions and convert those into
    callable funcitons.

    This formula parser was inspired by the fourFun pyparsing example and also
    benefited from additional substantial contributions by Paul McGuire.
    This module uses pyparsing for this purpose and the parser is adopted from
    the `fourFun example`__.

    Example usage::

        >>> parser = FormulaParser()
        >>> parser.set_formula('log(a * 3 + b)')
        >>> parser.evaluate({'a': 5, 'b': 23})
        ... 3.6375861597263857
        >>> parser.evaluate({'a': [5, 6, 7], 'b': [23, 24, 25]})
        ... array([ 3.63758616,  3.73766962,  3.8286414 ])

    __ http://pyparsing.wikispaces.com/file/view/fourFn.py
    """

    def __init__(self):
        """
        Setup the Backus Normal Form (BNF) parser logic.
        """
        # Set an empty formula attribute
        self.formula = None

        # Instantiate blank parser for BNF construction
        self.bnf = Forward()

        # Expression for parenthesis, which are suppressed in the atoms
        # after matching.
        lpar = Literal(const.LPAR).suppress()
        rpar = Literal(const.RPAR).suppress()

        # Expression for mathematical constants: Euler number and Pi
        e = Keyword(const.EULER)
        pi = Keyword(const.PI)
        null = Keyword(const.NULL)
        _true = Keyword(const.TRUE)
        _false = Keyword(const.FALSE)

        # Prepare operator expressions
        addop = oneOf(const.ADDOP)
        multop = oneOf(const.MULTOP)
        powop = oneOf(const.POWOP)
        unary = reduce(operator.add, (Optional(x) for x in const.UNOP))

        # Expression for floating point numbers, allowing for scientific notation.
        number = Regex(const.NUMBER)

        # Variables are alphanumeric strings that represent keys in the input
        # data dictionary.
        variable = delimitedList(Word(alphanums), delim=const.VARIABLE_NAME_SEPARATOR, combine=True)

        # Functional calls
        function = Word(alphanums) + lpar + self.bnf + rpar

        # Atom core - a single element is either a math constant,
        # a function or a variable.
        atom_core = function | pi | e | null | _true | _false | number | variable

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
        factor << atom + ZeroOrMore((powop + factor).setParseAction(self.push_first))

        term = factor + ZeroOrMore((multop + factor).setParseAction(self.push_first))
        self.bnf << term + ZeroOrMore((addop + term).setParseAction(self.push_first))

    def push_first(self, strg, loc, toks):
        self.expr_stack.append(toks[0])

    def push_unary_operator(self, strg, loc, toks):
        """
        Set custom flag for unary operators.
        """
        if toks and toks[0] in const.UNARY_REPLACE_MAP:
            self.expr_stack.append(const.UNARY_REPLACE_MAP[toks[0]])

    def evaluate_stack(self, stack):
        """
        Evaluate a stack element.
        """
        op = stack.pop()

        if op in const.UNARY_OPERATOR_MAP:
            return const.UNARY_OPERATOR_MAP[op](self.evaluate_stack(stack))

        elif op in const.OPERATOR_MAP:
            op2 = self.evaluate_stack(stack)
            op1 = self.evaluate_stack(stack)
            # Handle null case
            if isinstance(op1, six.string_types) and op1 == const.NULL:
                op2 = self.get_mask(op2, op)
                op1 = True
            elif isinstance(op2, six.string_types) and op2 == const.NULL:
                op1 = self.get_mask(op1, op)
                op2 = True
            return const.OPERATOR_MAP[op](op1, op2)

        elif op in const.FUNCTION_MAP:
            return const.FUNCTION_MAP[op](self.evaluate_stack(stack))

        elif op in const.KEYWORD_MAP:
            return const.KEYWORD_MAP[op]

        elif op in self.variable_map:
            return self.variable_map[op]

        else:
            try:
                return numpy.array(op, dtype=const.ALGEBRA_PIXEL_TYPE_NUMPY)
            except ValueError:
                raise RasterAlgebraException('Found an undeclared variable "{0}" in formula.'.format(op))

    @staticmethod
    def get_mask(data, operator):
        # Make sure the right operator is used
        if operator not in (const.EQUAL, const.NOT_EQUAL):
            raise RasterAlgebraException('NULL can only be used with "==" or "!=" operators.')
        # Get mask
        if numpy.ma.is_masked(data):
            return data.mask
        # If there is no mask, all values are not null
        return numpy.zeros(data.shape, dtype=numpy.bool)

    def set_formula(self, formula):
        """
        Store the input formula as the one to evaluate on.
        """
        # Remove any white space and line breaks from formula.
        self.formula = formula.replace(' ', '').replace('\n', '').replace('\r', '')

    def prepare_data(self):
        """
        Basic checks and conversion of input data.
        """
        for key, var in self.variable_map.items():
            # Keywords are not allowed as variables, variables can not start or
            # end with separator.
            if keyword.iskeyword(key) or key != key.strip(const.VARIABLE_NAME_SEPARATOR):
                raise RasterAlgebraException('Invalid variable name found: "{}".'.format(key))

            # Convert all data to numpy arrays
            if not isinstance(var, numpy.ndarray):
                self.variable_map[key] = numpy.array(var)

    def evaluate(self, data={}, formula=None):
        """
        Evaluate the input data using the current formula expression stack.

        The formula is stored as attribute and can be re-evaluated with several
        input data sets on an existing parser.
        """
        if formula:
            self.set_formula(formula)

        if not self.formula:
            raise RasterAlgebraException('Formula not specified.')

        # Store data for variables
        self.variable_map = data

        # Check and convert input data
        self.prepare_data()

        # Reset expression stack
        self.expr_stack = []

        # Populate the expression stack
        self.bnf.parseString(self.formula)

        # Evaluate stack on data
        return self.evaluate_stack(self.expr_stack)


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

        # Construct list of numpy arrays holding raster pixel data, converting
        # data to default number type. This is necessary because formula
        # evaluation can lead to unexpected results. This could be
        # differentiated in the future based on data types and formulas.
        data_arrays = {}
        for key, rast in data.items():

            keysplit = key.split(const.BAND_INDEX_SEPARATOR)

            variable = keysplit[0]

            if len(keysplit) > 1:
                band_index = int(keysplit[1])
            else:
                band_index = 0

            data_arrays[variable] = numpy.ma.masked_values(
                rast.bands[band_index].data().ravel().astype(const.ALGEBRA_PIXEL_TYPE_NUMPY),
                rast.bands[band_index].nodata_value
            )

        # Evaluate formula on raster data
        result = self.evaluate(data_arrays, formula)

        # Reference first original raster for constructing result
        orig = list(data.values())[0]

        # Get nodata value from mask or from original band data
        if numpy.ma.is_masked(result):
            # Get mask fill value
            nodata = float(result.fill_value)
            # Overwrite result with mask values filled in
            result = result.filled()
        else:
            nodata = orig.bands[0].nodata_value

        # Return GDALRaster holding results
        return GDALRaster({
            'datatype': const.ALGEBRA_PIXEL_TYPE_GDAL,
            'driver': 'MEM',
            'width': orig.width,
            'height': orig.height,
            'nr_of_bands': 1,
            'srid': orig.srs.srid,
            'origin': orig.origin,
            'scale': orig.scale,
            'skew': orig.skew,
            'bands': [{
                'nodata_value': nodata,
                'data': result,
            }],
        })

    def check_aligned(self, rasters):
        """
        Assert that all input rasters are properly aligned.
        """
        if not len(set([x.srs.srid for x in rasters])) == 1:
            raise RasterAlgebraException('Raster aligment check failed: SRIDs not all the same')

        gt = rasters[0].geotransform
        if any([gt != rast.geotransform for rast in rasters[1:]]):
            raise RasterAlgebraException('Raster aligment check failed: geotransform arrays are not all the same')
