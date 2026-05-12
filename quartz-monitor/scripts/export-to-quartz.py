#!/usr/bin/env python3
"""Export MiroShark simulation data to Obsidian-style markdown for Quartz."""

import json
import csv
import sqlite3
import os
import sys
import re
from pathlib import Path
from collections import defaultdict

SIMS_DIR = Path(os.environ.get("MIROSHARK_SIMS_DIR", "miroshark/backend/uploads/simulations"))


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def wiki(path: str, display: str) -> str:
    return f"[[{path}|{display}]]"


def load_simulation(sim_dir: Path) -> dict:
    data = {}

    with open(sim_dir / "simulation_config.json") as f:
        data["config"] = json.load(f)

    with open(sim_dir / "state.json") as f:
        data["state"] = json.load(f)

    with open(sim_dir / "trajectory.json") as f:
        data["trajectory"] = json.load(f)

    profiles_file = sim_dir / "twitter_profiles.csv"
    profiles = {}
    if profiles_file.exists():
        with open(profiles_file, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                profiles[int(row["user_id"])] = row
    data["profiles"] = profiles

    posts = []
    db_path = sim_dir / "twitter_simulation.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT p.post_id, p.user_id, p.content, p.created_at,
                   p.num_likes, p.num_dislikes, p.num_shares,
                   u.user_name, u.name
            FROM post p
            LEFT JOIN user u ON p.user_id = u.user_id
            WHERE p.content != ''
            ORDER BY p.post_id
        """)
        posts = [dict(r) for r in cur.fetchall()]
        conn.close()
    data["posts"] = posts

    actions = []
    actions_file = sim_dir / "twitter" / "actions.jsonl"
    if actions_file.exists():
        with open(actions_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    actions.append(json.loads(line))
    data["actions"] = actions

    return data


def extract_tokens_from_config(config: dict) -> list[str]:
    req = config.get("simulation_requirement", "")
    token_patterns = [
        "BTC", "ETH", "SOL", "oil", "gold", "silver", "natural gas",
    ]
    found = []
    for t in token_patterns:
        if t.lower() in req.lower():
            found.append(t)
    return found if found else ["BTC", "ETH"]


def get_agent_posts(posts: list, agent_id: int) -> list:
    return [p for p in posts if p["user_id"] == agent_id]


def get_agent_belief_trajectory(trajectory: dict, agent_id: int) -> dict:
    result = {}
    for snapshot in trajectory.get("snapshots", []):
        positions = snapshot.get("belief_positions", {})
        agent_key = str(agent_id)
        if agent_key in positions:
            result[snapshot["round_num"]] = positions[agent_key]
    return result


def format_belief_table(beliefs: dict, topics: list) -> str:
    if not beliefs:
        return "*No belief data recorded.*"

    rounds = sorted(beliefs.keys())
    sampled = rounds[::max(1, len(rounds) // 8)]
    if rounds[-1] not in sampled:
        sampled.append(rounds[-1])

    header = "| Round | " + " | ".join(topics) + " |"
    sep = "|---" * (len(topics) + 1) + "|"
    rows = []
    for r in sampled:
        vals = beliefs[r]
        cells = [f"{vals.get(t, 0):.2f}" for t in topics]
        rows.append(f"| {r} | " + " | ".join(cells) + " |")

    return "\n".join([header, sep] + rows)


def write_agent_page(out_dir: Path, agent: dict, profile: dict,
                     posts: list, beliefs: dict, topics: list,
                     sim_id: str, tokens: list[str]):
    slug = slugify(agent["entity_name"])
    content_lines = []

    bio = profile.get("description", "") if profile else ""
    entity_type = agent.get("entity_type", "Unknown")
    stance = agent.get("stance", "unknown")
    sentiment = agent.get("sentiment_bias", 0)

    content_lines.append("---")
    content_lines.append(f"title: \"{agent['entity_name']}\"")
    content_lines.append(f"tags: [agent, {entity_type.lower()}, {stance}]")
    content_lines.append("---")
    content_lines.append("")
    content_lines.append(f"# {agent['entity_name']}")
    content_lines.append("")
    content_lines.append(f"**Type:** {entity_type}  ")
    content_lines.append(f"**Stance:** {stance}  ")
    content_lines.append(f"**Sentiment Bias:** {sentiment}  ")
    content_lines.append(f"**Activity Level:** {agent.get('activity_level', 'N/A')}")
    content_lines.append("")

    if bio:
        short_bio = bio[:500] + ("..." if len(bio) > 500 else "")
        content_lines.append("## Bio")
        content_lines.append("")
        content_lines.append(short_bio)
        content_lines.append("")

    content_lines.append("## Simulations")
    content_lines.append("")
    content_lines.append(f"- {wiki(f'simulations/{sim_id}', f'Simulation {sim_id}')}")
    content_lines.append("")

    content_lines.append("## Tokens Discussed")
    content_lines.append("")
    for token in tokens:
        token_slug = slugify(token)
        content_lines.append(f"- {wiki(f'tokens/{token_slug}', token)}")
    content_lines.append("")

    if beliefs:
        content_lines.append("## Belief Trajectory")
        content_lines.append("")
        content_lines.append(format_belief_table(beliefs, topics))
        content_lines.append("")

    agent_posts = posts[:20]
    if agent_posts:
        content_lines.append("## Key Posts")
        content_lines.append("")
        for p in agent_posts:
            text = p["content"][:300].replace("\n", " ")
            likes = p.get("num_likes", 0)
            shares = p.get("num_shares", 0)
            content_lines.append(f"> {text}")
            content_lines.append(f"> — *{likes} likes, {shares} shares*")
            content_lines.append("")

    page = "\n".join(content_lines)
    (out_dir / "agents").mkdir(parents=True, exist_ok=True)
    (out_dir / "agents" / f"{slug}.md").write_text(page)


def write_token_page(out_dir: Path, token: str, agents: list,
                     sim_id: str, trajectory: dict):
    slug = slugify(token)
    topics = trajectory.get("topics", [])

    relevant_topic = None
    token_lower = token.lower()
    for t in topics:
        if token_lower in t.lower():
            relevant_topic = t
            break

    lines = []
    lines.append("---")
    lines.append(f"title: \"{token}\"")
    lines.append("tags: [token, asset]")
    lines.append("---")
    lines.append("")
    lines.append(f"# {token}")
    lines.append("")
    lines.append(f"**Ticker:** {token}  ")
    lines.append("")

    if relevant_topic:
        bt = trajectory.get("belief_trajectories", {}).get(relevant_topic, [])
        if bt:
            last = bt[-1]
            lines.append("## Market Sentiment")
            lines.append("")
            lines.append(f"**Topic:** {relevant_topic}  ")
            lines.append(f"**Final mean sentiment:** {last.get('mean', 0):.3f}  ")
            lines.append(f"**Spread:** {last.get('spread', 0):.3f}  ")
            lines.append(f"**Observations:** {last.get('count', 0)}")
            lines.append("")

    lines.append("## Analyzing Agents")
    lines.append("")
    for a in agents:
        a_slug = slugify(a["entity_name"])
        lines.append(f"- {wiki(f'agents/{a_slug}', a['entity_name'])}")
    lines.append("")

    lines.append("## Simulations")
    lines.append("")
    lines.append(f"- {wiki(f'simulations/{sim_id}', f'Simulation {sim_id}')}")
    lines.append("")

    (out_dir / "tokens").mkdir(parents=True, exist_ok=True)
    (out_dir / "tokens" / f"{slug}.md").write_text("\n".join(lines))


def write_simulation_page(out_dir: Path, sim_id: str, config: dict,
                          trajectory: dict, agents: list, tokens: list,
                          posts: list):
    topics = trajectory.get("topics", [])
    total_rounds = trajectory.get("total_rounds", 0)
    snapshots = trajectory.get("snapshots", [])

    lines = []
    lines.append("---")
    lines.append(f"title: \"Simulation {sim_id}\"")
    lines.append("tags: [simulation]")
    lines.append("---")
    lines.append("")
    lines.append(f"# Simulation {sim_id}")
    lines.append("")

    req = config.get("simulation_requirement", "")
    if req:
        lines.append("## Scenario")
        lines.append("")
        lines.append(req[:800])
        lines.append("")

    time_cfg = config.get("time_config", {})
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"**Duration:** {time_cfg.get('total_simulation_hours', '?')} hours  ")
    lines.append(f"**Minutes per round:** {time_cfg.get('minutes_per_round', '?')}  ")
    lines.append(f"**Total rounds:** {total_rounds}  ")
    lines.append(f"**Agents:** {len(agents)}  ")
    lines.append(f"**Total posts:** {len(posts)}")
    lines.append("")

    lines.append("## Topics")
    lines.append("")
    for t in topics:
        lines.append(f"- {t}")
    lines.append("")

    if snapshots:
        last = snapshots[-1]
        lines.append("## Final State")
        lines.append("")
        lines.append(f"**Total posts created:** {last.get('total_posts_created', '?')}  ")
        lines.append(f"**Total engagements:** {last.get('total_engagements', '?')}  ")
        lines.append("")

        sentiment = last.get("sentiment_summary", {})
        if sentiment:
            lines.append("### Final Sentiment")
            lines.append("")
            lines.append("| Topic | Sentiment |")
            lines.append("|---|---|")
            for topic, val in sentiment.items():
                lines.append(f"| {topic} | {val:.3f} |")
            lines.append("")

    bt = trajectory.get("belief_trajectories", {})
    if bt:
        lines.append("## Belief Trajectories")
        lines.append("")
        for topic, entries in bt.items():
            if entries:
                first = entries[0]
                last_entry = entries[-1]
                lines.append(f"**{topic}:** {first.get('mean', 0):.3f} → {last_entry.get('mean', 0):.3f}")
                lines.append("")

    lines.append("## Participating Agents")
    lines.append("")
    for a in agents:
        a_slug = slugify(a["entity_name"])
        lines.append(f"- {wiki(f'agents/{a_slug}', a['entity_name'])} ({a['entity_type']}, {a.get('stance', '?')})")
    lines.append("")

    lines.append("## Tokens Analyzed")
    lines.append("")
    for token in tokens:
        t_slug = slugify(token)
        lines.append(f"- {wiki(f'tokens/{t_slug}', token)}")
    lines.append("")

    lines.append("## Rounds")
    lines.append("")
    for i, snap in enumerate(snapshots):
        r = snap["round_num"]
        lines.append(f"- {wiki(f'rounds/{sim_id}-round-{r}', f'Round {r}')} — {snap.get('total_posts_created', 0)} posts, {snap.get('active_agent_count', 0)} active agents")
    lines.append("")

    (out_dir / "simulations").mkdir(parents=True, exist_ok=True)
    (out_dir / "simulations" / f"{sim_id}.md").write_text("\n".join(lines))


def write_round_pages(out_dir: Path, sim_id: str, trajectory: dict,
                      actions: list, agents_by_id: dict, topics: list):
    snapshots = trajectory.get("snapshots", [])
    actions_by_round = defaultdict(list)
    for a in actions:
        if "round" in a:
            actions_by_round[a["round"]].append(a)

    (out_dir / "rounds").mkdir(parents=True, exist_ok=True)

    for snap in snapshots:
        r = snap["round_num"]
        round_actions = actions_by_round.get(r, [])

        lines = []
        lines.append("---")
        lines.append(f"title: \"Round {r} — {sim_id}\"")
        lines.append("tags: [round]")
        lines.append("---")
        lines.append("")
        lines.append(f"# Round {r}")
        lines.append("")
        lines.append(f"**Simulation:** {wiki(f'simulations/{sim_id}', f'Simulation {sim_id}')}")
        lines.append(f"**Active agents:** {snap.get('active_agent_count', '?')}  ")
        lines.append(f"**Posts created:** {snap.get('total_posts_created', '?')}  ")
        lines.append(f"**Engagements:** {snap.get('total_engagements', '?')}")
        lines.append("")

        sentiment = snap.get("sentiment_summary", {})
        if sentiment:
            lines.append("## Sentiment")
            lines.append("")
            lines.append("| Topic | Score |")
            lines.append("|---|---|")
            for topic, val in sentiment.items():
                lines.append(f"| {topic} | {val:.3f} |")
            lines.append("")

        post_actions = [a for a in round_actions
                        if a.get("action_type") == "CREATE_POST" and a.get("success")]
        if post_actions:
            lines.append("## Posts This Round")
            lines.append("")
            for pa in post_actions[:10]:
                agent_name = pa.get("agent_name", f"Agent {pa.get('agent_id', '?')}")
                agent_slug = slugify(agent_name)
                content = pa.get("action_args", {}).get("content", "")[:200].replace("\n", " ")
                lines.append(f"**{wiki(f'agents/{agent_slug}', agent_name)}:**")
                lines.append(f"> {content}")
                lines.append("")

        (out_dir / "rounds" / f"{sim_id}-round-{r}.md").write_text("\n".join(lines))


def write_index(out_dir: Path, sim_ids: list, agent_count: int, token_count: int):
    lines = []
    lines.append("---")
    lines.append("title: \"Monitor the Situation\"")
    lines.append("tags: [index]")
    lines.append("---")
    lines.append("")
    lines.append("# Monitor the Situation")
    lines.append("")
    lines.append("Interactive visualization of agent networks and simulation results from MiroShark.")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append(f"- **{len(sim_ids)}** simulations")
    lines.append(f"- **{agent_count}** unique agents")
    lines.append(f"- **{token_count}** tokens tracked")
    lines.append("")
    lines.append("## Simulations")
    lines.append("")
    for sid in sim_ids:
        lines.append(f"- {wiki(f'simulations/{sid}', f'Simulation {sid}')}")
    lines.append("")
    lines.append("## Explore")
    lines.append("")
    lines.append("Use the **graph view** to explore relationships between agents, tokens, and simulations. "
                 "Click any node to navigate to its page.")
    lines.append("")

    (out_dir / "index.md").write_text("\n".join(lines))


def export_simulation(sim_dir: Path, out_dir: Path):
    sim_id = sim_dir.name
    print(f"Exporting {sim_id}...")

    data = load_simulation(sim_dir)
    config = data["config"]
    trajectory = data["trajectory"]
    agents = config.get("agent_configs", [])
    tokens = extract_tokens_from_config(config)
    posts = data["posts"]
    profiles = data["profiles"]
    topics = trajectory.get("topics", [])

    agents_by_id = {a["agent_id"]: a for a in agents}

    for agent in agents:
        aid = agent["agent_id"]
        agent_posts = get_agent_posts(posts, aid)
        beliefs = get_agent_belief_trajectory(trajectory, aid)
        profile = profiles.get(aid, {})
        write_agent_page(out_dir, agent, profile, agent_posts, beliefs,
                         topics, sim_id, tokens)

    for token in tokens:
        write_token_page(out_dir, token, agents, sim_id, trajectory)

    write_simulation_page(out_dir, sim_id, config, trajectory, agents, tokens, posts)
    write_round_pages(out_dir, sim_id, trajectory, data["actions"], agents_by_id, topics)

    return agents, tokens


def main():
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("content")
    out_dir.mkdir(parents=True, exist_ok=True)

    sim_dirs = sorted(SIMS_DIR.iterdir()) if SIMS_DIR.exists() else []
    sim_dirs = [d for d in sim_dirs if d.is_dir() and d.name.startswith("sim_")]

    if not sim_dirs:
        print("No simulation directories found.")
        sys.exit(1)

    all_agents = set()
    all_tokens = set()
    sim_ids = []

    for sim_dir in sim_dirs:
        agents, tokens = export_simulation(sim_dir, out_dir)
        sim_ids.append(sim_dir.name)
        for a in agents:
            all_agents.add(a["entity_name"])
        all_tokens.update(tokens)

    write_index(out_dir, sim_ids, len(all_agents), len(all_tokens))

    print(f"\nExported {len(sim_ids)} simulations to {out_dir}/")
    print(f"  Agents: {len(all_agents)}")
    print(f"  Tokens: {len(all_tokens)}")
    print(f"  Round pages: {sum(1 for _ in (out_dir / 'rounds').glob('*.md'))}")


if __name__ == "__main__":
    main()
