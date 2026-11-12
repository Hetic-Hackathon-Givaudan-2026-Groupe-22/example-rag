"""Controles des exports du lot 02, sans modifier les donnees brutes."""
import csv
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as fh:
        return list(csv.DictReader(fh))

class Lot02AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clean = rows(ROOT/'data/clean/google_trends_p0_M1_pays.csv')
        cls.world = rows(ROOT/'data/clean/google_trends_p0_WORLD_separe.csv')
        cls.reference = rows(ROOT/'data/clean/reference_30_sujets_labels_A_REVOIR.csv')
        cls.audit = json.loads((ROOT/'reports/audit_lot02.json').read_text(encoding='utf-8'))
        cls.m1 = ROOT/'artifacts/google_trends/lot02_P0_M1_statistical_v03'
    def test_country_rows_and_series(self):
        self.assertEqual(len(self.clean),1786)
        self.assertEqual(len(set((r['ingredient'],r['country'],r['normalization_scope']) for r in self.clean)),19)
    def test_no_world_as_country(self):
        self.assertEqual({r['country'] for r in self.clean},{'FR','US','JP','KR','AE'})
        self.assertEqual(len(self.world),282)
        self.assertEqual({r['segment_id'] for r in self.world},{'WORLD'})
    def test_quality_and_provenance(self):
        keys=[(r['ingredient'],r['country'],r['normalization_scope'],r['date']) for r in self.clean]
        self.assertEqual(len(keys),len(set(keys)))
        self.assertTrue(all(0<=float(r['value'])<=100 for r in self.clean))
        self.assertTrue(all(r['source_url'].startswith('https://trends.google.com/') for r in self.clean))
        self.assertTrue(all(r['is_synthetic']=='False' for r in self.clean))
    def test_reference_30_and_no_label_in_m1(self):
        self.assertEqual(len(self.reference),30)
        self.assertEqual(Counter(r['reference_label'] for r in self.reference),Counter({'buzz':15,'tendance':15}))
        self.assertEqual([r['topic_id'] for r in self.reference if r['in_food_scope']=='false'],['oud'])
        self.assertTrue(all('label' not in k.lower() for k in self.clean[0]))
    def test_snapshot_and_manifest(self):
        manifest=json.loads((self.m1/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['n_input_cleaned'],1786)
        self.assertEqual(manifest['n_series'],19)
        self.assertEqual(manifest['input_sha256'], self.audit['cleaned_input_sha256']['google_trends_p0_M1_pays'])
        self.assertFalse(manifest['contains_synthetic'])
    def test_m1_uses_real_outputs(self):
        manifest=json.loads((self.m1/'manifest.json').read_text(encoding='utf-8'))
        signals=json.loads((self.m1/'signals.json').read_text(encoding='utf-8'))
        self.assertEqual(len(signals),manifest['n_detected_events'])
        self.assertTrue(all(s['country'] in {'FR','US','JP','KR','AE'} for s in signals))
        self.assertTrue(all(not s['is_synthetic'] for s in signals))

if __name__=='__main__':
    unittest.main()
