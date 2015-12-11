import numpy

from raster.algebra.const import EQUOP, FUNCTION_MAP, OPERATOR_MAP
from raster.exceptions import RasterAlgebraException


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
            ret = OPERATOR_MAP[op](ret, operand.eval())
        return ret


class EvalAdd(EvalBinaryOp):
    initial = [0, '+']


class EvalMult(EvalBinaryOp):
    initial = [1, '*']


class EvalAnd(EvalBinaryOp):
    initial = [True, '&']


class EvalOr(EvalBinaryOp):
    initial = [False, '|']


class EvalExp(EvalBinaryOp):

    def assign_tokens(self):
        super(EvalExp, self).assign_tokens()
        self.ops = self.ops[::-1]

    def eval(self):
        ret = self.ops[0].eval()
        for op, operand in self.by_pairs(self.ops[1:]):
            ret = operand.eval() ** ret
        return ret


class EvalNull(EvalObject):
    def eval(self):
        return self


class EvalComparison(EvalObject):

    @staticmethod
    def get_mask(data, operator):
        # Make sure the right operator is used
        if operator not in EQUOP:
            raise RasterAlgebraException('NULL can only be used with "==" or "!=" operators.')
        # Get mask
        if numpy.ma.is_masked(data):
            return data.mask
        else:
            # If there is no mask, all values are not null
            return numpy.zeros(data.shape, dtype=numpy.bool)

    def eval(self):
        # Get tokens and evaluate operands
        op1, oper, op2 = self.tokens.asList()
        op1 = op1.eval()
        op2 = op2.eval()
        # If one of the operands is null, return mask of the other operand
        if isinstance(op1, EvalNull):
            op2 = self.get_mask(op2, oper)
            op1 = True
        elif isinstance(op2, EvalNull):
            op1 = self.get_mask(op1, oper)
            op2 = True
        return OPERATOR_MAP[oper](op1, op2)


class EvalUnary(EvalObject):

    def eval(self):
        op, oper = self.tokens.asList()
        return OPERATOR_MAP['unary ' + op](oper.eval())


class EvalFunction(EvalObject):

    def assign_tokens(self):
        self.fn = FUNCTION_MAP[self.tokens[0]]
        self.arg = self.tokens[1]

    def eval(self):
        return self.fn(self.arg.eval())


class EvalVariable(EvalObject):

    def eval(self):
        return self.tokens
