"""Exploratory analysis of preprocessed MANGO climate datasets."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "docs" / "eda_figures"
FIG.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="husl")

rain = pd.read_csv(PROC / "rainfall_final.csv", parse_dates=["date"])
maxt = pd.read_csv(PROC / "maxtemp_final.csv", parse_dates=["date"])
mint = pd.read_csv(PROC / "mintemp_final.csv", parse_dates=["date"])
merged = pd.read_csv(PROC / "climate_merged.csv", parse_dates=["date"])

findings = {}

# --- Coverage ---
findings["coverage"] = {
    "rainfall_rows": len(rain),
    "maxtemp_rows": len(maxt),
    "mintemp_rows": len(mint),
    "merged_rows": len(merged),
    "merge_rate_pct": round(100 * len(merged) / len(rain), 2),
    "date_range": f"{rain.date.min().date()} to {rain.date.max().date()}",
    "n_days": int(rain.date.nunique()),
    "rain_grid_cells_025deg": int(rain.groupby(["latitude", "longitude"]).ngroups),
    "temp_grid_cells_1deg": int(maxt.groupby(["latitude", "longitude"]).ngroups),
    "rain_lat_range": [float(rain.latitude.min()), float(rain.latitude.max())],
    "rain_lon_range": [float(rain.longitude.min()), float(rain.longitude.max())],
    "temp_lat_range": [float(maxt.latitude.min()), float(maxt.latitude.max())],
    "temp_lon_range": [float(maxt.longitude.min()), float(maxt.longitude.max())],
}

# --- Rainfall ---
cell_annual = rain.groupby(["latitude", "longitude"]).rainfall.sum()
cell_wet_frac = rain.groupby(["latitude", "longitude"]).apply(
    lambda x: (x.rainfall > 0).mean(), include_groups=False
)
daily_national = rain.groupby("date").rainfall.sum()

findings["rainfall"] = {
    "mean_mm_per_cell_day": round(rain.rainfall.mean(), 3),
    "median_mm": round(rain.rainfall.median(), 3),
    "std_mm": round(rain.rainfall.std(), 3),
    "max_mm_single_cell_day": round(rain.rainfall.max(), 3),
    "pct_zero_rain": round(100 * (rain.rainfall == 0).mean(), 2),
    "category_counts": {k: int(v) for k, v in rain.rain_category.value_counts().items()},
    "monthly_mean_daily_total_national": {
        int(m): round(rain[rain.month == m].groupby("date").rainfall.sum().mean(), 2)
        for m in range(1, 13)
    },
    "top_rain_day": str(daily_national.idxmax().date()),
    "top_rain_day_national_total_mm": round(float(daily_national.max()), 2),
    "highest_annual_cell_mm": {
        "lat": float(cell_annual.idxmax()[0]),
        "lon": float(cell_annual.idxmax()[1]),
        "total_mm": round(float(cell_annual.max()), 2),
    },
    "wettest_cell_fraction_wet_days": {
        "lat": float(cell_wet_frac.idxmax()[0]),
        "lon": float(cell_wet_frac.idxmax()[1]),
        "fraction": round(float(cell_wet_frac.max()), 3),
    },
}

# --- Temperature ---
temp_join = maxt.merge(mint, on=["date", "latitude", "longitude"])
temp_join["diurnal_range"] = temp_join["max_temp"] - temp_join["min_temp"]
lat_max = maxt.groupby("latitude").max_temp.mean()

findings["temperature"] = {
    "max_temp_mean": round(maxt.max_temp.mean(), 2),
    "max_temp_std": round(maxt.max_temp.std(), 2),
    "max_temp_range": [round(maxt.max_temp.min(), 2), round(maxt.max_temp.max(), 2)],
    "min_temp_mean": round(mint.min_temp.mean(), 2),
    "min_temp_std": round(mint.min_temp.std(), 2),
    "min_temp_range": [round(mint.min_temp.min(), 2), round(mint.min_temp.max(), 2)],
    "diurnal_range_mean": round(temp_join.diurnal_range.mean(), 2),
    "diurnal_range_max": round(temp_join.diurnal_range.max(), 2),
    "hottest_day_by_national_mean_max": str(maxt.groupby("date").max_temp.mean().idxmax().date()),
    "coldest_day_by_national_mean_min": str(mint.groupby("date").min_temp.mean().idxmin().date()),
    "monthly_mean_max_temp": {
        int(m): round(maxt[maxt.month == m].max_temp.mean(), 2) for m in range(1, 13)
    },
    "monthly_mean_min_temp": {
        int(m): round(mint[mint.month == m].min_temp.mean(), 2) for m in range(1, 13)
    },
    "coolest_lat_band_mean_max": round(float(lat_max.idxmin()), 1),
    "warmest_lat_band_mean_max": round(float(lat_max.idxmax()), 1),
}

# --- Correlations ---
merged = merged.copy()
merged["diurnal_range"] = merged["max_temp"] - merged["min_temp"]
corr = merged[["rainfall", "max_temp", "min_temp", "diurnal_range"]].corr()
findings["correlations"] = {
    k: {kk: round(vv, 3) for kk, vv in v.items()} for k, v in corr.to_dict().items()
}
findings["rain_maxtemp_corr_by_month"] = {
    mo: round(merged[merged.month == mo][["rainfall", "max_temp"]].corr().iloc[0, 1], 3)
    for mo in range(1, 13)
}

# --- Monsoon ---
monsoon = rain[rain.month.isin([6, 7, 8, 9])]
non_monsoon = rain[~rain.month.isin([6, 7, 8, 9])]
findings["monsoon"] = {
    "monsoon_rain_share_pct": round(100 * monsoon.rainfall.sum() / rain.rainfall.sum(), 1),
    "monsoon_mean_mm_per_cell_day": round(monsoon.rainfall.mean(), 3),
    "non_monsoon_mean_mm_per_cell_day": round(non_monsoon.rainfall.mean(), 3),
    "monsoon_wet_day_pct": round(100 * (monsoon.rainfall > 0).mean(), 1),
}

# --- Spatial 1deg ---
cell_stats = merged.groupby(["lat_match", "lon_match"]).agg(
    mean_rain=("rainfall", "mean"),
    mean_max=("max_temp", "mean"),
    mean_min=("min_temp", "mean"),
).reset_index()
findings["spatial_1deg"] = {
    "driest_cell": {
        "lat": float(cell_stats.loc[cell_stats.mean_rain.idxmin(), "lat_match"]),
        "lon": float(cell_stats.loc[cell_stats.mean_rain.idxmin(), "lon_match"]),
        "mean_rain": round(float(cell_stats.mean_rain.min()), 3),
    },
    "wettest_cell": {
        "lat": float(cell_stats.loc[cell_stats.mean_rain.idxmax(), "lat_match"]),
        "lon": float(cell_stats.loc[cell_stats.mean_rain.idxmax(), "lon_match"]),
        "mean_rain": round(float(cell_stats.mean_rain.max()), 3),
    },
}

# --- Quality & extremes ---
findings["quality"] = {
    "merged_duplicate_rows": int(merged.duplicated(subset=["date", "latitude", "longitude"]).sum()),
    "rainfall_negative": int((rain.rainfall < 0).sum()),
    "physically_invalid_max_lt_min": int((merged.max_temp < merged.min_temp).sum()),
    "rainfall_rows_not_merged": len(rain) - len(merged),
    "avg_merged_rows_per_day": round(len(merged) / merged.date.nunique(), 1),
}

findings["extremes"] = {
    "heavy_rain_ge_50mm_count": int((merged.rainfall >= 50).sum()),
    "heavy_rain_pct": round(100 * (merged.rainfall >= 50).mean(), 3),
    "extreme_heat_max_ge_40C": int((merged.max_temp >= 40).sum()),
    "extreme_cold_min_le_5C": int((merged.min_temp <= 5).sum()),
}

# --- Plots ---
month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

monthly_rain = rain.groupby("month").rainfall.sum() / rain.groupby("month").date.nunique()
axes[0, 0].bar(month_labels, [monthly_rain.get(i, 0) for i in range(1, 13)], color="steelblue")
axes[0, 0].set_title("Mean daily national rainfall total by month (2013)")
axes[0, 0].set_ylabel("mm / day (summed over grid)")

monthly_max = maxt.groupby("month").max_temp.mean()
monthly_min = mint.groupby("month").min_temp.mean()
axes[0, 1].plot(month_labels, [monthly_max[i] for i in range(1, 13)], "r-o", label="Max temp")
axes[0, 1].plot(month_labels, [monthly_min[i] for i in range(1, 13)], "b-o", label="Min temp")
axes[0, 1].set_title("National mean temperature by month")
axes[0, 1].set_ylabel("°C")
axes[0, 1].legend()

axes[1, 0].hist(
    rain.rainfall[rain.rainfall > 0],
    bins=50,
    color="steelblue",
    edgecolor="white",
    log=True,
)
axes[1, 0].set_title("Rainfall distribution (wet days only, log scale)")
axes[1, 0].set_xlabel("mm")

merged.sample(min(50000, len(merged)), random_state=42).plot.scatter(
    x="max_temp", y="rainfall", alpha=0.05, ax=axes[1, 1], s=5, color="green"
)
axes[1, 1].set_title("Rainfall vs max temperature (50k sample)")
axes[1, 1].set_xlabel("Max temp (°C)")
axes[1, 1].set_ylabel("Rainfall (mm)")

plt.tight_layout()
plt.savefig(FIG / "01_seasonality_and_distributions.png", dpi=150)
plt.close()

# Spatial mean rain
rain_cell = rain.groupby(["latitude", "longitude"]).rainfall.mean().reset_index()
pivot_rain = rain_cell.pivot(index="latitude", columns="longitude", values="rainfall")
fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(pivot_rain, cmap="YlGnBu", ax=ax, cbar_kws={"label": "Mean daily rainfall (mm)"})
ax.set_title("Mean daily rainfall by grid cell (2013)")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
plt.tight_layout()
plt.savefig(FIG / "02_spatial_mean_rainfall.png", dpi=150)
plt.close()

# Spatial mean max temp
maxt_cell = maxt.groupby(["latitude", "longitude"]).max_temp.mean().reset_index()
pivot_max = maxt_cell.pivot(index="latitude", columns="longitude", values="max_temp")
fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(pivot_max, cmap="RdYlBu_r", ax=ax, cbar_kws={"label": "Mean max temp (°C)"})
ax.set_title("Mean max temperature by grid cell (2013)")
plt.tight_layout()
plt.savefig(FIG / "03_spatial_mean_maxtemp.png", dpi=150)
plt.close()

# Correlation heatmap
fig, ax = plt.subplots(figsize=(6, 5))
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
ax.set_title("Variable correlations (climate_merged)")
plt.tight_layout()
plt.savefig(FIG / "04_correlation_matrix.png", dpi=150)
plt.close()

# Daily time series
daily = merged.groupby("date").agg(
    rain=("rainfall", "sum"),
    tmax=("max_temp", "mean"),
    tmin=("min_temp", "mean"),
)
fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.plot(daily.index, daily.rain, color="steelblue", alpha=0.7, label="National rain sum")
ax1.set_ylabel("Rainfall (mm, summed)", color="steelblue")
ax2 = ax1.twinx()
ax2.plot(daily.index, daily.tmax, color="red", alpha=0.6, label="Mean max temp")
ax2.plot(daily.index, daily.tmin, color="blue", alpha=0.6, label="Mean min temp")
ax2.set_ylabel("Temperature (°C)")
ax1.set_title("2013 daily national aggregates")
fig.legend(loc="upper right")
plt.tight_layout()
plt.savefig(FIG / "05_daily_timeseries.png", dpi=150)
plt.close()

out = ROOT / "docs" / "eda_findings.json"
out.write_text(json.dumps(findings, indent=2))
print(json.dumps(findings, indent=2))
print(f"\nFigures saved to {FIG}")
print(f"Findings JSON saved to {out}")
