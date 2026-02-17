#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import platform
import sys
from pathlib import Path

from dotenv import load_dotenv

# apps/batch/.env を読み込む（実行ディレクトリに依存しない）
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import psycopg2
import psycopg2.extras
import requests


# ==========
# Config
# ==========

@dataclass(frozen=True)
class Config:
    database_url: str
    rakuten_app_id: str
    api_base_url: str
    start_genre_id: int
    batch_size: int
    sleep_sec: float
    max_genres: Optional[int]
    lock_owner: str
    request_timeout_sec: int


DEFAULT_API_BASE_URL = "https://app.rakuten.co.jp/services/api/IchibaGenre/Search/20140222"


# ==========
# DB Helpers
# ==========

def get_conn(database_url: str):
    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    return conn


def seed_start_genre(conn, start_genre_id: int):
    """
    start_genre_id が state に無ければ PENDING で投入。
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into rakuten_genre_fetch_state (genre_id, status)
            values (%s, 'PENDING')
            on conflict (genre_id) do nothing
            """,
            (start_genre_id,),
        )
    conn.commit()


def claim_pending_genres(conn, lock_owner: str, batch_size: int) -> List[int]:
    """
    PENDING/ERROR を対象にバッチでロック取得し、IN_PROGRESS に更新して返す。
    並列起動しても重複取得しない（SKIP LOCKED）。
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            with target as (
              select genre_id
              from rakuten_genre_fetch_state
              where status in ('PENDING','ERROR')
              order by updated_at asc
              for update skip locked
              limit %s
            )
            update rakuten_genre_fetch_state s
            set status='IN_PROGRESS',
                locked_by=%s,
                locked_at=now(),
                updated_at=now()
            from target
            where s.genre_id = target.genre_id
            returning s.genre_id
            """,
            (batch_size, lock_owner),
        )
        rows = cur.fetchall()
    conn.commit()
    return [r[0] for r in rows]


def mark_done(conn, genre_id: int):
    with conn.cursor() as cur:
        cur.execute(
            """
            update rakuten_genre_fetch_state
            set status='DONE',
                last_error=null,
                updated_at=now()
            where genre_id=%s
            """,
            (genre_id,),
        )
    conn.commit()


def mark_error(conn, genre_id: int, err: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            update rakuten_genre_fetch_state
            set status='ERROR',
                try_count=try_count+1,
                last_error=%s,
                updated_at=now()
            where genre_id=%s
            """,
            (err[:2000], genre_id),
        )
    conn.commit()


def upsert_genre(conn, row: Dict[str, Any]):
    """
    最新1件のみ保持：genre_id PK で UPSERT。raw_json は必ず保存。
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            insert into rakuten_genre (
              genre_id, genre_name, genre_level, parent_genre_id,
              english_name, link_genre_id, chopper_flg, lowest_flg,
              raw_json, fetched_at, updated_at
            )
            values (
              %(genre_id)s, %(genre_name)s, %(genre_level)s, %(parent_genre_id)s,
              %(english_name)s, %(link_genre_id)s, %(chopper_flg)s, %(lowest_flg)s,
              %(raw_json)s::jsonb, now(), now()
            )
            on conflict (genre_id) do update set
              genre_name=excluded.genre_name,
              genre_level=excluded.genre_level,
              parent_genre_id=excluded.parent_genre_id,
              english_name=excluded.english_name,
              link_genre_id=excluded.link_genre_id,
              chopper_flg=excluded.chopper_flg,
              lowest_flg=excluded.lowest_flg,
              raw_json=excluded.raw_json,
              fetched_at=excluded.fetched_at,
              updated_at=now()
            """,
            row,
        )
    conn.commit()


def enqueue_candidates(conn, genre_ids: Iterable[int]):
    """
    未登録の genre_id だけ PENDING で投入（既存は何もしない）。
    """
    ids = list(dict.fromkeys(int(x) for x in genre_ids))  # unique + order preserving
    if not ids:
        return

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            insert into rakuten_genre_fetch_state (genre_id, status)
            values %s
            on conflict (genre_id) do nothing
            """,
            [(i, "PENDING") for i in ids],
            page_size=1000,
        )
    conn.commit()


# ==========
# API / Parsing
# ==========

def fetch_genre_from_api(cfg: Config, genre_id: int) -> Dict[str, Any]:
    params = {
        "applicationId": cfg.rakuten_app_id,
        "genreId": genre_id,
        "format": "json",
    }
    r = requests.get(cfg.api_base_url, params=params, timeout=cfg.request_timeout_sec)
    r.raise_for_status()
    return r.json()


def _unwrap_list_items(lst: Any) -> List[Dict[str, Any]]:
    """
    brothers/parents/children は [{"brother": {...}}, ...] のようなラッパー配列。
    ただし children のキー名は環境次第で揺れる可能性があるので、
    dictの要素が「キー1つで値がdict」ならその dict を採用する。
    """
    if not isinstance(lst, list):
        return []

    out: List[Dict[str, Any]] = []
    for item in lst:
        if isinstance(item, dict):
            if len(item) == 1:
                v = next(iter(item.values()))
                if isinstance(v, dict):
                    out.append(v)
                    continue
            # フォールバック：dict そのもの
            out.append(item)
    return out


def extract_neighbor_genre_ids(payload: Dict[str, Any]) -> List[int]:
    """
    周辺（parents/brothers/children/current）の genreId を拾う。
    """
    ids: List[int] = []

    cur = payload.get("current")
    if isinstance(cur, dict) and "genreId" in cur:
        ids.append(int(cur["genreId"]))

    for key in ("parents", "brothers", "children"):
        for g in _unwrap_list_items(payload.get(key)):
            if "genreId" in g:
                ids.append(int(g["genreId"]))

    return ids


def choose_parent_genre_id(payload: Dict[str, Any]) -> Optional[int]:
    """
    parent_genre_id を列として持ちたいので推定する。
    - まず parents の中から currentLevel-1 を探す（いればそれが直親）
    - 無ければ parents の最後（最も深い）を採用
    - それも無ければ None
    """
    cur = payload.get("current")
    if not isinstance(cur, dict) or "genreLevel" not in cur:
        return None
    cur_level = int(cur.get("genreLevel", 0))

    parents = _unwrap_list_items(payload.get("parents"))
    if not parents:
        return None

    # currentLevel-1 を優先
    target_level = cur_level - 1
    for p in parents:
        try:
            if int(p.get("genreLevel", -999)) == target_level:
                return int(p["genreId"])
        except Exception:
            pass

    # フォールバック：parents の中で最大 level のもの
    best = None
    best_level = -999
    for p in parents:
        try:
            lvl = int(p.get("genreLevel", -999))
            if lvl > best_level and "genreId" in p:
                best_level = lvl
                best = int(p["genreId"])
        except Exception:
            continue
    return best


def build_genre_row(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    rakuten_genre へ upsert する行データを組み立てる（raw_json込み）。
    サンプルの current には genreId/genreName/genreLevel/englishName/linkGenreId/chopperFlg/lowestFlg がある想定。
    :contentReference[oaicite:4]{index=4}
    """
    cur = payload.get("current")
    if not isinstance(cur, dict):
        raise ValueError("payload.current is missing or not an object")

    genre_id = int(cur["genreId"])
    row = {
        "genre_id": genre_id,
        "genre_name": cur.get("genreName") or "",
        "genre_level": int(cur.get("genreLevel", 0)),
        "parent_genre_id": choose_parent_genre_id(payload),
        "english_name": cur.get("englishName"),
        "link_genre_id": cur.get("linkGenreId"),
        "chopper_flg": cur.get("chopperFlg"),
        "lowest_flg": cur.get("lowestFlg"),
        "raw_json": json.dumps(payload, ensure_ascii=False),
    }
    return row


# ==========
# Main loop
# ==========

def run(cfg: Config) -> int:
    conn = get_conn(cfg.database_url)
    try:
        seed_start_genre(conn, cfg.start_genre_id)

        fetched_count = 0

        while True:
            if cfg.max_genres is not None and fetched_count >= cfg.max_genres:
                print(f"[STOP] reached --max-genres={cfg.max_genres}")
                return 0

            targets = claim_pending_genres(conn, cfg.lock_owner, cfg.batch_size)
            if not targets:
                print("[DONE] no pending genres")
                return 0

            for genre_id in targets:
                if cfg.max_genres is not None and fetched_count >= cfg.max_genres:
                    print(f"[STOP] reached --max-genres={cfg.max_genres}")
                    return 0

                try:
                    payload = fetch_genre_from_api(cfg, genre_id)
                    row = build_genre_row(payload)
                    upsert_genre(conn, row)

                    # 次に回す候補（parents/brothers/children/current）
                    candidates = extract_neighbor_genre_ids(payload)
                    enqueue_candidates(conn, candidates)

                    mark_done(conn, genre_id)
                    fetched_count += 1

                    print(f"[OK] genre_id={genre_id} name={row['genre_name']} candidates={len(candidates)} total={fetched_count}")

                    if cfg.sleep_sec > 0:
                        time.sleep(cfg.sleep_sec)

                except Exception as e:
                    mark_error(conn, genre_id, repr(e))
                    print(f"[ERR] genre_id={genre_id} {e}", file=sys.stderr)

    finally:
        conn.close()


def parse_args(argv: List[str]) -> Config:
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", default=os.getenv("NEON_DATABASE_URL"))
    p.add_argument("--rakuten-app-id", default=os.getenv("RAKUTEN_APP_ID"))
    p.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    p.add_argument("--start-genre-id", type=int, default=int(os.getenv("START_GENRE_ID", "0")))
    p.add_argument("--batch-size", type=int, default=int(os.getenv("BATCH_SIZE", "20")))
    p.add_argument("--sleep-sec", type=float, default=float(os.getenv("SLEEP_SEC", "0.2")))
    p.add_argument("--max-genres", type=int, default=None, help="テスト用：取得件数上限（例: 10）")
    p.add_argument("--timeout-sec", type=int, default=int(os.getenv("REQUEST_TIMEOUT_SEC", "20")))

    args = p.parse_args(argv)

    if not args.database_url:
        raise SystemExit("NEON_DATABASE_URL is required (arg or env)")
    if not args.rakuten_app_id:
        raise SystemExit("RAKUTEN_APP_ID is required (arg or env)")

    lock_owner = os.getenv("LOCK_OWNER") or f"{platform.node()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"

    return Config(
        database_url=args.database_url,
        rakuten_app_id=args.rakuten_app_id,
        api_base_url=args.api_base_url,
        start_genre_id=args.start_genre_id,
        batch_size=args.batch_size,
        sleep_sec=args.sleep_sec,
        max_genres=args.max_genres,
        lock_owner=lock_owner,
        request_timeout_sec=args.timeout_sec,
    )


if __name__ == "__main__":
    cfg = parse_args(sys.argv[1:])
    raise SystemExit(run(cfg))
