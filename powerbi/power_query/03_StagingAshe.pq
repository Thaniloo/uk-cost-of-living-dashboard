// StagingAshe (disable load): ONS ASHE median gross weekly pay, full-time workers, by region.
// Source: Nomis API, dataset NM_30_1 (ASHE resident analysis), 2015 onwards.
// URL used:
// https://www.nomisweb.co.uk/api/v01/dataset/NM_30_1.data.csv?geography=K02000001,TYPE480&date=2015-latest&sex=8&item=2&pay=1&measures=20100
let
    Source   = Csv.Document(File.Contents(RawFolder & "ashe_region_median_weekly_pay.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Renamed  = Table.RenameColumns(Promoted, {
                   {"DATE_NAME", "year"}, {"GEOGRAPHY_NAME", "region"},
                   {"GEOGRAPHY_CODE", "region_code"}, {"OBS_VALUE", "median_weekly_pay"}}),
    // Flag anything ONS marks as not a normal value (provisional, low quality, suppressed)
    Normal   = Table.SelectRows(Renamed, each [OBS_STATUS_NAME] = "Normal Value"),
    Typed    = Table.TransformColumnTypes(Normal, {{"year", Int64.Type}, {"median_weekly_pay", type number}}, "en-GB"),
    Result   = Table.SelectColumns(Typed, {"year", "region_code", "region", "median_weekly_pay"})
in
    Result
