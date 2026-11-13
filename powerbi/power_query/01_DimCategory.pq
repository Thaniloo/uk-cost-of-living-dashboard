// DimCategory: the COICOP 01.1 food classes plus two reference lines.
// Hand-entered because the mm23 file has no category hierarchy, only long series titles.
let
    Source = #table(
        type table [category_key = Int64.Type, cdid = text, category = text, category_short = text, sort_order = Int64.Type, category_group = text],
        {
            {1,  "D7BT", "All items CPI",                                "All items",            0,  "Reference"},
            {2,  "D7C8", "Food",                                         "Food (all)",           1,  "Reference"},
            {3,  "D7D5", "Bread & cereals",                              "Bread & cereals",      2,  "Food class"},
            {4,  "D7D6", "Meat",                                         "Meat",                 3,  "Food class"},
            {5,  "D7D7", "Fish",                                         "Fish",                 4,  "Food class"},
            {6,  "D7D8", "Milk, cheese & eggs",                          "Milk, cheese & eggs",  5,  "Food class"},
            {7,  "D7D9", "Oils & fats",                                  "Oils & fats",          6,  "Food class"},
            {8,  "D7DA", "Fruit",                                        "Fruit",                7,  "Food class"},
            {9,  "D7DB", "Vegetables incl. potatoes",                    "Vegetables",           8,  "Food class"},
            {10, "D7DC", "Sugar, jam, chocolate & confectionery",        "Sugar & sweets",       9,  "Food class"},
            {11, "D7DD", "Food products n.e.c. (sauces, ready meals)",   "Sauces & ready meals", 10, "Food class"}
        })
in
    Source
