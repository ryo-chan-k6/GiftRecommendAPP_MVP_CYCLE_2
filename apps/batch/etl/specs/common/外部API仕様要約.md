# 外部API仕様要約（楽天API差分）

## 0. 対象API（MVP ETLで利用）

| ETLジョブ | 利用API | 目的 |
| --- | --- | --- |
| JOB-R-01 Ranking ETL | Ichiba Item Ranking API | ランキング itemCode を取得し snapshot 更新 |
| JOB-I-01 Item ETL | Ichiba Item Search API | itemCode → 商品詳細を取得し item / item_tag を更新 |
| JOB-G-01 Genre ETL | Ichiba Genre Search API | genreId → ジャンル階層情報を取得し genre を更新 |
| JOB-T-01 Tag ETL | Ichiba Tag Search API | tagId → タグ階層情報を取得し tag_group / tag を更新 |

## 1. 共通仕様（全APIで共通）

### 1.1 HTTP / Endpoint

- いずれも HTTP GET
- エンドポイントは APIごとに `/services/api/<API名>/<Operation>/<version>` 形式  
  例：ItemSearch は `.../IchibaItem/Search/20220601`

### 1.2 共通入力パラメータ（Shared parameters）

各APIページに共通として掲載されているもの：

- applicationId（必須）
- affiliateId（任意）
- format（json / xml）
- callback（JSONP用）
- elements（出力フィールド絞り込み）
- formatVersion（JSONの配列構造が変わる：v1/v2）

**MVP実装推奨**

- format=json 固定
- formatVersion=2 固定（配列アクセスが素直になる）
- elements は「raw保存はフル、DB反映は必要項目だけ参照」の方針のため `未指定（全量）`

## 2. API別仕様

### 2.1 Ichiba Item Ranking API（JOB-R-01）

**Endpoint**

`https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601?...`

**主なリクエストパラメータ（service specific）**

| param | 型 | 用途 / 制約 |
| --- | --- | --- |
| genreId | long | ジャンル指定ランキング。age/sex と併用不可 |
| age | int | 10/20/30/40/50…（年代） |
| sex | int | 0=male, 1=female。ageと併用可、genreIdと併用不可 |
| page | int | 1〜34（ランキング下位も取得可） |
| period | string | realtime 等 |

**レスポンス形式（重要フィールド）**

| 分類 | フィールド例 |
| --- | --- |
| 全体 | title, lastBuildDate |
| items配列（各rank） | rank, itemCode, itemName, itemPrice, itemUrl, affiliateUrl, smallImageUrls, mediumImageUrls, availability など |

※ formatVersion=2 の配列名は `items`（小文字）。`Items` ではない点に注意。

#### JSONレスポンスサンプル（formatVersion=2の構造例）

```json
{
  "title": "楽天市場ランキング",
  "lastBuildDate": "2026-01-27T04:00:00+09:00",
  "items": [
    {
      "rank": 1,
      "itemName": "サンプル商品A",
      "catchcopy": "キャッチコピー",
      "itemCode": "shop:123456",
      "itemPrice": 2980,
      "itemUrl": "https://item.rakuten.co.jp/shop/123456/",
      "affiliateUrl": "https://hb.afl.rakuten.co.jp/...",
      "imageFlag": 1,
      "smallImageUrls": ["https://thumbnail.image.rakuten.co.jp/.../64x64.jpg"],
      "mediumImageUrls": ["https://thumbnail.image.rakuten.co.jp/.../128x128.jpg"],
      "availability": 1,
      "taxFlag": 0,
      "postageFlag": 0,
      "creditCardFlag": 1,
      "shopName": "サンプルショップ",
      "shopCode": "shop",
      "shopUrl": "https://www.rakuten.co.jp/shop/",
      "genreId": 100283
    }
  ]
}
```


### 2.2 Ichiba Item Search API（JOB-I-01）

**Endpoint**

`https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601?...`

**リクエストパラメータ（service specific：主要）**

「keyword / genreId / itemCode / shopCode のいずれか必須」

| param | 型 | MVPでの使い方 |
| --- | --- | --- |
| itemCode | String | JOB-I-01の主入力（ランキング itemCode を詳細化） |
| hits | int | 1〜30（itemCode指定なら通常 1） |
| page | int | 1〜100（itemCode指定なら 1） |
| sort | String | 取得順（MVPは不要） |
| tagId | long | tag指定検索（将来拡張） |
| asurakuFlag | int | 2024/7/1以降は常に0扱い（注意） |

**レスポンス形式（構造）**

- ページング系：count, page, first, last, hits, pageCount
- items配列に item 詳細（非常に多い）
- formatVersion=2 の配列名は `items`（小文字）

#### JSONレスポンスサンプル（formatVersion=2の構造例）

```json
{
  "count": 1,
  "page": 1,
  "first": 1,
  "last": 1,
  "hits": 1,
  "carrier": 0,
  "pageCount": 1,
  "items": [
    {
      "itemName": "サンプル商品A",
      "catchcopy": "キャッチコピー",
      "itemCode": "shop:123456",
      "itemPrice": 2980,
      "itemCaption": "商品説明（長文）",
      "itemUrl": "https://item.rakuten.co.jp/shop/123456/",
      "affiliateUrl": "https://hb.afl.rakuten.co.jp/...",
      "imageFlag": 1,
      "smallImageUrls": ["https://thumbnail.image.rakuten.co.jp/.../64x64.jpg"],
      "mediumImageUrls": ["https://thumbnail.image.rakuten.co.jp/.../128x128.jpg"],
      "availability": 1,
      "taxFlag": 0,
      "postageFlag": 0,
      "creditCardFlag": 1,
      "shopName": "サンプルショップ",
      "shopCode": "shop",
      "shopUrl": "https://www.rakuten.co.jp/shop/",
      "genreId": 100283,
      "reviewCount": 10,
      "reviewAverage": 4.4,
      "pointRate": 1
    }
  ]
}
```

> 注: Item Search API の出力パラメータは非常に多いため、上記はETLで参照しやすい代表項目のみを載せています（raw保存は全量・DB反映は必要項目だけ参照の方針）。


※あなたのETL設計（itemName/catchcopy/price/url/imageUrls/review/pointRate/giftFlag…）に相当する項目が返る前提で、rawをフル保存→DB反映は必要項目だけ抽出が堅い

### 2.3 Ichiba Genre Search API（JOB-G-01）

**Endpoint**

`https://app.rakuten.co.jp/services/api/IchibaGenre/Search/20170711?...`

**リクエストパラメータ（service specific）**

| param | 型 | 用途 |
| --- | --- | --- |
| genreId | int | 必須。0でルートから |

**レスポンス形式（重要フィールド）**

| 分類 | フィールド例 |
| --- | --- |
| 現在genre | current.genreId, current.genreName, current.genreLevel |
| 親/祖先 | parents（親～祖先の配列） |
| 兄弟 | brothers |
| 子 | children（genreId=0 のとき level=1 が返る等） |
| フラグ | lowestFlg, chopperFlg, linkGenreId |

#### JSONレスポンスサンプル（構造例）

```json
{
  "parents": [
    {
      "genreId": 0,
      "genreName": "楽天市場",
      "genreLevel": 0,
      "englishName": "Rakuten Ichiba",
      "linkGenreId": null,
      "chopperFlg": 0,
      "lowestFlg": 0
    }
  ],
  "current": {
    "genreId": 100283,
    "genreName": "洋菓子",
    "genreLevel": 2,
    "englishName": "Western Sweets",
    "linkGenreId": null,
    "chopperFlg": 0,
    "lowestFlg": 0
  },
  "brothers": [
    {
      "genreId": 100284,
      "genreName": "和菓子",
      "genreLevel": 2,
      "englishName": "Japanese Sweets",
      "linkGenreId": null,
      "chopperFlg": 0,
      "lowestFlg": 0
    }
  ],
  "children": [
    {
      "genreId": 100301,
      "genreName": "チョコレート",
      "genreLevel": 3,
      "englishName": "Chocolate",
      "linkGenreId": null,
      "chopperFlg": 0,
      "lowestFlg": 1
    }
  ]
}
```


※Genre Search の出力パラメータ表に Tag情報の項目が混ざって見える箇所がありますが、MVPでは genre系のみ採用でOK（Tagは Tag Search / ItemSearch 由来で処理）

### 2.4 Ichiba Tag Search API（JOB-T-01）

**Endpoint**

`https://app.rakuten.co.jp/services/api/IchibaTag/Search/20140222?...`

**リクエストパラメータ（service specific）**

| param | 型 | 用途 |
| --- | --- | --- |
| tagId | int | 必須。0は不可。最大10件をカンマ区切り指定可 |

**レスポンス形式（重要フィールド）**

| 分類 | フィールド例 |
| --- | --- |
| tagGroup | tagGroupName, tagGroupId |
| tags | tags[].tagId, tags[].tagName, tags[].parentTagId |

#### JSONレスポンスサンプル（構造例）

```json
{
  "tagGroup": {
    "tagGroupName": "スイーツ",
    "tagGroupId": 1000,
    "tags": [
      { "tagId": 1000317, "tagName": "チョコレート", "parentTagId": 0 },
      { "tagId": 1000318, "tagName": "クッキー", "parentTagId": 0 }
    ]
  }
}
```


## 3. エラーパターン（共通＋API固有）

### 3.1 共通（多くのAPIで同型）

レスポンスボディは概ね以下の形：

```json
{ "error": "<code>", "error_description": "<message>" }
```

**代表例**

- 400: wrong_parameter（必須不足/不正値）
- 404: not_found
- 429: too_many_requests
- 500: system_error
- 503: service_unavailable

### 3.2 Ranking API 固有の “組み合わせ制約” エラー例

- period を指定するなら age は 20/30/40…に制限、など
- genreId と sex/age の併用不可エラー

## 4. ETL実装に直結する差分・注意点（MVP向け）

### 4.1 formatVersion

- formatVersion=2 で固定（items配列アクセスが素直）

### 4.2 ItemSearch の asurakuFlag

ドキュメント上、「2024/7/1以降 asurakuFlag は常に 0」と明記あり  
→ フィルタとして使わない前提にする

### 4.3 レート制限（429）

バッチETLは 429を“仕様”として扱う（指数バックオフ＋上限回数で失敗判定、failure_rate>1% でfail 等、あなたのC-3方針に寄せる）

