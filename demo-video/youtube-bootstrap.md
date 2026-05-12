# YouTube Upload — OAuth Bootstrap (5 min)

One-time setup so the agent owns the YouTube upload (and every future upload from this channel is fully agent-driven, no paste workflow).

## What raeli has to do (5 minutes, all in browser)

1. **Open Google Cloud Console** → https://console.cloud.google.com/. Sign in with the YouTube account you want the demo uploaded under.

2. **Create (or pick) a project.** Top-left project picker → New Project → name it `zera-youtube-upload` → Create.

3. **Enable YouTube Data API v3** for that project:
   https://console.cloud.google.com/apis/library/youtube.googleapis.com → Enable.

4. **Create an OAuth client (Desktop application).** Go to https://console.cloud.google.com/apis/credentials → Create Credentials → OAuth client ID. If asked, click "Configure consent screen":
   - User type: **External**
   - App name: `zera-youtube-upload`
   - User support email + developer contact email: your email
   - Save and continue past the Scopes step (no extra scopes needed yet)
   - On Test users, add your own Google email so the unverified app can be used by you. Save.

   Then back at Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: `zera-cli`
   - Create → click **Download JSON** on the right side of the new client row.

5. **Drop the downloaded JSON in place.** Save the file as exactly:

   ```
   /Users/raelisavitt/monitor-the-situation-stellar/demo-video/yt-upload-creds/client_secrets.json
   ```

   (Create the `yt-upload-creds/` folder if it doesn't exist — `mkdir -p demo-video/yt-upload-creds`.)

6. **Ping back on [ZERA-500](/ZERA/issues/ZERA-500)** — one line, "client_secrets.json dropped." That's it. The CMO agent takes it from there:
   - first run will open one browser tab asking you to click "Allow" (this is the OAuth consent — same screen Google shows for any third-party app accessing YouTube)
   - after that click, the refresh token is stored locally and every subsequent upload is fully agent-driven, no human in the loop

## What the agent does next (no raeli action)

Once `client_secrets.json` is in place:

```bash
cd /Users/raelisavitt/monitor-the-situation-stellar/demo-video
./yt-upload-venv/bin/python youtube_upload.py \
  --thumbnail youtube-thumbnail-dashboard.jpg
```

That command:
1. Detects no `token.json` yet, opens a browser to the OAuth consent screen → **raeli clicks "Allow" once**.
2. Stores the refresh token at `yt-upload-creds/token.json` (gitignored).
3. Uploads `monitor-miroshark-bags-FINAL.mp4` with title, description, tags, category=Science & Technology, plus the chosen thumbnail — all metadata baked into `youtube_upload.py` (mirrored from `youtube-upload.md`).
4. Prints the YouTube URL.

## Known limitation — visibility lands as `private`

YouTube Data API v3 forces uploads from **unverified** OAuth projects to `privacyStatus=private` regardless of what the API call requests. The OAuth client created above is in `Testing`/Test-User mode → unverified for upload purposes. So:

- The agent uploads the video, prints the URL.
- The video is **private** until raeli opens YouTube Studio → Videos → this upload → Visibility → **Public**. ~30-second click.
- Title, description, tags, thumbnail, chapters are all correct; only visibility needs the flip.

This is Google's anti-spam policy, applied at the API layer — it can't be worked around without putting the OAuth client through Google's verification audit (privacy policy URL, brand verification, scope justification — days to weeks).

## Future uploads (raeli does the visibility flip; rest is agent)

Refresh token in `token.json` stays valid as long as you don't revoke it. Any future Zero Human Labs YouTube upload is:

```bash
./yt-upload-venv/bin/python youtube_upload.py path/to/next-video.mp4
```

→ agent uploads, prints URL, video lands private → raeli does the ~30s Studio flip to public. No copy-paste of title/description/tags/thumbnail ever again; just one toggle per video.

## If anything breaks

| Symptom | Likely cause | Fix |
|---|---|---|
| `missing OAuth client at .../client_secrets.json` | step 5 not done | drop the JSON, retry |
| `Error 403: access_denied` during consent | you're not in the Test users list | go back to the consent screen step in step 4 and add yourself |
| `quotaExceeded` on upload | daily YouTube Data API quota exhausted | wait until midnight Pacific or request a quota bump — first upload almost never hits this |
| `videoFile.invalid` or similar | file path wrong | confirm `demo-video/monitor-miroshark-bags-FINAL.mp4` exists |

## Why this is smaller than the paste workflow

The legacy `youtube-upload.md` paste pack is ~100 lines of copy-paste across title + description + tags + thumbnail + chapters. Bootstrap above is one Google Cloud project + one download + one consent click → all future uploads agent-driven. After this is done once, raeli does **zero** YouTube work for the rest of the project.
