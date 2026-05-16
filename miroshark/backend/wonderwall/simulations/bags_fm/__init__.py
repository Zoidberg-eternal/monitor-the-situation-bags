"""Bags.fm token launch simulation for OASIS.

Usage::

    from wonderwall.simulations.bags_fm import bags_fm_simulation

    env = oasis.make(
        agent_graph=agent_graph,
        simulation=bags_fm_simulation,
        database_path="./data/bags_fm.db",
    )
"""
from wonderwall.simulations.base import SimulationConfig
from wonderwall.simulations.bags_fm.actions import BagsFmAction
from wonderwall.simulations.bags_fm.environment import BagsFmEnvironment
from wonderwall.simulations.bags_fm.platform import BagsFmPlatform
from wonderwall.simulations.bags_fm.prompts import BagsFmPromptBuilder

bags_fm_simulation = SimulationConfig(
    name="bags_fm",
    platform_cls=BagsFmPlatform,
    action_cls=BagsFmAction,
    environment_cls=BagsFmEnvironment,
    prompt_builder=BagsFmPromptBuilder(),
    default_actions=[
        "buy_token", "sell_token",
        "do_nothing",
    ],
    platform_kwargs={
        "initial_balance": 1000.0,
        "initial_token_reserve": 1_000_000.0,
        "initial_usd_reserve": 1000.0,
    },
)

__all__ = [
    "bags_fm_simulation",
    "BagsFmPlatform",
    "BagsFmAction",
    "BagsFmEnvironment",
    "BagsFmPromptBuilder",
]
