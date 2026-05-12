#!/usr/bin/env bash
# Build the Monitor x MiroShark Bags FINAL cut at 1080p once raw shots land.
#
# Inputs expected in demo-video/ (or demo-video/raw-recordings/ — both searched):
#   raw-shot2-dashboard.{mov,mp4,mkv}    Shot 2 - Monitor dashboard / Bags.fm feed
#   raw-shot3-risk-gauge.{mov,mp4,mkv}   Shot 3 - composite risk gauge flip
#   raw-shot5-quartz-navigate.{mov,...}  Shot 5 - Quartz graph navigation
#   raw-shot6-quartz-report.{mov,...}    Shot 6 - cluster + ReACT consensus
#   raw-shot7-terminal-x402.{mov,...}    Shot 7 - terminal 402 -> pay -> 200
#   raw-shot8-solana-explorer.{mov,...}  Shot 8 - Solana Explorer tx view
#   ai-shot1-feed.mp4                    Shot 1 - Bags.fm feed AI b-roll (or fallback)
#   ai-shot9-outro.mp4                   Shot 9 - Solana globe outro (or fallback)
#
# Side inputs (already on disk): voiceover-bags.mp3, music.mp3, section3-swarm.mp4,
#   globe-broll.mp4, ovl-01..06 (regenerate via `python3 build-overlay-cards.py --final`).
#
# Output: monitor-miroshark-bags-FINAL.mp4 (1920x1080, ~2:00, H.264, AAC, <=12 Mbps).

set -euo pipefail
cd "$(dirname "$0")"

VO=voiceover-bags.mp3
MUSIC=music.mp3
OUT=monitor-miroshark-bags-FINAL.mp4

require() {
  if [ ! -f "$1" ]; then
    echo "missing required input: $1" >&2
    exit 1
  fi
}

# Locate a raw clip with any of {mov, mp4, mkv} extensions, in . or raw-recordings/.
find_raw() {
  local base=$1
  for dir in . raw-recordings; do
    for ext in mov mp4 mkv MOV MP4 MKV; do
      if [ -f "$dir/$base.$ext" ]; then
        echo "$dir/$base.$ext"
        return 0
      fi
    done
  done
  echo "missing raw: $base.{mov,mp4,mkv} (looked in . and raw-recordings/)" >&2
  exit 1
}

# 1. Normalize all raw + AI shots to 1920x1080/30fps/H.264/AAC stereo 48k.
normalize() {
  local src=$1 out=$2
  if [ -f "$out" ] && [ "$out" -nt "$src" ]; then
    echo "  skip (cached): $out"
    return 0
  fi
  ffmpeg -y -i "$src" \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30" \
    -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -ac 2 \
    "$out" </dev/null
}

echo "==> 1/5 Normalizing live recordings"
for base in raw-shot2-dashboard raw-shot3-risk-gauge raw-shot5-quartz-navigate \
            raw-shot6-quartz-report raw-shot7-terminal-x402 raw-shot8-solana-explorer; do
  src=$(find_raw "$base")
  normalize "$src" "norm-${base}.mp4"
done

echo "==> 2/5 Normalizing AI / fallback shots 1 + 9"

# Shot 1: prefer fresh AI gen if present, else retint section1-intro.mp4.
if [ -f ai-shot1-feed.mp4 ]; then
  normalize ai-shot1-feed.mp4 norm-ai-shot1-feed.mp4
else
  echo "  no ai-shot1-feed.mp4; using section1-intro.mp4 retint fallback"
  ffmpeg -y -i section1-intro.mp4 \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30,eq=saturation=1.2:contrast=1.05" \
    -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
    -an norm-ai-shot1-feed.mp4 </dev/null
fi

# Shot 9: prefer fresh AI gen if present, else reuse globe-broll.mp4 with PNG wordmark.
# NOTE: this homebrew ffmpeg lacks libfreetype (no drawtext) -- using PNG overlay path.
if [ -f ai-shot9-outro.mp4 ]; then
  normalize ai-shot9-outro.mp4 norm-ai-shot9-outro.mp4
else
  echo "  no ai-shot9-outro.mp4; building globe-broll + ovl-06-outro fallback"
  ffmpeg -y -i globe-broll.mp4 -i ovl-06-outro.png \
    -filter_complex "
      [0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30[bg];
      [bg][1:v]overlay=enable='between(t,1,8)'[v]
    " \
    -map "[v]" -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -an \
    norm-ai-shot9-outro.mp4 </dev/null
fi

# Swarm B-roll: normalize then freeze-frame pad so the swarm narrative beat lines up
# with the voiceover length (raw section3-swarm.mp4 is only ~5s).
echo "==> 3/5 Normalizing existing swarm B-roll"
normalize section3-swarm.mp4 norm-section3-swarm-1080-base.mp4
if [ ! -f norm-section3-swarm-1080.mp4 ] || [ norm-section3-swarm-1080-base.mp4 -nt norm-section3-swarm-1080.mp4 ]; then
  ffmpeg -y -loglevel error -i norm-section3-swarm-1080-base.mp4 \
    -vf "tpad=stop_mode=clone:stop_duration=5,fps=30" \
    -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
    -c:a aac -b:a 192k -ar 48000 -ac 2 \
    norm-section3-swarm-1080.mp4
fi

# Outro: hold the last frame so the wordmark + VO close out cleanly. We pad to
# 6s now because the v2 Quartz mock recording is ~6s shorter than v1; the extra
# hold time keeps the VO from being -shortest-cut before its final sentence.
if [ ! -f norm-ai-shot9-outro-padded.mp4 ] || [ norm-ai-shot9-outro.mp4 -nt norm-ai-shot9-outro-padded.mp4 ]; then
  ffmpeg -y -loglevel error -i norm-ai-shot9-outro.mp4 \
    -vf "tpad=stop_mode=clone:stop_duration=6,fps=30" \
    -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -an \
    norm-ai-shot9-outro-padded.mp4
fi
cp -f norm-ai-shot9-outro-padded.mp4 norm-ai-shot9-outro.mp4

echo "==> 4/5 Stitch + overlay captions"
require concat-bags-final.txt
require ovl-01-hook.png
require ovl-02-monitor.png
require ovl-03-miroshark.png
require ovl-04-quartz.png
require ovl-05-x402.png
require ovl-06-outro.png

# NOTE: must re-encode (NOT -c copy). Concat with `-c copy` preserves the per-
# segment PTS, which confuses ffmpeg's overlay filter — the PNG overlay frame
# held via repeatlast=1 only persists until the first PTS boundary, after which
# subsequent caption overlays silently fail to apply. Re-encoding produces a
# single monotonic PTS stream and the overlay holds for the full video.
ffmpeg -y -f concat -safe 0 -i concat-bags-final.txt \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -fflags +genpts \
  stitched-bags-final.mp4

# Caption overlay timing — re-cut against the actual 1:42.8 final timeline.
# Shot cumulative boundaries (in seconds), after Shots 5 + 6 were re-recorded
# against the Bags-narrative Quartz mock:
#   Shot 1 intro      0.000 - 5.033
#   Shot 2 dashboard  5.033 - 21.867
#   Shot 3 risk gauge 21.867 - 32.600
#   Shot 4 swarm     32.600 - 42.633
#   Shot 5 quartz nav 42.633 - 54.513
#   Shot 6 quartz rpt 54.513 - 63.233
#   Shot 7 x402      63.233 - 81.167
#   Shot 8 explorer  81.167 - 92.733
#   Shot 9 outro     92.733 - 102.767
# Captions are placed inside their owning shot, with breathing room at head and tail.
#   0-5       BAGS.FM hook       (Shot 1, full intro)
#   8-18      MONITOR            (Shot 2 dashboard, mid)
#   34-42     MIROSHARK          (Shot 4 swarm, late so it lands after first hit)
#   44-54     QUARTZ             (Shot 5 graph nav, mid)
#   65-75     x402               (Shot 7 terminal, mid)
#   94-102.7  outro full-frame   (Shot 9, full outro)
# Now that the stitched file has a single monotonic PTS stream (re-encoded
# above), all six caption overlays can be chained in a single ffmpeg pass.
ffmpeg -y -i stitched-bags-final.mp4 \
  -i ovl-01-hook.png \
  -i ovl-02-monitor.png \
  -i ovl-03-miroshark.png \
  -i ovl-04-quartz.png \
  -i ovl-05-x402.png \
  -i ovl-06-outro.png \
  -filter_complex "
    [0:v][1:v]overlay=enable='between(t,0,5)'[v1];
    [v1][2:v]overlay=enable='between(t,8,18)'[v2];
    [v2][3:v]overlay=enable='between(t,34,42)'[v3];
    [v3][4:v]overlay=enable='between(t,44,54)'[v4];
    [v4][5:v]overlay=enable='between(t,65,75)'[v5];
    [v5][6:v]overlay=enable='between(t,94,102.7)'[vout]
  " \
  -map "[vout]" -map 0:a? \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p \
  -c:a copy \
  stitched-bags-final-overlay.mp4

echo "==> 5/5 Mix VO + ducked music, final H.264 export"
require "$VO"
require "$MUSIC"

ffmpeg -y \
  -i stitched-bags-final-overlay.mp4 \
  -i "$VO" \
  -stream_loop -1 -i "$MUSIC" \
  -filter_complex "
    [2:a]atrim=0:130,volume=-18dB,afade=t=in:st=0:d=2,afade=t=out:st=101:d=4[bed];
    [1:a]apad=pad_dur=15[vox];
    [vox][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]
  " \
  -map 0:v -map "[mix]" \
  -c:v libx264 -preset slow -crf 19 -maxrate 12M -bufsize 24M -pix_fmt yuv420p \
  -c:a aac -b:a 192k -shortest \
  "$OUT"

echo "---"
ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate \
  -of default=nw=1 "$OUT"
echo "Final cut ready: $OUT"
