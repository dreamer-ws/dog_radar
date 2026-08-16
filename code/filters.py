"""过滤管线：在打分前后对池子做硬性过滤。"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from .config import Config
from .models import Pool

# 中文字符范围（用于判断币名是否含中文）
_CN_RE = re.compile(r"[\u4e00-\u9fff]")


class FilterPipeline:
    def __init__(self, config: Config):
        self.config = config

    def passes(self, pool: Pool) -> Tuple[bool, Optional[str]]:
        """返回 (是否通过, 未通过原因)。"""
        cfg = self.config

        # 币名语言过滤：默认只保留非中文币名；allow_cn_names=true 时只保留中文币名
        # 注：base_token 缺失时也参与判断（无法证明是中文 → true 模式下过滤）
        token = pool.base_token
        cn_text = " ".join(filter(None, [
            pool.name or "",
            token.name if token else "",
            token.symbol if token else "",
        ]))
        is_cn = bool(_CN_RE.search(cn_text))
        if not cfg.allow_cn_names and is_cn:
            return False, "中文币名（默认过滤，allow_cn_names=true 时只保留中文币名）"
        if cfg.allow_cn_names and not is_cn:
            return False, "非中文币名（allow_cn_names=true 时只保留中文币名）"

        # 报价代币白名单
        if cfg.enforce_quote_whitelist and pool.quote_token:
            sym = (pool.quote_token.symbol or "").upper()
            if sym and sym not in [q.upper() for q in cfg.quote_whitelist]:
                return False, f"报价币{sym}不在白名单"

        # 最小流动性
        if pool.reserve_usd < cfg.min_liquidity_usd:
            return False, f"流动性${pool.reserve_usd:,.0f}低于阈值"

        # 最大 FDV
        if cfg.max_fdv_usd is not None and pool.fdv_usd is not None and pool.fdv_usd > cfg.max_fdv_usd:
            return False, f"FDV${pool.fdv_usd:,.0f}高于阈值"

        # 最大年龄
        if cfg.max_age_minutes is not None:
            age = pool.age_minutes()
            if age is not None and age > cfg.max_age_minutes:
                return False, f"池子已存在{age:.0f}分钟"

        return True, None
