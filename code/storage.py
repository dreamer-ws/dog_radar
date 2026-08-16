"""SQLite 存储：去重 + 历史记录。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from .models import Discovery

_SCHEMA = """
CREATE TABLE IF NOT EXISTS discoveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network TEXT NOT NULL,
    pool_address TEXT NOT NULL,
    token_address TEXT,
    token_name TEXT,
    token_symbol TEXT,
    dex TEXT,
    score INTEGER,
    reserve_usd REAL,
    fdv_usd REAL,
    volume_h24_usd REAL,
    price_change_h24 REAL,
    buys_h24 INTEGER DEFAULT 0,
    sells_h24 INTEGER DEFAULT 0,
    reasons TEXT,
    created_at TEXT,
    first_seen TEXT,
    last_seen TEXT,
    alert_count INTEGER DEFAULT 0,
    UNIQUE(network, pool_address)
);
CREATE INDEX IF NOT EXISTS idx_discoveries_score ON discoveries(score DESC);
"""

# 老版本数据库升级：给已有表补加缺失的列
_MIGRATIONS = {
    "buys_h24": "INTEGER DEFAULT 0",
    "sells_h24": "INTEGER DEFAULT 0",
    "reasons": "TEXT",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Storage:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """老库补列：CREATE TABLE IF NOT EXISTS 不会修改已存在的表。"""
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(discoveries)")}
        for name, ddl in _MIGRATIONS.items():
            if name not in cols:
                self.conn.execute(f"ALTER TABLE discoveries ADD COLUMN {name} {ddl}")

    def is_new(self, network: str, pool_address: str) -> bool:
        """该池子是否首次出现。"""
        cur = self.conn.execute(
            "SELECT 1 FROM discoveries WHERE network=? AND pool_address=?",
            (network, pool_address),
        )
        return cur.fetchone() is None

    def upsert(self, d: Discovery) -> bool:
        """写入/更新一条发现，返回是否为新记录。"""
        pool = d.pool
        token = pool.base_token
        now = _now()
        new = self.is_new(pool.network, pool.address)
        if new:
            self.conn.execute(
                """
                INSERT INTO discoveries
                (network, pool_address, token_address, token_name, token_symbol, dex,
                 score, reserve_usd, fdv_usd, volume_h24_usd, price_change_h24,
                 buys_h24, sells_h24, reasons,
                 created_at, first_seen, last_seen, alert_count)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    pool.network, pool.address,
                    token.address if token else "",
                    token.name if token else "",
                    token.symbol if token else "",
                    pool.dex,
                    d.score, pool.reserve_usd, pool.fdv_usd, pool.volume_h24_usd,
                    pool.price_change_h24, pool.buys_h24, pool.sells_h24,
                    "；".join(d.reasons),
                    pool.created_at, now, now,
                    1 if d.flagged else 0,
                ),
            )
        else:
            self.conn.execute(
                """
                UPDATE discoveries SET
                    token_name=?, token_symbol=?, dex=?, score=?, reserve_usd=?,
                    fdv_usd=?, volume_h24_usd=?, price_change_h24=?,
                    buys_h24=?, sells_h24=?, reasons=?, created_at=?,
                    last_seen=?, alert_count = alert_count + ?
                WHERE network=? AND pool_address=?
                """,
                (
                    token.name if token else "",
                    token.symbol if token else "",
                    pool.dex, d.score, pool.reserve_usd, pool.fdv_usd,
                    pool.volume_h24_usd, pool.price_change_h24,
                    pool.buys_h24, pool.sells_h24,
                    "；".join(d.reasons),
                    pool.created_at, now, 1 if d.flagged else 0,
                    pool.network, pool.address,
                ),
            )
        self.conn.commit()
        return new

    def recent(self, limit: int = 50, flagged_only: bool = False) -> List[sqlite3.Row]:
        q = "SELECT * FROM discoveries"
        if flagged_only:
            q += " WHERE score >= 0"
        q += " ORDER BY score DESC, last_seen DESC LIMIT ?"
        return list(self.conn.execute(q, (limit,)))

    def close(self):
        self.conn.close()
