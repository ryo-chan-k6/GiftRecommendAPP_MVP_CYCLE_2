# Recommendation Reason Schema

## 1. Purpose
UI に提示する「なぜこれがおすすめか（reason）」を安定して生成するため、
`recommendation_item.reason`（jsonb）のスキーマと生成ルールを定義する。

---

## 2. Principles
- MVP は “説明可能” を優先（精緻さより一貫性）
- ADMIN debug（スコア内訳）とは分離する

---

## 3. JSON Schema (Draft)
```json
{
  "highSimilarity": true,
  "budgetFit": true,
  "matchedHints": ["実用的", "落ち着いた"],
  "popularRank": { "rank": 12, "source": "rakuten" },
  "review": { "average": 4.6, "count": 215 },
  "diversity": { "applied": true }
}
```

---

## 4. Field Rules

- highSimilarity：S_vec が上位閾値なら true
- budgetFit：budget 範囲内なら true
- matchedHints：features_like と item 属性/タグ一致（最大3件）
- popularRank：rank がある場合のみ
- review：count が一定以上なら表示
- diversity：MMRが適用されたことを示す（popular は省略可）

---

## 5. Admin Debug vs User Reason
- user reason：reason のみ
- admin debug：`items[].debug.scores` で別返却
