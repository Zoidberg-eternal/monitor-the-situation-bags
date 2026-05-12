"""
Risk scoring engine for Bags.fm token launches.

Computes a composite risk score (0-100) from launch velocity,
fee accumulation rate, liquidity depth, and price volatility.
Higher score = higher risk / more notable activity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "launch_velocity": 0.30,
    "fee_accumulation": 0.25,
    "liquidity_depth": 0.25,
    "volatility": 0.20,
}

THRESHOLDS = {
    "launch_velocity_ratio": 5.0,
    "fee_accumulation_high": 1_000_000_000,  # 1 SOL in lamports
    "liquidity_depth_low": 0.10,
    "price_volatility_pct": 0.50,
}

DEFAULT_ALERT_THRESHOLD = 60


@dataclass
class TokenRisk:
    token_mint: str
    symbol: str
    launch_velocity_score: float
    fee_score: float
    liquidity_score: float
    volatility_score: float
    composite: float
    alerts: list[str] = field(default_factory=list)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def score_launch_velocity(
    volume_24h: float,
    avg_launch_volume: float,
    threshold: float,
) -> float:
    """Score how fast volume ramps post-launch relative to average launches."""
    if avg_launch_volume <= 0 or threshold <= 0:
        return 0.0
    ratio = volume_24h / avg_launch_volume
    return _clamp(ratio / threshold * 100)


def score_fee_accumulation(
    lifetime_fees_lamports: float,
    threshold: float,
) -> float:
    """Score creator earnings trajectory. Higher fees = more activity."""
    if threshold <= 0:
        return 0.0
    return _clamp(lifetime_fees_lamports / threshold * 100)


def score_liquidity_depth(
    pool_liquidity: float,
    volume_24h: float,
    threshold: float,
) -> float:
    """Score pool liquidity relative to volume. Low ratio = thin liquidity = higher risk."""
    if volume_24h <= 0 or threshold <= 0:
        return 0.0
    ratio = pool_liquidity / volume_24h if volume_24h > 0 else 1.0
    if ratio >= 1.0:
        return 0.0
    inverse_score = (1.0 - ratio) / (1.0 - threshold)
    return _clamp(inverse_score * 100)


def score_price_volatility(
    price_change_pct: float,
    threshold: float,
) -> float:
    """Score short-term price swings."""
    if threshold <= 0:
        return 0.0
    return _clamp(abs(price_change_pct) / threshold * 100)


def compute_token_risk(
    token_mint: str,
    symbol: str,
    volume_24h: float = 0.0,
    avg_launch_volume: float = 1.0,
    lifetime_fees_lamports: float = 0.0,
    pool_liquidity: float = 0.0,
    price_change_pct: float = 0.0,
    weights: dict[str, float] | None = None,
    thresholds: dict[str, float] | None = None,
    alert_threshold: float = DEFAULT_ALERT_THRESHOLD,
) -> TokenRisk:
    """Compute composite risk score for a Bags.fm token.

    Returns:
        TokenRisk with component scores and composite.
    """
    w = weights or DEFAULT_WEIGHTS
    t = thresholds or THRESHOLDS

    lv = score_launch_velocity(volume_24h, avg_launch_volume, t["launch_velocity_ratio"])
    fs = score_fee_accumulation(lifetime_fees_lamports, t["fee_accumulation_high"])
    ld = score_liquidity_depth(pool_liquidity, volume_24h, t["liquidity_depth_low"])
    vs = score_price_volatility(price_change_pct, t["price_volatility_pct"])

    composite = _clamp(
        lv * w["launch_velocity"]
        + fs * w["fee_accumulation"]
        + ld * w["liquidity_depth"]
        + vs * w["volatility"]
    )

    alerts: list[str] = []
    if composite >= alert_threshold:
        alerts.append(
            f"[{symbol}] HIGH RISK ({composite:.1f}/100): "
            f"velocity={lv:.0f}, fees={fs:.0f}, liquidity={ld:.0f}, volatility={vs:.0f}"
        )
    if lv >= 80:
        alerts.append(f"[{symbol}] Volume spike post-launch: {volume_24h:.0f} vs avg {avg_launch_volume:.0f}")
    if ld >= 80:
        alerts.append(f"[{symbol}] Thin liquidity: pool={pool_liquidity:.0f} vs volume={volume_24h:.0f}")
    if vs >= 80:
        alerts.append(f"[{symbol}] High volatility: {price_change_pct:+.1f}%")

    return TokenRisk(
        token_mint=token_mint,
        symbol=symbol,
        launch_velocity_score=lv,
        fee_score=fs,
        liquidity_score=ld,
        volatility_score=vs,
        composite=composite,
        alerts=alerts,
    )
