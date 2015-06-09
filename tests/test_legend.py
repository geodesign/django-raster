import json

from django.test import TestCase
from raster.models import Legend, LegendEntry, LegendSemantics


class RasterLegendTests(TestCase):

    def test_pixel_size_level1(self):
        sem1 = LegendSemantics.objects.create(name='Earth')
        sem2 = LegendSemantics.objects.create(name='Wind')

        ent1 = LegendEntry.objects.create(semantics=sem1, expression='1', color='#123456')
        ent2 = LegendEntry.objects.create(semantics=sem2, expression='2', color='#654321')

        leg = Legend.objects.create(title='MyLegend')
        leg.entries.add(ent1, ent2)
        self.assertTrue({"color": "#123456", "expression": "1", "name": "Earth"} in json.loads(leg.json))
        self.assertTrue({"color": "#654321", "expression": "2", "name": "Wind"} in json.loads(leg.json))

        ent1.color = '#000000'
        ent1.save()
        leg = Legend.objects.get(id=leg.id)  # Reload from db
        self.assertTrue({"color": "#000000", "expression": "1", "name": "Earth"} in json.loads(leg.json))

        sem1.name = 'Fire'
        sem1.save()
        leg = Legend.objects.get(id=leg.id)  # Reload from db
        self.assertTrue({"color": "#000000", "expression": "1", "name": "Fire"} in json.loads(leg.json))
