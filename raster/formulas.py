import numpy
from pyparsing import CaselessLiteral, Combine, Forward, Literal, Optional, Word, ZeroOrMore, alphas, nums

from django.contrib.gis.gdal import GDALRaster

from .const import ALGEBRA_PIXEL_TYPE_GDAL, ALGEBRA_PIXEL_TYPE_NUMPY


class FormulaParser(object):
    """
    Deconstruct mathematical algebra expressions and convert those into
    callable funcitons.

    Adopted from: http://pyparsing.wikispaces.com/file/view/fourFn.py
    """
    expr_stack = []

    # The data dictionary holds the values on which to evaluate the formula
    data = {}

    # Map operator symbols to arithmetic operations in numpy
    opn = {
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
        "&": numpy.logical_and
    }

    # Map function names to python functions
    fn = {
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

    def __init__(self):
        """
        Setup the Backus Normal Form (BNF) parser logic.
        """
        point = Literal(".")

        e = CaselessLiteral("E")

        fnumber = Combine(
            Word("+-" + nums, nums) +
            Optional(point + Optional(Word(nums))) +
            Optional(e + Word("+-" + nums, nums))
        )

        ident = Word(alphas, alphas + nums + "_$")

        # Operators
        plus = Literal("+")
        minus = Literal("-")
        mult = Literal("*")
        div = Literal("/")
        eq = Literal("==")
        neq = Literal("!=")
        lt = Literal("<")
        le = Literal("<=")
        gt = Literal(">")
        ge = Literal(">=")
        ior = Literal("|")
        iand = Literal("&")
        lpar = Literal("(").suppress()
        rpar = Literal(")").suppress()
        addop = plus | minus | eq
        multop = mult | div | eq | neq | ge | le | gt | lt | ior | iand  # Order matters here due to "<=" being caught by "<"
        expop = Literal("^")
        pi = CaselessLiteral("PI")

        # Letters for variables
        aa = CaselessLiteral("a")
        bb = CaselessLiteral("b")
        cc = CaselessLiteral("c")
        dd = CaselessLiteral("d")
        ee = CaselessLiteral("e")
        ff = CaselessLiteral("f")
        gg = CaselessLiteral("g")
        hh = CaselessLiteral("h")
        ii = CaselessLiteral("i")
        jj = CaselessLiteral("j")
        kk = CaselessLiteral("k")
        ll = CaselessLiteral("l")
        mm = CaselessLiteral("m")
        nn = CaselessLiteral("n")
        oo = CaselessLiteral("o")
        pp = CaselessLiteral("p")
        qq = CaselessLiteral("q")
        rr = CaselessLiteral("r")
        ss = CaselessLiteral("s")
        tt = CaselessLiteral("t")
        uu = CaselessLiteral("u")
        vv = CaselessLiteral("v")
        ww = CaselessLiteral("w")
        xx = CaselessLiteral("x")
        yy = CaselessLiteral("y")
        zz = CaselessLiteral("z")

        bnf = Forward()

        atom = (
            Optional('-') + Optional("!") + (
                pi | e | fnumber | ident + lpar + bnf + rpar |  # pi needs to be before the letters for it to be found
                aa | bb | cc | dd | ee | ff | gg | hh | ii | jj | kk | ll | mm |
                nn | oo | pp | qq | rr | ss | tt | uu | vv | ww | xx | yy | zz
            ).setParseAction(self.push_first) | (lpar + bnf.suppress() + rpar)
        ).setParseAction(self.push_unary_operator)

        # By defining exponentiation as "atom [ ^ factor ]..." instead of "atom [ ^ atom ]...",
        # we get right-to-left exponents, instead of left-to-righ
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor << atom + ZeroOrMore((expop + factor).setParseAction(self.push_first))

        term = factor + ZeroOrMore((multop + factor).setParseAction(self.push_first))
        bnf << term + ZeroOrMore((addop + term).setParseAction(self.push_first))

        self.bnf = bnf

    def push_first(self, strg, loc, toks):
        self.expr_stack.append(toks[0])

    def push_unary_operator(self, strg, loc, toks):
        """
        Sets custom flag for unary operators.
        """
        if toks:
            if toks[0] == '-':
                self.expr_stack.append('unary -')
            elif toks[0] == '!':
                self.expr_stack.append('unary !')

    def evaluate_stack(self, stack):
        """
        Evaluate a stack element.
        """
        # Get operator element
        op = stack.pop()

        # Evaluate unary operators
        if op == 'unary -':
            return -self.evaluate_stack(stack)
        if op == 'unary !':
            return numpy.logical_not(self.evaluate_stack(stack))

        # Evaluate binary operators
        if op in ["+", "-", "*", "/", "^", ">", "<", "==", "!=", "<=", ">=", "|", "&", "!"]:
            op2 = self.evaluate_stack(stack)
            op1 = self.evaluate_stack(stack)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return numpy.pi
        elif op == "E":
            return numpy.e
        elif op in self.fn:
            return self.fn[op](self.evaluate_stack(stack))
        elif op[0].isalpha() and len(op[0]) == 1 and op[0] in self.data:
            return self.data[op[0]]
        elif op[0].isalpha() and len(op[0]) == 1:
            raise Exception('Found an undeclared variable in formula.')
        else:
            # If numeric, convert to numpy float
            return numpy.array(op, dtype=ALGEBRA_PIXEL_TYPE_NUMPY)

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
            raise Exception('Please specify a formula to evaluate.')

        # Update dataset
        if data:
            self.data = data

        # Evaluate stack on data
        self.result = self.evaluate_stack(self.expr_stack)

        return self.result

    def evaluate_formula(self, formula, data={}):
        """
        Helper function to set formula and evaluate in one call.
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
            self.check_aligned(data.values())

        # Construct list of numpy arrays holding raster pixel data
        data_arrays = {
            key: numpy.ma.masked_values(rast.bands[0].data().ravel(), rast.bands[0].nodata_value)
            for key, rast in data.items()
        }

        # Evaluate formula on raster data
        result = self.evaluate_formula(formula, data_arrays)

        # Reference first original raster for constructing result
        orig = data.values()[0]
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
            raise Exception('Raster aligment check failed: SRIDs not all the same')

        gt = rasters[0].geotransform
        if any([gt != rast.geotransform for rast in rasters[1:]]):
            raise Exception('Raster aligment check failed: geotransform arrays are not all the same')
