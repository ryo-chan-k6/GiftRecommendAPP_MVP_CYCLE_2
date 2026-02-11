# 共通処理仕様書（Common Processing Spec）

## 0. 目的と適用範囲

### 目的

楽天API → 正規化 → hash差分判定 → S3 raw immutable保存 → apl.staging（最新台帳）更新 → apl反映  
という再実行・差分耐性の高い共通ETL骨格を、ジョブ横断で再利用できる形で仕様化する。

### 適用範囲（対象ジョブ）

- JOB-R-01 Ranking ETL
- JOB-I-01 Item ETL
- JOB-G-01 Genre ETL
- JOB-T-01 Tag ETL
- JOB-A-01 is_active 更新（※S3/stagingを使わないが共通SQLとして規定）
- JOB-E-01 / JOB-E-02（※ETL骨格は使わず専用フローで実装）

## 1. 共通アーキテクチャ（論理）

- handler（jobs/）：引数解釈、context生成、service起動、exit code
- etl_service（services/etl_service.py）：ETL共通フロー制御（1件処理の骨格）
- policy.py：  
  当日更新分の定義と、stagingを起点とした  
  「ETL処理対象集合（source_id群）」の確定ロジックを集約
- rakuten_client（clients/）：楽天API呼び出し（リトライ詳細はC-3で確定）
- hasher/normalize（core/）：正規化→hash生成（差分耐性の中核）
- raw_store（core/）：S3 put + key生成（案A固定）
- staging_repo（repos/）：apl.staging 専用I/F
- apl_*_repo（repos/apl/）：apl反映（ジョブ責務を守るためrepo分割）

## 2. 共通データフロー（1件処理の骨格）
※ apl.staging は「最新raw参照台帳」であり、履歴は持たない。  
  履歴の正は S3 raw にあり、staging は常に最新1件のみを指す。  

対象（entityごとに共通）：

1. fetch（外部API）
2. normalize
3. hash
4. stagingにhash存在チェック
5. 差分ありのみS3 put
6. staging upsert（最新台帳）
7. apl反映（upsert / insert）

※ JOB-A-01は「6〜7」の代わりに is_active 一括UPDATEを行う。

### 2.1 staging反映管理（applied_at / applied_version）

apl.staging は content_hash の差分判定だけでなく、apl反映の実行状態を管理する。

- applied_at: 最後に apl 反映（applier）を完了した時刻
- applied_version: apl反映ロジックのバージョン番号

**運用ルール**

- 各ジョブは `*_APPLY_VERSION` を定数で持ち、`apply_version` としてETLに渡す
- `*_APPLY_VERSION` は「**apl反映（applier）を再実行すべきか**」を判定するための制御値
- **applier の出力に影響する変更**（正規化・applier処理・参照テーブル変更）時は version をインクリメント
- **ログ追加など出力に影響しない変更**では version を上げない
- content_hash が更新された場合、applied_at / applied_version はリセットして再反映対象とする

**判定方法（実行時の条件）**

- 最新の staging 行（source, entity, source_id の最新）を取得
- `content_hash` が一致しない場合は通常フロー（S3 put → staging upsert → applier）
- `content_hash` が一致する場合は以下で分岐
  - `applied_version == *_APPLY_VERSION`：apl反映済みのため **スキップ**
  - `applied_version != *_APPLY_VERSION`：apl反映ロジック差分ありのため **再実行**

**想定更新方法（applied_* の更新タイミング）**

- applier が正常終了した時点で `applied_at = now()` を記録
- 併せて `applied_version = *_APPLY_VERSION` を記録
- `content_hash` が変わった場合は staging upsert 時に `applied_*` を **null にリセット**

**applied_version のインクリメント運用（いつ・どの処理で行うか）**

- インクリメントは **自動ではなく手動**で行う
- 実施箇所は各ジョブの定数 `*_APPLY_VERSION`（例: `TAG_APPLY_VERSION`）を更新
- 「applierの出力に影響する変更」をリリースするタイミングで +1 する
  - 例: 正規化ルール変更 / applierのupsert項目変更 / 参照テーブル変更
- 変更後のジョブ実行時に `applied_version != *_APPLY_VERSION` が検知され、再反映が走る

## 3. 実行コンテキスト（services/context.py）

### 3.1 Contextの責務

- ジョブ実行の一意な実行単位を表現する（ログ・冪等性・当日更新分抽出に使う）
- 当日更新分の定義境界（:job_start_at）を提供する

### 3.2 データ構造（Python）

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

Env = Literal["dev", "prod"]
Entity = Literal["ranking", "item", "genre", "tag"]

@dataclass(frozen=True)
class JobContext:
    env: Env
    job_id: str                 # e.g., "JOB-I-01"
    run_id: str                 # UUID等（handler生成）
    job_start_at: datetime      # handler生成（当日更新分の基準）
    dry_run: bool = False
    limit: Optional[int] = None # 任意：対象件数上限
```

**仕様（重要）**

- job_start_at は handler 起動時に必ず確定し、policyに渡す
- 「当日更新分」は saved_at >= :day_start を基本とする
- :day_start は job_start_at の当日0:00（UTC）

## 4. 共通I/F（Pythonシグネチャ）

ここでは **「実装が迷わない最小限の固定」**を行う。  
（詳細な例外型・リトライ挙動はC-3で上書き）

### 4.1 clients/rakuten_client.py

```python
from typing import Any, Mapping

class RakutenClient:
    def fetch_ranking(self, *, genre_id: int) -> Mapping[str, Any]: ...
    def fetch_item(self, *, item_code: str) -> Mapping[str, Any]: ...
    def fetch_genre(self, *, genre_id: int) -> Mapping[str, Any]: ...
    def fetch_tag(self, *, tag_id: int) -> Mapping[str, Any]: ...
```

**仕様（MVP）**

- 返却は raw JSON（dict）
- タイムアウト・429対応などはC-3で確定し、client側に閉じる

### 4.2 core/normalize.py / core/hasher.py

```python
from typing import Any, Mapping
import hashlib
import json

def normalize(entity: str, raw: Mapping[str, Any]) -> Mapping[str, Any]:
    """
    entity別の正規化を行う。
    - キー順安定化
    - 意味を持たない順序のソート
    - hashに含めないメタ情報の除外
    """
    ...

def compute_content_hash(normalized: Mapping[str, Any]) -> str:
    """
    正規化済みJSONを安定な文字列に変換してSHA256等でhash化する。
    """
    stable = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()
```

**仕様（重要）**

- hashは normalized にのみ依存する
- “揺れる値”をhash対象に入れない（取得時刻等）

### 4.2.1 正規化ルール一覧（MVP固定）

**共通ルール**
- JSONキーは辞書順に安定化（sort_keys=true）
- 文字列は前後trim
- 空文字は null に正規化（対象カラムはentity別に明記）
- ETLが付与するメタ情報は除外（例：fetched_at / requested_at / request_id / response_headers / http_status / api_version など）

**entity別ルール**

| entity | 除外キー | 配列ソート対象（順序が意味を持たないもののみ） | 順序保持対象 |
| --- | --- | --- | --- |
| item | `fetched_at`, `requested_at`, `request_id`, `response_headers`, `http_status`, `api_version` | `smallImageUrls`, `mediumImageUrls`, `tagIds` | - |
| ranking | 同上 | なし | ランキングの順位順（APIレスポンス順）を保持 |
| genre | 同上 | なし | - |
| tag | 同上 | なし | - |

※ 配列ソート対象は **順序が意味を持たないもののみ**。意味がある配列は順序維持。  
※ entity別の除外キーは将来拡張可だが、MVPは上表に固定。

### 4.3 core/raw_store.py（S3保存＋key生成）

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Optional

@dataclass(frozen=True)
class RawPutResult:
    s3_key: str
    etag: Optional[str]
    saved_at: datetime

class RawStore:
    def build_key(self, *, source: str, entity: str, source_id: str, content_hash: str) -> str:
        # 案A固定
        # raw/source=rakuten/entity=item/source_id=<itemCode>/hash=<hash>.json
        ...

    def put_json(self, *, bucket: str, s3_key: str, body: Mapping[str, Any]) -> RawPutResult:
        ...
```

**仕様**

- bucketは env により分離（giftrecommend-raw-dev / giftrecommend-raw-prod）
- immutable（削除しない）
- put対象は原則 normalized（MVP確定）

### 4.4 repos/staging_repo.py（共通SQLのI/F）

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Sequence

@dataclass(frozen=True)
class StagingRow:
    source: str
    entity: str
    source_id: str
    content_hash: str
    s3_key: str
    etag: Optional[str]
    saved_at: datetime

class StagingRepo:
    def exists_hash(self, *, source: str, entity: str, source_id: str, content_hash: str) -> bool:
        """(source, entity, source_id) の最新hashが content_hash と一致するか判定する。"""
        ...

    def batch_upsert(self, *, rows: Sequence[StagingRow]) -> int:
        """apl.staging を (source, entity, source_id) でupsertし、件数を返す。"""
        ...
```

**仕様（重要）**

- “hash差分判定” は staging_repo.exists_hash が正となる
- batch_upsertは差分ありでS3 put成功した行のみを対象とする（MVP方針）

### 4.5 repos/apl（apl反映I/F：ジョブ別に使用）

**item_repo.py（JOB-I-01）**

```python
from typing import Any, Mapping, Sequence

class ItemRepo:
    def upsert_item(self, *, normalized_item: Mapping[str, Any]) -> str: ...
    def sync_item_images(self, *, item_id: str, normalized_item: Mapping[str, Any]) -> int: ...
    def insert_market_snapshot(self, *, item_id: str, collected_at, normalized_item: Mapping[str, Any]) -> int: ...
    def insert_review_snapshot(self, *, item_id: str, collected_at, normalized_item: Mapping[str, Any]) -> int: ...
    def upsert_shop(self, *, normalized_item: Mapping[str, Any]) -> str: ...
```

**item_tag_repo.py（JOB-I-01専管）**

```python
from typing import Sequence

class ItemTagRepo:
    def sync_item_tags(self, *, item_id: str, rakuten_tag_ids: Sequence[int]) -> int:
        """item単位でタグ集合に同期（推奨）。方式はC-3と整合しつつ実装で固定。"""
        ...
```

**rank_repo.py（JOB-R-01）**

```python
from typing import Mapping, Sequence

class RankRepo:
    def insert_rank_snapshot(self, *, run_id: str, genre_id: int, ranking_items: Sequence[Mapping[str, Any]]) -> int:
        ...
```

**genre_repo.py（JOB-G-01）**

```python
from typing import Mapping

class GenreRepo:
    def upsert_genre(self, *, normalized_genre: Mapping[str, Any]) -> int: ...
```

**tag_repo.py（JOB-T-01）**

```python
from typing import Mapping

class TagRepo:
    def upsert_tag_group(self, *, normalized_tag: Mapping[str, Any]) -> int: ...
    def upsert_tag(self, *, normalized_tag: Mapping[str, Any]) -> int: ...
```

### 4.6 services/etl_service.py（共通フローI/F）

ジョブ差分を吸収するため、policy と fetcher と applier を注入する設計にする。

```python
from typing import Iterable, Mapping, Any, Protocol

Target = str  # source_id（例: itemCode / tagId / genreId / ranking.genreId）

class Fetcher(Protocol):
    def __call__(self, target: Target) -> Mapping[str, Any]: ...

class Applier(Protocol):
    def __call__(self, normalized: Mapping[str, Any], ctx: JobContext, target: Target) -> None: ...

class TargetProvider(Protocol):
    def __call__(self, ctx: JobContext) -> Iterable[Target]: ...

class EtlService:
    def run_entity_etl(
        self,
        *,
        ctx: JobContext,
        source: str,
        entity: str,
        target_provider: TargetProvider,
        fetcher: Fetcher,
        applier: Applier,
    ) -> dict:
        """
        共通ETLフローを実行する。
        戻り値は以下を含むサマリとする：
        - total_targets
        - success_count
        - failure_count
        - failure_rate
        """
        ...
```

**共通フロー仕様（run_entity_etlの内部規約）**

- targetごとに：
  - fetch → normalize(entity, raw) → hash
  - staging.exists_hash() で差分判定
- 差分あり：
  - raw_store.build_key() → raw_store.put_json()
  - staging.batch_upsert()（1件でも良いがMVPはbatch推奨）
  - applier() 実行
- 差分なし：
  - S3 putしない
  - applierは呼ばない（MVP方針：無駄DB更新回避）  
    （理由：aplは最新状態を保持しており、同一内容での再upsertは無駄更新・updated_at汚染になるため）
- dry_run：
  - S3 put / DB更新（staging/apl）を行わない（ログのみ）

## 5. policy（services/policy.py）— 当日更新分の定義

### 5.1 方針

「当日処理対象」はジョブごとに異なるが、共通して

- apl.staging(entity=item) を当日更新分集合の定義に使う
- 属性（genreId/tagIdなど）は staging単体では持たないため、aplテーブルとJOINする
- job_start_at は UTC の timestamptz（秒精度）として扱う
- staging抽出は s.saved_at >= day_start を基準とする（tzはUTCで統一）

**性能前提（index）**

- apl.staging: (source, entity, saved_at)
- apl.item: (rakuten_item_code)
- apl.item_tag: (item_id, rakuten_tag_id)

### 5.2 I/F例

```python
from typing import Iterable

def targets_ranking_genre_ids(ctx: JobContext) -> Iterable[str]: ...
def targets_item_codes(ctx: JobContext) -> Iterable[str]: ...

def targets_genre_ids_from_today_items(ctx: JobContext) -> Iterable[str]:
    """staging(item)の当日分 → item → genreId"""
    ...

def targets_tag_ids_from_today_items(ctx: JobContext) -> Iterable[str]:
    """staging(item)の当日分 → item → item_tag → tagId"""
    ...
```

## 6. 共通SQL仕様（4本）

以降のSQLは `apps/batch/etl/sql/common/` に配置する。

### 6.1 staging hash存在チェック

**staging_select_not_exists_hash.sql**（※exists判定に利用）

**目的**  
(source, entity, source_id) の現在の content_hash が一致するか判定

**推奨SQL（exists判定）**

```sql
-- returns 1 row if matches; 0 rows otherwise
select 1
from apl.staging s
where s.source = :source
  and s.entity = :entity
  and s.source_id = :source_id
  and s.content_hash = :content_hash
limit 1;
```

**仕様**

- 一致すれば “差分なし”
- 一致しなければ “差分あり”（S3 put + staging upsert + apl反映）

### 6.2 staging batch upsert

**staging_batch_upsert.sql**

**目的**  
最新台帳を (source, entity, source_id) で upsert

**推奨SQL**

```sql
insert into apl.staging (
  source, entity, source_id,
  content_hash, s3_key, etag, saved_at,
  created_at, updated_at
)
values (
  :source, :entity, :source_id,
  :content_hash, :s3_key, :etag, :saved_at,
  now(), now()
)
on conflict (source, entity, source_id)
do update set
  content_hash = excluded.content_hash,
  s3_key       = excluded.s3_key,
  etag         = excluded.etag,
  saved_at     = excluded.saved_at,
  updated_at   = now();
```

**仕様（重要）**

- 呼び出しは「差分ありでS3 put成功した」行のみ
- saved_at は RawStore の戻り値を採用（S3保存時刻と一致させる）

### 6.3 is_active 一括更新

**item_is_active_update.sql**（JOB-A-01で使用）

**目的**  
apl.item の is_active を EXISTS判定で確定し、無駄更新を避ける

**推奨SQL（重複計算を避ける版）**

```sql
with computed as (
  select
    i.id,
    (
      exists (select 1 from apl.genre g where g.rakuten_genre_id = i.rakuten_genre_id)
      and
      exists (select 1 from apl.shop s where s.rakuten_shop_code = i.rakuten_shop_code)
    ) as next_is_active
  from apl.item i
)
update apl.item i
set
  is_active  = c.next_is_active,
  updated_at = now()
from computed c
where i.id = c.id
  and i.is_active is distinct from c.next_is_active;
```

**仕様**

- tagは条件に含めない（MVP）
- updated_at は変更行のみ更新

### 6.4 Embedding差分抽出

**embedding_source_diff_select.sql**（JOB-E-02で使用）

**目的**  
`apl.item_embedding_source` と `apl.item_embedding` を比較し、差分対象を抽出する

## 7. エラー / リトライ / 冪等性（MVP方針）

### 7.1 冪等性の中心

- 差分判定の真実：apl.staging.content_hash
- rawは immutable（hash keyで履歴蓄積）
- apl反映は upsert/insert を設計に従い行う

### 7.2 エラー時の最低限方針（詳細はC-3）

- API失敗：対象単位（itemCode等）で失敗を記録し、ジョブ全体は「失敗扱い」にできる
- MVP推奨：一定割合以上失敗でexit!=0（運用で決める）
- S3 put失敗：その対象は staging/apl を更新しない（原子性の擬似担保）
- DB失敗：ジョブ失敗（exit!=0）、再実行前提

## 8. 受け入れ条件（C-2 Done）

- すべてのジョブが etl_service.run_entity_etl() の骨格で実装できる
- staging差分判定・S3 key設計・staging upsert が共通で動く
- is_active SQLが「無駄更新なし」で動く
- policyで「当日更新分のみ」が抽出できる（JOB-G/JOB-TのJOIN含む）

