# Experiment Protocol v1

狀態：待 PLEIAData 下載與 schema audit 後凍結

## 1. Primary estimands

### E1：Forecast value

相較 seasonal naive，使用 weather、indoor state 與 HVAC state 的模型，在 unseen
rolling folds 上能降低多少 block-level consumption MAE？

### E2：Decision value

相較 observed/rule-based setpoint schedule，模型式策略在 offline rollout 中能降低
多少 predicted consumption，同時將 occupied-period temperature 維持於預先指定的
comfort band？

### E3：Synthetic-to-real gap

現有 synthetic CSV 與 PLEIAData 在 autocorrelation、feature-target relationship、
model ranking 與 explanation stability 上有多大差異？

## 2. Unit of analysis

- Forecast：building block × hour。
- Thermal model：room/device × hour，必要時以 block aggregation。
- Decision episode：固定 6-hour horizon，待資料 schema 後確認。

## 3. Outcomes

### Forecast outcomes

- MAE、RMSE、normalized MAE；
- peak-period MAE；
- prediction interval coverage 與 width。

### Decision outcomes

- predicted energy reduction；
- peak demand reduction；
- occupied comfort violation degree-hours；
- setpoint changes per day；
- worst-case performance under forecast uncertainty。

任何節能數值必須標示為 `offline estimated`、`simulation validated` 或
`field measured` 其中一種，不可混用。

## 4. Experimental splits

- chronological rolling-origin folds；
- 至少涵蓋 heating、mild、cooling seasons；
- 最後一段時間保留為 untouched final test；
- PLEIA blocks 採 leave-one-block-out sensitivity analysis；
- BDG2 採 building/site holdout，避免同建築資料洩漏至 train/test。

確切日期需根據資料有效 coverage 決定，不預先硬編。

## 5. Models

### Baselines

- persistence；
- seasonal naive 24 h / 168 h；
- historical profile；
- regularized linear model。

### Candidate models

- Random Forest；
- gradient-boosted trees；
- compact MLP；
- sequence model 僅在 tree model 後，且需證明增益。

## 6. Ablations

- calendar only；
- + weather；
- + historical consumption；
- + indoor temperature；
- + HVAC state/mode；
- + setpoint；
- full model。

這可將「哪些資料真正有用」與單純 feature importance 分離。

## 7. Explainability

- permutation importance；
- SHAP global、dependence、event-level local explanation；
- fold/seed 間 top-k rank stability；
- sign consistency 與 building-physics sanity checks；
- explanation drift：PLEIA block 間及 PLEIA vs BDG2。

## 8. Statistical analysis

- 以相同 timestamp/episode 的 loss difference 做 paired comparison；
- 同時報告 confidence interval 與 effect size；
- 多模型比較時控制 multiple comparisons；
- 不以單一 p-value 取代 practical significance；
- model ranking 必須跨 fold/seed 報告。

## 9. Decision-support formulation

### State

forecast consumption、indoor temperature、weather、HVAC state/mode、setpoint、
time features，以及 uncertainty interval。

### Action

有限 setpoint adjustment，例如 {-1, 0, +1} °C；實際範圍需依資料觀察與設備
規格決定，不在 schema audit 前假定。

### Objective

minimize：energy/cost proxy + comfort penalty + switching penalty。

### Constraints

- occupied comfort band；
- device mode compatibility；
- setpoint bounds；
- ramp/change-frequency limit；
- uncertainty safety margin。

### Baselines

- observed schedule；
- fixed setpoint；
- time-based rule；
- perfect-forecast oracle upper bound。

## 10. Reproducibility gates

- raw file hashes；
- immutable raw data directory；
- deterministic preprocessing manifest；
- configuration-driven experiments；
- one metrics table as the source of every paper table/figure；
- environment lock；
- no manual number transfer into the manuscript。

## 11. Pre-registered failure conditions

研究不得宣稱決策框架有效，如果：

- advanced models 未穩定優於 seasonal naive；
- indoor temperature/HVAC alignment 無法可靠建立；
- counterfactual model 缺乏 overlap/support；
- comfort violations 增加；
- 結果只在單一 block/fold/seed 成立；
- model-based saving 對合理的不確定性假設不穩健。

