# Hermes Trading System - 项目状态总结
# 保存时间: 2026-06-18 20:41:24

======================================================================
一、项目结构
======================================================================

两个GitHub仓库：
1. https://github.com/Y-wln/trading-system  (Hermes v2 - 原交易系统)
2. https://github.com/Y-wln/QuantDinger     (Hermes版 - 改造后的完整系统)

本地路径：
- Hermes v2:  C:\Users\ZhuanZ\Documents\Codex\2026-06-06\hermes-agent-agent-agent\
- QuantDinger: C:\Users\ZhuanZ\Documents\Codex\QuantDinger\

服务器：
- ubuntu@124.221.104.66 (代理 127.0.0.1:7891)
- systemd服务: hermes-v2, hermes-merculab, hermes-fsc, hermes-liqws

======================================================================
二、QuantDinger改造内容（5个commit已推送）
======================================================================

Commit 1: V1 - Hermes rebrand + billing/community removal
- 品牌: QuantDinger → Hermes Trading
- 删除: billing路由, community路由, USDT支付
- 替换: billing_service/community_service为安全stub
- 35个文件变更

Commit 2: V2 - Full MerCu signal engine + 35 unit tests
- 新增: hermes_mercu.py (19.8KB)
  - 6阶段识别 (吸筹→洗盘→主升→赶顶→派发→崩盘)
  - 21项信号评分
  - 4种币种分类
  - 多时间框架OI分析 (5m/15m/1h)
  - 熔断器 (CircuitBreaker)
- 新增: test_hermes_mercu.py (35个测试)

Commit 3: CI - hermes-tests job
- .github/workflows/basic-ci.yml 添加Hermes测试

Commit 4: V3 - Hermes strategy service
- 新增: hermes_strategy_service.py (11.5KB)
  - 后台轮询服务 (每30秒)
  - 仓位管理 (8上限)
  - 冷却期机制
  - 5%止损
  - 信号历史追踪
- 新增: test_hermes_strategy_service.py
- 注册到app启动流程

Commit 5: V4 - Full QuantDinger integration
- 新增: hermes_integration.py (13.7KB)
  - 执行桥接: Hermes信号 → place_order_from_signal
  - 通知桥接: Hermes → 飞书/Telegram/邮件/Webhook
  - 仓位桥接: Hermes → Portfolio Monitor
  - 回测桥接: 信号历史 → 回测格式
  - 仪表盘: 仓位/币种/评分统计
- 新增: test_hermes_integration.py

======================================================================
三、API端点
======================================================================

GET  /api/hermes/signals          - 实时信号
GET  /api/hermes/data             - 原始Mercu数据
GET  /api/hermes/status           - 策略运行状态
GET  /api/hermes/dashboard        - 仪表盘指标
GET  /api/hermes/backtest-data    - 回测数据
GET  /api/hermes/integration-status - 整合状态
POST /api/hermes/score            - 单币评分
POST /api/hermes/push             - 外部信号推送

======================================================================
四、环境变量
======================================================================

HERMES_ENABLED=true           - 启用Hermes策略服务
HERMES_AUTO_EXECUTE=true      - 启用自动交易 (默认关闭，安全)
HERMES_EXCHANGE=binance       - 交易所
HERMES_MARKET_TYPE=swap       - swap或spot
HERMES_POLL_INTERVAL=30       - 轮询间隔(秒)
HERMES_MAX_POSITIONS=8        - 最大仓位
HERMES_MIN_SCORE_LONG=8       - 开多最低分
HERMES_MIN_SCORE_SHORT=-5     - 开空最高分
HERMES_POSITION_SIZE_PCT=0.1  - 单仓10%
HERMES_STOP_LOSS_PCT=0.05     - 止损5%
HERMES_COOLDOWN_MINUTES=5     - 冷却时间
MERCU_API_BASE=https://cryptosniper-epic.zeabur.app
MERCU_JWT_TOKEN=              - MerCu JWT token

======================================================================
五、MerCu信号文档核心内容
======================================================================

币种分类: 妖币控盘型, 情绪收割型, 机构趋势型, 高位派发型

6阶段:
- 吸筹期: 底部吸筹+现货托底+OI小幅暴涨
- 洗盘期: OI暴跌+不破支撑+现货托底
- 主升期: 多头共振+OI暴涨+Vol爆发
- 赶顶期: 连续高陷阱+OI暴涨
- 派发期: 顶部派发+OI背离
- 出货崩盘期: OI暴跌+现货流出

评分:
12+ → 主升确认
8-12 → 偏多启动
4-8 → 吸筹/试盘
0-4 → 震荡
-5-0 → 风险区
-5以下 → 派发/出货

======================================================================
六、网络配置
======================================================================

代理: 127.0.0.1:7897
Git配置:
  git config --global http.proxy http://127.0.0.1:7897
  git config --global https.proxy http://127.0.0.1:7897

======================================================================
七、重要文件路径
======================================================================

QuantDinger核心文件:
  app/data_providers/hermes_mercu.py          - 信号引擎
  app/services/hermes_strategy_service.py     - 策略服务
  app/services/hermes_integration.py          - 全功能整合
  app/routes/hermes.py                        - API路由
  app/config/settings.py                      - 品牌配置
  tests/test_hermes_mercu.py                  - 信号测试
  tests/test_hermes_strategy_service.py       - 策略测试
  tests/test_hermes_integration.py            - 整合测试
  .github/workflows/basic-ci.yml              - CI流水线

MerCu数据(本地缓存):
  mercu_data/anomaly-v4.json
  mercu_data/momentum.json
  mercu_data/rank.json
  mercu_data/surge.json