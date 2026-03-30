import pandas as pd
import numpy as np

def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # clean column names
    df.columns = [
        "date",
        "cbp_apprehended",
        "cbp_custody",
        "cbp_transferred",
        "hhs_care",
        "hhs_discharged"
    ]

    # drop empty rows
    df = df.dropna(subset=["date"])
    df = df[df["date"].str.strip() != ""]

    # parse dates
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # clean numeric columns (remove commas)
    numeric_cols = [
        "cbp_apprehended", "cbp_custody",
        "cbp_transferred", "hhs_care", "hhs_discharged"
    ]
    for col in numeric_cols:
        df[col] = (
            df[col].astype(str)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # --- derived metrics ---

    # total system load
    df["total_load"] = df["cbp_custody"] + df["hhs_care"]

    # net daily intake (pressure indicator)
    df["net_intake"] = df["cbp_transferred"] - df["hhs_discharged"]

    # discharge offset ratio (how well discharges keep up with transfers)
    df["discharge_ratio"] = np.where(
        df["cbp_transferred"] > 0,
        (df["hhs_discharged"] / df["cbp_transferred"] * 100).round(1),
        0
    )

    # 7-day and 14-day rolling averages for HHS care load
    df["hhs_7day_avg"]  = df["hhs_care"].rolling(7,  min_periods=1).mean().round(1)
    df["hhs_14day_avg"] = df["hhs_care"].rolling(14, min_periods=1).mean().round(1)

    # 7-day rolling net intake (backlog trend)
    df["net_intake_7day"] = df["net_intake"].rolling(7, min_periods=1).mean().round(1)

    # care load growth rate (day-over-day %)
    df["growth_rate"] = df["hhs_care"].pct_change().multiply(100).round(2)

    # backlog accumulation (cumulative net intake from start)
    df["backlog_cumulative"] = df["net_intake"].cumsum()

    # year and month columns for grouping
    df["year"]       = df["date"].dt.year
    df["month"]      = df["date"].dt.month
    df["year_month"] = df["date"].dt.to_period("M").astype(str)

    return df


def compute_kpis(df: pd.DataFrame) -> dict:
    latest = df.iloc[-1]
    return {
        "total_load":        int(latest["total_load"]),
        "hhs_care":          int(latest["hhs_care"]),
        "cbp_custody":       int(latest["cbp_custody"]),
        "net_pressure":      int(df["net_intake"].tail(7).mean().round(0)),
        "discharge_ratio":   float(df["discharge_ratio"].tail(7).mean().round(1)),
        "peak_hhs":          int(df["hhs_care"].max()),
        "peak_date":         df.loc[df["hhs_care"].idxmax(), "date"].strftime("%b %d, %Y"),
        "avg_daily_intake":  int(df["cbp_apprehended"].mean().round(0)),
        "volatility_index":  int(df["hhs_care"].std().round(0)),
        "date_range":        f"{df['date'].min().strftime('%b %Y')} – {df['date'].max().strftime('%b %Y')}",
    }