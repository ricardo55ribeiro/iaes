import pandas as pd

# Load the original dataset
df = pd.read_csv("data/icon_prices.csv")
df["DateTime"] = pd.to_datetime(df["DateTime"], dayfirst=True)

# Keep complete days with 48 periods and valid forecast/actual prices
df = df.groupby(df["DateTime"].dt.date).filter(
    lambda day: len(day) == 48
    and day["SMPEA"].notna().all()
    and day["SMPEP2"].notna().all()
)

# Save the cleaned dataset
df.to_csv("data/icon_prices_clean.csv", index=False)
