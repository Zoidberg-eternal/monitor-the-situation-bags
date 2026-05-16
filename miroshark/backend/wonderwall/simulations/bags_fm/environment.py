"""Bags.fm agent environment — what the agent sees each turn."""
from __future__ import annotations

from wonderwall.simulations.base import BaseEnvironment


class BagsFmEnvironment(BaseEnvironment):
    """Converts Bags.fm state into the text prompt the agent observes."""

    async def to_text_prompt(self) -> str:
        portfolio = await self.action.view_portfolio()
        tokens = await self.action.browse_tokens()

        parts = []

        if portfolio.get("success"):
            balance = portfolio['balance']
            parts.append(f"YOUR PORTFOLIO:\n  Cash: ${balance:.2f}")

            holdings = portfolio.get("holdings", [])
            if holdings:
                total_value = 0
                parts.append("  Token holdings:")
                for h in holdings:
                    value = h['current_value']
                    total_value += value
                    parts.append(
                        f"    - {h['ticker']} (#{h['token_id']}): "
                        f"{h['amount']:.1f} tokens "
                        f"@ ${h['current_price']:.6f} "
                        f"(value: ${value:.2f})"
                    )
                portfolio_value = balance + total_value
                parts.append(f"  Total portfolio value: ${portfolio_value:.2f}")
            else:
                parts.append("  No token holdings.")

        if tokens.get("success") and tokens.get("tokens"):
            parts.append("\nLAUNCHED TOKENS:")
            for t in tokens["tokens"]:
                narrative_preview = t.get("narrative", "")
                if len(narrative_preview) > 60:
                    narrative_preview = narrative_preview[:60] + "..."

                parts.append(
                    f"  #{t['token_id']}: ${t['ticker']} ({t['name']}) "
                    f"— price: ${t['price']:.6f}, "
                    f"mcap: ${t['market_cap']:.2f}, "
                    f"vol: ${t['volume']:.2f} "
                    f"({t['num_trades']} trades)"
                )
                if narrative_preview:
                    parts.append(f"    Narrative: {narrative_preview}")
                if t.get("creator_fees", 0) > 0:
                    parts.append(
                        f"    Creator fees earned: ${t['creator_fees']:.4f}")
        else:
            parts.append("\nNo tokens launched yet.")

        if self.extra_observation_context:
            parts.append(
                f"\nSOCIAL MEDIA CONTEXT:\n{self.extra_observation_context}")

        parts.append(
            "\nDecide: buy_token, sell_token, or do_nothing."
            "\nConsider the social media context above — it tells you what "
            "people are discussing on Twitter and Reddit. Viral social "
            "sentiment can drive token prices. If a token's narrative aligns "
            "with trending social topics, that's a buying signal."
        )

        return "\n".join(parts)
