"""Contrôles sur les artefacts livrés. Lancer depuis la racine du lot."""
import json
import unittest
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'

class CleaningQualityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quality=json.loads((OUT/'quality_summary.json').read_text(encoding='utf8'))
        cls.ready=pd.read_csv(OUT/'m1_wikipedia_contract.csv',encoding='utf-8-sig')
        cls.series=pd.read_csv(OUT/'series_quality_recomputed.csv',encoding='utf-8-sig')
        cls.quarantine=pd.read_csv(OUT/'observations_quarantine.csv',encoding='utf-8-sig')

    def test_totals_and_counts(self):
        self.assertEqual(self.quality['raw_observations'],15212)
        self.assertEqual(self.quality['n_m1_eligible'],12690)
        self.assertEqual(self.quality['n_quarantine'],2522)
        self.assertEqual(len(self.ready),12690)
        self.assertEqual(len(self.series),159)

    def test_no_fake_countries(self):
        self.assertTrue(self.ready['country_iso2'].isna().all())
        self.assertTrue(self.ready['segment_id'].str.endswith('.wikipedia').all())
        self.assertEqual(set(self.ready['segment_type']),{'wiki_project'})

    def test_no_label_leakage(self):
        self.assertNotIn('label_reference',self.ready.columns)
        self.assertTrue((self.ready['is_synthetic']==False).all())

    def test_no_duplicates_and_nonnegative(self):
        self.assertFalse(self.ready.duplicated(['ingredient','segment_id','source','metric','date']).any())
        self.assertTrue(self.ready['value'].ge(0).all())
        self.assertTrue((self.ready['date']<='2026-10-01').all())

    def test_quarantine_not_discarded(self):
        self.assertEqual(self.quarantine['quality_status'].value_counts().to_dict(),{'a_verifier':1065,'exclu_perimetre':1012,'insuffisant':445})
        self.assertTrue(self.series['quality_report_matches'].all())

    def test_original_zero_counts(self):
        self.assertEqual(self.quality['n_zero_values_preserved'],81)
        clean=pd.read_csv(OUT/'observations_clean_all.csv',encoding='utf-8-sig')
        self.assertEqual(int(clean['value'].eq(0).sum()),81)

if __name__=='__main__':unittest.main()
