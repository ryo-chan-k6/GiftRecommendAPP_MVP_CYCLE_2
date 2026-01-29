# Scoring Definition

## 1. Purpose

本ドキュメントは、レコメンド処理における **スコア計算ロジック（② Re-rank）** を明確に定義する。

- 各スコアの意味・役割を固定する
- mode による重み変更が「どう効くか」を説明可能にする
- 実装・検証・ログ解析時のブレを防ぐ

---

## 2. Scoring Pipeline Overview

Re-rank フェーズでは、以下 3 種類のスコアを算出・正規化し、重み付き合成を行う。

1. **S_vec** : 意図と商品の意味的類似度
2. **S_pop** : 商品の人気度（外部・内部シグナル）
3. **S_rev** : レビューによる品質・信頼度

```
S_final = w_vec * S_vec + w_pop * S_pop + w_rev * S_rev
```

※ 予算適合はハードフィルタで処理し、スコアには含めない。

---

## 3. Vector Similarity Score (S_vec)

### 3.1 定義

- ContextVector と ItemVector の **cosine similarity**
- pgvector により算出

```
sim_i = cosine_similarity(context_vector, item_vector_i)
```

### 3.2 正規化（Candidate 集合内）

候補集合内で 0〜1 に正規化する。

```
S_vec(i) = (sim_i - min(sim)) / (max(sim) - min(sim) + ε)
```

### 3.3 意図

- 意味的に「条件に合っているか」を最も強く表す軸
- balanced / diverse では最重要スコア
- popular では相対的に重みを下げる

---

## 4. Popularity Score (S_pop)

### 4.1 スコアの役割

- 「外さなさ」「多くの人に支持されている」度合い
- 意味的類似度だけでは補えない安心感を担保

---

### 4.2 入力シグナル（MVP）

MVP では以下を前提とする。

- 外部ランキング順位（rank）
  - 1 位が最も人気
  - 数値が小さいほど良い

---

### 4.3 raw スコア算出（逆数方式・推奨）

```
raw_pop(i) = 1 / (rank_i + c)
```

- `c` : スムージング定数（例: 1.0）
- rank=1 の突出を抑制する目的

---

### 4.4 正規化（Candidate 集合内）

```
S_pop(i) = normalize_0_1(raw_pop(i))
```

---

### 4.5 代替案（将来拡張）

- exp 方式：`exp(-rank / τ)`（トップ集中）
- sales / purchase_count
- favorite / click（自前ログ）

---

## 5. Review Score (S_rev)

### 5.1 課題

- review_average 単体は信頼できない
  - ★5 × 1 件 が過大評価される

---

### 5.2 分解アプローチ

レビューを以下 2 軸に分解する。

1. **評価の高さ（Quality）**
2. **信頼度（Confidence）**

---

### 5.3 Quality（平均評価）

```
Q(i) = clamp(review_average_i / 5, 0, 1)
```

---

### 5.4 Confidence（件数補正・log）

```
C(i) = log(1 + review_count_i) / log(1 + C_max)
```

- `C_max` : Candidate 集合内の最大 review_count
- log により「件数の暴れ」を抑制

---

### 5.5 合成（MVP 採用）

```
S_rev(i) = Q(i) * C(i)
```

---

## 6. Final Re-rank Score

### 6.1 合成式

```
S_final = w_vec * S_vec + w_pop * S_pop + w_rev * S_rev
```

### 6.2 重みの役割

- w_vec : 意図適合度
- w_pop : 外さなさ
- w_rev : 品質・安心感

mode により w\_\* を切り替える。

---

## 7. Examples

### 7.1 スコア例（概念）

| item | S_vec | S_pop | S_rev | S_final (balanced) |
| ---- | ----- | ----- | ----- | ------------------ |
| A    | 0.90  | 0.30  | 0.80  | 0.72               |
| B    | 0.75  | 0.85  | 0.70  | 0.78               |
| C    | 0.88  | 0.40  | 0.30  | 0.66               |

→ popular では B が、diverse/balanced では A が上に来やすい。

---

## 8. Notes

- 全スコアは **Candidate 集合内正規化**が前提
- スコア定義を変える場合は本ドキュメントを更新する
- 本定義は MMR の入力（S_final）としても利用される

---

## 9. Out of Scope (MVP)

- Bayesian Average（レビュー高度化）
- 時系列減衰（新しさ補正）
- ユーザー別重み学習
