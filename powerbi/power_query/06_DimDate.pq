// DimDate: one row per month (both sources are monthly or annual, so no daily grain needed).
// month_index is a contiguous counter so DAX can step back 12 months without time-intelligence
// functions, which expect a daily calendar.
let
    StartDate = #date(2015, 1, 1),
    EndDate   = Date.StartOfMonth(DateTime.Date(DateTime.LocalNow())),
    Months    = List.Generate(() => StartDate, each _ <= EndDate, each Date.AddMonths(_, 1)),
    AsTable   = Table.FromList(Months, Splitter.SplitByNothing(), type table [date = date]),
    AddKey    = Table.AddColumn(AsTable, "date_key", each Date.Year([date]) * 10000 + Date.Month([date]) * 100 + 1, Int64.Type),
    AddYear   = Table.AddColumn(AddKey, "year", each Date.Year([date]), Int64.Type),
    AddMonth  = Table.AddColumn(AddYear, "month_number", each Date.Month([date]), Int64.Type),
    AddName   = Table.AddColumn(AddMonth, "month_name", each Date.ToText([date], "MMM", "en-GB"), type text),
    AddYM     = Table.AddColumn(AddName, "year_month", each Date.ToText([date], "yyyy-MM"), type text),
    AddIndex  = Table.AddColumn(AddYM, "month_index", each [year] * 12 + [month_number] - 1, Int64.Type),
    AddAshe   = Table.AddColumn(AddIndex, "is_ashe_reference_month", each [month_number] = 4, type logical)
in
    AddAshe
