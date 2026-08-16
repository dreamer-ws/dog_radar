"""土狗（Meme 币）特征评分与年龄计算。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .config import Config
from .models import Pool

# 中文字符范围（用于识别中文币名）
_CN_RE = re.compile(r"[\u4e00-\u9fff]")


def _parse_dt(s: str) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def age_minutes(created_at: str, now: Optional[datetime] = None) -> Optional[float]:
    """计算池子创建至今的分钟数。"""
    dt = _parse_dt(created_at)
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 60.0)


class DogDetector:
    """对池子打分，判断其「土狗」程度（0-100）。"""

    def __init__(self, config: Config):
        self.config = config
        self._kw = [k.lower() for k in config.meme_keywords]

    def score(self, pool: Pool) -> Tuple[int, List[str]]:
        cfg = self.config
        score = 0
        reasons: List[str] = []
        token = pool.base_token
        text = ""
        if token:
            text = f"{token.name or ''} {token.symbol or ''}".lower()

        # 1. meme 关键词命中
        hit = [k for k in self._kw if k and k in text]
        if hit:
            # symbol 命中权重更高
            symbol = (token.symbol or "").lower()
            sym_hit = any(k in symbol for k in hit)
            score += 30 if sym_hit else 15
            reasons.append(f"meme关键词命中: {', '.join(hit[:5])}")

        # 中文币名（中文 MEME 土狗特征明显）
        if _CN_RE.search(text):
            score += 20
            reasons.append("中文币名")

        # 2. 创建时间越新越像土狗
        age = pool.age_minutes()
        if age is not None:
            if age <= 10:
                score += 20
                reasons.append(f"新池子(≤10分钟)")
            elif age <= 60:
                score += 15
                reasons.append(f"新池子(≤1小时)")
            elif age <= 360:
                score += 10
                reasons.append(f"较新(≤6小时)")
            elif age <= 1440:
                score += 5
                reasons.append("较新(≤24小时)")

        # 3. 流动性低
        liq = pool.reserve_usd
        if 0 < liq < 10_000:
            score += 15
            reasons.append(f"流动性极低(${liq:,.0f})")
        elif liq < 50_000:
            score += 10
            reasons.append(f"流动性偏低(${liq:,.0f})")
        elif liq < 200_000:
            score += 5
            reasons.append(f"流动性一般(${liq:,.0f})")

        # 4. FDV 低
        if pool.fdv_usd is not None:
            fdv = pool.fdv_usd
            if fdv < 100_000:
                score += 15
                reasons.append(f"FDV极低(${fdv:,.0f})")
            elif fdv < 1_000_000:
                score += 10
                reasons.append(f"FDV低(${fdv:,.0f})")
            elif fdv < 5_000_000:
                score += 5
                reasons.append(f"FDV较低(${fdv:,.0f})")

        # 5. 涨跌幅（暴涨或暴跌都值得关注）
        p24 = pool.price_change_h24
        if p24 is not None:
            if p24 > 100:
                score += 10
                reasons.append(f"24h暴涨({p24:+.0f}%)")
            elif p24 > 50:
                score += 5
                reasons.append(f"24h大涨({p24:+.0f}%)")
            elif p24 < -50:
                score += 5
                reasons.append(f"24h暴跌({p24:+.0f}%)")

        # 6. 买卖比（买盘踊跃 = FOMO）
        if pool.sells_h24 > 0 and pool.buys_h24 > 0:
            ratio = pool.buys_h24 / pool.sells_h24
            if ratio >= 2:
                score += 10
                reasons.append(f"买压活跃(买卖比{ratio:.1f})")
            elif ratio >= 1.3:
                score += 5
                reasons.append(f"买盘占优(买卖比{ratio:.1f})")

        # 7. pump.fun 内盘（未毕业的土狗）
        dex = (pool.dex or "").lower()
        if "pump" in dex:
            score += 5
            reasons.append("pump.fun 内盘")

        return max(0, min(100, score)), reasons
