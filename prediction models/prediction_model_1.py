"""Model 1: our original histogram gradient boosting predictor."""
from sklearn.ensemble import HistGradientBoostingRegressor


def build_model():
    return HistGradientBoostingRegressor(random_state=42)
