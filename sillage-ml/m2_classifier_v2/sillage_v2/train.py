"""Entraînement + validation Leave-One-Topic-Out de la classification M2.

L'objectif est une démonstration exploratoire, pas une validation prospective
avec labels tiers. Ne pas utiliser les milliers de mois comme autant de labels.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score,balanced_accuracy_score,precision_recall_fscore_support,confusion_matrix,roc_auc_score,brier_score_loss
import sklearn
from sillage_v2.features import FEATURE_COLUMNS,extract_features,FeaturePolicy

VERSION='2.0.0-experimental'
SEED=42


def classifier()->Pipeline:
    # Spécification fixe, pas de grid search sur ces 29 cas.
    return Pipeline([('scaler',StandardScaler()),('model',LogisticRegression(C=0.3,class_weight='balanced',random_state=SEED,max_iter=2000))])


def scores(y_true:np.ndarray, y_pred:np.ndarray, y_prob:np.ndarray)->dict:
    pr,rc,f1,_=precision_recall_fscore_support(y_true,y_pred,labels=[0,1],zero_division=0)
    mat=confusion_matrix(y_true,y_pred,labels=[0,1])
    return {'n_cases':int(len(y_true)), 'accuracy':float(accuracy_score(y_true,y_pred)),
      'balanced_accuracy':float(balanced_accuracy_score(y_true,y_pred)),
      'f1_macro':float(np.mean(f1)), 'precision_buzz':float(pr[0]),'recall_buzz':float(rc[0]),
      'f1_buzz':float(f1[0]),'precision_tendance':float(pr[1]),'recall_tendance':float(rc[1]),
      'f1_tendance':float(f1[1]),
      'confusion_buzz_tendance':{'TN':int(mat[0,0]),'FP':int(mat[0,1]),'FN':int(mat[1,0]),'TP':int(mat[1,1])},
      'roc_auc':float(roc_auc_score(y_true,y_prob)) if len(np.unique(y_true))==2 else None,
      'brier_score':float(brier_score_loss(y_true,y_prob))}


def train_evaluate(in_file:Path|None, output:Path, features_file:Path|None=None, audit_file:Path|None=None)->dict:
    output.mkdir(parents=True,exist_ok=True)
    if features_file is not None:
        if audit_file is None: raise ValueError('--audit nécessaire avec --features')
        features=pd.read_csv(features_file,encoding='utf-8-sig')
        audit=pd.read_csv(audit_file,encoding='utf-8-sig')
        required=['topic_id','label']+FEATURE_COLUMNS
        if any(c not in features.columns for c in required):raise ValueError('Features manquantes')
        if features['topic_id'].duplicated().any():raise ValueError('Plusieurs lignes pour le même topic')
        if not np.isfinite(features[FEATURE_COLUMNS].to_numpy(float)).all():raise ValueError('Features invalides')
        input_path=features_file
    else:
        if in_file is None:raise ValueError('Fichier brut ou features requis')
        raw=pd.read_csv(in_file,low_memory=False,encoding='utf-8-sig')
        features,audit=extract_features(raw, FeaturePolicy(min_zones=1))
        input_path=in_file
    if len(audit)!=30:raise ValueError(f'Attendu 30 topics de référence, reçu {len(audit)}')
    if len(features)<15:raise ValueError('Trop peu de cas exploitables')
    features.to_csv(output/'features_by_topic.csv',index=False)
    audit.to_csv(output/'audit_30_references.csv',index=False)
    x=features[FEATURE_COLUMNS].to_numpy(float)
    y=features['label'].to_numpy(int)
    if len(np.unique(y))!=2:raise ValueError('Les deux classes doivent être présentes')
    pred=np.zeros(len(y),int); prob=np.zeros(len(y),float)
    dummy_pred=np.zeros(len(y),int); dummy_prob=np.zeros(len(y),float)
    for tr,te in LeaveOneOut().split(x):
        model=classifier().fit(x[tr],y[tr])
        pred[te]=model.predict(x[te]);prob[te]=model.predict_proba(x[te])[:,1]
        # Baseline FIXE avant toute validation : toujours prédire buzz (0).
        dummy_pred[te]=0;dummy_prob[te]=0.0
    # Résultats OUT-OF-FOLD pour les sujets de référence, pas in-sample.
    oof=pd.DataFrame({'topic_id':features.topic_id,'label_reference':np.where(y,'tendance','buzz'),
                      'prediction_oof':np.where(pred,'tendance','buzz'),
                      'score_tendance_non_calibre':prob.round(6),
                      'correct_oof':pred==y,'fold':'leave_one_topic_out',
                      'label_verifie_independamment':False})
    oof=oof.merge(audit[['topic_id','n_zones','status']],on='topic_id',how='left')
    predictions_name=f'predictions_{len(features)}_oof.csv'
    oof.to_csv(output/predictions_name,index=False)
    full=classifier().fit(x,y)
    dump({'model':full,'feature_columns':FEATURE_COLUMNS,'version':VERSION,
          'training_topic_ids':features.topic_id.tolist(),'training_n':len(y),'model_type':'logistic_regression',
          'label_status':'provisional_unverified','prediction_scope':'retrospective_full_window_2019_2026',
          'classes':{'0':'buzz','1':'tendance'}},output/'model_v2.joblib')
    metrics={
      'version':VERSION,'model':'M2_regression_logistique_buzz_tendance',
      'evaluation':'leave_one_topic_out','reference_topics_total':len(audit),
      'food_cases_evaluated':len(features),'excluded_topics':audit.loc[audit.status!='ok','topic_id'].tolist(),
      'class_counts':{'buzz':int((y==0).sum()),'tendance':int((y==1).sum())},
      'logistic_regression':scores(y,pred,prob),
      'always_buzz_baseline':scores(y,dummy_pred,dummy_prob),
      'warnings':[
        'Classification RETROSPECTIVE de signatures 2019-2026, PAS prévision à date historique.',
        'Labels buzz/tendance fournis mais NON vérifiés indépendamment : métriques exploratoires.',
        f'{len(features)} sujets alimentaires évalués sur {len(audit)} références ; exclus: {audit.loc[audit.status!="ok","topic_id"].tolist()}.',
        'Whipped lemonade: 1 seul pays disponible ; profil exploité à titre exploratoire avec couverture faible.',
        'Même indicateur Google Trends ne permet pas la comparaison des volumes absolus entre pays.',
        'Séries rééchelonnées sur la fenêtre complète ; données futures présentes dans les features rétrospectives.',
        'Score logistique non calibré : ne pas l’appeler probabilité métier ni confiance validée.',
        'Test Leave-One-Topic-Out évite fuite du même sujet entre apprentissage et test mais non les biais de sélection des sujets.',
        'Vérifier les requêtes et les exports API Google Trends, ainsi que les labels, avant toute validation scientifique.',
        *(['CAS PISTACHE PROVISOIRE: label tendance proposé par hypothèse de travail, non validé indépendamment ; il ne constitue PAS un cas de test indépendant.',
            'NORMALISATION NON HOMOGENE: pistache provient du P0 2019-2026, alors que le référentiel historique provient de séries exportées 2014-2026 puis limitées à 2019-2026 ; métriques de comparaison affectées.'] if 'pistachio' in features.topic_id.values else []),
      ],
    }
    (output/'metrics_v2.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    h=hashlib.sha256(input_path.read_bytes()).hexdigest()
    manifest={
      'version':VERSION,'created_at_utc':datetime.now(timezone.utc).isoformat(),
      'data_file':str(input_path),'data_sha256':h,
      'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__,
      'features':FEATURE_COLUMNS,'policy':FeaturePolicy().__dict__,'model_params':full.get_params(),
      'metrics_file':'metrics_v2.json','predictions_file':predictions_name,
      'repro_command':f'python -m sillage_v2.train --input {input_path.as_posix()} --out {output.as_posix()}'
    }
    (output/'manifest_v2.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    # Rapport humain lisible pour comité V2.
    r=metrics['logistic_regression']; b=metrics['always_buzz_baseline']
    (output/'RESULTATS_V2.md').write_text(
       '# Sillage — Evaluation expérimentale M2 V2\n\n'
       f'- Données : **{len(audit)} sujets**, dont **{len(features)} alimentaires évalués** ; {metrics["excluded_topics"]} hors scope.\n'
       '- Validation : **Leave-One-Topic-Out** (un sujet entièrement absent de son entraînement).\n'
       '- Labels : **provisoires, non vérifiés par une revue historique indépendante**.\n\n'
       '## Comparaison\n\n| Métrique | Logistic Regression | Toujours buzz |\n|---|---:|---:|\n'
       f'| Accuracy | {r["accuracy"]:.3f} | {b["accuracy"]:.3f} |\n'
       f'| Balanced accuracy | {r["balanced_accuracy"]:.3f} | {b["balanced_accuracy"]:.3f} |\n'
       f'| Macro F1 | {r["f1_macro"]:.3f} | {b["f1_macro"]:.3f} |\n'
       f'| ROC-AUC | {r["roc_auc"]:.3f} | {b["roc_auc"]:.3f} |\n\n'
       '## Limites\n\n' + '\n'.join('- '+w for w in metrics['warnings'])+'\n',encoding='utf-8')
    return metrics


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,default=Path('data/raw/reference_30_cas_google_trends_2019_2026.csv'))
    ap.add_argument('--out',type=Path,default=Path('artifacts/v2'))
    ap.add_argument('--features',type=Path,default=None,help='Caractéristiques dérivées pour dépôt sans raw')
    ap.add_argument('--audit',type=Path,default=None)
    args=ap.parse_args();r=train_evaluate(None if args.features else args.input,args.out,args.features,args.audit)
    print(json.dumps({'n_cases_evaluated':r['food_cases_evaluated'],
                      'balanced_accuracy':r['logistic_regression']['balanced_accuracy'],
                      'f1_macro':r['logistic_regression']['f1_macro'],
                      'baseline_f1_macro':r['always_buzz_baseline']['f1_macro']},indent=2))

if __name__=='__main__':main()
