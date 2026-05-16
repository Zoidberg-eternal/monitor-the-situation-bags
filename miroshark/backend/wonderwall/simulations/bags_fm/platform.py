"""Bags.fm token launch simulation platform.

Server-side platform that handles token launches, trading via constant-product
AMM, creator fee accounting, and portfolio management.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from wonderwall.clock.clock import Clock
from wonderwall.simulations.base import BasePlatform
from wonderwall.simulations.bags_fm.amm import (
    get_token_price, get_market_cap, quote_buy, quote_sell,
)

logger = logging.getLogger(__name__)


class BagsFmPlatform(BasePlatform):
    """Token launch platform with bonding-curve AMM and 1% creator fees."""

    required_schemas = [
        "token.sql",
        "portfolio.sql",
        "holding.sql",
        "trade.sql",
        "comment.sql",
    ]

    core_schemas = ["user.sql", "trace.sql"]

    def __init__(
        self,
        db_path: str,
        channel: Any = None,
        sandbox_clock: Clock | None = None,
        start_time: datetime | None = None,
        initial_balance: float = 1000.0,
        initial_token_reserve: float = 1_000_000.0,
        initial_usd_reserve: float = 1000.0,
    ):
        self.initial_balance = initial_balance
        self.initial_token_reserve = initial_token_reserve
        self.initial_usd_reserve = initial_usd_reserve
        super().__init__(
            db_path=db_path,
            channel=channel,
            sandbox_clock=sandbox_clock,
            start_time=start_time,
        )

    async def sign_up(self, agent_id, user_message):
        result = await super().sign_up(agent_id, user_message)
        if result["success"]:
            self._execute_db_command(
                "INSERT INTO portfolio (user_id, balance) VALUES (?, ?)",
                (agent_id, self.initial_balance),
                commit=True,
            )
        return result

    async def launch_token(self, agent_id, token_message):
        """Launch a new token on the platform."""
        name, ticker, narrative = token_message
        current_time = self.get_current_time()
        try:
            self._execute_db_command(
                "INSERT INTO token (creator_id, name, ticker, narrative, "
                "token_reserve, usd_reserve, total_supply, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (agent_id, name, ticker.upper(), narrative,
                 self.initial_token_reserve, self.initial_usd_reserve,
                 self.initial_token_reserve, current_time),
                commit=True,
            )
            token_id = self.db_cursor.lastrowid
            price = get_token_price(
                self.initial_token_reserve, self.initial_usd_reserve)
            self._record_trace(
                agent_id, "launch_token",
                {"token_id": token_id, "name": name, "ticker": ticker,
                 "initial_price": price},
                current_time,
            )
            return {"success": True, "token_id": token_id,
                    "initial_price": round(price, 6)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def buy_token(self, agent_id, trade_message):
        """Buy tokens using USD."""
        token_id, amount_usd = trade_message
        amount_usd = float(amount_usd)
        current_time = self.get_current_time()

        self._execute_db_command(
            "SELECT balance FROM portfolio WHERE user_id = ?", (agent_id,))
        row = self.db_cursor.fetchone()
        if not row:
            return {"success": False, "error": "No portfolio found"}
        balance = row[0]
        if balance < amount_usd:
            return {"success": False, "error": "Insufficient balance",
                    "balance": balance, "requested": amount_usd}

        self._execute_db_command(
            "SELECT token_reserve, usd_reserve, ticker, creator_id "
            "FROM token WHERE token_id = ?", (token_id,))
        token = self.db_cursor.fetchone()
        if not token:
            return {"success": False, "error": "Token not found"}
        token_reserve, usd_reserve, ticker, creator_id = token

        pool_value = usd_reserve * 2
        max_trade = pool_value * 0.05
        if amount_usd > max_trade:
            amount_usd = max_trade

        trade = quote_buy(token_reserve, usd_reserve, amount_usd)

        self._execute_db_command(
            "UPDATE token SET token_reserve = ?, usd_reserve = ?, "
            "creator_fees_earned = creator_fees_earned + ? "
            "WHERE token_id = ?",
            (trade.new_token_reserve, trade.new_usd_reserve,
             trade.creator_fee, token_id),
            commit=True,
        )

        self._execute_db_command(
            "UPDATE portfolio SET balance = balance - ? WHERE user_id = ?",
            (amount_usd, agent_id),
            commit=True,
        )

        self._execute_db_command(
            "INSERT INTO holding (user_id, token_id, amount) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, token_id) "
            "DO UPDATE SET amount = amount + ?",
            (agent_id, token_id, trade.tokens_exchanged,
             trade.tokens_exchanged),
            commit=True,
        )

        self._execute_db_command(
            "INSERT INTO trade (user_id, token_id, side, tokens, price, "
            "cost, creator_fee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_id, token_id, "buy", trade.tokens_exchanged,
             trade.effective_price, amount_usd, trade.creator_fee,
             current_time),
            commit=True,
        )

        self._record_trace(
            agent_id, "buy_token",
            {"token_id": token_id, "ticker": ticker,
             "tokens": trade.tokens_exchanged,
             "price": trade.effective_price, "cost": amount_usd,
             "creator_fee": trade.creator_fee},
            current_time,
        )

        return {
            "success": True,
            "tokens_received": round(trade.tokens_exchanged, 4),
            "effective_price": round(trade.effective_price, 6),
            "total_cost": round(amount_usd, 2),
            "creator_fee": round(trade.creator_fee, 4),
        }

    async def sell_token(self, agent_id, trade_message):
        """Sell tokens back to the pool."""
        token_id, num_tokens = trade_message
        num_tokens = float(num_tokens)
        current_time = self.get_current_time()

        self._execute_db_command(
            "SELECT amount FROM holding "
            "WHERE user_id = ? AND token_id = ?",
            (agent_id, token_id))
        row = self.db_cursor.fetchone()
        if not row or row[0] < num_tokens:
            return {"success": False, "error": "Insufficient tokens",
                    "held": row[0] if row else 0}

        self._execute_db_command(
            "SELECT token_reserve, usd_reserve, ticker, creator_id "
            "FROM token WHERE token_id = ?", (token_id,))
        token = self.db_cursor.fetchone()
        if not token:
            return {"success": False, "error": "Token not found"}
        token_reserve, usd_reserve, ticker, creator_id = token

        trade = quote_sell(token_reserve, usd_reserve, num_tokens)
        usd_received = -trade.total_cost

        self._execute_db_command(
            "UPDATE token SET token_reserve = ?, usd_reserve = ?, "
            "creator_fees_earned = creator_fees_earned + ? "
            "WHERE token_id = ?",
            (trade.new_token_reserve, trade.new_usd_reserve,
             trade.creator_fee, token_id),
            commit=True,
        )

        self._execute_db_command(
            "UPDATE portfolio SET balance = balance + ? WHERE user_id = ?",
            (usd_received, agent_id),
            commit=True,
        )

        self._execute_db_command(
            "UPDATE holding SET amount = amount - ? "
            "WHERE user_id = ? AND token_id = ?",
            (num_tokens, agent_id, token_id),
            commit=True,
        )

        self._execute_db_command(
            "INSERT INTO trade (user_id, token_id, side, tokens, price, "
            "cost, creator_fee, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_id, token_id, "sell", num_tokens,
             trade.effective_price, -usd_received, trade.creator_fee,
             current_time),
            commit=True,
        )

        self._record_trace(
            agent_id, "sell_token",
            {"token_id": token_id, "ticker": ticker,
             "tokens": num_tokens, "price": trade.effective_price,
             "usd_received": usd_received,
             "creator_fee": trade.creator_fee},
            current_time,
        )

        return {
            "success": True,
            "usd_received": round(usd_received, 2),
            "effective_price": round(trade.effective_price, 6),
            "creator_fee": round(trade.creator_fee, 4),
        }

    async def browse_tokens(self, agent_id):
        """Browse launched tokens with current prices and market caps."""
        self._execute_db_command(
            "SELECT token_id, name, ticker, narrative, token_reserve, "
            "usd_reserve, total_supply, creator_fees_earned, created_at "
            "FROM token ORDER BY token_id DESC LIMIT 20"
        )
        rows = self.db_cursor.fetchall()
        tokens = []
        for row in rows:
            (tid, name, ticker, narrative, tr, ur, supply,
             fees, created) = row
            price = get_token_price(tr, ur)
            mcap = get_market_cap(tr, ur, supply)
            self._execute_db_command(
                "SELECT COUNT(*) FROM trade WHERE token_id = ?", (tid,))
            trade_count = self.db_cursor.fetchone()[0]
            self._execute_db_command(
                "SELECT COALESCE(SUM(ABS(cost)), 0) FROM trade "
                "WHERE token_id = ?", (tid,))
            volume = self.db_cursor.fetchone()[0]
            tokens.append({
                "token_id": tid,
                "name": name,
                "ticker": ticker,
                "narrative": narrative[:100],
                "price": round(price, 6),
                "market_cap": round(mcap, 2),
                "volume": round(volume, 2),
                "num_trades": trade_count,
                "creator_fees": round(fees, 4),
                "created_at": created,
            })
        return {"success": True, "tokens": tokens}

    async def view_portfolio(self, agent_id):
        """View agent's balance and token holdings."""
        self._execute_db_command(
            "SELECT balance FROM portfolio WHERE user_id = ?", (agent_id,))
        row = self.db_cursor.fetchone()
        balance = row[0] if row else 0

        self._execute_db_command(
            "SELECT h.token_id, h.amount, t.name, t.ticker, "
            "t.token_reserve, t.usd_reserve "
            "FROM holding h JOIN token t ON h.token_id = t.token_id "
            "WHERE h.user_id = ? AND h.amount > 0",
            (agent_id,))
        rows = self.db_cursor.fetchall()
        holdings = []
        for row in rows:
            tid, amount, name, ticker, tr, ur = row
            price = get_token_price(tr, ur)
            holdings.append({
                "token_id": tid,
                "name": name,
                "ticker": ticker,
                "amount": round(amount, 4),
                "current_price": round(price, 6),
                "current_value": round(amount * price, 2),
            })

        return {
            "success": True,
            "balance": round(balance, 2),
            "holdings": holdings,
        }

    async def comment_on_token(self, agent_id, comment_message):
        """Post a comment on a token."""
        token_id, content = comment_message
        current_time = self.get_current_time()
        try:
            self._execute_db_command(
                "INSERT INTO token_comment (token_id, user_id, content, "
                "created_at) VALUES (?, ?, ?, ?)",
                (token_id, agent_id, content, current_time),
                commit=True,
            )
            self._record_trace(
                agent_id, "comment_on_token",
                {"token_id": token_id, "content": content},
                current_time,
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_fee_report(self, agent_id):
        """Get fee economics report for all tokens."""
        self._execute_db_command(
            "SELECT token_id, name, ticker, creator_fees_earned, "
            "creator_id FROM token ORDER BY creator_fees_earned DESC"
        )
        rows = self.db_cursor.fetchall()
        report = []
        total_fees = 0.0
        for row in rows:
            tid, name, ticker, fees, creator = row
            total_fees += fees
            report.append({
                "token_id": tid,
                "ticker": ticker,
                "creator_fees_earned": round(fees, 4),
                "creator_id": creator,
            })
        return {
            "success": True,
            "total_platform_fees": round(total_fees, 4),
            "tokens": report,
        }

    def tick_clock(self):
        self.sandbox_clock.time_step += 1
