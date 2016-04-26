from __future__ import unicode_literals

from unittest import skip

from tests.raster_testcase import RasterTestCase


class RasterLayerBandHistogram(RasterTestCase):

    def test_histogram_creation(self):
        self.assertEqual(self.rasterlayer.rasterlayerbandmetadata_set.count(), 1)

    @skip('Fails on current release -- Refs #25734.')
    def test_histogram_values(self):
        self.assertEqual(
            self.rasterlayer.rasterlayerbandmetadata_set.first().hist_values,
            [21741.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 695.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 56.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4131.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 31490.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1350.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2977.0]
        )

    @skip('Fails on current release -- Refs #25734.')
    def test_histogram_bins(self):
        self.assertEqual(
            self.rasterlayer.rasterlayerbandmetadata_set.first().hist_bins,
            [0.0, 0.09, 0.18, 0.27, 0.36, 0.45, 0.54, 0.63, 0.72, 0.81, 0.9, 0.99, 1.08, 1.17, 1.26, 1.35, 1.44, 1.53, 1.62, 1.71, 1.8, 1.89, 1.98, 2.07, 2.16, 2.25, 2.34, 2.43, 2.52, 2.61, 2.7, 2.79, 2.88, 2.97, 3.06, 3.15, 3.24, 3.33, 3.42, 3.51, 3.6, 3.69, 3.78, 3.87, 3.96, 4.05, 4.14, 4.23, 4.32, 4.41, 4.5, 4.59, 4.68, 4.77, 4.86, 4.95, 5.04, 5.13, 5.22, 5.31, 5.4, 5.49, 5.58, 5.67, 5.76, 5.85, 5.94, 6.03, 6.12, 6.21, 6.3, 6.39, 6.48, 6.57, 6.66, 6.75, 6.84, 6.93, 7.02, 7.11, 7.2, 7.29, 7.38, 7.47, 7.56, 7.65, 7.74, 7.83, 7.92, 8.01, 8.1, 8.19, 8.28, 8.37, 8.46, 8.55, 8.64, 8.73, 8.82, 8.91, 9.0]
        )
