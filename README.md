# 🐕 土狗发现程序 (dog-discover)

基于 Python 的 **Meme 币（土狗）发现工具**。自动扫描多条公链上最新创建的流动性池，根据 meme 特征、流动性、估值、涨跌幅、买卖盘等多维度打分，实时发现潜在的「土狗」并告警。

> ⚠️ 免责声明：本工具仅用于链上数据分析与学习研究，不构成任何投资建议。土狗币风险极高，请谨慎参与。

## ✨ 特性

- **零第三方依赖**：纯 Python 标准库实现（`urllib` / `sqlite3` / `argparse`），Python 3.8+ 开箱即用
- **多链扫描**：Solana、Base、BSC、Ethereum 等 200+ 链（GeckoTerminal 支持范围）
- **土狗评分**：meme 关键词命中、池龄、流动性、FDV、24h 涨跌幅、买卖比、pump.fun 内盘等多因子打分
- **去重存储**：SQLite 本地记录，同一土狗只告警一次，避免刷屏
- **多种告警**：控制台彩色输出 + 可选 Webhook（Telegram / Discord / 飞书 / 通用）
- **两种模式**：单次扫描 + 持续监控

## 🚀 快速开始

```bash
# 1. 单次扫描（默认 solana/base/bsc/ethereum）
python main.py

# 2. 指定链 + 提高阈值
python main.py --networks solana,base --min-score 70

# 3. 持续监控（每 2 分钟一次）
python main.py --watch --interval 120

# 4. 从配置文件加载
python main.py --config config.example.json
```

## 📊 评分模型（0-100 分）

| 因子 | 说明 | 加分 |
|------|------|------|
| meme 关键词 | 名称/代码命中 doge、pepe、shib 等 | +15~30 |
| 池龄 | 越新越像土狗（≤10分钟 ~ ≤24小时） | +5~20 |
| 流动性 | 越低越危险 | +5~15 |
| FDV | 估值越低越早期 | +5~15 |
| 24h 涨跌 | 暴涨或暴跌都值得关注 | +5~10 |
| 买/卖比 | 买盘踊跃（FOMO） | +5~10 |
| pump.fun | 内盘未毕业 | +5 |

默认 `--min-score 60` 判定为土狗。

## ⚙️ 命令行参数

```
--config              JSON 配置文件路径
--networks            链列表（逗号分隔）
--pages               每网络抓取页数
--min-score           土狗判定阈值 (0-100)
--min-liquidity       最小流动性（美元）
--max-fdv             最大 FDV（美元）
--max-age             只关注 N 分钟内新池
--db                  SQLite 数据库路径
--webhook             Webhook 告警地址
--webhook-type        generic | telegram | discord | feishu
--telegram-chat-id    Telegram chat_id
--watch               进入监控模式
--interval            监控间隔秒数
--verbose             详细日志
--no-color            关闭彩色输出
```

## 📁 项目结构

```
dog_discover/
├── main.py                  # CLI 入口
├── config.example.json      # 配置示例
├── README.md
└── dog_discover/
    ├── config.py            # 配置加载
    ├── models.py            # 数据模型
    ├── detector.py          # 土狗评分
    ├── filters.py           # 过滤管线
    ├── storage.py           # SQLite 存储
    ├── alerter.py           # 控制台 + Webhook 告警
    ├── runner.py            # 运行编排
    └── sources/
        ├── geckoterminal.py # GeckoTerminal 新池子
        └── dexscreener.py   # DexScreener 画像增强
```

## 🔌 数据源

- **GeckoTerminal 公共 API**（主）：`/api/v2/networks/{network}/new_pools`，免费、无需 key，限流约 30 次/分钟
- **DexScreener**（增强）：`/token-profiles/latest/v1`，补充代币描述与社交链接

## 🔔 告警接入示例

**Telegram**（先用 @BotFather 创建机器人拿到 token 和 chat_id）：
```bash
python main.py --webhook https://api.telegram.org/bot<TOKEN>/sendMessage \
  --webhook-type telegram --telegram-chat-id <CHAT_ID>
```

**飞书群机器人**：
```bash
python main.py --webhook https://open.feishu.cn/open-apis/bot/v2/hook/<TOKEN> --webhook-type feishu
```

**Discord**：
```bash
python main.py --webhook https://discord.com/api/webhooks/<ID>/<TOKEN> --webhook-type discord
```

## 🛠 后续可扩展

- 增加 honeypot / rugpull 风险检测（合约代码分析）
- 接入钱包监听，跟踪「聪明钱」建仓
- Web 可视化 Dashboard
- 多线程并发拉取 + 智能限流
