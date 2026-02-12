# CI ワークフロー仕様

## 1. 概要

統一CI（`ci.yaml`）は、batch / web / api / reco の単体テスト・検証を1ワークフローで並列実行し、全ジョブ成功後に PR を自動作成する。

---

## 2. ワークフロー

| ファイル | 用途 |
|----------|------|
| `.github/workflows/ci.yaml` | 統一CI（単体テスト・検証・PR作成） |
| `.github/workflows/batch-etl.yml` | バッチETL実行（手動） |

---

## 3. トリガー

- `push`（main 以外）
- `pull_request`（opened, synchronize, reopened）

---

## 4. ジョブ一覧

| ジョブ名 | 対象 | 実行内容 |
|----------|------|----------|
| batch-unit | apps/batch | `pytest -m "unit"` |
| web-check | apps/web | pnpm lint + build |
| api-check | apps/api | `tsc --noEmit`（型チェック） |
| reco-check | apps/reco | アプリ読み込み検証 |
| create-pr | - | 全ジョブ成功後、PR が存在しなければ作成 |

---

## 5. 実行順序

- batch-unit / web-check / api-check / reco-check は **並列実行**
- create-pr は上記4ジョブの **成功後に実行**

---

## 6. 必要環境

- Node.js 20
- pnpm 10
- Python 3.13.3

---

## 7. 参照

- [README：CI / ワークフロー](../../../README.md)
- [リポジトリ戦略](../../repo_strategy_giftrecommend_mvp.md)
- [C-4 GitHub Actions](../../../apps/batch/etl/specs/common/C-4_github_actions.md)
