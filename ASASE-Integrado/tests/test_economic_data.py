import json
import unittest
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class EconomicDataTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'frontend/data/economic-references.json').read_text())

    def test_exact_catalog_coverage_and_provenance(self):
        catalog=json.loads((ROOT/'cultivos.json').read_text())
        self.assertEqual(set(self.data['crops']),{str(c['id']) for c in catalog})
        for c in self.data['crops'].values():
            self.assertGreaterEqual(c['revenue'],0)
            self.assertGreaterEqual(c['cost'],0)
            self.assertEqual(c['currency'],'GHS')
            self.assertEqual(c['unit'],'ha/cycle')
            source=self.data['sources'][c['source']]
            self.assertTrue(source['url'].startswith('https://'))
            self.assertTrue(source['en'] and source['es'] and source['year'])
        self.assertTrue(self.data['crops']['10']['external'])
        self.assertFalse(self.data['crops']['12']['external'])

    def test_generated_script_matches_json(self):
        text=(ROOT/'frontend/data/economic-references.js').read_text()
        self.assertEqual(json.loads(text.split('const ECONOMIC_DATA = ',1)[1].strip().removesuffix(';')),self.data)

    def test_currency_area_and_fixed_cost_conversions(self):
        crops=self.data['crops']
        def truncate(x):return float(x.quantize(Decimal('.01'),rounding=ROUND_DOWN))
        for field in ['revenue','cost']:
            c=crops['8'];v=c['conversion']
            expected=Decimal(str(v['original_'+field]))*Decimal(10000)/Decimal(str(v['square_metres_per_acre']))*Decimal(str(v['ghs_per_usd']))
            self.assertEqual(c[field],truncate(expected))
            c=crops['10'];v=c['conversion']
            expected=Decimal(str(v['original_'+field]))*Decimal(str(v['ghs_per_usd']))/Decimal(str(v['aud_per_usd']))
            self.assertEqual(c[field],truncate(expected))
        self.assertEqual(crops['9']['cost'],2452-250)
        self.assertEqual(crops['3']['cost'],1015)  # Published total, not silently corrected.
        self.assertEqual(crops['11']['cost'],351.87)  # Excludes fixed depreciation.
