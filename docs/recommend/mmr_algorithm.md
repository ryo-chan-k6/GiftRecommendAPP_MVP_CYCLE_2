# MMR Algorithm Specification

## 1. Purpose

本ドキュメントは、本サービスで利用する **MMR（Maximal Marginal Relevance）アルゴリズム**について、
目的・数式・処理手順・実装指針を明確に定義する。

- 「なぜ MMR を使うのか」を説明できる
- 実装時のブレを防ぐ
- λ（多様性パラメータ）の意味を共有する

---

## 2. Why MMR?

### 2.1 課題

ベクトル類似度や Re-rank のみでは、以下の問題が発生する。

- 類似した商品が連続して表示される
- ブランド・カテゴリが固まり、探索体験が悪化する

### 2.2 MMR の役割

MMR は以下を同時に満たすことを目的とする。

- **関連性（Relevance）を保つ**
- **冗長性（Redundancy）を抑える**

---

## 3. Conceptual Definition

MMR は「逐次選択型」のアルゴリズムである。

- 1 件ずつ商品を確定させる
- すでに選ばれた集合を考慮して、次の 1 件を決める

---

## 4. Mathematical Definition

### 4.1 記号定義

- S : すでに選択された商品集合（index list）
- C : 未選択の商品集合
- Rel(x) : 商品 x の関連度（S_final）
- Sim(x, y) : 商品 x と y の cosine similarity

---

### 4.2 MMR スコア

未選択商品 x ∈ C に対し、以下を計算する。

```
MMR(x) = λ * Rel(x) - (1 - λ) * max_{s ∈ S} Sim(x, s)
```

---

## 5. Step-by-step Algorithm

### 5.1 Inputs

- 候補商品集合（TopK）
- 各商品の Re-rank スコア（S_final）
- 商品ベクトル行列 V（正規化済み, shape=(K, d)）
- λ（mode により決定）
- 出力件数 N

---

### 5.2 手順（概念）

1. **初期選択**
   - Rel(x) が最大の商品を S に追加
2. **逐次選択**
   - |S| < N の間、以下を繰り返す
     - 各 x ∈ C について MMR(x) を計算
     - 最大の MMR(x) を S に追加
     - C から除外

---

## 6. Similarity Definition

### 6.1 商品間類似度

- ItemVector 同士の cosine similarity
- ベクトルが unit 正規化されていれば **内積 = cosine similarity**

```
Sim(x, y) = x.vector · y.vector
```

---

## 7. λ (Lambda) Interpretation

| λ    | 挙動                       |
| ---- | -------------------------- |
| 0.85 | 関連性重視（popular 寄り） |
| 0.55 | バランス                   |
| 0.25 | 多様性重視（diverse）      |

---

## 8. Candidate Size (K) and Output Size (N)

- K : MMR に投入する候補数
- N : 最終的に返却する件数

---

## 9. Implementation Notes

### 9.1 計算場所

- Vector Retrieval / Re-rank : DB / API
- MMR : アプリケーション層（Node / Python）

---

### 9.2 擬似コード（行列演算版・推奨）

```python
import numpy as np

def mmr_select(V, rel, top_n, lam):
    K = V.shape[0]

    selected = []
    remaining = np.ones(K, dtype=bool)

    # 1st: relevance 最大
    first = int(np.argmax(rel))
    selected.append(first)
    remaining[first] = False

    while len(selected) < top_n and remaining.any():
        sims = V @ V[selected].T          # (K, |S|)
        max_sim = sims.max(axis=1)        # 各候補の「被り度」
        mmr = lam * rel - (1 - lam) * max_sim
        mmr[~remaining] = -np.inf

        best = int(np.argmax(mmr))
        selected.append(best)
        remaining[best] = False

    return selected
```

---

## 10. Observability

- recommendation に algorithm / params（λ, K, N）を保存
- recommendation_item に vector_score / rerank_score / score を保存

---

## 11. Summary

- MMR は逐次選択による多様性制御アルゴリズム
- 実装では **内積（@）による一括類似度計算**を推奨
- λ により多様性の強弱を安全に制御する
