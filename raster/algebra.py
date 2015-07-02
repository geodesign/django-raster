from raster.formulas import FormulaParser


class RasterAlgebra(object):

    rasters = []
    names = []
    formula = ''
    data = {}
    parser = None
    result = None

    def __init__(self, rasters, names, formula, check_aligned=True):
        # Check that all input rasters are aligned
        if check_aligned:
            self.check_aligned(rasters)

        # Set attributes necessary for computing algebra
        self.rasters = rasters
        self.names = names
        self.formula = formula

        # Set formula parser
        self.parser = FormulaParser()

        # Wrap input data into dictionary for formula evaluation
        data = dict(zip(names, [rast.bands[0].data().ravel() for rast in rasters]))

        # Make copy of first raster to hold results
        self.result = rasters[0].warp({'name': 'algebra_result'})

        # Instantiate formula parser and evaluate
        algebra_result = self.parser.evaluate_formula(formula, data)
        # TODO: Convert to dtype of raster automatically
        algebra_result = algebra_result.astype(self.result.bands[0].data().dtype)

        # Write result to target raster
        self.result.bands[0].data(algebra_result)

    def check_aligned(self, rasters):
        if not len(set([x.srs.srid for x in rasters])) == 1:
            raise Exception('Raster aligment check failed: SRIDs not all the same')

        if not len(set([x.origin.x for x in rasters])) == 1:
            raise Exception('Raster aligment check failed: Origins are not all the same')
