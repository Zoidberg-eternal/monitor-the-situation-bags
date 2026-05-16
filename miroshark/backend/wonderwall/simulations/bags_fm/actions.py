"""Bags.fm agent actions — the tools the LLM can call."""
from __future__ import annotations

from wonderwall.simulations.base import BaseAction


class BagsFmAction(BaseAction):
    """Actions available to agents in a Bags.fm token trading simulation."""

    async def browse_tokens(self):
        """Browse launched tokens with current prices and market data.

        Returns:
            dict: A dictionary with 'success' and 'tokens' containing a list
                of launched tokens with prices, market caps, and volume.

            Example:
            {
                "success": True,
                "tokens": [
                    {
                        "token_id": 1,
                        "name": "DogeCoin2",
                        "ticker": "DOGE2",
                        "price": 0.001,
                        "market_cap": 1000.0,
                        "volume": 500.0,
                        "num_trades": 15
                    }
                ]
            }
        """
        return await self.perform_action(None, "browse_tokens")

    async def buy_token(self, token_id: int, amount_usd: float):
        """Buy tokens by spending USD. A 1% creator fee is deducted.

        The price is determined by a bonding curve AMM — buying pushes the
        price up. The creator of the token earns 1% of every trade.

        Args:
            token_id (int): The ID of the token to buy.
            amount_usd (float): How many USD to spend.

        Returns:
            dict: Contains 'tokens_received', 'effective_price', 'total_cost',
                'creator_fee'.

            Example:
            {
                "success": True,
                "tokens_received": 9500.0,
                "effective_price": 0.00105,
                "total_cost": 10.0,
                "creator_fee": 0.10
            }
        """
        return await self.perform_action(
            (token_id, amount_usd), "buy_token"
        )

    async def sell_token(self, token_id: int, num_tokens: float):
        """Sell tokens back to the bonding curve for USD.

        Use this when:
        - The token price has pumped and you want to take profit
        - You've lost conviction in the token's narrative
        - Social sentiment has turned negative
        - You want to rotate into a different token

        A 1% creator fee is deducted from the sale proceeds.

        Args:
            token_id (int): The token to sell.
            num_tokens (float): Number of tokens to sell.

        Returns:
            dict: Contains 'usd_received', 'effective_price', 'creator_fee'.
        """
        return await self.perform_action(
            (token_id, num_tokens), "sell_token"
        )

    async def view_portfolio(self):
        """View your current cash balance and token holdings.

        Returns:
            dict: Contains 'balance' (USD) and 'holdings' (list of tokens).

            Example:
            {
                "success": True,
                "balance": 900.0,
                "holdings": [
                    {
                        "token_id": 1,
                        "name": "DogeCoin2",
                        "ticker": "DOGE2",
                        "amount": 9500.0,
                        "current_price": 0.00112,
                        "current_value": 10.64
                    }
                ]
            }
        """
        return await self.perform_action(None, "view_portfolio")

    async def comment_on_token(self, token_id: int, content: str):
        """Post a comment on a token's page.

        Args:
            token_id (int): The token to comment on.
            content (str): Your comment text.
        """
        return await self.perform_action(
            (token_id, content), "comment_on_token"
        )
