"""Build the star schema for the cost-of-living dashboard from the raw ONS files.

This mirrors the Power Query steps in powerbi/power_query/ one for one, so the model
can be checked (and the README numbers reproduced) without Power BI.

Usage:  python src/build_model.py
Input:  data/raw/mm23.csv                         (ONS Consumer price inflation dataset)
        data/raw/ashe_region_median_weekly_pay.csv (ONS ASHE via Nomis, full-time median weekly pay)
Output: data/model/*.csv, results/findings.json, charts/*.png, dashboard/data.js
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, MODEL, CH, RES, DASH = (ROOT / p for p in ("data/raw", "data/model", "charts", "results", "dashboard"))
for d in (MODEL, CH, RES, DASH):
    d.mkdir(parents=True, exist_ok=True)

BASE_YEAR = 2020

# CDID -> (category, short name, sort order). COICOP 01.1.x food classes plus two reference lines.
SERIES = {
    "D7BT": ("All items CPI", "All items", 0, "Reference"),
    "D7C8": ("Food", "Food (all)", 1, "Reference"),
    "D7D5": ("Bread & cereals", "Bread & cereals", 2, "Food class"),
    "D7D6": ("Meat", "Meat", 3, "Food class"),
    "D7D7": ("Fish", "Fish", 4, "Food class"),
    "D7D8": ("Milk, cheese & eggs", "Milk, cheese & eggs", 5, "Food class"),
    "D7D9": ("Oils & fats", "Oils & fats", 6, "Food class"),
    "D7DA": ("Fruit", "Fruit", 7, "Food class"),
    "D7DB": ("Vegetables incl. potatoes", "Vegetables", 8, "Food class"),
    "D7DC": ("Sugar, jam, chocolate & confectionery", "Sugar & sweets", 9, "Food class"),
    "D7DD": ("Food products n.e.c. (sauces, ready meals)", "Sauces & ready meals", 10, "Food class"),
}
REGION_GROUP = {"E12": "England", "W92": "Wales", "S92": "Scotland", "N92": "Northern Ireland", "K02": "United Kingdom"}


def load_cpi() -> pd.DataFrame:
    """mm23.csv has ~7 header rows (Title, CDID, PreUnit, Unit, Release Date, Next release, Notes)
    followed by annual, quarterly and monthly rows stacked in one column. Keep CDID as the key,
    keep only monthly rows ('2020 JAN'), unpivot."""
    raw = pd.read_csv(RAW / "mm23.csv", header=None, dtype=str, encoding="latin-1", low_memory=False)
    cdid_row = raw.index[raw[0] == "CDID"][0]
    cols = raw.iloc[cdid_row].tolist()
    cols[0] = "period"
    body = raw.iloc[cdid_row + 1:].copy()
    body.columns = cols
    body = body[["period"] + list(SERIES)]
    monthly = body[body.period.str.fullmatch(r"\d{4} [A-Z]{3}", na=False)].copy()
    monthly["date"] = pd.to_datetime(monthly.period, format="%Y %b")
    long = monthly.melt(id_vars="date", value_vars=list(SERIES), var_name="cdid", value_name="index_value")
    long["index_value"] = pd.to_numeric(long.index_value, errors="coerce")
    return long.dropna().query("date >= '2015-01-01'").sort_values(["cdid", "date"])


def load_pay() -> pd.DataFrame:
    df = pd.read_csv(RAW / "ashe_region_median_weekly_pay.csv")
    df = df.rename(columns={"DATE_NAME": "year", "GEOGRAPHY_NAME": "region", "GEOGRAPHY_CODE": "region_code",
                            "OBS_VALUE": "median_weekly_pay"})
    return df[["year", "region_code", "region", "median_weekly_pay"]]


def build():
    cpi, pay = load_cpi(), load_pay()

    # --- dimensions ---
    dim_date = pd.DataFrame({"date": pd.date_range("2015-01-01", cpi.date.max(), freq="MS")})
    dim_date["date_key"] = dim_date.date.dt.strftime("%Y%m%d").astype(int)
    dim_date["year"] = dim_date.date.dt.year
    dim_date["month_number"] = dim_date.date.dt.month
    dim_date["month_name"] = dim_date.date.dt.strftime("%b")
    dim_date["year_month"] = dim_date.date.dt.strftime("%Y-%m")
    dim_date["month_index"] = dim_date.year * 12 + dim_date.month_number - 1   # contiguous month counter for DAX
    dim_date["is_ashe_reference_month"] = dim_date.month_number == 4   # ASHE pay is measured in April

    dim_category = pd.DataFrame([{"category_key": i + 1, "cdid": k, "category": v[0], "category_short": v[1],
                                  "sort_order": v[2], "category_group": v[3]} for i, (k, v) in enumerate(SERIES.items())])

    regions = pay[["region_code", "region"]].drop_duplicates().sort_values("region_code").reset_index(drop=True)   # same order as Power Query
    regions["region_key"] = regions.index + 1
    regions["nation"] = regions.region_code.str[:3].map(REGION_GROUP)
    regions["is_uk_total"] = regions.region_code == "K02000001"
    dim_region = regions[["region_key", "region_code", "region", "nation", "is_uk_total"]]

    # --- facts ---
    fact_prices = (cpi.merge(dim_category[["cdid", "category_key"]], on="cdid")
                      .assign(date_key=lambda d: d.date.dt.strftime("%Y%m%d").astype(int))
                      [["date_key", "category_key", "index_value"]])
    fact_pay = (pay.merge(dim_region[["region_code", "region_key"]], on="region_code")
                   .assign(date_key=lambda d: d.year * 10000 + 401)                 # April of each year
                   [["date_key", "region_key", "median_weekly_pay"]])

    for name, df in [("dim_date", dim_date), ("dim_category", dim_category), ("dim_region", dim_region),
                     ("fact_prices", fact_prices), ("fact_pay", fact_pay)]:
        df.to_csv(MODEL / f"{name}.csv", index=False)
        print(f"{name:14s} {len(df):>6,} rows")
    return cpi, pay, dim_category, dim_region


def analyse(cpi, pay, dim_category, dim_region):
    names = dict(zip(dim_category.cdid, dim_category.category_short))
    wide = cpi.pivot(index="date", columns="cdid", values="index_value")
    latest = wide.index.max()
    base = wide.loc[f"{BASE_YEAR}-01-01"]

    # 1) cumulative change since Jan 2020, by category
    cum = ((wide.loc[latest] / base - 1) * 100).rename(index=names).sort_values(ascending=False)
    # 2) year-on-year change, latest month
    yoy = ((wide.loc[latest] / wide.loc[latest - pd.DateOffset(years=1)] - 1) * 100).rename(index=names)
    # peak food inflation
    food_yoy = (wide["D7C8"] / wide["D7C8"].shift(12) - 1) * 100
    peak = food_yoy.idxmax()

    # 3) real pay: April pay vs April food index / April all-items index, both rebased to 2020
    april = wide[wide.index.month == 4]
    april.index = april.index.year
    p = pay.pivot(index="year", columns="region", values="median_weekly_pay")
    last_pay_year = int(p.index.max())
    nominal = (p.loc[last_pay_year] / p.loc[BASE_YEAR] - 1) * 100
    food_inf = (april.loc[last_pay_year, "D7C8"] / april.loc[BASE_YEAR, "D7C8"] - 1) * 100
    cpi_inf = (april.loc[last_pay_year, "D7BT"] / april.loc[BASE_YEAR, "D7BT"] - 1) * 100
    real_food = ((1 + nominal / 100) / (1 + food_inf / 100) - 1) * 100
    real_cpi = ((1 + nominal / 100) / (1 + cpi_inf / 100) - 1) * 100
    reg = pd.DataFrame({"nominal_pay_change_pct": nominal, "real_vs_food_pct": real_food,
                        "real_vs_cpi_pct": real_cpi,
                        f"pay_{BASE_YEAR}": p.loc[BASE_YEAR], f"pay_{last_pay_year}": p.loc[last_pay_year]}).sort_values("real_vs_food_pct")
    reg.round(2).to_csv(RES / "region_real_pay.csv")
    cum.round(2).to_csv(RES / "category_change_since_2020.csv", header=["pct_change"])

    # real wage index over time (UK + regions), 2020 = 100
    idx = (p / p.loc[BASE_YEAR]).div(april["D7C8"] / april.loc[BASE_YEAR, "D7C8"], axis=0).dropna() * 100

    regions_only = reg.drop(index="United Kingdom")
    F = {
        "latest_cpi_month": latest.strftime("%B %Y"),
        "base": f"January {BASE_YEAR}",
        "food_change_since_base_pct": round(float(cum["Food (all)"]), 1),
        "all_items_change_since_base_pct": round(float(cum["All items"]), 1),
        "fastest_category": {"name": cum.drop(["Food (all)", "All items"]).index[0],
                             "pct": round(float(cum.drop(["Food (all)", "All items"]).iloc[0]), 1)},
        "slowest_category": {"name": cum.drop(["Food (all)", "All items"]).index[-1],
                             "pct": round(float(cum.drop(["Food (all)", "All items"]).iloc[-1]), 1)},
        "category_change_since_base": cum.round(1).to_dict(),
        "food_yoy_latest_pct": round(float(yoy["Food (all)"]), 1),
        "food_yoy_peak": {"month": peak.strftime("%B %Y"), "pct": round(float(food_yoy.max()), 1)},
        "pay_years": f"April {BASE_YEAR} to April {last_pay_year}",
        "food_inflation_same_period_pct": round(float(food_inf), 1),
        "cpi_inflation_same_period_pct": round(float(cpi_inf), 1),
        "uk_nominal_pay_change_pct": round(float(reg.loc["United Kingdom", "nominal_pay_change_pct"]), 1),
        "uk_real_vs_food_pct": round(float(reg.loc["United Kingdom", "real_vs_food_pct"]), 1),
        "weakest_region": {"name": regions_only.index[0], **regions_only.iloc[0].round(1).to_dict()},
        "strongest_region": {"name": regions_only.index[-1], **regions_only.iloc[-1].round(1).to_dict()},
        "regions_behind_food": int((regions_only.real_vs_food_pct < 0).sum()),
        "regions_total": int(len(regions_only)),
    }
    (RES / "findings.json").write_text(json.dumps(F, indent=2))
    print(json.dumps(F, indent=2))

    # data for the HTML preview of the dashboard
    series = {names[c]: [[d.strftime("%Y-%m"), round(v, 2)] for d, v in wide[c].dropna().items()] for c in wide}
    dash = {"findings": F, "series": series,
            "categories": dim_category.sort_values("sort_order").category_short.tolist(),
            "pay": {r: {int(y): v for y, v in p[r].dropna().items()} for r in p},
            "food_april": {int(y): round(v, 2) for y, v in april["D7C8"].items()},
            "cpi_april": {int(y): round(v, 2) for y, v in april["D7BT"].items()},
            "regions": dim_region.sort_values("region_key").region.tolist()}
    (DASH / "data.js").write_text("window.DASH = " + json.dumps(dash) + ";\n")
    charts(wide, names, cum, reg, idx, F)


def charts(wide, names, cum, reg, idx, F):
    BLUE, ORANGE, GREY, INK, INK2 = "#2a78d6", "#eb6834", "#8a8984", "#0b0b0b", "#52514e"
    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
        "font.size": 10, "axes.edgecolor": "#d6d5d0", "axes.labelcolor": INK2, "xtick.color": INK2,
        "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "grid.color": "#ecebe7", "axes.axisbelow": True})

    def save(fig, ax, title, name):
        fig.suptitle(title, x=0.012, ha="left", fontsize=12, fontweight="bold", color=INK)
        fig.tight_layout()
        fig.savefig(CH / name, dpi=160)
        plt.close(fig)

    # headline: food vs all items, indexed Jan 2020 = 100
    w = wide.loc["2019-01-01":]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for cdid, col, lab in [("D7C8", ORANGE, "Food"), ("D7BT", BLUE, "All items CPI")]:
        s = w[cdid] / wide.loc["2020-01-01", cdid] * 100
        ax.plot(s.index, s, color=col, lw=2)
        ax.text(s.index[-1] + pd.Timedelta(days=20), s.iloc[-1], f"{lab} {s.iloc[-1]:.0f}", color=INK2, va="center", fontsize=9)
    ax.axhline(100, color=GREY, lw=0.8, ls="--")
    ax.set_ylabel("Index, Jan 2020 = 100")
    ax.set_xlim(w.index[0], w.index[-1] + pd.Timedelta(days=330))
    save(fig, ax, f"Food prices are up {F['food_change_since_base_pct']:.0f}% since January 2020, "
                  f"vs {F['all_items_change_since_base_pct']:.0f}% for everything", "01_food_vs_cpi.png")

    # category ranking
    c = cum.drop(["All items"]).sort_values()
    fig, ax = plt.subplots(figsize=(8, 4.4))
    colors = [ORANGE if n == "Food (all)" else BLUE for n in c.index]
    ax.barh(c.index, c.values, color=colors, height=0.6)
    for y, v in enumerate(c.values):
        ax.text(v + 0.8, y, f"+{v:.0f}%", va="center", fontsize=9, color=INK2)
    ax.axvline(F["all_items_change_since_base_pct"], color=INK2, lw=1, ls="--")
    ax.text(F["all_items_change_since_base_pct"] + 0.8, -0.9, "All items CPI", fontsize=8.5, color=INK2)
    ax.set_ylim(-1.3, len(c) - 0.4)
    ax.set_xlabel(f"Price change, January 2020 to {F['latest_cpi_month']}")
    ax.grid(axis="y", visible=False)
    save(fig, ax, "Which food categories rose fastest", "02_category_change.png")

    # regions: real pay vs food prices
    r = reg.sort_values("real_vs_food_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    colors = [GREY if n == "United Kingdom" else (ORANGE if v < 0 else BLUE) for n, v in zip(r.index, r.real_vs_food_pct)]
    ax.barh(r.index, r.real_vs_food_pct, color=colors, height=0.6)
    for y, v in enumerate(r.real_vs_food_pct):
        ax.text(v + (0.15 if v >= 0 else -0.15), y, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK2)
    ax.axvline(0, color=INK2, lw=1)
    ax.invert_yaxis()
    lo, hi = r.real_vs_food_pct.min(), r.real_vs_food_pct.max()
    ax.set_xlim(min(lo * 1.5, -1), max(hi * 1.5, 1))
    ax.set_xlabel(f"Median full-time weekly pay vs food prices, {F['pay_years']}")
    ax.grid(axis="y", visible=False)
    save(fig, ax, "Where wages kept up least with food prices", "03_region_real_pay.png")


if __name__ == "__main__":
    analyse(*build())
