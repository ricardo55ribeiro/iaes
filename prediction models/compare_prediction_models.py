"""Compare 5 electricity-price predictors with chronological cross-validation.

Run from the project root:
    python "prediction models/compare_prediction_models.py"

Input:
    data/icon_prices_clean.csv

Outputs:
    prediction models/Comparison_of_Predictions.csv  (overall ranking)
    data/Predictions_2013.csv                   (out-of-sample 2013 forecasts)

Method: expanding-window, 2-month forward tests from Jul 2012 through Dec 2013.
A model is trained ONLY on dates before each test block. Later folds can use
previous 2013 data for training, but never the data they are testing on.

All prices and errors are in EUR/MWh (divide by 1000 for the MiniZinc model).
Models and their settings are defined in prediction_model_1.py through _5.py.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error

from prediction_model_1 import build_model as histgb
from prediction_model_2 import build_model as lightgbm
from prediction_model_3 import build_model as catboost
from prediction_model_4 import build_model as xgboost
from prediction_model_5 import build_model as lasso

DATA_FILE = Path("data/icon_prices_clean.csv")
COMPARISON_DIR = Path("prediction models")
PREDICTIONS_DIR = Path("data")
FEATURES = ["SMPEA", "ForecastWindProduction", "SystemLoadEA", "PeriodOfDay", "Month"]
TARGET = "SMPEP2"

# First 8 months are training only. The next 18 months are evaluated in order.
FIRST_TEST = pd.Timestamp("2012-07-01")
AFTER_LAST_TEST = pd.Timestamp("2014-01-01")
TEST_BLOCK_MONTHS = 2

MODELS = {
    "HistGradientBoosting": histgb,
    "LightGBM": lightgbm,
    "CatBoost": catboost,
    "XGBoost": xgboost,
    "Lasso": lasso,
}


def main():
    if not DATA_FILE.is_file():
        raise FileNotFoundError(f"Cannot find {DATA_FILE}. Run from the IAES project root.")

    df = pd.read_csv(DATA_FILE)
    needed = ["DateTime", *FEATURES, TARGET]
    missing = [col for col in needed if col not in df.columns]
    if missing:
        raise ValueError(f"Missing dataset columns: {missing}")

    df["DateTime"] = pd.to_datetime(df["DateTime"], errors="raise")
    df = df.sort_values(["DateTime", "PeriodOfDay"]).reset_index(drop=True)
    if df["DateTime"].duplicated().any():
        raise ValueError("Duplicate timestamps found. Please inspect the dataset first.")

    # Input forecasts and actual prices must exist. Other features can be imputed.
    if df[["SMPEA", TARGET]].isna().any().any():
        raise ValueError("Missing original forecast or actual price values.")
    for column in FEATURES:
        df[column] = pd.to_numeric(df[column], errors="raise")
    df[TARGET] = pd.to_numeric(df[TARGET], errors="raise")

    if df["DateTime"].min() >= FIRST_TEST or df["DateTime"].max() < AFTER_LAST_TEST - pd.Timedelta(days=1):
        raise ValueError("Expected historical data covering late 2011 through the end of 2013.")

    # Per-row predictions are filled only when that row belongs to a future test block.
    oof_predictions = {"Original SMPEA": df["SMPEA"].to_numpy(dtype=float).copy()}
    oof_predictions.update({name: np.full(len(df), np.nan) for name in MODELS})
    tested = np.zeros(len(df), dtype=bool)
    fold_rows = []

    test_start = FIRST_TEST
    fold_number = 0
    while test_start < AFTER_LAST_TEST:
        test_end = min(test_start + pd.DateOffset(months=TEST_BLOCK_MONTHS), AFTER_LAST_TEST)
        train_mask = df["DateTime"] < test_start
        test_mask = (df["DateTime"] >= test_start) & (df["DateTime"] < test_end)
        train = df.loc[train_mask]
        test = df.loc[test_mask]
        if len(train) < 48 * 180 or len(test) < 48 * 28:
            raise ValueError(f"Insufficient history or test data for block starting {test_start.date()}.")
        if tested[test_mask].any():
            raise ValueError("Test blocks overlap. Check FIRST_TEST / TEST_BLOCK_MONTHS.")
        tested[test_mask] = True
        fold_number += 1

        # Fit imputation on older data only. Keep column names for Lasso's pipeline.
        imputer = SimpleImputer(strategy="median")
        train_X = pd.DataFrame(imputer.fit_transform(train[FEATURES]), columns=FEATURES)
        test_X = pd.DataFrame(imputer.transform(test[FEATURES]), columns=FEATURES)
        train_y = train[TARGET].to_numpy()
        test_y = test[TARGET].to_numpy()

        common = {
            "Fold": fold_number,
            "Train_through": (test_start - pd.Timedelta(days=1)).date().isoformat(),
            "Test_from": test_start.date().isoformat(),
            "Test_through": (test_end - pd.Timedelta(days=1)).date().isoformat(),
            "Test_periods": len(test),
        }
        baseline_mae = mean_absolute_error(test_y, test["SMPEA"])
        fold_rows.append({**common, "Model": "Original SMPEA", "MAE_EUR_MWh": baseline_mae})

        print(f"Fold {fold_number}: train before {test_start.date()}, test {test_start.date()} to {(test_end - pd.Timedelta(days=1)).date()}", flush=True)
        for name, factory in MODELS.items():
            model = factory()  # completely NEW model at every fold (no look-ahead)
            model.fit(train_X, train_y)
            pred = np.asarray(model.predict(test_X), dtype=float)
            if pred.shape != (len(test),) or not np.isfinite(pred).all():
                raise ValueError(f"Invalid predictions from {name} on fold {fold_number}")
            oof_predictions[name][test_mask] = pred
            fold_rows.append({**common, "Model": name, "MAE_EUR_MWh": mean_absolute_error(test_y, pred)})
        test_start = test_end

    expected_test = (df["DateTime"] >= FIRST_TEST) & (df["DateTime"] < AFTER_LAST_TEST)
    if not np.array_equal(tested, expected_test.to_numpy()):
        raise ValueError("Not all eligible test dates were evaluated.")

    baseline_mae = mean_absolute_error(df.loc[tested, TARGET], oof_predictions["Original SMPEA"][tested])
    fold_results = pd.DataFrame(fold_rows)
    # A second view of robustness: how often each method wins a whole test block.
    fold_winners = fold_results.loc[
        fold_results.groupby("Fold")["MAE_EUR_MWh"].idxmin(), "Model"
    ].value_counts()
    baseline_by_fold = fold_results.loc[
        fold_results["Model"] == "Original SMPEA"
    ].set_index("Fold")["MAE_EUR_MWh"]
    overall = []
    for name, pred in oof_predictions.items():
        score = mean_absolute_error(df.loc[tested, TARGET], pred[tested])
        model_folds = fold_results.loc[fold_results["Model"] == name, "MAE_EUR_MWh"]
        overall.append({
            "Model": name,
            "WalkForward_MAE_EUR_MWh": score,
            "Improvement_vs_SMPEA_pct": 100 * (baseline_mae - score) / baseline_mae,
            "Mean_fold_MAE_EUR_MWh": model_folds.mean(),
            "Folds_won": int(fold_winners.get(name, 0)),
            "Folds_better_than_SMPEA": int(sum(
                row.MAE_EUR_MWh < baseline_by_fold.loc[row.Fold]
                for row in fold_results.loc[fold_results["Model"] == name].itertuples()
            )),
        })

    ranking = pd.DataFrame(overall).sort_values("WalkForward_MAE_EUR_MWh").reset_index(drop=True)
    winner = ranking.loc[0, "Model"]
    ranking["Selected"] = np.where(ranking["Model"] == winner, "YES", "")

    # Keep the 2013 per-period forecasts for later scheduling comparisons.
    in_2013 = tested & (df["DateTime"].dt.year.to_numpy() == 2013)
    predictions_2013 = pd.DataFrame({
        "DateTime": df.loc[in_2013, "DateTime"].dt.strftime("%Y-%m-%d %H:%M:%S").to_numpy(),
        "PeriodOfDay": df.loc[in_2013, "PeriodOfDay"].to_numpy(),
        "Actual_SMPEP2": df.loc[in_2013, TARGET].to_numpy(),
        "Original_SMPEA": oof_predictions["Original SMPEA"][in_2013],
        **{name: predictions[in_2013] for name, predictions in oof_predictions.items() if name != "Original SMPEA"},
    })

    COMPARISON_DIR.mkdir(exist_ok=True)
    PREDICTIONS_DIR.mkdir(exist_ok=True)
    ranking.to_csv(COMPARISON_DIR / "Comparison_of_Predictions.csv", index=False, float_format="%.4f")
    predictions_2013.to_csv(PREDICTIONS_DIR / "Predictions_2013.csv", index=False, float_format="%.6f")

    print("\nChronological cross-validation ranking (lower MAE = better):")
    print(ranking.to_string(index=False, float_format=lambda value: f"{value:.3f}"))
    print(f"\nSelected: {winner} (best pooled MAE across {fold_number} future test blocks)")
    print(f"Test periods evaluated: {int(tested.sum()):,}")
    print(f"Saved: {COMPARISON_DIR / 'Comparison_of_Predictions.csv'}")
    print(f"Saved: {PREDICTIONS_DIR / 'Predictions_2013.csv'} ({len(predictions_2013):,} rows)")
    print("Note: These scores select among the current five fixed configurations, not all possible models.")
    print("Selection and performance estimation use the same folds; a truly unbiased final assessment needs later unseen data.")
    print("All models use the original SMPEA price forecast as an input.")


if __name__ == "__main__":
    main()
