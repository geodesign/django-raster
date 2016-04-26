from __future__ import unicode_literals

import json

from django.test import TestCase
from raster.models import Legend, LegendEntry, LegendSemantics


class RasterLegendTests(TestCase):

    def setUp(self):
        self.sem1 = LegendSemantics.objects.create(name='Earth')
        sem2 = LegendSemantics.objects.create(name='Wind')

        self.ent1 = LegendEntry.objects.create(semantics=self.sem1, expression='1', color='#123456')
        ent2 = LegendEntry.objects.create(semantics=sem2, expression='2', color='#654321')

        self.leg = Legend.objects.create(title='MyLegend')
        self.leg.entries.add(self.ent1, ent2)

    def test_raster_legend_json_string(self):
        self.assertEqual(
            [
                {"color": "#123456", "expression": "1", "name": "Earth"},
                {"color": "#654321", "expression": "2", "name": "Wind"}
            ],
            json.loads(self.leg.json)
        )

    def test_raster_legend_change_semantics_signal(self):
        self.sem1.name = 'Fire'
        self.sem1.save()
        leg = Legend.objects.get(id=self.leg.id)  # Reload from db
        self.assertTrue({"color": "#123456", "expression": "1", "name": "Fire"} in json.loads(leg.json))

    def test_raster_legend_change_legend_entry_signal(self):
        self.ent1.color = '#000000'
        self.ent1.save()
        leg = Legend.objects.get(id=self.leg.id)  # Reload from db
        self.assertTrue({"color": "#000000", "expression": "1", "name": "Earth"} in json.loads(leg.json))

    def test_raster_legend_entry_list_change_signal(self):
        self.leg.entries.remove(self.ent1)
        self.assertEqual(
            [{"color": "#654321", "expression": "2", "name": "Wind"}],
            json.loads(self.leg.json)
        )
