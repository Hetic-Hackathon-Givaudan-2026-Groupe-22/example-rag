import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from sillage_v2.features import FEATURE_COLUMNS,FeaturePolicy,extract_features,validate_reference,features_for_new_topic
from sillage_v2.train import classifier,train_evaluate
from sillage_v2.api import app

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/raw/reference_30_cas_google_trends_2019_2026.csv'
ART=ROOT/'artifacts/v2'

class MLTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.df=pd.read_csv(SOURCE) if SOURCE.exists() else pd.DataFrame()

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_30_topics_and_no_duplicates(self):
        d=validate_reference(self.df)
        self.assertEqual(d.topic_id.nunique(),30)
        self.assertFalse(d.duplicated(['topic_id','zone','mois']).any())

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_food_scope_29(self):
        f,a=extract_features(self.df,FeaturePolicy(min_zones=1))
        self.assertEqual(len(a),30)
        self.assertEqual(len(f),29)
        self.assertIn('oud',a.loc[a.status!='ok','topic_id'].tolist())
        self.assertNotIn('oud',f.topic_id.tolist())

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_features_not_labels(self):
        f,_=extract_features(self.df,FeaturePolicy(min_zones=1))
        self.assertEqual(len(FEATURE_COLUMNS),7)
        self.assertFalse(f[FEATURE_COLUMNS].isna().any().any())
        self.assertTrue(np.isfinite(f[FEATURE_COLUMNS].to_numpy(float)).all())
        # Les labels ne sont pas des features.
        self.assertFalse(set(FEATURE_COLUMNS)&{'label','topic_id','terme','zone','raw_file'})

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_label_conflict_rejected(self):
        wrong=self.df.copy();wrong.loc[0,'label']='tendance' if wrong.loc[0,'label']=='buzz' else 'buzz'
        with self.assertRaises(ValueError):validate_reference(wrong)

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_duplicate_rejected(self):
        wrong=pd.concat([self.df,self.df.iloc[:1]],ignore_index=True)
        with self.assertRaises(ValueError):validate_reference(wrong)

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_unknown_new_topic_with_2_zones(self):
        s=self.df.loc[(self.df.topic_id=='matcha')&(self.df.zone.isin(['FR','US'])),['zone','mois','indice_0_100']]
        out=features_for_new_topic(s)
        self.assertTrue(all(np.isfinite(list(out.values()))))

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_single_zone_new_topic_rejected(self):
        s=self.df.loc[(self.df.topic_id=='matcha')&(self.df.zone=='FR'),['zone','mois','indice_0_100']]
        with self.assertRaises(ValueError):features_for_new_topic(s)

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_training_and_leave_one_topic_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=train_evaluate(SOURCE,Path(tmp))
            o=pd.read_csv(Path(tmp)/'predictions_29_oof.csv')
            self.assertEqual(len(o),29)
            self.assertTrue((o['fold']=='leave_one_topic_out').all())
            self.assertEqual(m['food_cases_evaluated'],29)
            self.assertEqual(m['logistic_regression']['n_cases'],29)
            self.assertEqual(sum(m['logistic_regression']['confusion_buzz_tendance'].values()),29)
            self.assertTrue((Path(tmp)/'model_v2.joblib').exists())

    def test_replay_from_published_features(self):
        processed=ROOT/'data/processed/features_by_topic.csv'
        audit=ROOT/'data/processed/audit_30_references.csv'
        with tempfile.TemporaryDirectory() as tmp:
            metrics=train_evaluate(None,Path(tmp),processed,audit)
            self.assertEqual(metrics['food_cases_evaluated'],29)
            self.assertEqual(metrics['logistic_regression']['confusion_buzz_tendance'],
                             {'TN':14,'FP':1,'FN':1,'TP':13})

    def test_api_metrics(self):
        t=TestClient(app)
        r=t.get('/v2/metrics');self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['food_cases_evaluated'],30)
        self.assertEqual(len(t.get('/v2/cases').json()['cases']),30)
        self.assertEqual(len(t.get('/v2/references').json()['data']),30)
        self.assertEqual(t.get('/v2/model').json()['model'],'Random Forest')

    @unittest.skipUnless(SOURCE.exists(), 'Source brute locale non versionnée : test en attente de la collecte')
    def test_api_prediction_on_observations(self):
        s=self.df.loc[(self.df.topic_id=='matcha')&(self.df.zone.isin(['FR','US'])),['zone','mois','indice_0_100']]
        req={'topic_id':'matcha_test','observations':s.to_dict('records')}
        t=TestClient(app);r=t.post('/v2/predict',json=req)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['n_zones'],2)
        self.assertIn(r.json()['classification_exploratoire'],['buzz','tendance'])

    def test_api_no_world(self):
        t=TestClient(app);r=t.post('/v2/predict',json={'topic_id':'x','observations':[{'zone':'WORLD','mois':'2020-01','indice_0_100':1}]})
        self.assertEqual(r.status_code,400)

if __name__=='__main__': unittest.main()
