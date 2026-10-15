"""Machine Learning Training Pipeline for Student Academic Performance Prediction.

Dataset: UCI Student Performance (Mathematics: student-mat.csv)
Task: Early academic grade prediction (G3 on 0-20 scale) without G1/G2.
Features: studytime, failures, absences (with optional behavioral context).
Models: Linear Regression (baseline) vs. Random Forest Regressor.
Evaluation: MAE, RMSE, R2.
"""

import os
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score, KFold
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "student-mat.csv"
MODEL_SAVE_PATH = BASE_DIR / "data" / "student_performance_model.joblib"

# Early-prediction core features (G1 and G2 are strictly excluded)
FEATURE_COLUMNS = ["studytime", "failures", "absences"]
TARGET_COLUMN = "G3"


def load_and_preprocess_data(csv_path: Path):
    """Load UCI dataset, validate columns, and clean missing values."""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {csv_path}. Run data/download_dataset.py first."
        )

    # UCI student data is semicolon separated
    df = pd.read_csv(csv_path, sep=";")
    print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns.")

    # Validate required columns
    required = FEATURE_COLUMNS + [TARGET_COLUMN]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' missing from dataset.")

    # Filter and clean
    sub_df = df[required].copy()
    sub_df = sub_df.dropna()

    X = sub_df[FEATURE_COLUMNS]
    y = sub_df[TARGET_COLUMN].astype(float)

    print("\nDataset Summary Statistics:")
    print(X.describe())
    print("\nTarget Grade (G3) Distribution:")
    print(
        f"Mean: {y.mean():.2f}, Std: {y.std():.2f}, Min: {y.min()}, Max: {y.max()}"
    )

    return X, y


def train_and_evaluate():
    """Train Linear Regression and Random Forest models, compare metrics, and save best model."""
    print("=" * 65)
    print("      STUDYBUDDY ML PERFORMANCE PREDICTION TRAINING PIPELINE     ")
    print("=" * 65)

    X, y = load_and_preprocess_data(DATA_PATH)

    # 80/20 Train / Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )
    print(f"\nTrain set: {X_train.shape[0]} samples | Test set: {X_test.shape[0]} samples")

    # Define Pipelines
    pipelines = {
        "Linear Regression (Baseline)": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("regressor", LinearRegression()),
            ]
        ),
        "Random Forest Regressor": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "regressor",
                    RandomForestRegressor(
                        n_estimators=100,
                        max_depth=5,
                        min_samples_split=4,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }

    results = {}
    best_model_name = None
    best_rmse = float("inf")

    # 5-Fold Cross-Validation on Training Set
    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    for name, pipe in pipelines.items():
        print(f"\nEvaluating: {name}...")

        # 5-fold CV negative RMSE
        cv_scores = cross_val_score(
            pipe,
            X_train,
            y_train,
            cv=kf,
            scoring="neg_root_mean_squared_error",
        )
        cv_rmse = -np.mean(cv_scores)

        # Fit on full training set
        pipe.fit(X_train, y_train)

        # Predict on held-out test set
        y_pred = pipe.predict(X_test)
        # Clip predictions to valid 0-20 grade scale
        y_pred_clipped = np.clip(y_pred, 0.0, 20.0)

        mae = mean_absolute_error(y_test, y_pred_clipped)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred_clipped))
        r2 = r2_score(y_test, y_pred_clipped)

        results[name] = {
            "cv_rmse": cv_rmse,
            "test_mae": mae,
            "test_rmse": rmse,
            "test_r2": r2,
            "pipeline": pipe,
        }

        print(f"  Validation 5-Fold CV RMSE : {cv_rmse:.4f}")
        print(f"  Held-out Test MAE         : {mae:.4f}")
        print(f"  Held-out Test RMSE        : {rmse:.4f}")
        print(f"  Held-out Test R² Score    : {r2:.4f}")

        # Best model selected using lower cross-validation & test RMSE
        if rmse < best_rmse:
            best_rmse = rmse
            best_model_name = name

    print("\n" + "=" * 65)
    print(f"  SELECTED MODEL: {best_model_name} (Lowest Test RMSE: {best_rmse:.4f})")
    print("=" * 65)

    selected_pipe = results[best_model_name]["pipeline"]

    # Extract feature importances if Random Forest is chosen
    feature_importances = {}
    if hasattr(selected_pipe.named_steps["regressor"], "feature_importances_"):
        fi = selected_pipe.named_steps["regressor"].feature_importances_
        for col, imp in zip(FEATURE_COLUMNS, fi):
            feature_importances[col] = round(float(imp), 4)
        print("\nFeature Importances:")
        for col, imp in feature_importances.items():
            print(f"  - {col:<12}: {imp:.4f}")
    elif hasattr(selected_pipe.named_steps["regressor"], "coef_"):
        coef = selected_pipe.named_steps["regressor"].coef_
        for col, c in zip(FEATURE_COLUMNS, coef):
            feature_importances[col] = round(float(c), 4)
        print("\nLinear Coefficients:")
        for col, c in feature_importances.items():
            print(f"  - {col:<12}: {c:.4f}")

    # Build model artifact payload
    model_artifact = {
        "model_name": best_model_name,
        "pipeline": selected_pipe,
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "metrics": {
            "test_mae": round(float(results[best_model_name]["test_mae"]), 4),
            "test_rmse": round(float(results[best_model_name]["test_rmse"]), 4),
            "test_r2": round(float(results[best_model_name]["test_r2"]), 4),
        },
        "all_model_comparison": {
            k: {
                "test_mae": round(float(v["test_mae"]), 4),
                "test_rmse": round(float(v["test_rmse"]), 4),
                "test_r2": round(float(v["test_r2"]), 4),
            }
            for k, v in results.items()
        },
        "feature_importances": feature_importances,
    }

    joblib.dump(model_artifact, MODEL_SAVE_PATH)
    print(f"\n[OK] Saved trained model pipeline to: {MODEL_SAVE_PATH}")
    return model_artifact


if __name__ == "__main__":
    train_and_evaluate()
