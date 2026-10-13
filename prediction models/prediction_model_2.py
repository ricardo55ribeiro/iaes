"""Model 2: LightGBM."""
from lightgbm import LGBMRegressor


def build_model():
    return LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=15,
        random_state=42,
        n_jobs=2,
        verbosity=-1,
    )
