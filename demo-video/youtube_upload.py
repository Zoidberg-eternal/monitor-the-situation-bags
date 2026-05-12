#!/usr/bin/env python3
"""Agent-driven YouTube upload for the Bags Hackathon demo.

Reads metadata (title/description/tags) inline from this script (mirrored from
`youtube-upload.md` so they stay in sync — edit both if you tweak copy).

Usage:
    cd demo-video
    yt-upload-venv/bin/python youtube_upload.py [VIDEO_PATH]

Default VIDEO_PATH: monitor-miroshark-bags-FINAL.mp4

Credential paths (relative to this script's directory unless absolute):
    yt-upload-creds/client_secrets.json   -- OAuth Desktop client from Google Cloud Console
    yt-upload-creds/token.json            -- generated on first run, reused after

First-run flow: opens a browser tab for one OAuth consent. After that, the refresh
token in token.json is reused. Every subsequent upload is fully agent-driven.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCRIPT_DIR = Path(__file__).resolve().parent
CREDS_DIR = SCRIPT_DIR / "yt-upload-creds"
CLIENT_SECRETS = CREDS_DIR / "client_secrets.json"
TOKEN_PATH = CREDS_DIR / "token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

TITLE = "Monitor × MiroShark — Bags Hackathon Demo"

DESCRIPTION = """Monitor × MiroShark is an autonomous AI risk console for Bags.fm token launches, with explainable swarm consensus and agent-native USDC payments on Solana. Submitted to the Bags Hackathon by Zero Human Labs.

Code, docker-compose stack, simulations, and the Quartz knowledge graph:
https://github.com/Zoidberg-eternal/monitor-the-situation-stellar

Submission entry:
https://dorahacks.io/hackathon/the-bags-hackathon/detail

— Chapters —
0:00 Hook · Bags.fm 30-second rug cycles
0:05 Monitor · live token feed + 4-signal composite risk
0:22 Anomaly · risk gauge flips green → amber → red
0:33 MiroShark · 100s of personas across X / Reddit / Polymarket / Bags.fm
0:43 Quartz · navigable belief graph, every stance traced
0:55 Consensus · cluster convergence + ReACT report
1:03 x402 · curl → 402 → USDC payment → 200 + analysis JSON
1:21 Solana · on-chain settlement (devnet)
1:33 Outro · agent-native payments on Solana

— What's real, what's a demo UI —
The Monitor risk console shown is a UI built for this demo on top of the live Monitor API (monitor/server.py, FastAPI at :8402). The token feed, anomaly detection, and risk scoring are real; the visual shell is purpose-built for the walkthrough.

The Quartz graph + ReACT consensus view is similarly a UI built for this demo reflecting MiroShark's real swarm primitives (persona archetypes, 5-layer grounding, belief-trajectory schema, ReACT consensus). The live quartz-monitor/ site renders the same primitives against actual simulation runs.

The terminal x402 exchange in 1:03 is scripted against the real x402 / Solana gateway response shape — signatures and JSON match what the live solana-gateway:3403 returns on devnet.

Full disclosure in the repo README: https://github.com/Zoidberg-eternal/monitor-the-situation-stellar/tree/main/demo-video

— Built by —
Zero Human Labs — where every employee is an AI agent.
https://github.com/Zoidberg-eternal"""

TAGS = [
    "solana", "bags hackathon", "bags.fm", "x402", "ai agents", "autonomous agents",
    "dorahacks", "swarm intelligence", "monitor the situation", "miroshark",
    "zero human labs", "ai trading", "on-chain payments", "USDC", "defi",
    "agent native payments", "neo4j", "knowledge graph", "explainable ai", "hackathon",
]

CATEGORY_ID = "28"  # Science & Technology
# YouTube Data API v3 forces uploads from unverified OAuth projects to
# privacyStatus=private regardless of the value sent here. The upload lands
# as private; flipping to public is a manual step in YouTube Studio until
# the OAuth client passes Google's verification audit (days–weeks).
PRIVACY = "public"


def load_credentials() -> Credentials:
    if not CLIENT_SECRETS.exists():
        sys.exit(
            f"missing OAuth client at {CLIENT_SECRETS}\n"
            "see demo-video/youtube-bootstrap.md for the 5-minute Google Cloud setup."
        )

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_PATH.write_text(creds.to_json())
            return creds

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
    # run_local_server opens the consent screen in the default browser and listens
    # on a random localhost port for the redirect — works without any manual paste.
    creds = flow.run_local_server(port=0, open_browser=True)
    CREDS_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    return creds


def upload(video_path: Path) -> str:
    if not video_path.exists():
        sys.exit(f"video not found: {video_path}")

    creds = load_credentials()
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": TITLE,
            "description": DESCRIPTION,
            "tags": TAGS,
            "categoryId": CATEGORY_ID,
        },
        "status": {
            "privacyStatus": PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    last_pct = -1
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                if pct != last_pct:
                    print(f"  upload progress: {pct}%", flush=True)
                    last_pct = pct
        except HttpError as e:
            sys.exit(f"upload failed: {e}")

    video_id = response["id"]
    return f"https://www.youtube.com/watch?v={video_id}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?", default=str(SCRIPT_DIR / "monitor-miroshark-bags-FINAL.mp4"))
    parser.add_argument("--thumbnail", help="optional path to a thumbnail JPG to attach after upload")
    args = parser.parse_args()

    url = upload(Path(args.video))
    print(f"\nuploaded: {url}")

    if args.thumbnail:
        thumb_path = Path(args.thumbnail)
        if not thumb_path.exists():
            print(f"thumbnail not found: {thumb_path}; skipping", file=sys.stderr)
            return
        creds = load_credentials()
        youtube = build("youtube", "v3", credentials=creds)
        video_id = url.split("=")[-1]
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb_path), mimetype="image/jpeg"),
            ).execute()
            print(f"thumbnail set: {thumb_path.name}")
        except HttpError as e:
            print(f"thumbnail upload failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
