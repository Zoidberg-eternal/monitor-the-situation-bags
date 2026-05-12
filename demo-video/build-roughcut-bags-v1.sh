#!/usr/bin/env bash
# Build Monitor x MiroShark Bags rough-cut v1.
# Inputs: stitched-bags-roughcut.mp4 + PNG overlay cards + voiceover-bags.mp3 + music.mp3
# Output: monitor-miroshark-bags-ROUGHCUT-v1.mp4 (~1:56, 1280x720, 24fps)
#
# Overlay timing (seconds, on stitched timeline):
#   0-115  watermark "ROUGH CUT v1" upper-right
#   1-8    BAGS.FM caption (lower bar)
#   14-24  MONITOR caption
#   38-48  MIROSHARK caption
#   68-78  QUARTZ caption
#   90-100 x402 caption
#   108-115 outro wordmark (full-frame dim + title)
set -euo pipefail
cd "$(dirname "$0")"

STITCHED=stitched-bags-roughcut.mp4
VO=voiceover-bags.mp3
MUSIC=music.mp3
OUT=monitor-miroshark-bags-ROUGHCUT-v1.mp4

ffmpeg -y \
  -i "$STITCHED" \
  -i ovl-07-watermark.png \
  -i ovl-01-hook.png \
  -i ovl-02-monitor.png \
  -i ovl-03-miroshark.png \
  -i ovl-04-quartz.png \
  -i ovl-05-x402.png \
  -i ovl-06-outro.png \
  -filter_complex "
    [0:v][1:v]overlay=enable='between(t,0,115)'[v1];
    [v1][2:v]overlay=enable='between(t,1,8)'[v2];
    [v2][3:v]overlay=enable='between(t,14,24)'[v3];
    [v3][4:v]overlay=enable='between(t,38,48)'[v4];
    [v4][5:v]overlay=enable='between(t,68,78)'[v5];
    [v5][6:v]overlay=enable='between(t,90,100)'[v6];
    [v6][7:v]overlay=enable='between(t,108,115)'[vout]
  " \
  -map "[vout]" \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -an stitched-bags-overlay.mp4

# Mix VO + ducked, looped music. Music is ~30s; loop to cover full 116s video.
# Voice on top, music bed at -18 dB with 2s fade in / 3s fade out.
ffmpeg -y \
  -i stitched-bags-overlay.mp4 \
  -i "$VO" \
  -stream_loop -1 -i "$MUSIC" \
  -filter_complex "
    [2:a]atrim=0:120,volume=-18dB,afade=t=in:st=0:d=2,afade=t=out:st=113:d=3[bed];
    [1:a]apad=pad_dur=15[vox];
    [vox][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mix]
  " \
  -map 0:v -map "[mix]" \
  -c:v copy -c:a aac -b:a 192k -shortest \
  "$OUT"

echo "---"
ls -la "$OUT"
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT"
