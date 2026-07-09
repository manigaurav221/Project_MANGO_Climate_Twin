"""Regenerate all processed climate CSVs with consistent 2025 dates."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"

DATA_YEAR = 2025
N_DAYS = 365
ROWS_PER_DAY = 31
TEMP_SENTINEL = 99.90
RAIN_SENTINEL = -999

longitudes = np.arange(67.5, 98.5, 1)
latitudes = np.arange(7.5, 38.5, 1)
dates = pd.date_range(f"{DATA_YEAR}-01-01", periods=N_DAYS, freq="D")


def rain_category(rain: float) -> str:
    if rain == 0:
        return "No Rain"
    if rain < 2.5:
        return "Light"
    if rain < 50:
        return "Moderate"
    return "Heavy"


def process_rainfall() -> pd.DataFrame:
    rain = pd.read_csv(RAW / "Rainfall_ind2025_rfp25.csv", sep=r"\s+", header=None)
    date_rows = rain[rain[0] > 1_000_000].index

    all_days = []
    for i in range(len(date_rows)):
        start = date_rows[i]
        end = date_rows[i + 1] if i < len(date_rows) - 1 else len(rain)
        block = rain.iloc[start:end]

        date_str = str(int(block.iloc[0, 0]))
        block_longitudes = block.iloc[0, 1:].values

        grid = block.iloc[1:].copy()
        grid.columns = ["latitude"] + list(block_longitudes)
        grid = grid.apply(pd.to_numeric, errors="coerce")
        grid = grid.replace(RAIN_SENTINEL, np.nan)

        day = grid.melt(
            id_vars="latitude",
            var_name="longitude",
            value_name="rainfall",
        )
        day["date"] = date_str
        all_days.append(day)

    rain_final = pd.concat(all_days, ignore_index=True)
    rain_final = rain_final.dropna(subset=["rainfall"])
    rain_final["date"] = pd.to_datetime(
        rain_final["date"].astype(str).str.zfill(8),
        format="%d%m%Y",
    )
    rain_final["year"] = rain_final["date"].dt.year
    rain_final["month"] = rain_final["date"].dt.month
    rain_final["day"] = rain_final["date"].dt.day
    rain_final["rain_category"] = rain_final["rainfall"].apply(rain_category)
    return rain_final


def process_temperature(path: Path, value_col: str) -> pd.DataFrame:
    raw = pd.read_csv(path, sep=r"\s+", header=None).replace(TEMP_SENTINEL, np.nan)
    all_days = []

    for day_idx in range(N_DAYS):
        grid = raw.iloc[day_idx * ROWS_PER_DAY : (day_idx + 1) * ROWS_PER_DAY].copy()
        grid.columns = longitudes
        grid["latitude"] = latitudes

        day = grid.melt(
            id_vars="latitude",
            var_name="longitude",
            value_name=value_col,
        )
        day["date"] = dates[day_idx]
        all_days.append(day)

    result = pd.concat(all_days, ignore_index=True).dropna(subset=[value_col])
    result["year"] = result["date"].dt.year
    result["month"] = result["date"].dt.month
    result["day"] = result["date"].dt.day
    return result


def merge_climate(rain_final: pd.DataFrame, maxtemp_final: pd.DataFrame, mintemp_final: pd.DataFrame) -> pd.DataFrame:
    rain_for_merge = rain_final.copy()
    rain_for_merge["lat_match"] = np.floor(rain_for_merge["latitude"]) + 0.5
    rain_for_merge["lon_match"] = np.floor(rain_for_merge["longitude"]) + 0.5

    maxtemp_for_merge = maxtemp_final[["date", "latitude", "longitude", "max_temp"]].rename(
        columns={"latitude": "lat_match", "longitude": "lon_match"}
    )
    mintemp_for_merge = mintemp_final[["date", "latitude", "longitude", "min_temp"]].rename(
        columns={"latitude": "lat_match", "longitude": "lon_match"}
    )

    return (
        rain_for_merge
        .merge(maxtemp_for_merge, on=["date", "lat_match", "lon_match"], how="inner")
        .merge(mintemp_for_merge, on=["date", "lat_match", "lon_match"], how="inner")
    )


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)

    rain_final = process_rainfall()
    maxtemp_final = process_temperature(RAW / "Maxtemp_MaxT_2025.CSV", "max_temp")
    mintemp_final = process_temperature(RAW / "Mintemp_MinT_2025.CSV", "min_temp")
    climate_merged = merge_climate(rain_final, maxtemp_final, mintemp_final)

    rain_final.to_csv(PROC / "rainfall_final.csv", index=False)
    maxtemp_final.to_csv(PROC / "maxtemp_final.csv", index=False)
    mintemp_final.to_csv(PROC / "mintemp_final.csv", index=False)
    climate_merged.to_csv(PROC / "climate_merged.csv", index=False)

    print(f"rainfall_final:   {rain_final.shape} | years: {sorted(rain_final.year.unique())}")
    print(f"maxtemp_final:    {maxtemp_final.shape} | years: {sorted(maxtemp_final.year.unique())}")
    print(f"mintemp_final:    {mintemp_final.shape} | years: {sorted(mintemp_final.year.unique())}")
    print(f"climate_merged:   {climate_merged.shape}")
    print(f"date range:       {rain_final.date.min().date()} to {rain_final.date.max().date()}")


if __name__ == "__main__":
    main()
