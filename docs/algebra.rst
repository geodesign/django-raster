==============
Raster Algebra
==============
Django-raster has raster calculator functionality. The raster calculator
allows rendering raster tiles based on algebraic formulas. The use is very
similar to a standard z/x/y tile endpoint, but allows the evaluation of
a broad range of algebraic expressions applied to existing pixel values.
The z/x/y structure can be used directly in online mapping software such
as `OpenLayers`__ or `Leaflet`__.

Similar to the regular tiles endpoint, the django-raster url patterns need
to be installed for the raster algebra endpoint to work. For the documentation
we assume that the ``/raster/`` base url is used as proposed in the
:doc:`installation` section.

Raster algebra TMS endpoint
---------------------------
The raster algebra url base is used only to specify the z/x/y tile index. All
the rest of the configuration is done through the query parameters. The input
to the raster algebra is a named list of :class:`RasterLayer` ids and a formula
for evaluation. These values are passed to the backend through two required
query parameters: ``layers`` and ``formula``.

The layers query parameter identifies which raster layers to use for evaluation.
It is a comma separated list of variable-name and RasterLayer id pairs. The
variable names are matched with the names in the formula. An example is
``layers=a=2,b=4`` which will match :class:`RasterLayer` with id ``2`` to variable
name ``a`` and the layer with id ``4`` with the variable name ``b``.

The formula query parameter is a string specifying a formula for evaluation.
The formula is an algebraic expression based on the names given to the layers
in the ``layers`` query parameter.  The formula has to be an expression that
can be evaluated by the :class:`FormulaParser`. It accepts a broad range of
algebraic expressions. The endpoint supports most of the common mathematical
operators (``+``, ``-``, ``*``, ``/``, etc), functions (``sin``, ``cos``,
``exp``, etc.), and logical operators (``&``, ``!``, ``>``, ``=``, etc.).
It also has a set of predefined constants through reserved keywords such
as pi ``PI`` or the Euler number ``E``.

Putting it all together, an example request to the raster algebra endpoint
could look like this:

::

    /raster/algebra/{z}/{x}/{y}.png?layers=a=1,b=3,c=6&formula=log(a+b)*c&legend=5

In addition to the required query parameters: ``layers`` and ``formula``, a
:class:`Legend` id can be specified using the ``legend`` query parameter.
If specified, the legend will be used to interpret the result of the algebra
expression. This is convenient to use predefined colormaps for the endpoint.

__ http://openlayers.org/
__ http://leafletjs.com/

Dynamic colormap
^^^^^^^^^^^^^^^^
For a more dynamic rendering scheme, a dynamic colormap can be passed to the
endpoint using the ``colormap`` query parameter. The following request would
color all pixels that result in a value bigger than zero in red, and all other
pixels in green.

::

    /raster/algebra/{z}/{x}/{y}.png?layers=a=1,b=3,c=6&formula=log(a+b)*c&colormap={'x>0':'#FF0000','x<=0':'#00FF00'}

Using specific bands
^^^^^^^^^^^^^^^^^^^^
By default, the algebra endpoint uses the first band in each layer specified.
To select specific bands to evaluate on, the band can be specified as
By default, the first band is used for calculations on the raster algebra
endpoint. To specify a specific band the syntax is ``'variable:band'``, where
variable is the name of the variable, and band is the band index. For example
``{'a:3': 23}`` would match band 3 of the :class:`RasterLayer` with the id
``23`` to the variable name ``a``.

Encoding
^^^^^^^^
Both the colormap and the formula should be properly url encoded. The
examples here are not encoded and should be considered as instructive
examples only.

RGB endpoint
^^^^^^^^^^^^
The algebra endpoint can also be used to render RGB images. For this, only
three query parameters are expected: ``r``, ``g``, and ``b``. If these
three parameters are found in the list of query parameters, and no formula
has been specified, the three input bands are interpreted as RGB channels
of an RGB image. For example to use raster layer with id ``1`` as red,
id ``3`` as green and id ``6`` as blue, the following url can be used:

::

    /raster/algebra/{z}/{x}/{y}.png?layers=r=1,g=3,b=6

If the raw data in the tiles is not already scaled to the range [0, 255], an
additional scaling factor can be specified, which will be used to rescale
all three bands to the default RGB color range. For instance, the following
query would assume that the input bands have values in the range of
[5, 10000], and would rescale them to the RGB color space.

::

    /raster/algebra/{z}/{x}/{y}.png?layers=r=1,g=3,b=6&scale=5,10000

An alpha channel can be activated by passing the ``alpha`` query parameter. The
alpha parameter makes all the pixels transparent that have values equal to
``0`` in all three RGB channels.

Formula parser
--------------
At the heart of the raster calculator is the :class:`FormulaParser`, which
is based on the pyparsing__ package. The :class:`FormulaParser` is a general
purpose formula evaluation class. It is It does not know about rasters and
operates with Numpy arrays directly. To use it, you need a dictionary with
Numpy arrays of equal shape and a formula as string. The keys in the dictionary
are the variable names and are used to match data to variables in the formula.
Here are some examples of how to use the formula parser:
::

    # Import parser and instantiate an instance.
    >>> from raster.algebra.parser import FormulaParser
    >>> parser = FormulaParser()
    # Create a data dictionary and evaluate a simple sum.
    >>> data = {'a': range(5), 'b': range(5)}
    >>> formula = 'a + b'
    >>> parser.evaluate(data, formula)
    ... array([0, 2, 4, 6, 8])
    # Use the sin function and divide by b.
    >>> formula = 'sin(a) / b'
    >>> parser.evaluate(data, formula)
    ... array([ nan, 0.84147098, 0.45464871, 0.04704, -0.18920062])
    # Use a logical array.
    >>> data.update({'a_new_var': [True, False, False, True, False]})
    >>> formula = '!a_new_var * a + 3'
    >>> parser.evaluate(data, formula)
    ... array([ 3.,  4.,  5.,  3.,  7.])
    # Use the PI keyword in a formula.
    >>> formula = 'a * PI'
    >>> parser.evaluate(data, formula)
    >>> array([0. , 3.14159265, 6.28318531, 9.42477796, 12.56637061])

__ http://pyparsing.wikispaces.com/


Raster algebra parser
---------------------
The :class:`RasterAlgebraParser` class is a wrapper that can be used to apply
the generic formula parser to raster objects directly. The use is identical
to the generic case except that the objects in the data dictionary are expected
to be :class:GDALRaster objects. The data arrays are extracted from the raster
objects automatically and are passed to the formula parser. The result array is
converted into a :class:`GDALRaster` before returning.

By default, the first band is used for calculations, to specify a specific band
to be used the syntax is ``'variable:band'``, where variable is the name of the
variable, and band is the band index. For example ``{'a:3': rst}`` would match
band 3 of the GDALRaster ``rst`` to the variable name ``a``.

Here is a complete example for how to use the :class:`RasterAlgebraParser`.
::

    >>> from raster.algebra.parser import RasterAlgebraParser
    >>> parser = RasterAlgebraParser()
    >>> base = {
    >>>     'datatype': 1,
    >>>     'driver': 'MEM',
    >>>     'width': 2,
    >>>     'height': 2,
    >>>     'srid': 3086,
    >>>     'origin': (500000, 400000),
    >>>     'scale': (100, -100),
    >>>     'skew': (0, 0),
    >>>     'bands': [
    >>>         {'nodata_value': 10},
    >>>         {'nodata_value': 10},
    >>>         {'nodata_value': 10},
    >>>     ],
    >>> }
    >>> base['bands'][0]['data'] = range(20, 24)
    >>> base['bands'][1]['data'] = range(10, 14)
    >>> rast1 = GDALRaster(base)
    >>> base['bands'][0]['data'] = [1, 1, 1, 1]
    >>> rast2 = GDALRaster(base)
    >>> base['bands'][0]['data'] = [30, 31, 32, 33]
    >>> base['bands'][0]['nodata_value'] = 31
    >>> rast3 = GDALRaster(base)
    >>> data = dict(zip(['x:1', 'y:0', 'z'], [rast1, rast2, rast3]))
    >>> rst = parser.evaluate_raster_algebra('x*(x>11) + 2*y + 3*z*(z==30)')
    >>> rst.bands[0].data()
    ... array([[ 10.,  10.],
    ...        [ 14.,  15.]])

Keywords, Operators and Functions
---------------------------------
The following tables list the available operators, functions and reserved
keywords from the :class:`FormulaParser` and the corresponding raster
calculator.

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
