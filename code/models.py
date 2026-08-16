"""数据模型定义。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Token:
    """代币基础信息。"""
    address: str = ""
    name: str = ""
    symbol: str = ""
    network: str = ""


@dataclass
class Pool:
    """DEX 流动性池信息（土狗通常对应一个新建的池子）。"""
    address: str = ""
    network: str = ""
    name: str = ""
    dex: str = ""
    base_token: Optional[Token] = None
    quote_token: Optional[Token] = None
    reserve_usd: float = 0.0          # 池子流动性（美元）
    fdv_usd: Optional[float] = None   # 完全稀释估值
    volume_h24_usd: float = 0.0       # 24h 成交额
    price_change_h1: Optional[float] = None   # 1h 涨跌幅 %
    price_change_h24: Optional[float] = None  # 24h 涨跌幅 %
    buys_h24: int = 0
    sells_h24: int = 0
    buyers_h24: int = 0
    sellers_h24: int = 0
    created_at: str = ""              # 池子创建时间 ISO 8601

    def age_minutes(self, now=None) -> Optional[float]:
        """池子从创建到现在的分钟数；无法解析时返回 None。"""
        from .detector import age_minutes as _age
        return _age(self.created_at, now)


@dataclass
class Discovery:
    """一次发现结果：一个池子 + 土狗评分。"""
    pool: Pool
    score: int = 0
    reasons: List[str] = field(default_factory=list)
    flagged: bool = False

    @property
    def token(self) -> Optional[Token]:
        return self.pool.base_token
