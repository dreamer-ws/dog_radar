"""GeckoTerminal 公共 API 数据源。

免费、无需 API key，限流约 30 次/分钟。
端点：GET /api/v2/networks/{network}/new_pools
返回 JSON:API 结构（data + included）。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional

from ..models import Pool, Token

BASE_URL = "https://api.geckoterminal.com/api/v2"
USER_AGENT = "dog-discover/0.1 (https://example.local)"

# 兜底链列表：仅当动态获取全部链失败时使用
FALLBACK_NETWORKS = [
    "solana", "base", "bsc", "ethereum", "arbitrum", "optimism",
    "polygon_pos", "avalanche", "fantom", "gnosis", "kava", "manta",
]


def _num(value) -> Optional[float]:
    """把 API 返回的字符串数字安全转成 float，失败返回 None。"""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get(path: str, params: Optional[dict] = None, timeout: int = 20, retries: int = 3) -> dict:
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:  # 限流，指数退避
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            time.sleep(1)
    raise last_err  # type: ignore


def _index_included(payload: dict) -> Dict[str, dict]:
    return {item["id"]: item for item in payload.get("included", [])}


def _resolve(rel: Optional[dict], included: Dict[str, dict]) -> Optional[dict]:
    if not rel:
        return None
    data = rel.get("data")
    if not data:
        return None
    return included.get(data.get("id"), {"type": data.get("type"), "id": data.get("id"), "attributes": {}})


def _token_from(item: Optional[dict], network: str) -> Optional[Token]:
    if not item:
        return None
    attrs = item.get("attributes", {}) or {}
    return Token(
        address=attrs.get("address", ""),
        name=attrs.get("name", "") or "",
        symbol=attrs.get("symbol", "") or "",
        network=network,
    )


class GeckoTerminalSource:
    """从 GeckoTerminal 拉取新建流动性池。"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url

    def list_networks(self) -> List[str]:
        """获取 GeckoTerminal 支持的全部链 id（用于未指定网络时扫描全部链）。"""
        nets: List[str] = []
        for page in range(1, 6):
            payload = _get("/networks", params={"page": page, "limit": 100})
            items = payload.get("data", []) or []
            for item in items:
                nid = (item.get("id") or "").rsplit("/", 1)[-1]
                if nid and nid not in nets:
                    nets.append(nid)
            if len(items) < 100:  # 最后一页
                break
        return nets or list(FALLBACK_NETWORKS)

    def fetch_new_pools(
        self,
        network: str = "solana",
        page: int = 1,
        limit: Optional[int] = None,
        include: tuple = ("base_token", "quote_token", "dex"),
    ) -> List[Pool]:
        params: Dict[str, object] = {"page": page, "include": ",".join(include)}
        if limit is not None:
            params["limit"] = max(1, min(100, limit))  # GeckoTerminal 单页上限 100
        payload = _get(
            f"/networks/{network}/new_pools",
            params=params,
        )
        included = _index_included(payload)
        pools: List[Pool] = []
        for item in payload.get("data", []):
            attrs = item.get("attributes", {}) or {}
            rels = item.get("relationships", {}) or {}

            dex_item = _resolve(rels.get("dex"), included)
            dex_name = (dex_item or {}).get("attributes", {}).get("name", "") or ""

            volume = attrs.get("volume_usd") or {}
            pct = attrs.get("price_change_percentage") or {}
            txns = attrs.get("transactions") or {}
            txn_h24 = txns.get("h24") or {} if isinstance(txns, dict) else {}

            base = _token_from(_resolve(rels.get("base_token"), included), network)
            quote = _token_from(_resolve(rels.get("quote_token"), included), network)

            pools.append(
                Pool(
                    address=attrs.get("address", ""),
                    network=network,
                    name=attrs.get("name", "") or "",
                    dex=dex_name,
                    base_token=base,
                    quote_token=quote,
                    reserve_usd=_num(attrs.get("reserve_in_usd")) or 0.0,
                    fdv_usd=_num(attrs.get("fdv_usd")),
                    volume_h24_usd=_num(volume.get("h24")) or 0.0,
                    price_change_h1=_num(pct.get("h1")),
                    price_change_h24=_num(pct.get("h24")),
                    buys_h24=int(txn_h24.get("buys", 0) or 0),
                    sells_h24=int(txn_h24.get("sells", 0) or 0),
                    buyers_h24=int(txn_h24.get("buyers", 0) or 0),
                    sellers_h24=int(txn_h24.get("sellers", 0) or 0),
                    created_at=attrs.get("pool_created_at", "") or "",
                )
            )
        return pools
