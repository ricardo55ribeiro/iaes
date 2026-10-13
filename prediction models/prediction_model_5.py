"""Model 5: simple Lasso regression baseline (not the full LEAR model)."""
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Lasso
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def build_model():
    preprocessing = ColumnTransformer([
        ("numbers", StandardScaler(), ["SMPEA", "ForecastWindProduction", "SystemLoadEA"]),
        ("calendar", OneHotEncoder(handle_unknown="ignore"), ["PeriodOfDay", "Month"]),
    ])
    return Pipeline([
        ("preprocessing", preprocessing),
        ("regression", Lasso(alpha=0.05, max_iter=20000)),
    ])
