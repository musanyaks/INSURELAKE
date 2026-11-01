"""
Train a synthetic-data fraud classifier.
Works with or without Docker / Kafka / MinIO - pure Python.
Outputs ml/models/fraud_xgb.pkl and prints validation AUC.
"""
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

FEATURES = [
    "claim_amount", "log_amount", "days_since_policy_start",
    "customer_claim_count", "policy_claim_count", "provider_claim_count",
    "county_risk", "is_weekend", "hour_of_day", "dup_score",
]


def synth(n: int = 20_000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "claim_amount":            rng.lognormal(11, 1.0, n),
        "days_since_policy_start": rng.integers(1, 1500, n),
        "customer_claim_count":    rng.poisson(1.2, n),
        "policy_claim_count":      rng.poisson(0.8, n),
        "provider_claim_count":    rng.poisson(1.5, n),
        "county_risk":             rng.choice([0.2, 0.5, 0.8], n),
        "is_weekend":              rng.integers(0, 2, n),
        "hour_of_day":             rng.integers(0, 24, n),
        "dup_score":               rng.random(n) * 0.5,
    })
    df["log_amount"] = np.log1p(df["claim_amount"])
    score = (
        0.35 * (df["days_since_policy_start"] < 30) +
        0.20 * (df["customer_claim_count"] >= 3) +
        0.25 * (df["provider_claim_count"] >= 3) +
        0.15 * (df["log_amount"] > 13) +
        0.10 * (df["county_risk"] > 0.7) +
        0.10 * (df["dup_score"] > 0.4)
    )
    prob = 1 / (1 + np.exp(-(score * 6 - 2)))
    df["is_fraud"] = (rng.random(n) < prob).astype(int)
    return df


def main():
    df = synth()
    X, y = df[FEATURES], df["is_fraud"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, stratify=y, test_size=0.2, random_state=7)

    neg, pos = (ytr == 0).sum(), (ytr == 1).sum()
    model = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        scale_pos_weight=neg / max(pos, 1),
        eval_metric="auc", use_label_encoder=False, verbosity=0,
    )
    model.fit(Xtr, ytr)

    proba = model.predict_proba(Xte)[:, 1]
    print(f"\nValidation AUC: {roc_auc_score(yte, proba):.4f}\n")
    print(classification_report(yte, (proba > 0.5).astype(int), digits=3))

    fi = (pd.Series(model.feature_importances_, index=FEATURES)
            .sort_values(ascending=False))
    print("\nFeature importance:\n" + fi.to_string())

    Path("ml/models").mkdir(parents=True, exist_ok=True)
    with open("ml/models/fraud_xgb.pkl", "wb") as f:
        pickle.dump(model, f)
    print("\nsaved -> ml/models/fraud_xgb.pkl")


if __name__ == "__main__":
    main()
