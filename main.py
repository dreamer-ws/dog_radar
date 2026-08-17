#!/usr/bin/env python3
"""土狗发现程序入口。

用法示例：
    python main.py                                  # 单次扫描，用默认配置
    python main.py --networks solana,base --min-score 70
    python main.py --watch --interval 120           # 每 2 分钟监控一次
    python main.py --config config.json             # 从配置文件读取
"""
from __future__ import annotations

import argparse
import sys

from code.config import Config
from code.runner import Runner


def _csv_list(s: str):
    return [x.strip() for x in s.split(",") if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dog-discover",
        description="土狗（Meme 币）发现程序 — 基于 GeckoTerminal 公共 API 的新币发现工具",
    )
    p.add_argument("--config", help="JSON 配置文件路径")
    p.add_argument("--networks", type=_csv_list, help="链列表，逗号分隔，如 solana,base,bsc,ethereum")
    p.add_argument("--pages", type=int, help="每个网络抓取的页数")
    p.add_argument("--page-size", type=int, dest="page_size", help="每页抓取条数")
    p.add_argument("--min-score", type=int, dest="min_score", help="判定为土狗的最低评分(0-100)")
    p.add_argument("--min-liquidity", type=float, dest="min_liquidity_usd", help="最小流动性(美元)")
    p.add_argument("--max-fdv", type=float, dest="max_fdv_usd", help="最大 FDV(美元)")
    p.add_argument("--max-age", type=int, dest="max_age_minutes", help="只关注创建 N 分钟内的池子")
    p.add_argument("--quote-whitelist", type=_csv_list, dest="quote_whitelist",
                   help="报价代币白名单，逗号分隔")
    p.add_argument("--no-enforce-quote-whitelist", dest="enforce_quote_whitelist",
                   action="store_false", default=None, help="不强制报价代币白名单")
    p.add_argument("--meme-keywords", type=_csv_list, dest="meme_keywords",
                   help="meme 关键词，逗号分隔")
    p.add_argument("--allow-cn-names", dest="allow_cn_names", action="store_true", default=None,
                   help="只保留中文币名（默认保留非中文币名）")
    p.add_argument("--db", dest="db_path", help="SQLite 数据库路径")
    p.add_argument("--webhook", dest="webhook_url", help="告警 Webhook URL")
    p.add_argument("--webhook-type", choices=["generic", "telegram", "discord", "feishu"],
                   default=None, help="Webhook 类型")
    p.add_argument("--telegram-bot-token", dest="telegram_bot_token", help="Telegram Bot Token")
    p.add_argument("--telegram-chat-id", dest="telegram_chat_id", help="Telegram chat_id")
    # 以下参数默认 None：未在命令行指定时不覆盖配置文件的值（以 config.json 为主）
    p.add_argument("--watch", action="store_true", default=None, help="进入持续监控模式")
    p.add_argument("--interval", type=int, default=None, help="监控间隔秒数")
    p.add_argument("--verbose", action="store_true", default=None, help="输出详细日志")
    p.add_argument("--no-color", action="store_true", default=None, help="关闭彩色输出")
    p.add_argument("--version", action="version", version="dog-discover 0.1.0")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    cfg = Config.from_file(args.config) if args.config else Config()
    cfg.apply_cli(args)

    runner = Runner(cfg)
    try:
        if cfg.watch:
            runner.watch(interval=cfg.interval)
        else:
            runner.scan_once()
    finally:
        runner.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
