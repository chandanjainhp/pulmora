"""ML service: trains the logistic regression model once (at startup, via the
FastAPI lifespan handler) and serves predictions from the trained model.

Training replicates the original ``Home/views.py`` exactly:

    df = pd.read_csv("static/dataset/lungcancer.csv")
    labels = df.columns[0:-1]
    X = np.asarray(df[labels], dtype="float64")
    Y = df["Level"]
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=0.25, random_state=1)
    reg = LogisticRegression()
    reg.fit(X_train, Y_train)

Only the *training* split is used to fit, as in the original code.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

# Diagnosis code -> label (exact mapping from views.py)
DIAGNOSIS_LABELS = {1: "Positive", 0: "Medium", -1: "Negative"}


class MLModel:
    """A trained LogisticRegression plus its feature metadata."""

    def __init__(self, model: LogisticRegression, feature_names: list[str]):
        self.model = model
        self.feature_names = feature_names

    def predict(self, features: list[int]) -> dict:
        """Run the model on one sample of 22 features.

        Returns ``{"diagnosis_code", "diagnosis", "probability"}`` where
        probability is the model's confidence in the predicted class.
        """
        x = np.array([features], dtype="float64")
        pred = self.model.predict(x)
        diagnosis_code = int(pred[0])
        proba = self.model.predict_proba(x)[0]
        class_index = int(np.where(self.model.classes_ == diagnosis_code)[0][0])
        return {
            "diagnosis_code": diagnosis_code,
            "diagnosis": DIAGNOSIS_LABELS.get(diagnosis_code, "Negative"),
            "probability": float(proba[class_index]),
        }

    @property
    def train_accuracy(self) -> float:
        """Accuracy on the held-out test split (for /health diagnostics)."""
        return float(self._test_accuracy)

    def set_test_metrics(self, X_test: np.ndarray, Y_test) -> None:
        self._test_accuracy = self.model.score(X_test, Y_test)


def train_model(dataset_path: str | Path) -> MLModel:
    """Train the model exactly like the original Django view did."""
    df = pd.read_csv(dataset_path)
    labels = df.columns[0:-1]
    X = np.asarray(df[labels], dtype="float64")
    Y = df["Level"]
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=0.25, random_state=1
    )
    reg = LogisticRegression()
    reg.fit(X_train, Y_train)

    ml_model = MLModel(model=reg, feature_names=[str(c) for c in labels])
    ml_model.set_test_metrics(X_test, Y_test)
    logger.info(
        "ML model trained on %s (%d training rows, %d features); "
        "held-out accuracy: %.4f",
        dataset_path,
        len(X_train),
        len(labels),
        ml_model.train_accuracy,
    )
    return ml_model
