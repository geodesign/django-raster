import numpy

# Map operator symbols to arithmetic operations in numpy
operator_map = {
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
    "unary +": numpy.array,
    "unary -": numpy.negative,
    "unary !": numpy.logical_not,
}

# Map function names to numpy functions
function_map = {
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


class EvalObject(object):

    def __init__(self, *args):
        self.tokens = args[-1][0]
        self.assign_tokens()

    def assign_tokens(self):
        """
        Abstract method for class-specific token initialization.
        """

    def eval(self):
        """
        Abstract method for class-specific evaluation code.
        """


class EvalConstant(EvalObject):

    def assign_tokens(self):
        self.value = float(self.tokens)

    def eval(self):
        return self.value


class EvalBinaryOp(EvalObject):

    initial = []

    @staticmethod
    def by_pairs(seq):
        seq_end = object()
        it = iter(seq)
        next_val = next(it, seq_end)
        while next_val != seq_end:
            yield (next_val, next(it))
            next_val = next(it, seq_end)

    def assign_tokens(self):
        self.ops = self.initial + self.tokens.asList()

    def eval(self):
        ret = self.ops[0]
        for op, operand in self.by_pairs(self.ops[1:]):
            ret = operator_map[op](ret, operand.eval())
        return ret


class EvalAdd(EvalBinaryOp):
    initial = [0, '+']


class EvalMult(EvalBinaryOp):
    initial = [1, '*']


class EvalExp(EvalBinaryOp):

    def assign_tokens(self):
        super(EvalExp, self).assign_tokens()
        self.ops = self.ops[::-1]

    def eval(self):
        ret = self.ops[0].eval()
        for op, operand in self.by_pairs(self.ops[1:]):
            ret = operand.eval() ** ret
        return ret


class EvalComparison(EvalObject):

    def eval(self):
        op1, oper, op2 = self.tokens.asList()
        return operator_map[oper](op1.eval(), op2.eval())


class EvalUnary(EvalObject):

    def eval(self):
        op, oper = self.tokens.asList()
        return operator_map['unary ' + op](oper.eval())


class EvalAnd(EvalBinaryOp):
    initial = [True, '&']


class EvalOr(EvalBinaryOp):
    initial = [False, '|']


class EvalNot(EvalObject):

    def eval(self):
        return not self.tokens[0][1].eval()


class EvalFunction(EvalObject):

    def assign_tokens(self):
        self.fn = function_map[self.tokens[0]]
        self.arg = self.tokens[1]

    def eval(self):
        return self.fn(self.arg.eval())


class EvalVariable(EvalObject):

    def eval(self):
        return self.tokens
