"""运行编排：单次扫描 + 持续监控。"""
from __future__ import annotations

import time
from typing import List, Optional

from .alerter import Alerter, print_summary
from .config import Config
from .detector import DogDetector
from .filters import FilterPipeline
from .models import Discovery, Pool
from .sources import DexScreenerSource, GeckoTerminalSource
from .sources.geckoterminal import FALLBACK_NETWORKS
from .storage import Storage


class Runner:
    """扫描流程编排器，负责拉取池子、过滤、打分、存储和告警。"""
    def __init__(self, config: Config):
        self.config = config
        self.gecko = GeckoTerminalSource()
        self._all_networks: Optional[List[str]] = None  # 缓存动态获取的全部链
        self.dex = DexScreenerSource()
        self.detector = DogDetector(config)
        self.filters = FilterPipeline(config)
        self.storage = Storage(config.db_path)
        self.alerter = Alerter(
            color=not config.no_color,
            webhook_url=config.webhook_url,
            webhook_type=config.webhook_type,
            telegram_bot_token=config.telegram_bot_token,
            telegram_chat_id=config.telegram_chat_id,
        )

    def _resolve_networks(self) -> List[str]:
        """配置了 networks 就用配置的；否则动态获取 GeckoTerminal 全部链（结果缓存）。"""
        if self.config.networks:
            return self.config.networks
        if self._all_networks is None:
            try:
                self._all_networks = self.gecko.list_networks()
            except Exception as e:
                if self.config.verbose:
                    print(f"[warn] 获取全部链列表失败，回退到默认链: {e}")
                self._all_networks = list(FALLBACK_NETWORKS)
            if self.config.verbose:
                print(f"未指定网络，扫描 GeckoTerminal 全部 {len(self._all_networks)} 条链")
        return self._all_networks

    def fetch_pools(self) -> List[Pool]:
        pools: List[Pool] = []
        for network in self._resolve_networks():
            for page in range(1, self.config.pages + 1):
                try:
                    got = self.gecko.fetch_new_pools(network=network, page=page, limit=self.config.page_size)
                    if not got:
                        break
                    pools.extend(got)
                except Exception as e:
                    if self.config.verbose:
                        print(f"[warn] 拉取 {network} 第{page}页失败: {e}")
        return pools

    def scan_once(self) -> int:
        pools = self.fetch_pools()
        if self.config.verbose:
            print(f"共拉取 {len(pools)} 个池子，开始过滤打分...")

        flagged: List[Discovery] = []
        for pool in pools:
            ok, reason = self.filters.passes(pool)
            print(f"[filter] ok={ok}, reason={reason}，pool.name={pool.name}")
            if not ok:
                if self.config.verbose:
                    print(f"  过滤: {pool.name or pool.address} -> {reason}")
                continue

            score, reasons = self.detector.score(pool)
            d = Discovery(pool=pool, score=score, reasons=reasons, flagged=score >= self.config.min_score)

            if self.config.verbose and not d.flagged:
                print(f"  低分: {pool.base_token.symbol if pool.base_token else '?'} -> {score}分")

            is_new = self.storage.upsert(d)
            if d.flagged:
                flagged.append(d)
                if is_new:  # 只对新发现的土狗告警，避免重复刷屏
                    self.alerter.notify(d)

        flagged.sort(key=lambda x: x.score, reverse=True)
        print_summary(flagged, len(pools), color=not self.config.no_color)
        return len(flagged)

    def watch(self, interval: int = 60) -> None:
        print(f"进入监控模式，每 {interval} 秒扫描一次 (Ctrl+C 退出)...")
        try:
            while True:
                self.scan_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n已退出监控。")
        finally:
            self.storage.close()

    def close(self):
        self.storage.close()
