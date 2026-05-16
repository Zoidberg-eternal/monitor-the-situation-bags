"""Constant-product AMM for Bags.fm token trading.

Bags.fm uses a bonding curve where each token has a single liquidity pool
against a base currency (USD). Unlike prediction markets with two outcomes,
this is a simple token/USD pool with a 1% creator fee on every trade.

The AMM uses x * y = k where:
- x = token reserve
- y = USD reserve
- k = constant product

Token price = usd_reserve / token_reserve
"""
from __future__ import annotations

from dataclasses import dataclass


CREATOR_FEE_RATE = 0.01


@dataclass
class TradeResult:
    tokens_exchanged: float
    effective_price: float
    total_cost: float
    creator_fee: float
    new_token_reserve: float
    new_usd_reserve: float


def get_token_price(token_reserve: float, usd_reserve: float) -> float:
    if token_reserve == 0:
        return 0.0
    return usd_reserve / token_reserve


def get_market_cap(token_reserve: float, usd_reserve: float,
                   total_supply: float) -> float:
    price = get_token_price(token_reserve, usd_reserve)
    return price * total_supply


def quote_buy(
    token_reserve: float,
    usd_reserve: float,
    amount_usd: float,
) -> TradeResult:
    """Buy tokens by spending amount_usd. 1% creator fee deducted first."""
    if amount_usd <= 0:
        raise ValueError("amount_usd must be positive")

    creator_fee = amount_usd * CREATOR_FEE_RATE
    net_usd = amount_usd - creator_fee

    k = token_reserve * usd_reserve
    new_usd_reserve = usd_reserve + net_usd
    new_token_reserve = k / new_usd_reserve
    tokens_out = token_reserve - new_token_reserve

    effective_price = amount_usd / tokens_out if tokens_out > 0 else 0

    return TradeResult(
        tokens_exchanged=tokens_out,
        effective_price=effective_price,
        total_cost=amount_usd,
        creator_fee=creator_fee,
        new_token_reserve=new_token_reserve,
        new_usd_reserve=new_usd_reserve,
    )


def quote_sell(
    token_reserve: float,
    usd_reserve: float,
    num_tokens: float,
) -> TradeResult:
    """Sell tokens back to the pool. 1% creator fee deducted from proceeds."""
    if num_tokens <= 0:
        raise ValueError("num_tokens must be positive")

    k = token_reserve * usd_reserve
    new_token_reserve = token_reserve + num_tokens
    new_usd_reserve = k / new_token_reserve
    gross_usd_out = usd_reserve - new_usd_reserve

    creator_fee = gross_usd_out * CREATOR_FEE_RATE
    net_usd_out = gross_usd_out - creator_fee

    effective_price = net_usd_out / num_tokens if num_tokens > 0 else 0

    return TradeResult(
        tokens_exchanged=num_tokens,
        effective_price=effective_price,
        total_cost=-net_usd_out,
        creator_fee=creator_fee,
        new_token_reserve=new_token_reserve,
        new_usd_reserve=new_usd_reserve,
    )
