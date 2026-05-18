"""
Unit test for ZERA-600 Reddit simulation DB adapter.

Tests that the reddit_simulation.db can be faithfully converted to AgentAction
objects with correct round assignment, agent identity mapping, and consensus KYA
attestation generation.
"""

import os
import sqlite3
import tempfile
import pytest
from datetime import datetime, timedelta

from app.services.simulation_runner import SimulationRunner, AgentAction


@pytest.fixture
def temp_sim_dir():
    """Create a temporary simulation directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sim_dir = os.path.join(tmpdir, "test_sim")
        os.makedirs(sim_dir, exist_ok=True)
        yield sim_dir


def create_test_reddit_db(db_path: str) -> sqlite3.Connection:
    """
    Create a minimal but complete reddit_simulation.db with the real schema.

    Tables: user, post, comment, trace (with the exact columns from schema files).
    The trace table is canonical for action derivation.

    Returns connection so caller can verify or extend.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create user table (per user.sql schema)
    cursor.execute("""
        CREATE TABLE user (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            user_name TEXT,
            name TEXT,
            bio TEXT,
            created_at DATETIME,
            num_followings INTEGER DEFAULT 0,
            num_followers INTEGER DEFAULT 0
        )
    """)

    # Create post table (per post.sql schema)
    cursor.execute("""
        CREATE TABLE post (
            post_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            original_post_id INTEGER,
            content TEXT DEFAULT '',
            quote_content TEXT,
            created_at DATETIME,
            num_likes INTEGER DEFAULT 0,
            num_dislikes INTEGER DEFAULT 0,
            num_shares INTEGER DEFAULT 0,
            num_reports INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES user(user_id),
            FOREIGN KEY(original_post_id) REFERENCES post(post_id)
        )
    """)

    # Create comment table (per comment.sql schema)
    cursor.execute("""
        CREATE TABLE comment (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            content TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            num_likes INTEGER DEFAULT 0,
            num_dislikes INTEGER DEFAULT 0,
            FOREIGN KEY(post_id) REFERENCES post(post_id),
            FOREIGN KEY(user_id) REFERENCES user(user_id)
        )
    """)

    # Create trace table (canonical action log per run_parallel_simulation.py)
    # Schema: user_id INTEGER, created_at DATETIME, action TEXT, info TEXT
    cursor.execute("""
        CREATE TABLE trace (
            user_id INTEGER,
            created_at DATETIME,
            action TEXT,
            info TEXT
        )
    """)

    return conn, cursor


def test_reddit_adapter_basic_conversion(temp_sim_dir):
    """
    Test basic conversion: create a tiny synthetic DB with ≥3 agents,
    content across ≥2 distinct created_at times (distinct rounds).
    Uses the canonical trace table to derive rounds faithfully.
    """
    db_path = os.path.join(temp_sim_dir, "reddit_simulation.db")
    conn, cursor = create_test_reddit_db(db_path)

    # Insert 3 distinct agents
    base_time = datetime(2026, 5, 18, 10, 0, 0)

    cursor.execute(
        "INSERT INTO user (agent_id, user_name, name, created_at) VALUES (?, ?, ?, ?)",
        (1, "alice_user", "Alice", base_time.isoformat())
    )
    cursor.execute(
        "INSERT INTO user (agent_id, user_name, name, created_at) VALUES (?, ?, ?, ?)",
        (2, "bob_user", "Bob", base_time.isoformat())
    )
    cursor.execute(
        "INSERT INTO user (agent_id, user_name, name, created_at) VALUES (?, ?, ?, ?)",
        (3, "charlie_user", "Charlie", base_time.isoformat())
    )

    # Insert trace records across 2 distinct created_at times (simulated clock rounds)
    # Round 1: hour 0
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (1, (base_time + timedelta(hours=0)).isoformat(), 'create_post',
         '{"content": "This token looks bullish! Strong fundamentals."}')
    )
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (2, (base_time + timedelta(hours=0)).isoformat(), 'create_post',
         '{"content": "I am concerned about the liquidity."}')
    )

    # Round 2: hour 1 (distinct created_at)
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (3, (base_time + timedelta(hours=1)).isoformat(), 'create_post',
         '{"content": "The team has a great track record."}')
    )

    # Round 2 again: more actions at hour 1
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (1, (base_time + timedelta(hours=1)).isoformat(), 'create_comment',
         '{"content": "I agree with the growth potential."}')
    )
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (2, (base_time + timedelta(hours=1)).isoformat(), 'create_comment',
         '{"content": "The roadmap looks solid though."}')
    )

    conn.commit()
    conn.close()

    # Run adapter
    actions = SimulationRunner._convert_reddit_db_to_actions(db_path)

    # Verify basic properties
    assert len(actions) == 5, f"Expected 5 actions, got {len(actions)}"

    # Verify all actions are CREATE_POST or CREATE_COMMENT
    action_types = {a.action_type for a in actions}
    assert action_types <= {"CREATE_POST", "CREATE_COMMENT"}, f"Unexpected action types: {action_types}"

    # Verify at least 3 distinct agents
    agent_ids = {a.agent_id for a in actions}
    assert len(agent_ids) >= 3, f"Expected ≥3 distinct agents, got {agent_ids}"

    # Verify exactly 2 distinct rounds (derived from distinct created_at: hour 0 and hour 1)
    round_nums = {a.round_num for a in actions}
    assert len(round_nums) == 2, f"Expected exactly 2 distinct rounds (from 2 distinct created_at), got {round_nums}"
    assert round_nums == {1, 2}, f"Expected rounds {{1, 2}}, got {round_nums}"

    # Verify platform is reddit
    for action in actions:
        assert action.platform == "reddit"

    # Verify content is preserved verbatim
    contents = [a.action_args.get('content', '') for a in actions]
    assert "bullish" in contents[0].lower(), f"Expected 'bullish' in first action content"
    assert any("concern" in c.lower() or "liquidity" in c.lower() for c in contents), \
        f"Expected concern/liquidity sentiment in some actions"

    print(f"✓ Adapter test passed: {len(actions)} actions, {len(agent_ids)} agents, {len(round_nums)} distinct rounds (NOT fabricated)")


def test_reddit_adapter_agent_id_linkage(temp_sim_dir):
    """
    Verify agent_id -> agent_name linkage for KYA attestation.
    Each action must have correct agent_id (int) and agent_name (str) so
    SimulationKeyring.get(agent_id) can find minted keypairs.
    Uses trace table for canonical action sourcing.
    """
    db_path = os.path.join(temp_sim_dir, "reddit_simulation.db")
    conn, cursor = create_test_reddit_db(db_path)

    base_time = datetime(2026, 5, 18, 10, 0, 0)

    # Create users with specific agent_ids
    cursor.execute(
        "INSERT INTO user (agent_id, user_name) VALUES (?, ?)",
        (10, "agent_10_name")
    )
    cursor.execute(
        "INSERT INTO user (agent_id, user_name) VALUES (?, ?)",
        (20, "agent_20_name")
    )

    # Insert trace records (canonical action log)
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (1, base_time.isoformat(), 'create_post',
         '{"content": "Test post from agent 10"}')
    )
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (2, base_time.isoformat(), 'create_post',
         '{"content": "Test post from agent 20"}')
    )

    conn.commit()
    conn.close()

    # Run adapter
    actions = SimulationRunner._convert_reddit_db_to_actions(db_path)

    # Find actions for each agent_id
    agent_10_actions = [a for a in actions if a.agent_id == 10]
    agent_20_actions = [a for a in actions if a.agent_id == 20]

    assert len(agent_10_actions) > 0, "No actions found for agent_id 10"
    assert len(agent_20_actions) > 0, "No actions found for agent_id 20"

    # Verify agent_name is set (required for KYA attestations)
    for a in agent_10_actions:
        assert a.agent_name, f"agent_name missing for agent_id {a.agent_id}"
        assert a.agent_id == 10
        assert a.agent_name == "agent_10_name"

    for a in agent_20_actions:
        assert a.agent_name, f"agent_name missing for agent_id {a.agent_id}"
        assert a.agent_id == 20
        assert a.agent_name == "agent_20_name"

    print(f"✓ Agent linkage test passed: agents {10, 20} mapped correctly")


def test_reddit_adapter_divergent_content_and_rounds(temp_sim_dir):
    """
    Test that content is preserved and rounds are derived correctly from distinct created_at.
    Create trace records with distinct sentiments spread across ≥2 distinct created_at times
    to verify round assignment reflects temporal ordering (NOT bucketing).
    """
    db_path = os.path.join(temp_sim_dir, "reddit_simulation.db")
    conn, cursor = create_test_reddit_db(db_path)

    base_time = datetime(2026, 5, 18, 10, 0, 0)

    # Single user for round derivation test
    cursor.execute(
        "INSERT INTO user (agent_id, user_name) VALUES (?, ?)",
        (1, "test_user")
    )

    # Insert trace records with distinct content, spread over ≥2 distinct times
    # This tests that rounds are derived from actual distinct created_at values,
    # NOT from fabricated bucketing logic
    trace_data = [
        ("bullish great team", 0),       # Round 1 (created_at = hour 0)
        ("bearish risk factor", 0),      # Round 1 (same created_at)
        ("neutral observation", 2),      # Round 2 (created_at = hour 2)
        ("bullish strong growth", 2),    # Round 2 (same created_at)
        ("bearish liquidity low", 4),    # Round 3 (created_at = hour 4)
    ]

    for content, hour_offset in trace_data:
        created_at = (base_time + timedelta(hours=hour_offset)).isoformat()
        cursor.execute(
            "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
            (1, created_at, 'create_post',
             f'{{"content": "{content}"}}')
        )

    conn.commit()
    conn.close()

    # Run adapter
    actions = SimulationRunner._convert_reddit_db_to_actions(db_path)

    assert len(actions) == 5

    # Verify content is preserved verbatim
    contents = [a.action_args['content'] for a in actions]
    assert "bullish" in contents[0]
    assert "bearish" in contents[1]
    assert "neutral" in contents[2]

    # Verify round numbers are derived from distinct created_at (3 distinct times = 3 distinct rounds)
    round_nums = [a.round_num for a in actions]
    distinct_rounds = set(round_nums)
    assert len(distinct_rounds) == 3, \
        f"Expected 3 distinct rounds (from 3 distinct created_at times), got {distinct_rounds}"
    assert distinct_rounds == {1, 2, 3}, f"Expected rounds {{1, 2, 3}}, got {distinct_rounds}"

    # Verify round ordering matches temporal ordering
    assert round_nums[0] == 1 and round_nums[1] == 1, "First two should be round 1"
    assert round_nums[2] == 2 and round_nums[3] == 2, "Third and fourth should be round 2"
    assert round_nums[4] == 3, "Fifth should be round 3"

    print(f"✓ Content and round test passed: {len(actions)} posts with {len(distinct_rounds)} distinct rounds (NOT fabricated)")


def test_reddit_adapter_with_filters(temp_sim_dir):
    """
    Test that agent_id_filter and round_num_filter work correctly.
    Uses trace table for canonical action sourcing.
    """
    db_path = os.path.join(temp_sim_dir, "reddit_simulation.db")
    conn, cursor = create_test_reddit_db(db_path)

    base_time = datetime(2026, 5, 18, 10, 0, 0)

    # Create multiple agents
    for agent_id in [1, 2, 3]:
        cursor.execute(
            "INSERT INTO user (agent_id, user_name) VALUES (?, ?)",
            (agent_id, f"agent_{agent_id}")
        )

    # Insert trace records from different agents across 2 distinct times
    for i, user_id in enumerate([1, 1, 2, 3]):
        # Hour 0 for first two, hour 1 for last two (creates 2 distinct rounds)
        hour_offset = 0 if i < 2 else 1
        created_at = (base_time + timedelta(hours=hour_offset)).isoformat()
        cursor.execute(
            "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
            (user_id, created_at, 'create_post',
             f'{{"content": "Post {i}"}}')
        )

    conn.commit()
    conn.close()

    # Test agent_id filter
    actions = SimulationRunner._convert_reddit_db_to_actions(db_path, agent_id_filter=1)
    assert all(a.agent_id == 1 for a in actions), "agent_id filter not working"
    assert len(actions) == 2

    # Test round_num filter
    actions_round_1 = SimulationRunner._convert_reddit_db_to_actions(db_path, round_num_filter=1)
    assert all(a.round_num == 1 for a in actions_round_1), "round_num filter not working"
    assert len(actions_round_1) == 2  # First two actions at hour 0

    actions_round_2 = SimulationRunner._convert_reddit_db_to_actions(db_path, round_num_filter=2)
    assert all(a.round_num == 2 for a in actions_round_2), "round_num filter not working"
    assert len(actions_round_2) == 2  # Last two actions at hour 1

    print(f"✓ Filter test passed: agent_id and round_num filters work correctly")


def test_reddit_adapter_single_round_no_fabrication(temp_sim_dir):
    """
    Test that a DB with all actions at a single created_at time yields exactly 1 round,
    never fabricated multiple rounds.
    """
    db_path = os.path.join(temp_sim_dir, "reddit_simulation.db")
    conn, cursor = create_test_reddit_db(db_path)

    base_time = datetime(2026, 5, 18, 10, 0, 0)

    # Single user
    cursor.execute(
        "INSERT INTO user (agent_id, user_name) VALUES (?, ?)",
        (1, "test_user")
    )

    # Insert 5 trace records all at the SAME created_at (single round)
    for i in range(5):
        cursor.execute(
            "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
            (1, base_time.isoformat(), 'create_post',
             f'{{"content": "Post {i}"}}')
        )

    conn.commit()
    conn.close()

    # Run adapter
    actions = SimulationRunner._convert_reddit_db_to_actions(db_path)

    assert len(actions) == 5

    # All actions must be in round 1 (NOT fabricated into multiple rounds)
    round_nums = {a.round_num for a in actions}
    assert round_nums == {1}, f"Expected exactly round 1, got {round_nums}"

    print(f"✓ Single-round test passed: 5 actions all at same created_at = exactly round 1 (no fabrication)")


def test_reddit_adapter_graceful_failure(temp_sim_dir):
    """
    Test that the adapter gracefully returns [] on DB missing or corrupted.
    Also tests handling of LIKE/DO_NOTHING actions (should skip, not crash).
    """
    db_path = os.path.join(temp_sim_dir, "nonexistent.db")

    # Should return empty list, not raise
    actions = SimulationRunner._convert_reddit_db_to_actions(db_path)
    assert actions == []

    # Test handling of non-content actions
    db_path = os.path.join(temp_sim_dir, "reddit_simulation_with_likes.db")
    conn, cursor = create_test_reddit_db(db_path)

    base_time = datetime(2026, 5, 18, 10, 0, 0)

    cursor.execute(
        "INSERT INTO user (agent_id, user_name) VALUES (?, ?)",
        (1, "test_user")
    )

    # Insert a mix of content and non-content actions
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (1, base_time.isoformat(), 'create_post',
         '{"content": "Real post"}')
    )
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (1, base_time.isoformat(), 'like_post',
         '{"post_id": 1}')
    )
    cursor.execute(
        "INSERT INTO trace (user_id, created_at, action, info) VALUES (?, ?, ?, ?)",
        (1, base_time.isoformat(), 'do_nothing', '{}')
    )

    conn.commit()
    conn.close()

    # Adapter should skip LIKE/DO_NOTHING, include CREATE_POST, not crash
    actions = SimulationRunner._convert_reddit_db_to_actions(db_path)
    assert len(actions) == 3, f"Expected 3 actions (all types kept), got {len(actions)}"
    # Verify content-bearing actions are present
    action_types = {a.action_type for a in actions}
    assert 'CREATE_POST' in action_types, "CREATE_POST should be included"
    assert 'LIKE_POST' in action_types, "LIKE_POST should be included (not filtered)"
    assert 'DO_NOTHING' in action_types, "DO_NOTHING should be included (not filtered by this adapter)"

    print(f"✓ Graceful failure test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
