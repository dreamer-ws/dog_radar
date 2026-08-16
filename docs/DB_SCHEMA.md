# SQLite 数据库结构说明

数据库文件：`dog_discover.db`（路径可在配置 `db_path` 中修改）

## 表：discoveries（土狗发现记录）

存储每次扫描发现的池子及其评分，`(network, pool_address)` 唯一，重复扫描只更新不重复插入。

| 列名 | 类型 | 必填 | 默认值 | 含义 | 示例 |
|---|---|---|---|---|---|
| id | INTEGER | ✅ | 自增 | 主键，自增 | 1 |
| network | TEXT | ✅ | — | 链名称 | solana |
| pool_address | TEXT | ✅ | — | 池子地址 | 4aYfGWXizyB8cvbiH3s1kEzif872gNtx2LcZUPjYU2m3 |
| token_address | TEXT | — | — | 代币地址 | FwaZabym6YVQjbcURMREbaKHwuJ95B2dJKpoayhwpump |
| token_name | TEXT | — | — | 代币名称 | Test Dog |
| token_symbol | TEXT | — | — | 代币符号 | TDOG |
| dex | TEXT | — | — | DEX 名称 | Pump.fun |
| score | INTEGER | — | — | 土狗评分（0-100，≥min_score 判定为土狗） | 65 |
| reserve_usd | REAL | — | — | 池子流动性（美元） | 5000.46 |
| fdv_usd | REAL | — | — | 完全稀释估值（美元） | 16273 |
| volume_h24_usd | REAL | — | — | 24h 成交额（美元） | 1369 |
| price_change_h24 | REAL | — | — | 24h 涨跌幅（%） | 90.2 |
| buys_h24 | INTEGER | — | 0 | 24h 买入笔数 | 5 |
| sells_h24 | INTEGER | — | 0 | 24h 卖出笔数 | 3 |
| reasons | TEXT | — | — | 命中特征列表，用「；」连接 | 新池子(≤10分钟)；流动性极低($5,000) |
| created_at | TEXT | — | — | 池子创建时间（ISO 8601 UTC） | 2026-08-16T07:25:40Z |
| first_seen | TEXT | — | — | 首次发现时间（UTC） | 2026-08-16T07:30:00Z |
| last_seen | TEXT | — | — | 最近一次扫描时间（UTC） | 2026-08-16T07:32:00Z |
| alert_count | INTEGER | — | 0 | 命中土狗后的告警次数（每次扫描命中 +1） | 2 |

### 约束与索引

```sql
UNIQUE(network, pool_address)               -- 去重键
CREATE INDEX idx_discoveries_score ON discoveries(score DESC);  -- 按评分排序查询加速
```

### 写入行为（Storage.upsert）

- 首次出现：INSERT，`first_seen = last_seen = 当前时间`，`alert_count = 1`（若 flagged）
- 再次扫描到：UPDATE 刷新所有业务字段（score / 流动性 / FDV / 成交 / 涨跌 / 买卖 / 命中特征 / created_at / last_seen），`alert_count = alert_count + 1`（若 flagged）
- 返回布尔值：`True` = 新记录，`False` = 已有记录

### 常用查询

```sql
-- 评分最高的 20 条
SELECT * FROM discoveries ORDER BY score DESC LIMIT 20;

-- 最近 1 小时内首次发现的土狗
SELECT * FROM discoveries WHERE first_seen >= datetime('now', '-1 hour') ORDER BY score DESC;

-- 按链统计
SELECT network, COUNT(*) AS cnt FROM discoveries GROUP BY network;
```

## 版本迁移

`CREATE TABLE IF NOT EXISTS` 不会修改已存在的表，因此 `Storage._migrate()` 在启动时用 `PRAGMA table_info` 检查并自动补加缺失列：

| 版本 | 新增列 |
|---|---|
| v1（初始） | 基础字段（id ~ alert_count 中的旧 16 列） |
| v2 | buys_h24, sells_h24, reasons |
