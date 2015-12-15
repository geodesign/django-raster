"""
Define all mappings between operators and string representations.
"""
import numpy

# Operator strings
ADD = '+'
SUBSTRACT = '-'
MULTIPLY = '*'
DIVIDE = '/'
POWER = '^'
EQUAL = '=='
NOT_EQUAL = '!='
GREATER = '>'
GREATER_EQUAL = '>='
LESS = '<'
LESS_EQUAL = '<='
LOGICAL_OR = '|'
LOGICAL_AND = '&'
LOGICAL_NOT = '!'
UNARY_AND = 'unary +'
UNARY_LESS = 'unary -'
UNARY_NOT = 'unary !'

# Euler number, pi and null values
EULER = 'E'
PI = 'PI'
NULL = 'NULL'
TRUE = 'TRUE'
FALSE = 'FALSE'

# Operator groups
ADDOP = (ADD, SUBSTRACT)
POWOP = (POWER, )
UNOP = (ADD, SUBSTRACT, LOGICAL_NOT)
MULTOP = (MULTIPLY, DIVIDE)
EQUOP = (EQUAL, NOT_EQUAL)
SIZEEQOP = (GREATER_EQUAL, LESS_EQUAL)
SIZEOP = (GREATER, LESS)
ANDOP = (LOGICAL_AND, )
OROP = (LOGICAL_OR, )

# Map operator symbols to arithmetic operations in numpy
OPERATOR_MAP = {
    ADD: numpy.add,
    SUBSTRACT: numpy.subtract,
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
    UNARY_AND: numpy.array,
    UNARY_LESS: numpy.negative,
    UNARY_NOT: numpy.logical_not,
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
}

ALGEBRA_PIXEL_TYPE_GDAL = 7

ALGEBRA_PIXEL_TYPE_NUMPY = 'Float64'
