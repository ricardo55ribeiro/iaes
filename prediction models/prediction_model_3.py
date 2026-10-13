"""Model 3: CatBoost."""
from catboost import CatBoostRegressor


def build_model():
    return CatBoostRegressor(
        iterations=350,
        depth=5,
        learning_rate=0.05,
        loss_function="RMSE",
        random_seed=42,
        thread_count=2,
        verbose=False,
        allow_writing_files=False,
    )
