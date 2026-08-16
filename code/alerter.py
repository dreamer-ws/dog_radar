"""告警输出：控制台 + 可选 Webhook（Telegram / Discord / 飞书 / 通用）。"""
from __future__ import annotations

import json
import urllib.request
from typing import List

from .models import Discovery

# ANSI 颜色
_RESET = "\033[0m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"


def _c(text: str, color: str, enabled: bool = True) -> str:
    return f"{color}{text}{_RESET}" if enabled else text


def _fmt_price_change(p: float | None, enabled: bool) -> str:
    if p is None:
        return "—"
    s = f"{p:+.1f}%"
    # 中国习惯：涨=红，跌=绿
    if p > 0:
        return _c(s, _RED, enabled)
    if p < 0:
        return _c(s, _GREEN, enabled)
    return s


def format_discovery(d: Discovery, color: bool = True) -> str:
    pool = d.pool
    token = pool.base_token
    quote = pool.quote_token
    name = (token.name or token.symbol or "未知") if token else "未知"
    symbol = (token.symbol or "") if token else ""
    quote_sym = (quote.symbol or "") if quote else ""

    age = pool.age_minutes()
    age_s = f"{age:.0f}分钟" if age is not None else "未知"

    score_color = _RED if d.score >= 80 else (_YELLOW if d.score >= 60 else _GREEN)
    score_s = _c(f"{d.score}", score_color, color)

    lines = [
        _c("=" * 60, _CYAN, color),
        _c(f"🐕 土狗发现 | {name} ({symbol})", _BOLD, color),
        _c("=" * 60, _CYAN, color),
        f"  链        : {pool.network}",
        f"  DEX       : {pool.dex or '未知'}",
        f"  池子地址  : {pool.address}",
    ]
    if token and token.address:
        lines.append(f"  代币地址  : {token.address}")
    lines += [
        f"  流动性    : ${pool.reserve_usd:,.2f}  (24h成交 ${pool.volume_h24_usd:,.0f})",
        f"  FDV       : {'$' + format(pool.fdv_usd, ',.0f') if pool.fdv_usd else '未知'}",
        f"  24h涨跌   : {_fmt_price_change(pool.price_change_h24, color)}",
        f"  买/卖     : {pool.buys_h24}/{pool.sells_h24}",
        f"  创建时间  : {pool.created_at or '未知'} (约{age_s}前)",
        f"  土狗评分  : {score_s} / 100",
    ]
    if d.reasons:
        lines.append("  命中特征  : " + "；".join(d.reasons))
    lines.append(_c("=" * 60, _CYAN, color))
    return "\n".join(lines)


# Telegram 单条消息上限 4096 字符，留一点余量
_TELEGRAM_MAX_LEN = 4000


class Alerter:
    def __init__(self, color: bool = True, webhook_url: str = "", webhook_type: str = "generic",
                 telegram_bot_token: str = "", telegram_chat_id: str = ""):
        self.color = color
        self.webhook_url = webhook_url
        self.webhook_type = webhook_type
        self.telegram_bot_token = telegram_bot_token
        self.telegram_chat_id = telegram_chat_id

    def notify(self, d: Discovery) -> None:
        self._console(d)
        if self.webhook_url:
            try:
                self._webhook(d)
            except Exception as e:
                print(f"[webhook 发送失败] {e}")

    def _console(self, d: Discovery) -> None:
        print(format_discovery(d, color=self.color))

    def _webhook(self, d: Discovery) -> None:
        text = format_discovery(d, color=False)
        t = self.webhook_type.lower()
        url = self.webhook_url
        payload = {}
        headers = {"Content-Type": "application/json"}

        if t == "telegram":
            # 优先用 bot_token 自动构造 API 地址，也兼容手填完整 sendMessage URL
            if self.telegram_bot_token:
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {"chat_id": self.telegram_chat_id, "text": text[: _TELEGRAM_MAX_LEN]}
        elif t == "discord":
            payload = {"content": f"```\n{text}\n```"}
        elif t == "feishu":
            payload = {"msg_type": "text", "content": {"text": text}}
        else:  # generic
            payload = {"text": text}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        # Telegram 返回 {"ok": true} 或 {"ok": false, "description": "..."}，失败时抛错便于排查
        if t == "telegram":
            try:
                result = json.loads(body)
            except ValueError:
                return
            if not result.get("ok"):
                desc = result.get("description", body)
                if "chat not found" in str(desc).lower():
                    desc += "（请先在 Telegram 中向该 bot 发送一条消息如 /start 以建立会话，再核对 telegram_chat_id）"
                raise RuntimeError(f"Telegram API 返回失败: {desc}")


def print_summary(flagged: List[Discovery], total_scanned: int, color: bool = True) -> None:
    print()
    print(_c(f"扫描完成：共扫描 {total_scanned} 个池子，命中土狗 {len(flagged)} 个。", _CYAN, color))
