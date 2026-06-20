"""Hermes QD Bridge V3 - connects Hermes event-driven architecture to QuantDinger.

This bridge wires:
  V3 EventBus + RiskEngine + PositionManager
  → QD live_trading (execution)
  → QD signal_notifier (Feishu/webhook)
  → QD portfolio_monitor (tracking)
  → QD backtest data feed
  → QD dashboard metrics

Single integration point - one call at startup connects everything.
Replaces hermes_integration.py (V2).
"""
from __future__ import annotations
import os
import time
import threading
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

from app.utils.logger import get_logger

logger = get_logger(__name__)
BJT = timezone(timedelta(hours=8))

# ============================================================
# Configuration (env-overridable)
# ============================================================

QD_BRIDGE_AUTO_EXECUTE = os.getenv("HERMES_AUTO_EXECUTE", "false").lower() == "true"
QD_BRIDGE_EXCHANGE = os.getenv("HERMES_EXCHANGE", "binance")
QD_BRIDGE_MARKET_TYPE = os.getenv("HERMES_MARKET_TYPE", "swap")
QD_BRIDGE_POSITION_SIZE_PCT = float(os.getenv("HERMES_POSITION_SIZE_PCT", "0.1"))
QD_BRIDGE_NOTIFY_CHANNEL = os.getenv("HERMES_NOTIFY_CHANNEL", "webhook")
QD_BRIDGE_WEBHOOK_URL = os.getenv("HERMES_WEBHOOK_URL", "")


# ============================================================
# 1. EXCHANGE CLIENT MANAGEMENT
# ============================================================

def _get_exchange_client(exchange_id: str = "binance", market_type: str = "swap"):
    """Get a live trading client. Mirrors V2 hermes_integration._get_exchange_client."""
    try:
        from app.services.live_trading.factory import create_client
        from app.services.live_trading.contracts import normalize_order_market_type
        creds = _get_credentials_for_exchange(exchange_id)
        if not creds:
            logger.warning(f"No credentials for {exchange_id}")
            return None
        mt = normalize_order_market_type(market_type or "swap")
        return create_client(
            exchange_id=exchange_id, market_type=mt,
            api_key=creds.get("api_key", ""),
            secret_key=creds.get("secret_key", ""),
            passphrase=creds.get("passphrase", ""),
        )
    except Exception as e:
        logger.error(f"Exchange client creation failed: {e}")
        return None


def _get_credentials_for_exchange(exchange_id: str) -> Optional[dict]:
    """Get first active credential from DB."""
    try:
        from app.utils.db import get_db_connection
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "SELECT api_key, secret_key, passphrase FROM qd_credentials "
                "WHERE exchange_id = %s AND is_active = 1 LIMIT 1",
                (exchange_id,),
            )
            row = cur.fetchone()
            cur.close()
            return dict(row) if row else None
    except Exception as e:
        logger.warning(f"DB credential lookup: {e}")
    return None


def _normalize_symbol(symbol: str, exchange_id: str = "binance") -> str:
    """Convert Hermes symbol to exchange format (SYMBOL/USDT)."""
    sym = symbol.upper().replace("$", "").strip()
    if "/" in sym:
        return sym
    return f"{sym}/USDT"


def _get_account_balance(client, market_type: str = "swap") -> float:
    """Get available USDT balance."""
    try:
        if hasattr(client, "get_balance"):
            bi = client.get_balance()
            if isinstance(bi, dict):
                return float(bi.get("free", bi.get("available", 0)) or 0)
        if hasattr(client, "fetch_balance"):
            bal = client.fetch_balance()
            return float(bal.get("USDT", {}).get("free", 0) or 0)
    except Exception:
        pass
    return 1000.0


# ============================================================
# 2. EXECUTION BRIDGE
# ============================================================

def execute_signal(
    symbol: str, direction: str, score: int,
    stage: str = "", exchange_id: str = "binance",
    market_type: str = "swap", position_size_pct: float = 0.1,
    price: float = 0,
) -> Optional[dict]:
    """Execute a Hermes signal as a real trade through QD.
    
    Returns order result dict or None on failure.
    """
    if not QD_BRIDGE_AUTO_EXECUTE:
        logger.debug(f"Auto-execute disabled, skip: {symbol}")
        return {"ok": False, "error": "auto_execute_disabled"}

    try:
        from app.services.live_trading.execution import place_order_from_signal
        from app.services.live_trading.base import LiveTradingError

        client = _get_exchange_client(exchange_id, market_type)
        if not client:
            return {"ok": False, "error": "no_client"}

        norm = _normalize_symbol(symbol, exchange_id)
        balance = _get_account_balance(client, market_type)
        position_usd = balance * position_size_pct
        signal_type = "buy" if direction == "LONG" else "sell"

        result = place_order_from_signal(
            client=client, signal_type=signal_type,
            symbol=norm, amount=position_usd,
            market_type=market_type, quote_amount=position_usd,
        )
        logger.info(f"[QD-BRIDGE] EXEC {direction} {symbol} score={score} stage={stage} size=${position_usd:.0f}")
        return {
            "ok": True, "symbol": symbol, "direction": direction,
            "score": score, "price": price, "size_usd": position_usd,
            "order_result": str(result),
        }
    except LiveTradingError as e:
        logger.error(f"[QD-BRIDGE] Trading error {symbol}: {e}")
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(f"[QD-BRIDGE] Unexpected error {symbol}: {e}")
        return {"ok": False, "error": str(e)}


def execute_close(symbol: str, direction: str, reason: str = "",
                  exchange_id: str = "binance", market_type: str = "swap") -> Optional[dict]:
    """Execute a close order (opposite direction to existing position)."""
    close_dir = "SHORT" if direction == "LONG" else "LONG"
    return execute_signal(
        symbol=symbol, direction=close_dir, score=0,
        stage=f"Close: {reason}", exchange_id=exchange_id,
        market_type=market_type, position_size_pct=QD_BRIDGE_POSITION_SIZE_PCT,
    )


# ============================================================
# 3. NOTIFICATION BRIDGE
# ============================================================

def send_notification(signal: dict, channel: str = "webhook") -> bool:
    """Send Hermes signal through QD notification system."""
    try:
        from app.services.signal_notifier import send_notification as qd_notify
        config = {"channels": [channel], "targets": {channel: QD_BRIDGE_WEBHOOK_URL}}
        event = {
            "event": "hermes_signal",
            "strategy": "Hermes MerCu V3",
            "instrument": signal.get("symbol", ""),
            "signal": f"{signal.get('direction', '')} score={signal.get('score', 0)}",
            "stage": signal.get("stage", ""),
            "details": ", ".join(signal.get("signals", [])[:5]),
            "price": signal.get("price"),
            "timestamp": signal.get("timestamp", ""),
        }
        qd_notify(notification_config=config, event=event)
        return True
    except Exception as e:
        logger.warning(f"Notification failed: {e}")
        return False


def format_feishu_card(signals: List[dict]) -> dict:
    """Format Hermes signals as Feishu interactive card.
    Mirrors V2 hermes_format_feishu_card with V3 modules info."""
    if not signals:
        return {"msg_type": "text", "content": {"text": "📡 Hermes V3: 暂无信号"}}

    now = datetime.now(BJT).strftime("%m/%d %H:%M")
    lines = [f"📡 Hermes V3 | {now}", "━━━━━━━━━━━━"]

    for s in signals[:10]:
        emoji = "🟢" if s.get("direction") == "LONG" else "🔴"
        fire = "🔥" if abs(s.get("score", 0)) >= 8 else ""
        score = s.get("score", 0)
        dir_label = "做多" if s.get("direction") == "LONG" else "做空"
        price_str = f"${s.get('price')}" if s.get("price") else ""
        sig_str = ", ".join(s.get("signals", [])[:3]) if s.get("signals") else ""
        line = f"{emoji} {dir_label} {s.get('symbol','?'):8s} {score:+d}分 {fire} {price_str}"
        if sig_str:
            line += f"\n  ↳ {sig_str}"
        lines.append(line)

    lines.append("━━━━━━━━━━━━")
    return {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"content": f"📡 Hermes V3 | {now}", "tag": "plain_text"}},
            "elements": [{"tag": "div", "text": {"content": "\n".join(lines), "tag": "plain_text"}}],
        },
    }


# ============================================================
# 4. PORTFOLIO SYNC
# ============================================================

def sync_to_portfolio(positions: List[dict]):
    """Sync Hermes positions to QD portfolio tracking."""
    try:
        from app.services.portfolio_monitor import record_position_snapshot
        for pos in positions:
            record_position_snapshot(
                symbol=pos["symbol"], side=pos["direction"].lower(),
                quantity=pos.get("size_usd", 0), entry_price=pos.get("entry_price", 0),
                strategy_name="Hermes MerCu V3", exchange=QD_BRIDGE_EXCHANGE,
            )
        logger.debug(f"Synced {len(positions)} positions to portfolio")
    except Exception as e:
        logger.debug(f"Portfolio sync: {e}")


# ============================================================
# 5. BACKTEST DATA PREP
# ============================================================

def prepare_backtest_data(signals_history: List[dict]) -> List[dict]:
    """Convert Hermes signal history to QD backtest-compatible format."""
    bt = []
    for s in signals_history:
        bt.append({
            "timestamp": s.get("timestamp", s.get("_logged_at", "")),
            "symbol": s.get("symbol", ""),
            "signal_type": "buy" if s.get("direction") == "LONG" else "sell",
            "score": s.get("score", 0),
            "stage": s.get("stage", ""),
            "price": s.get("price"),
            "details": s.get("signals", []),
        })
    return bt


# ============================================================
# 6. DASHBOARD METRICS
# ============================================================

def get_dashboard_metrics() -> dict:
    """Get Hermes V3 metrics for QD dashboard."""
    try:
        from .position_manager import PositionManager
        from .signal_tracker import SignalTracker
        pm = PositionManager.get()
        st = SignalTracker.get()
        pm_metrics = pm.get_dashboard_metrics()
        tracker_stats = st.get_accuracy_stats()
        return {
            **pm_metrics,
            "tracker": tracker_stats,
            "module_version": "V3",
        }
    except Exception as e:
        return {"error": str(e), "module_version": "V3"}


# ============================================================
# 7. AUTO-EXECUTE SUBSCRIBER (EventBus → QD Execution)
# ============================================================

class QDBridgeAutoExecutor:
    """Listens to EventBus SIGNAL_FILTERED events and auto-executes trades.
    
    Runs as a subscriber to the EventBus, checking RiskEngine before executing.
    """
    
    def __init__(self):
        self._enabled = QD_BRIDGE_AUTO_EXECUTE
        self._subscribed = False
    
    def subscribe(self):
        """Attach to EventBus for auto-execution."""
        if self._subscribed:
            return
        try:
            from .event_bus import EventBus, EventType, Event
            bus = EventBus.get()
            bus.subscribe(EventType.SIGNAL_FILTERED, self._on_signal)
            self._subscribed = True
            logger.info(f"[QD-BRIDGE] Auto-executor subscribed (enabled={self._enabled})")
        except Exception as e:
            logger.error(f"[QD-BRIDGE] Failed to subscribe: {e}")
    
    def _on_signal(self, event):
        """Handle SIGNAL_FILTERED event."""
        if not self._enabled:
            return
        data = event.data
        symbol = data.get("symbol", "")
        direction = data.get("direction", "LONG")
        score = data.get("score", 0)
        stage = data.get("stage", "")
        price = data.get("price", 0)
        
        # Check RiskEngine
        try:
            from .risk_engine import RiskEngine
            risk = RiskEngine.get()
            verdict = risk.check_signal(data)
            if not verdict.passed:
                logger.info(f"[QD-BRIDGE] Risk blocked {symbol}: {verdict.reason}")
                return
        except Exception:
            pass
        
        # Execute
        execute_signal(
            symbol=symbol, direction=direction, score=score,
            stage=stage, exchange_id=QD_BRIDGE_EXCHANGE,
            market_type=QD_BRIDGE_MARKET_TYPE,
            position_size_pct=QD_BRIDGE_POSITION_SIZE_PCT,
            price=price,
        )
        
        # Notify
        send_notification(data, channel=QD_BRIDGE_NOTIFY_CHANNEL)


# ============================================================
# 8. MASTER INTEGRATION
# ============================================================

_qd_bridge_executor: Optional[QDBridgeAutoExecutor] = None


def integrate_with_quantdinger() -> dict:
    """Master integration: wire Hermes V3 into QuantDinger.
    
    Call once at startup. Returns integration status dict.
    """
    global _qd_bridge_executor
    
    result = {
        "execution": "disabled",
        "notification": "ready",
        "portfolio": "ready",
        "backtest": "ready",
        "module_version": "V3",
    }
    
    if not QD_BRIDGE_AUTO_EXECUTE:
        logger.info("[QD-BRIDGE] Auto-execution disabled (set HERMES_AUTO_EXECUTE=true to enable)")
        return result
    
    # Verify exchange connection
    client = _get_exchange_client(QD_BRIDGE_EXCHANGE, QD_BRIDGE_MARKET_TYPE)
    if not client:
        logger.warning(f"[QD-BRIDGE] Cannot connect to {QD_BRIDGE_EXCHANGE}")
        result["execution"] = "no_credentials"
        return result
    
    # Start auto-executor
    _qd_bridge_executor = QDBridgeAutoExecutor()
    _qd_bridge_executor.subscribe()
    
    result["execution"] = "active"
    result["exchange"] = QD_BRIDGE_EXCHANGE
    result["market_type"] = QD_BRIDGE_MARKET_TYPE
    result["notification"] = "active"
    
    logger.info(f"[QD-BRIDGE] Fully integrated: exchange={QD_BRIDGE_EXCHANGE} type={QD_BRIDGE_MARKET_TYPE}")
    return result


def get_bridge_status() -> dict:
    """Get current bridge status."""
    return {
        "auto_execute": QD_BRIDGE_AUTO_EXECUTE,
        "exchange": QD_BRIDGE_EXCHANGE,
        "market_type": QD_BRIDGE_MARKET_TYPE,
        "position_size_pct": QD_BRIDGE_POSITION_SIZE_PCT,
        "notify_channel": QD_BRIDGE_NOTIFY_CHANNEL,
        "executor_subscribed": _qd_bridge_executor._subscribed if _qd_bridge_executor else False,
        "module_version": "V3",
    }
