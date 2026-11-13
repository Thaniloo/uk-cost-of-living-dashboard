// FactPay: ASHE is a snapshot of pay in April each year, so it joins to the April row of DimDate.
let
    Source   = StagingAshe,
    WithKey  = Table.AddColumn(Source, "date_key", each [year] * 10000 + 401, Int64.Type),
    Merged   = Table.NestedJoin(WithKey, {"region_code"}, DimRegion, {"region_code"}, "r", JoinKind.Inner),
    Expanded = Table.ExpandTableColumn(Merged, "r", {"region_key"}),
    Result   = Table.SelectColumns(Expanded, {"date_key", "region_key", "median_weekly_pay"})
in
    Result
