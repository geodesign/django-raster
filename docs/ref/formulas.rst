Formulas
========

.. module:: raster.formulas

Algebra parsing functionality based on pyparsing__.

__ http://pyparsing.wikispaces.com/

.. class:: FormulaParser

    Deconstruct mathematical algebra expressions and convert those into
    callable functions. This module uses pyparsing for this purpose and
    the parser is adopted from the `fourFun example`__.

    Example usage::

        >>> parser = FormulaParser()
        >>> parser.parse_formula('log(a * 3 + b)')
        >>> parser.evaluate({'a': 5, 'b': 23})
        ... 3.6375861597263857
        >>> parser.evaluate({'a': [5, 6, 7], 'b': [23, 24, 25]})
        ... array([ 3.63758616,  3.73766962,  3.8286414 ])

    .. method:: parse_formula(formula)

         Sets the formula for this parser. Decomposes the input string into a
         BNF expression.

    .. method:: evaluate(data=None)

        Evaluates the previously specified formula using the input data. The
        input is a dictionary that has the variable names from the formula as
        keys and data arrays as corresponding values. The values can be
        numbers, tuples, lists, or numpy arrays.

    .. method:: evaluate_formula(formula, data=None)

        A wrapper to set the formula and evaluate it on data in one step.

__ http://pyparsing.wikispaces.com/file/view/fourFn.py


.. class:: RasterAlgebraParser(FormulaParser)

    Compute raster algebra expressions using the FormulaParser class.

    .. method:: evaluate_raster_algebra(self, data, formula, check_aligned=False)

        Evaluate a raster algebra expression on a set of rasters. All input
        rasters need to be strictly aligned (same size, geotransform and srid).

        The input raster list will be zipped into a dictionary using the input
        names. The resulting dictionary will be used as input data for formula
        evaluation. If the check_aligned flag is set, the input rasters are
        compared to make sure they are aligned.
