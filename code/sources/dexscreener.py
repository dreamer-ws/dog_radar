"""DexScreener 公共 API 数据源。

免费、无需 API key。主要用于增强代币画像（描述、社交链接等）。
端点：GET /token-profiles/latest/v1  （约 60 次/分钟）
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional

BASE_URL = "https://api.dexscreener.com"
USER_AGENT = "dog-discover/0.1"


def _get(path: str, params: Optional[dict] = None, timeout: int = 20, retries: int = 3) -> dict:
    url = BASE_URL + path
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 * (attempt + 1))
                last_err = e
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            time.sleep(1)
    raise last_err  # type: ignore


class DexScreenerSource:
    """DexScreener 代币画像数据源。"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url

    def latest_token_profiles(self) -> List[dict]:
        """返回最近新增的代币画像（含 description、links 等）。"""
        payload = _get("/token-profiles/latest/v1")
        return payload  # 直接返回原始 list

    def profiles_by_address(self) -> Dict[str, dict]:
        """构建 {代币地址: 画像} 索引。"""
        index: Dict[str, dict] = {}
        try:
            for item in self.latest_token_profiles():
                addr = (item.get("tokenAddress") or "").lower()
                if addr:
                    index[addr] = item
        except Exception:
            pass
        return index
