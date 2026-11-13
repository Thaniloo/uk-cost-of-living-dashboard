// FactPrices: cleans the ONS mm23.csv "Consumer price inflation" dataset.
// The file is wide (4,000+ series as columns) with 7 header rows:
//   Title | CDID | PreUnit | Unit | Release Date | Next release | Important Notes
// and annual ("2020"), quarterly ("2020 Q1") and monthly ("2020 JAN") rows stacked in one column.
let
    Source      = Csv.Document(File.Contents(RawFolder & "mm23.csv"), [Delimiter = ",", Encoding = 1252, QuoteStyle = QuoteStyle.Csv]),

    // 1. Use the CDID row (row 2) as headers: series codes are stable, titles get reworded.
    DropTitle   = Table.Skip(Source, 1),
    Promoted    = Table.PromoteHeaders(DropTitle, [PromoteAllScalars = true]),
    Renamed     = Table.RenameColumns(Promoted, {{"CDID", "Period"}}),

    // 2. Keep only the series in DimCategory (avoids loading 4,000 columns).
    Wanted      = DimCategory[cdid],
    Kept        = Table.SelectColumns(Renamed, List.Combine({{"Period"}, Wanted}), MissingField.Error),

    // 3. Keep monthly rows only. This also drops the metadata rows (PreUnit, Unit, Release Date...).
    Months      = {"JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"},
    MonthlyOnly = Table.SelectRows(Kept, each Text.Length([Period]) = 8 and List.Contains(Months, Text.End([Period], 3))),

    // 4. Wide -> long, then type the values (blank cells become null and are removed).
    Unpivoted   = Table.UnpivotOtherColumns(MonthlyOnly, {"Period"}, "cdid", "index_value"),
    WithDate    = Table.AddColumn(Unpivoted, "date", each #date(
                      Number.From(Text.Start([Period], 4)),
                      List.PositionOf(Months, Text.End([Period], 3)) + 1, 1), type date),
    Typed       = Table.TransformColumns(WithDate, {{"index_value", each try Number.From(_, "en-GB") otherwise null, type number}}),
    NoBlanks    = Table.SelectRows(Typed, each [index_value] <> null and [date] >= #date(2015, 1, 1)),

    // 5. Surrogate keys for the star schema.
    WithKey     = Table.AddColumn(NoBlanks, "date_key", each Date.Year([date]) * 10000 + Date.Month([date]) * 100 + 1, Int64.Type),
    Merged      = Table.NestedJoin(WithKey, {"cdid"}, DimCategory, {"cdid"}, "cat", JoinKind.Inner),
    Expanded    = Table.ExpandTableColumn(Merged, "cat", {"category_key"}),
    Result      = Table.SelectColumns(Expanded, {"date_key", "category_key", "index_value"})
in
    Result
