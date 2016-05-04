==============
Raster Algebra
==============
Django-raster has raster calculator functionality. The raster calculator
allows rendering raster tiles based on algebraic formulas. The raster
calculator operates at the pixel level.

At the heart of the raster calculator is the :class:`FormulaParser`, which
is based on pyparsing__.

__ http://pyparsing.wikispaces.com/

Keywords, Operators and Function Reference
------------------------------------------
The folowing tables list all Operators, functions and reseved keywords
available on the raster calculator.


.. table:: Keyword symbols

    ============= =========
    Keyword       Symbol
    ============= =========
    Euler Number  ``E``
    Pi            ``PI``
    True Boolean  ``TRUE``
    False Boolean ``FALSE``
    Null          ``NULL``
    Infinite      ``INF``
    ============= =========

.. table:: Operator symbols

    ======================== ============
    Operator                 Symbol
    ======================== ============
    Add                      ``+``
    Substract                ``-``
    Multiply                 ``*``
    Divide                   ``/``
    Power                    ``^``
    Equal                    ``==``
    Not Equal                ``!=``
    Greater                  ``>``
    Greater or Equal         ``>=``
    Less                     ``<``
    Less or Equal            ``<=``
    Logical Or               ``|``
    Logial And               ``&``
    Logcal Not               ``!``
    Fill Nodata Values       ``~``
    Unary And                ``+``
    Unary Minus              ``-``
    Unary Not                ``!``
    ======================== ============

.. table:: Function symbols

    ======================== ============
    Function                 Symbol   
    ======================== ============
    Sinus                    ``sin``
    Cosinus                  ``cos``
    Tangens                  ``tan``
    Natural Logarithm        ``log``
    Exponential Function     ``exp``
    Absolute Value           ``abs``
    Integer                  ``int``
    Round                    ``round``
    Sign                     ``sign``
    Minimum                  ``min``
    Maximum                  ``max``
    Mean                     ``mean``
    Median                   ``median``
    Standard Deviation       ``std``
    Sum                      ``sum``
    ======================== ============
