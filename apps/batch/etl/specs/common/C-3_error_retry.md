# エラーハンドリング・リトライ仕様（MVP）

## 0. 目的

- 外部API（楽天）・S3・DBの失敗を想定し、ETLの信頼性と再実行耐性を確保する
- 「部分成功」や「途中失敗」が起きても、次回再実行で回復できるようにする
- MVPでは複雑な分散制御を避け、単純かつ安全側に倒す

## 1. 例外分類（Error Taxonomy）

| 区分 | 例 | 代表原因 | リトライ | 失敗扱い | 備考 |
| --- | --- | --- | --- | --- | --- |
| Rakuten: Rate Limit | HTTP 429 | 超過 | ✅ | 条件付き | バックオフ必須 |
| Rakuten: Transient | HTTP 5xx / timeout / connection reset | 一時障害 | ✅ | 条件付き | リトライで回復見込み |
| Rakuten: Client Error | HTTP 400/401/403/404 | パラメータ/認証/権限 | ❌ | ✅ | 設計/設定ミス |
| S3: Transient | 5xx, timeout | 一時障害 | ✅ | ✅ | 保存できなければ進めない |
| S3: Auth/Perm | 403 | 権限 | ❌ | ✅ | 設定ミス |
| DB: Transient | deadlock, serialization, timeout | 競合/一時 | ✅ | ✅ | リトライ有効 |
| DB: Logic | constraint violation 等 | データ不整合 | ❌ | ✅ | バグ/前提崩れ |

## 2. リトライ共通ポリシー（MVP）

### 2.1 回数・待機（推奨値）

- 最大試行回数：`max_attempts = 5`
- バックオフ：指数バックオフ（ジッターあり）
- base: 1s
- 例：1s → 2s → 4s → 8s → 16s（±ランダム）

### 2.2 リトライ対象

- ✅ 429 / 5xx / timeout / 一時的ネットワーク
- ✅ DB deadlock / serialization failure / timeout
- ❌ 400/401/403/404（即fail）
- ❌ constraint violation（即fail）

### 2.3 「対象単位リトライ」と「ジョブ全体リトライ」

- リトライは基本「対象単位（itemCode/tagId等）」で行う（スコープを小さくする）
- それでも失敗した対象は失敗対象として記録し、ジョブ全体の結果判定に使う

## 3. Rakuten API（clients/rakuten_client.py）の扱い

### 3.1 仕様

- RakutenClientは「例外を握りつぶさず、分類して投げる」
- 429はリトライ（必要ならレスポンスヘッダに従うが、MVPは指数バックオフでOK）
- 401/403は即fail（Secrets/設定ミス）

### 3.2 失敗時のジョブ全体判定（MVP）

- 成功率が一定未満ならジョブ失敗扱い（exit != 0）

**推奨しきい値**

- failure_rate > 1% で失敗扱い（Ranking/Genre/Tag）
- failure_rate > 5% で失敗扱い（Item）

## 4. S3 Raw 保存（core/raw_store.py）の扱い

### 4.1 重要原則（事実）

- S3 put に成功しない限り staging/apl を更新してはいけない
- staging が “最新参照台帳” であり、S3を指せない状態は破綻

### 4.2 リトライ

- S3 5xx/timeout はリトライ（max_attempts=5）
- 403は即fail（権限）

### 4.3 失敗した場合の挙動（MVP）

- 対象単位で失敗として記録
- ジョブ全体判定の「失敗率」に加算
- DB側は更新しないので、再実行で回復可能

## 5. DB（repos/*）の扱い

### 5.1 staging更新（staging_repo.batch_upsert）

- DB transient（deadlock等）はリトライ
- それでも失敗したらジョブ失敗（exit != 0）

### 5.2 apl反映（apl_*_repo）

- upsert/insert は原則リトライ可能
- ただし「同期操作」（item_tagやimagesの同期で delete を伴う）を行う場合：
  - トランザクション必須
  - 失敗時はロールバックで整合性を守る

### 5.3 トランザクション境界（MVP推奨）

- 「対象1件（itemCode等）」を1トランザクションにする
- staging upsert と apl反映は同一トランザクションに入れてよい
- ただし S3 put はトランザクション外（外部I/O）

**推奨順序（1対象）**

1. API取得 → normalize → hash
2. staging.exists_hash で差分判定
3. 差分ありなら S3 put
4. DBトランザクション開始
5. staging upsert
6. apl upsert/sync
7. commit

## 6. 部分成功と冪等性（実運用で壊れないための規約）

### 6.1 “対象単位の原子性”

- 対象単位（itemCode等）で成功/失敗を分ける
- ある対象が失敗しても、他対象は処理継続可

### 6.2 二重実行（多重起動）時の考え方（MVP）

- staging unique (source, entity, source_id) により最新が勝つ
- rawは hash key なので同一hashのputは理論上冪等（ただし課金/ETag差はあり得る）
- GHA側で同一ワークフローの同時実行を抑止する（C-4で確定）

## 7. ログ仕様（最低限：原因追跡可能にする）

### 7.1 ログに必ず含めるキー

- job_id, run_id, env, job_start_at
- entity, source_id（target）
- attempt, max_attempts
- error_category（上表の分類）
- http_status（APIの場合）
- exception_name, message（短く）

### 7.2 サマリログ（ジョブ終了時）

- total_targets, success_targets, failed_targets
- diff_new_hash
- s3_put_success / fail
- db_upsert_success / fail
- failure_rate
- exit_code（0/1）

## 8. エラー別の具体対応表（実装直結）

| 失敗ポイント | エラー | 対応 | 次回再実行で回復？ |
| --- | --- | --- | --- |
| Rakuten API | 429 | バックオフしてリトライ、上限で失敗記録 | ✅ |
| Rakuten API | 5xx/timeout | リトライ、上限で失敗記録 | ✅ |
| Rakuten API | 401/403 | 即ジョブ失敗（設定修正が必要） | ❌（設定次第） |
| S3 put | timeout/5xx | リトライ、上限でジョブ失敗寄り | ✅ |
| S3 put | 403 | 即ジョブ失敗 | ❌ |
| DB | deadlock/timeout | トランザクション単位でリトライ | ✅ |
| DB | unique/constraint | 即ジョブ失敗（設計/同期バグ） | ❌（修正必要） |

## 9. 受け入れ条件（C-3 Done）

- 429/5xx/timeout でリトライされる
- 401/403/400/404 は即failで原因がログから分かる
- S3 put 失敗時に staging/apl を更新しない
- 対象単位で成功/失敗が分離され、再実行で回復する
- ジョブ終了時にサマリが出る

