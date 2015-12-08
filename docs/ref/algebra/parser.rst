========
Formulas
========

.. module:: raster.algebra.parser

Algebra parsing functionality based on pyparsing__.

__ http://pyparsing.wikispaces.com/


.. class:: FormulaParser

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

    .. method:: set_formula(formula)

         Set the formula for this parser. Once the formula is set it will be
         used for evalution.

    .. method:: evaluate(data={}, formula=None)

        Evaluate a formula with data.
        
        The input is a dictionary that has the variable names from the formula
        as keys and data arrays as corresponding values. The values can be
        numbers, tuples, lists, or numpy arrays (see examples above).
        
        A formula can be set or updated on evaluation through the ``formula``
        argument.


.. class:: RasterAlgebraParser(FormulaParser)

    Compute raster algebra expressions using the FormulaParser class.

    .. method:: evaluate_raster_algebra(self, data, formula, check_aligned=False)

        Evaluate a raster algebra expression on a set of rasters. All input
        rasters need to be strictly aligned (same size, geotransform and srid).

        The input raster list will be zipped into a dictionary using the input
        names. The resulting dictionary will be used as input data for formula
        evaluation. If the check_aligned flag is set, the input rasters are
        compared to make sure they are aligned.
