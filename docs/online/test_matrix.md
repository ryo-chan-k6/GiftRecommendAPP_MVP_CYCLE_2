# Test Matrix (MVP)

## 1. Purpose
Cursor AI がそのままテストケースに落とし込めるように、観点を表にする。

---

## 2. Core Scenarios

| ID | Category | Scenario | Expected |
|---|---|---|---|
| T-01 | Mode | popular | 返却、resolvedAlgorithm.name=vector_ranked_mmr |
| T-02 | Mode | balanced | 返却、params確認 |
| T-03 | Mode | diverse | Kが大きい（params） |
| T-04 | Budget | min/max | 範囲外が混ざらない |
| T-05 | Budget |片側のみ| 片側フィルタ |
| T-06 | NG | featuresNg | 除外される |
| T-07 | Reuse | 同一入力2回 | contextHash同一、reuse方針通り |
| T-08 | Admin | vector_only | MMRなし、baseline比較 |
| T-09 | Debug | ADMIN debug | score内訳返却 |
| T-10 | Error | embedding失敗 | EMBEDDING_FAILED |

---

## 3. Regression Focus
- min-max 分母0（ε）
- review_count=0
- rank 欠損
- MMR max_sim の計算
