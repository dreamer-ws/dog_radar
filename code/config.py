"""配置加载：默认值 + JSON 文件 + 命令行覆盖。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class Config:
    # 扫描范围：空列表 = 扫描全部链；填一个或多个链名则只扫指定链
    # 例：["solana"] 单链，["solana", "base"] 多链
    networks: List[str] = field(default_factory=list)
    pages: int = 1                 # 每个网络抓取的页数（每页约 20 条）
    page_size: int = 20

    # 土狗评分
    min_score: int = 60            # 达到该分数才判定为「土狗」
    max_age_minutes: Optional[int] = None  # 只关注创建时间在 N 分钟内的池子（None=不限）
    min_liquidity_usd: float = 0.0  # 最小流动性（美元），低于则丢弃
    max_fdv_usd: Optional[float] = None   # 最大 FDV（美元），高于则丢弃

    # 报价代币白名单（只关注这些「基准币」配对的池子，降低噪声）
    quote_whitelist: List[str] = field(default_factory=lambda: [
        "SOL", "WETH", "ETH", "USDC", "USDT", "WBNB", "BNB", "DAI", "WSOL", "POL", "MATIC",
    ])
    enforce_quote_whitelist: bool = True

    # meme 关键词（命中则加分）
    meme_keywords: List[str] = field(default_factory=lambda: [
        "doge", "dog", "pepe", "shib", "shiba", "cat", "kitty", "meow", "frog", "moon",
        "rocket", "elon", "musk", "trump", "biden", "ai", "gpt", "chad", "wojak", "ape",
        "bear", "bull", "wif", "bonk", "ponke", "mog", "popcat", "neiro", "meme", "inu",
        "coin", "toilet", "fart", "cum", "pump", "based", "sigma", "giga", "rizz",
    ])

    # 存储
    db_path: str = "dog_discover.db"

    # 告警
    webhook_url: str = ""
    webhook_type: str = "generic"  # generic | telegram | discord | feishu
    telegram_bot_token: str = ""   # Telegram Bot Token（与 webhook_url 二选一，推荐用这个）
    telegram_chat_id: str = ""

    # 运行
    watch: bool = False        # 进入持续监控模式
    interval: int = 10         # 监控间隔秒数
    verbose: bool = False
    no_color: bool = False
    allow_cn_names: bool = False   # 币名语言模式：False 只保留非中文币名；True 只保留中文币名

    @classmethod
    def from_file(cls, path: str) -> "Config":
        p = Path(path)
        data = {}
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        cfg = cls()
        for k, v in data.items():
            if hasattr(cfg, k) and v is not None:
                setattr(cfg, k, v)
        return cfg

    def apply_cli(self, args) -> "Config":
        """把 argparse 命名空间里非 None 的字段覆盖进来。"""
        for k, v in vars(args).items():
            if v is not None and hasattr(self, k):
                setattr(self, k, v)
        return self

    def to_dict(self) -> dict:
        return asdict(self)
