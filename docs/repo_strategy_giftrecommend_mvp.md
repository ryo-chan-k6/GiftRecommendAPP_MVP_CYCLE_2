# GiftRecommend MVP リポジトリ戦略（モノレポ前提）

作成日: 2026-01-24  
対象: GiftRecommend MVP（`web / api / reco / batch`）

---

## 0. 前提整理（事実）

- 4コンポーネント
  - `web`：フロント（サーバ独立）
  - `api`：バックエンド（サーバ独立）
  - `reco`：外部API連携/推論系（サーバ独立）
  - `batch`：Python（GitHub Actions の Runner 上で起動→処理→終了）
- 現状は **単一リポジトリ** で管理している（モノレポ）。
- 現状の課題
  - `main` 直コミット運用で、未完の変更が混ざりやすい
  - batch を頻繁に Actions で試したいが、`api` 側が途中でもコミットが必要になり、コミット粒度が崩れる

---

## 1. 結論（推奨方針）

### 1.1 モノレポ継続 + 「ブランチ運用」と「Actions トリガ分離」で解消する
- **リポジトリ分割は不要**（MVP・一人開発・変更が跨りやすい段階では運用コスト増が勝ちやすい）
- 代わりに以下を採用する
  1) `main` は常に動く状態（デプロイ可能）  
  2) 作業は feature ブランチで行い、PR 経由で `main` に取り込む  
  3) Actions を「定期実行（main専用）」と「検証実行（任意ブランチ）」に分ける  
  4) `paths` フィルタで、変更があったコンポーネントのCIだけ動かす  

---

## 2. ディレクトリ構成（推奨）

例（現状の `apps/batch` は踏襲）:

```
apps/
  web/
  api/
  reco/
  batch/
packages/
  shared/          # 型・共通ユーティリティ（必要になったら）
  sdk/             # OpenAPI から生成するクライアント（必要になったら）
.github/
  workflows/
```

**狙い**  
- 変更影響範囲をディレクトリで区切り、CI を `paths` で選別できるようにする。

---

## 3. ブランチ戦略（運用ルール）

### 3.1 ブランチ種別
- `main`：常にデプロイ可能（安定）
- `feature/<topic>`：新機能/改修（例: `feature/batch-retry-policy`）
- `fix/<topic>`：不具合修正
- `chore/<topic>`：依存更新・リファクタ

### 3.2 PR ルール（1人でも PR 運用する）
- `main` への取り込みは **PR 経由**
- マージ方式は原則 **Squash merge**
  - feature ブランチ上のコミットは「途中」でも良い
  - `main` は PR 単位で綺麗な履歴になる

### 3.3 コミット粒度の考え方
- **feature ブランチ**：作業ログ（小さくOK）
- **main**：まとまり単位（PR単位で担保）
- 「xx機能実装完了 / 単体テスト完了 / 結合テスト完了」をコミットで厳格にやるより、**PR の説明とチェックリスト**で担保する方が運用上強い。

---

## 4. GitHub Actions 戦略（重要）

### 4.1 目標
- `api` が途中でも、**batch だけを Actions 上で検証できる**
- 定期実行は `main` の安定版だけに限定する
- 変更があったコンポーネントのワークフローだけ動かす

---

## 5. 現状 workflow の読み解き（事実）

添付の `batch-daily.yml`（抜粋）:

- `on.schedule`：毎日 0:00 JST（15:00 UTC）実行
- `workflow_dispatch`：手動実行可能
- `apps/batch` で `pip install -r requirements.txt`
- secrets から `.env.local` を生成（DB/楽天/OpenAI）
- `python cli.py fetch:* / etl:* / build:*` を順に実行
- `continue-on-error` の方針あり（ranking/item は継続可、genre/tag などは停止）

**注意点（確認推奨）**  
YAML 先頭付近が ` on:` になっているように見えます（先頭にスペース）。  
実ファイルでも同様なら、GitHub Actions は `on` を認識できずトリガされない可能性があります。  
→ リポジトリ上の実ファイルで `on:` が行頭になっているか確認してください。

---

## 6. 推奨: batch のワークフローを「定期」と「検証」に分割

### 6.1 なぜ分割するか（推論）
- 定期実行は「本番相当の安定ジョブ」
- 検証は「feature ブランチでも回したい」
- これを同一 workflow にまとめると、運用ポリシーが曖昧になり、`main` に未完の変更を入れがちになる

### 6.2 分割案
- `batch-daily.yml`：**schedule（mainのみ） + workflow_dispatch**
- `batch-ci.yml`：**push/PR/dispatch（任意ブランチ）** で batch のみ検証

---

## 7. `paths` フィルタで「必要なCIだけ」動かす

### 7.1 各コンポーネントにCIを用意（例）
- `web-ci.yml`：`apps/web/**` が変わったら動く
- `api-ci.yml`：`apps/api/**` が変わったら動く
- `reco-ci.yml`：`apps/reco/**` が変わったら動く
- `batch-ci.yml`：`apps/batch/**` が変わったら動く

### 7.2 batch-ci.yml のイメージ（骨子）
- feature ブランチでも手動実行できる（`workflow_dispatch`）
- `push`/`pull_request` は batch 配下の変更時のみ

```yaml
name: Batch CI

on:
  workflow_dispatch:
    inputs:
      job:
        description: "Which batch job to run"
        required: true
        default: "fetch:ranking"
        type: choice
        options: ["fetch:ranking","fetch:item","fetch:genre","fetch:tag","etl:item","build:embedding"]
  push:
    paths:
      - "apps/batch/**"
      - ".github/workflows/batch-ci.yml"
  pull_request:
    paths:
      - "apps/batch/**"
      - ".github/workflows/batch-ci.yml"
```

**効果**  
- `api` 実装途中でも、batch だけ変更して batch-ci が回る  
- `main` に入れなくても feature ブランチで検証できる

---

## 8. 環境（dev/prod）分離ルール（推奨）

### 8.1 最小ルール
- feature ブランチで回す batch は **dev DB** を使う
- `main` の schedule は **prod DB** を使う（または stg → 問題なければ prod）

### 8.2 GitHub Environments を使う（推奨）
- `Environment: dev`：`DEV_DATABASE_URL` 等
- `Environment: prod`：`PROD_DATABASE_URL` 等（保護ルールをかけられる）

**運用例**
- `batch-ci.yml`：dev environment
- `batch-daily.yml`：prod environment（手動実行には承認を要求する、など）

---

## 9. ブランチ運用で「コミット粒度が崩れる」問題を解消する

### 9.1 いまの問題の置き換え
- これまで: 「Actions に反映させるため main にコミットせざるを得ない」
- これから: 「feature ブランチにコミット → 手動で batch-ci を実行 → 仕上がったら PR で main へ」

### 9.2 推奨運用フロー（例）
1. `feature/batch-x` を切る
2. `apps/batch` のみ変更してコミット（途中でもOK）
3. GitHub Actions → `Batch CI` を `workflow_dispatch` で実行（dev DB）
4. 期待通りになったら PR 作成
5. PR で batch-ci が緑になることを確認
6. squash merge で main へ（main に未完が混ざらない）

---

## 10. PR テンプレ（運用の型）

`PULL_REQUEST_TEMPLATE.md`（例）

- 目的
- 変更点
- 影響範囲（web/api/reco/batch）
- 動作確認
  - [ ] unit
  - [ ] integration
  - [ ] batch-ci (dev)
- ロールバック案

---

## 11. 付録: .github/workflows の整理指針

- `*-ci.yml`：変更検知（push/PR/dispatch）
- `*-deploy.yml`：デプロイ（main へのマージや tag）
- `batch-daily.yml`：定期ジョブ（schedule）

---

## 12. 次にやること（最小TODO）

1. `main` 直コミットを止め、feature ブランチ + PR 運用へ移行
2. batch を `batch-daily.yml` と `batch-ci.yml` に分割
3. `paths` フィルタを入れて、不要なCI実行を減らす
4. dev/prod の secrets（DB URL）を分ける（最低限）
5. PR テンプレを追加する

---

以上。
