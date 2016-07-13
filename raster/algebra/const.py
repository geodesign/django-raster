"""
Define all mappings between operators and string representations.
"""
from __future__ import unicode_literals

import numpy

ALGEBRA_PIXEL_TYPE_GDAL = 7
ALGEBRA_PIXEL_TYPE_NUMPY = "Float64"

LPAR = "("
RPAR = ")"

NUMBER = r"[+-]?\d+(\.\d*)?([Ee][+-]?\d+)?"

VARIABLE_NAME_SEPARATOR = "_"
BAND_INDEX_SEPARATOR = ":"

# Keywords
EULER = "E"
PI = "PI"
TRUE = "TRUE"
FALSE = "FALSE"
NULL = "NULL"
INFINITE = "INF"

KEYWORD_MAP = {
    EULER: numpy.e,
    PI: numpy.pi,
    TRUE: True,
    FALSE: False,
    NULL: NULL,
    INFINITE: numpy.inf,
}

# Operator strings
ADD = "+"
SUBTRACT = "-"
MULTIPLY = "*"
DIVIDE = "/"
POWER = "^"
EQUAL = "=="
NOT_EQUAL = "!="
GREATER = ">"
GREATER_EQUAL = ">="
LESS = "<"
LESS_EQUAL = "<="
LOGICAL_OR = "|"
LOGICAL_AND = "&"
LOGICAL_NOT = "!"
FILL = "~"
UNARY_AND = "unary +"
UNARY_LESS = "unary -"
UNARY_NOT = "unary !"
UNARY_FILL = "unary ~"

# Operator groups
ADDOP = (ADD, SUBTRACT, )
POWOP = (POWER, )
UNOP = (ADD, SUBTRACT, LOGICAL_NOT, FILL)
# The order the operators in this group matters due to "<=" being caught by "<".
MULTOP = (
    MULTIPLY,
    DIVIDE,
    EQUAL,
    NOT_EQUAL,
    GREATER_EQUAL,
    LESS_EQUAL,
    GREATER,
    LESS,
    LOGICAL_AND,
    LOGICAL_OR
)

# Map operator symbols to arithmetic operations in numpy
OPERATOR_MAP = {
    ADD: numpy.add,
    SUBTRACT: numpy.subtract,
    MULTIPLY: numpy.multiply,
    DIVIDE: numpy.divide,
    POWER: numpy.power,
    EQUAL: numpy.equal,
    NOT_EQUAL: numpy.not_equal,
    GREATER: numpy.greater,
    GREATER_EQUAL: numpy.greater_equal,
    LESS: numpy.less,
    LESS_EQUAL: numpy.less_equal,
    LOGICAL_OR: numpy.logical_or,
    LOGICAL_AND: numpy.logical_and,
}

UNARY_OPERATOR_MAP = {
    UNARY_AND: numpy.array,
    UNARY_LESS: numpy.negative,
    UNARY_NOT: numpy.logical_not,
    UNARY_FILL: numpy.ma.filled,
}

UNARY_REPLACE_MAP = {
    ADD: UNARY_AND,
    SUBTRACT: UNARY_LESS,
    LOGICAL_NOT: UNARY_NOT,
    FILL: UNARY_FILL,
}

# Map function names to numpy functions
FUNCTION_MAP = {
    "sin": numpy.sin,
    "cos": numpy.cos,
    "tan": numpy.tan,
    "log": numpy.log,
    "exp": numpy.exp,
    "abs": numpy.abs,
    "int": numpy.int,
    "round": numpy.round,
    "sign": numpy.sign,
    "min": numpy.min,
    "max": numpy.max,
    "mean": numpy.mean,
    "median": numpy.median,
    "std": numpy.std,
    "sum": numpy.sum,
}
