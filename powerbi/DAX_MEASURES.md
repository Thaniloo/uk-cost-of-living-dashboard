# DAX measures: what each one does and why

| Measure | What it returns | Design note |
|---|---|---|
| `Price Index` | ONS index (2015 = 100) for the category/month in context | Plain average: one row per category-month, so it's exact |
| `Price YoY %` | Change vs the same month a year earlier | Uses `month_index − 12` rather than `DATEADD`. Time-intelligence functions expect a daily calendar, and this model is monthly by design. |
| `Base Month Index` | Index in January of the chosen base year | `Base Year` is a what-if parameter, so a viewer can re-base to 2019 (pre-pandemic) in one click |
| `Price Change Since Base %` / `(Latest)` | Cumulative change from the base month to the month in context, or to the latest month | The "latest" variant drives the KPI cards and the ranking bar |
| `Rebased Index` | Index with the base month = 100 | Puts categories with very different 2015 levels on one comparable axis |
| `Fastest Rising Category` | Name of the food class with the largest change | `TOPN(1, …)` over the food classes only, so "Food (all)" and "All items" can't win |
| `Median Weekly Pay` / `Base Year Pay` / `Latest Pay` | ASHE median full-time gross weekly pay | ASHE is an April snapshot, so pay facts sit on April rows of DimDate |
| `Food Index (April)` | Food CPI in April of the year in context | Matches the timing of the pay survey, so pay and prices are compared at the same point in the year |
| `Real Wage Index` | (pay ÷ base pay) ÷ (food index ÷ base food index) × 100 | Below 100 means a week's pay buys less food than in the base year |
| `Real Pay Change vs Food %` | (1 + pay change) ÷ (1 + food inflation) − 1 | Ratio, not subtraction: it's the correct way to deflate, and the difference grows when inflation is high |
| `Weakest Region` / `Regions Behind Food Prices` | Worst region and count of regions below zero | UK total excluded through `is_uk_total` |

**What was left out on purpose:**
- Regional CPI. ONS doesn't publish it, and inventing regional deflators would look precise but be wrong. The footer states this.
- A map. With 12 regions, a sorted bar is faster to read and doesn't make large, empty regions look important.
- Item-level series (about 60 food items). They exist in mm23, but 9 COICOP classes keep the slicer readable. Adding items is a one-line change to `DimCategory`.
