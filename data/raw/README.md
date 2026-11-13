Re-download the raw data (both Open Government Licence v3.0):

```bash
curl -L -o mm23.csv "https://www.ons.gov.uk/file?uri=/economy/inflationandpriceindices/datasets/consumerpriceindices/current/mm23.csv"
curl -o ashe_region_median_weekly_pay.csv "https://www.nomisweb.co.uk/api/v01/dataset/NM_30_1.data.csv?geography=K02000001,TYPE480&date=2015-latest&sex=8&item=2&pay=1&measures=20100&select=date_name,geography_name,geography_code,sex_name,item_name,pay_name,obs_value,obs_status_name"
```
