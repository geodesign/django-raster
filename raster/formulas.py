import numpy
from pyparsing import CaselessLiteral, Combine, Forward, Literal, Optional, Word, ZeroOrMore, alphas, nums


class FormulaParser(object):
    """
    Deconstructs a raster algebra expression and converts it into a callable.
    http://pyparsing.wikispaces.com/file/view/fourFn.py
    """
    epsilon = 1e-12

    # Map operator symbols to corresponding arithmetic operations in numpy
    opn = {
        "+": numpy.add,
        "-": numpy.subtract,
        "*": numpy.multiply,
        "/": numpy.divide,
        "^": numpy.power,
        "==": numpy.equal,
        ">": numpy.greater,
        ">=": numpy.greater_equal,
        "<": numpy.less,
        "<=": numpy.less_equal,
        "|": numpy.logical_or,
        "&": numpy.logical_and,
        "!": numpy.logical_not,
    }

    exprStack = []
    tiles = {}

    def __init__(self):
        self.fn = {
            "sin": numpy.sin,
            "cos": numpy.cos,
            "tan": numpy.tan,
            "abs": abs,
            "trunc": lambda a: int(a),
            "round": round,
            "sgn": lambda a: abs(a) > self.epsilon and cmp(a, 0) or 0,
        }

    def pushFirst(self, strg, loc, toks):
        self.exprStack.append(toks[0])

    def pushUMinus(self, strg, loc, toks):
        if toks and toks[0] == '-':
            self.exprStack.append('unary -')

    _bnf = None

    @property
    def bnf(self):
        """
        expop   :: '^'
        multop  :: '*' | '/'
        addop   :: '+' | '-'
        integer :: ['+' | '-'] '0'..'9'+
        atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
        factor  :: atom [ expop factor ]*
        term    :: factor [ multop factor ]*
        expr    :: term [ addop term ]*
        """
        if not self._bnf:
            point = Literal(".")
            e = CaselessLiteral("E")
            fnumber = Combine(
                Word("+-" + nums, nums) +
                Optional(point + Optional(Word(nums))) +
                Optional(e + Word("+-" + nums, nums))
            )
            ident = Word(alphas, alphas + nums + "_$")

            plus = Literal("+")
            minus = Literal("-")
            mult = Literal("*")
            div = Literal("/")
            eq = Literal("==")
            lt = Literal("<")
            le = Literal("<=")
            gt = Literal(">")
            ge = Literal(">=")
            ior = Literal("|")
            iand = Literal("&")
            inot = Literal("!")
            lpar = Literal("(").suppress()
            rpar = Literal(")").suppress()
            addop = plus | minus | eq
            multop = mult | div | ge | le | gt | lt | ior | iand | inot  # Order matters here due to <= being caught by <
            expop = Literal("^")
            pi = CaselessLiteral("PI")

            # Letters
            xx = CaselessLiteral("x")
            yy = CaselessLiteral("y")
            zz = CaselessLiteral("z")

            expr = Forward()
            atom = (Optional("-") + (xx | yy | zz | pi | e | fnumber | ident + lpar + expr + rpar).setParseAction(self.pushFirst) | (lpar + expr.suppress() + rpar)).setParseAction(self.pushUMinus)

            # by defining exponentiation as "atom [ ^ factor ]..." instead of "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-righ
            # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
            factor = Forward()
            factor << atom + ZeroOrMore((expop + factor).setParseAction(self.pushFirst))

            term = factor + ZeroOrMore((multop + factor).setParseAction(self.pushFirst))
            expr << term + ZeroOrMore((addop + term).setParseAction(self.pushFirst))
            self._bnf = expr

        return self._bnf

    def evaluateStack(self, stack):
        op = stack.pop()
        if op == 'unary -':
            return -self.evaluateStack(stack)
        if op in ["+", "-", "*", "/", "^", ">", "<", "==", "<=", ">=", "|", "&", "!"]:
            op2 = self.evaluateStack(stack)
            op1 = self.evaluateStack(stack)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return numpy.pi  # 3.1415926535
        elif op == "E":
            return numpy.e  # 2.718281828
        elif op in self.fn:
            return self.fn[op](self.evaluateStack(stack))
        elif op[0].isalpha() and len(op[0]) == 1 and op[0] in self.tiles:
            return self.tiles[op[0]]
        elif op[0].isalpha():
            return 0
        else:
            return numpy.array(float(op))

    def eval_formula(self, formula, tiles={}):
        self.tiles = tiles
        self.exprStack = []
        self.bnf.parseString(formula)
        val = self.evaluateStack(self.exprStack)
        return val
