// DimRegion: the 12 ITL1 regions/nations plus a UK total row.
let
    Source   = Table.Distinct(Table.SelectColumns(StagingAshe, {"region_code", "region"})),
    Sorted   = Table.Sort(Source, {{"region_code", Order.Ascending}}),
    Indexed  = Table.AddIndexColumn(Sorted, "region_key", 1, 1, Int64.Type),
    Nation   = Table.AddColumn(Indexed, "nation", each
                   if Text.StartsWith([region_code], "E12") then "England"
                   else if Text.StartsWith([region_code], "W92") then "Wales"
                   else if Text.StartsWith([region_code], "S92") then "Scotland"
                   else if Text.StartsWith([region_code], "N92") then "Northern Ireland"
                   else "United Kingdom", type text),
    IsUK     = Table.AddColumn(Nation, "is_uk_total", each [region_code] = "K02000001", type logical)
in
    IsUK
