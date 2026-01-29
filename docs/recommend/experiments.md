# Experiments & Evaluation Guide

## 1. Purpose

本ドキュメントは、レコメンドロジックの **検証・比較・改善** を目的とした
実験（experiments）の設計指針と運用方法を定義する。

- Algorithm / mode / パラメータ差分を安全に比較する
- 結果の再現性を担保する
- 主観評価と定量評価を分離して整理する

---

## 2. Experiments の基本方針

### 2.1 前提

- 一般ユーザー向けの Algorithm は固定（Pattern A）
- 実験は **ADMIN 操作または内部バッチ** のみで実施する
- 本番ユーザー体験を壊さないことを最優先とする

---

### 2.2 実験の単位

本システムにおける実験の最小単位は以下。

- **Context**（条件スナップショット）
- **Algorithm + Params**
- **出力された Recommendation Result**

---

## 3. Experiment Types

### 3.1 Algorithm Comparison

Algorithm 自体の違いを比較する実験。

| 比較対象                         | 目的                   |
| -------------------------------- | ---------------------- |
| vector_only vs vector_ranked_mmr | ベクトル単体の限界確認 |
| vector_ranked_mmr (λ 差分)       | 多様性制御の効果確認   |

---

### 3.2 Mode Comparison

mode によるパラメータセットの違いを比較する。

| mode     | 観点              |
| -------- | ----------------- |
| popular  | 外さなさ / 安心感 |
| balanced | 全体バランス      |
| diverse  | 被り回避 / 探索性 |

---

### 3.3 Parameter Sweep

単一パラメータを段階的に変化させる実験。

- λ sweep（例: 0.1 / 0.3 / 0.5 / 0.7 / 0.9）
- CandidateSize(K) sweep
- weight 比率変更（w_vec / w_pop / w_rev）

---

## 4. Experiment Execution Flow

```
[Context Fix]
     |
     v
[Parameter / Algorithm Override (ADMIN)]
     |
     v
[Recommendation Execution]
     |
     v
[Result Persistence]
     |
     v
[Offline Evaluation]
```

---

## 5. Required Logging & Persistence

### 5.1 Recommendation Header

recommendation テーブルに必ず保存する。

- context_id
- algorithm
- params
- mode
- executed_at

---

### 5.2 Recommendation Items

recommendation_item テーブル。

- rank
- score
- vector_score
- rerank_score
- reason

---

## 6. Evaluation Axes

### 6.1 定量評価（Offline）

- カテゴリ多様性（例: unique category count）
- 平均 cosine similarity（selected 同士）
- 上位 N の人気スコア平均
- レビュー平均値

---

### 6.2 定性評価（Human-in-the-loop）

- 人が見て「被っている」と感じるか
- 意図に合っていると説明できるか
- 「選びやすい並び」になっているか

---

## 7. Example Experiment

### 7.1 λ 比較（同一 Context）

| λ    | 上位 5 商品                          | 所感       |
| ---- | ------------------------------------ | ---------- |
| 0.25 | 時計 / ネクタイ / 財布 / 香水 / マグ | 多様性高い |
| 0.55 | 財布 / 時計 / 香水 / ネクタイ / 靴   | バランス   |
| 0.85 | 財布 / 財布 / 財布 / 時計 / 香水     | 被り多い   |

---

## 8. Analysis Tips

- **vector_only を基準線（baseline）として必ず残す**
- 結果はスクリーンショット + JSON で保存
- mode を変えたら λ / weights も必ず併記する

---

## 9. Failure Patterns

- K が小さすぎて diverse が機能しない
- λ を下げすぎて relevance が崩壊
- popularity を強めすぎて意味的ズレが発生

---

## 10. Out of Scope (MVP)

- オンライン AB テスト
- CTR / CVR ベースの最適化
- 自動ハイパーパラメータ探索

---

## 11. Summary

- experiments は設計の延長であり、運用の土台
- **Context × Params × Result** を揃えて保存することが最重要
- 本ドキュメントは改善サイクルのチェックリストとして使う
