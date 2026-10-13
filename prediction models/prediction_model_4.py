"""Model 4: XGBoost."""
from xgboost import XGBRegressor


def build_model():
    return XGBRegressor(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        tree_method="hist",
        random_state=42,
        n_jobs=2,
        verbosity=0,
    )
