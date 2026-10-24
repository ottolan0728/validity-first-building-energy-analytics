# PLEIAData Schema Audit

稽核日期：2026-07-12  
Verification Status：`VERIFIED`（archive checksum）／`ANALYZED`（table schema）

## 1. Archive integrity

| Item | Value |
|---|---|
| Source | Zenodo record 7096790, v1 |
| Archive | `Data_Nature.zip` |
| Bytes | 275,019,580 |
| Official MD5 | `f2deee82939dc05663078b2220639285` |
| Local MD5 | `f2deee82939dc05663078b2220639285` |
| Integrity | PASS |
| Extracted files | 54 |
| Extracted bytes | 2,138,203,534 |

Raw files are stored under `data/raw/pleiadata/` and excluded from Git.

## 2. Delimiter contract

Most CSV files use semicolon delimiters despite the `.csv` extension. Parsers must detect or
explicitly declare `sep=';'`. `data-presence.csv` uses commas. Treat delimiter as a file-level
contract; never rely on the filename extension.

## 3. Analysis-ready hourly tables

### Consumption

| Block | File | Rows | Period (UTC) | Coverage | Missing cells |
|---|---|---:|---|---:|---:|
| A | `consA-60T.csv` | 8,266 | 2021-01-01 00:00 to 2021-12-18 00:00 | 98.11% | 0 |
| B | `consB-60T.csv` | 8,268 | same | 98.14% | 0 |
| C | `consC-60T.csv` | 7,965 | same | 94.54% | 0 |

Variables:

- `dif_cons_real`: hourly consumption difference, primary forecasting target candidate;
- `cons_total`: cumulative consumption, not a direct model target;
- `dif_cons_smooth`: smoothed value; must not be used as an input until its window and
  direction are verified, because centered/future smoothing could leak future information.

### Indoor temperature

Each `temp-sensor{A,B,C}-60T.csv` contains 8,424 unique hourly timestamps from
2021-01-01 01:00 to 2021-12-18 00:00 with no missing cells.

### HVAC aggregate

Each `hvac-agg{A,B,C}-60T.csv` contains 8,425 unique hourly timestamps from
2021-01-01 00:00 to 2021-12-18 00:00 with no missing cells.

Important fields:

- `V4`: number/aggregate state of active HVAC devices;
- `V12`: mean setpoint;
- `V26`: aggregate device type encoding;
- `V5_0`, `V5_1`, `V5_2`: predominant/off, heating, and cooling mode indicators.

These interpretations must be verified against the author notebook before final feature naming.

### Weather

`data-weather-60T.csv` contains 8,424 unique hourly timestamps from
2021-01-01 00:00 to 2021-12-17 23:00 with no missing cells. Variables include outdoor
temperature, humidity, radiation, wind, precipitation, dew point, and vapor pressure deficit.

## 4. Author merged modeling tables

| Block | Rows | Period | Coverage over period |
|---|---:|---|---:|
| A | 7,611 | 2021-01-05 07:00 to 2021-12-17 23:00 | 91.47% |
| B | 8,266 | 2021-01-01 01:00 to 2021-12-17 23:00 | 98.14% |
| C | 7,963 | 2021-01-01 01:00 to 2021-12-17 23:00 | 94.54% |

The author tables are useful for comparison, but the paper pipeline will rebuild them from the
component tables. This makes join direction, timezone conversion, gap treatment, and leakage
controls explicit.

## 5. Relationship tables

| Relation | Rows |
|---|---:|
| HVAC device to block/room | 87 |
| temperature sensor to block/room | 90 |
| CO2 sensor to block/room | 14 |
| presence sensor to block/room | 12 |

Presence is a motion signal/proxy, not verified occupancy. It must not be called ground-truth
occupancy in the manuscript.

## 6. Modeling decisions after audit

1. Primary granularity: block-hour.
2. Primary target: `dif_cons_real` at t+1; secondary horizons t+3 and t+6.
3. Common initial window: 2021-01-05 through 2021-12-17, finalized after explicit joins.
4. Keep missing consumption timestamps missing; do not bridge gaps with target interpolation.
5. Create contiguous-segment identifiers so lag/rolling features never cross gaps.
6. Fit preprocessing within each rolling training fold.
7. Exclude `dif_cons_smooth` until its construction is proven strictly causal.
8. Use raw sensor/device tables only after the hourly baseline is reproducible.
9. Treat setpoint analysis as observational; enforce common-support checks before any
   counterfactual claim.

## 7. Remaining checks before model execution

- Inspect the author notebook code that generates every 60-minute table.
- Confirm local timezone and daylight-saving handling.
- Verify `V4`, `V12`, `V26`, and `V5_*` aggregation semantics.
- Quantify gap lengths and contiguous segments by block.
- Check impossible temperature/setpoint values and HVAC mode conflicts.
- Determine whether consumption is total building electricity or monitored HVAC aggregation.
- Freeze a processed-data schema and hash.

