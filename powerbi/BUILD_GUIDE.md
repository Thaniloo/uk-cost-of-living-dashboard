# Building the .pbix (about 45 minutes in Power BI Desktop)

Power BI Desktop runs on Windows only. This repo contains everything the report needs: Power Query M, a star schema, DAX measures and a page spec. A working HTML preview of the same two pages is in `dashboard/`.

## 1. Load and clean (Power Query)
1. **Home → Transform data → Manage Parameters → New**: `RawFolder` (Text) = the full path to `data/raw\`, including the trailing backslash.
2. For each file in `power_query/`, in order: **New Source → Blank Query → Advanced Editor**, paste, and name the query after the file (`DimCategory`, `FactPrices`, `StagingAshe`, `DimRegion`, `FactPay`, `DimDate`).
3. Right-click `StagingAshe` → untick **Enable load**. It only feeds `DimRegion` and `FactPay`.
4. **Close & Apply.** Expected row counts: FactPrices ≈ 1,550, FactPay 143, DimRegion 13, DimCategory 11.

> Shortcut: `data/model/*.csv` are the same tables built by `src/build_model.py`. Use **Get data → Text/CSV** if you just want to get to the DAX.

## 2. Model view
| From (many) | To (one) | Direction |
|---|---|---|
| FactPrices[date_key] | DimDate[date_key] | Single |
| FactPrices[category_key] | DimCategory[category_key] | Single |
| FactPay[date_key] | DimDate[date_key] | Single |
| FactPay[region_key] | DimRegion[region_key] | Single |

- Mark **DimDate** as the date table (column `date`).
- Sort `DimCategory[category_short]` by `sort_order`, and `DimDate[month_name]` by `month_number`.
- Hide all key columns and `month_index`.
- **Modeling → New parameter → Numeric range**: name `Base Year`, 2015–2025, increment 1, default 2020.
- Create an empty `_Measures` table and paste in the measures from `measures.dax`.

## 3. Page 1: Summary (one screen)
| Visual | Fields | Notes |
|---|---|---|
| Card | `Food Change Since Base %` | Subtitle: `KPI Subtitle Food` |
| Card | `Fastest Rising Category %` | Category label: `Fastest Rising Category` |
| Card | `Real Pay Change vs Food %`, filtered to region = United Kingdom | |
| Card | `Weakest Region %` | Category label: `Weakest Region` |
| Line chart | X: DimDate[date], Y: `Rebased Index`, Legend: category_short | Filter: category_short in {Food (all), All items}; date ≥ 2019 |

Title the line chart with the finding ("Food prices rose 38% since January 2020…"), not the chart type.

## 4. Page 2: Drill-down
- **Slicers** (top row): `DimCategory[category_short]` as chips (Food class only), `DimRegion[region]` as a dropdown, and the `Base Year` parameter.
- **Line**: `Rebased Index` by date, legend = category, for the selected categories plus All items (dashed).
- **Bar** (horizontal): `Price Change Since Base (Latest) %` by category_short, sorted descending, with a constant line at `CPI Change Since Base %`.
- **Line**: `Real Wage Index` by DimDate[year], for the selected region vs UK (filter `is_uk_total` with an OR in the visual filter).
- **Bar** (horizontal): `Real Pay Change vs Food %` by region, excluding the UK, sorted ascending.

## 5. Publish
**File → Publish → Publish to web** (if your tenant allows it). Otherwise record a 60-second walkthrough and use the screenshots in `screenshots/`.
