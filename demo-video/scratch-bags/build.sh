#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

DV="$(cd .. && pwd)"   # demo-video/ — parent of this script's dir

VENC=(-c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30)
AENC=(-c:a aac -b:a 192k -ar 48000 -ac 2)
SCALE="scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,fps=30,setsar=1"

# Helper: PNG → MP4 (silent stereo audio track, $2 seconds)
mk_clip_from_png() {
  local png="$1" dur="$2" out="$3"
  ffmpeg -y -loop 1 -i "${png}" \
    -f lavfi -i "anullsrc=r=48000:cl=stereo" \
    -t "${dur}" -vf "fps=30,setsar=1" \
    "${VENC[@]}" "${AENC[@]}" "${out}"
}

echo "== 01 hook (12s, looped section1-intro tinted purple) =="
ffmpeg -y -stream_loop -1 -i "${DV}/section1-intro.mp4" \
  -f lavfi -i "anullsrc=r=48000:cl=stereo" \
  -filter_complex "[0:v]${SCALE},colorbalance=rs=.18:bs=.30:gs=-.10,eq=saturation=1.25[v]" \
  -map "[v]" -map "1:a" -t 12 \
  "${VENC[@]}" "${AENC[@]}" 01-hook.mp4

echo "== 02 dashboard slate =="
mk_clip_from_png slate-02-dashboard.png 14 02-dashboard.mp4
echo "== 03 risk-gauge slate =="
mk_clip_from_png slate-03-risk.png 14 03-risk-gauge.mp4

echo "== 04 swarm (35s, looped section3-swarm) =="
ffmpeg -y -stream_loop -1 -i "${DV}/section3-swarm.mp4" \
  -f lavfi -i "anullsrc=r=48000:cl=stereo" \
  -filter_complex "[0:v]${SCALE}[v]" \
  -map "[v]" -map "1:a" -t 35 \
  "${VENC[@]}" "${AENC[@]}" 04-swarm.mp4

echo "== 05 quartz-nav slate =="
mk_clip_from_png slate-05-quartz-nav.png 15 05-quartz-nav.mp4
echo "== 06 quartz-react slate =="
mk_clip_from_png slate-06-quartz-react.png 15 06-quartz-react.mp4
echo "== 07 x402 slate =="
mk_clip_from_png slate-07-x402.png 15 07-x402.mp4
echo "== 08 explorer slate =="
mk_clip_from_png slate-08-explorer.png 15 08-explorer.mp4

echo "== 09 outro (15s, looped globe-broll + wordmark overlay) =="
ffmpeg -y -stream_loop -1 -i "${DV}/globe-broll.mp4" \
  -loop 1 -i outro-overlay.png \
  -f lavfi -i "anullsrc=r=48000:cl=stereo" \
  -filter_complex "
    [0:v]${SCALE}[bg];
    [1:v]format=rgba,fade=t=in:st=1:d=1.5:alpha=1[ovl];
    [bg][ovl]overlay=0:0:eof_action=pass[v]
  " \
  -map "[v]" -map "2:a" -t 15 \
  "${VENC[@]}" "${AENC[@]}" 09-outro.mp4

echo "== concat =="
cat > concat-scratch.txt <<EOF
file '01-hook.mp4'
file '02-dashboard.mp4'
file '03-risk-gauge.mp4'
file '04-swarm.mp4'
file '05-quartz-nav.mp4'
file '06-quartz-react.mp4'
file '07-x402.mp4'
file '08-explorer.mp4'
file '09-outro.mp4'
EOF
ffmpeg -y -f concat -safe 0 -i concat-scratch.txt -c copy stitched-scratch.mp4

echo "== mix VO + looped music =="
ffmpeg -y \
  -i stitched-scratch.mp4 \
  -i "${DV}/voiceover-bags.mp3" \
  -stream_loop -1 -i "${DV}/music.mp3" \
  -filter_complex "
    [2:a]atrim=0:152,volume=-18dB,afade=t=in:st=0:d=2,afade=t=out:st=148:d=2[bed];
    [1:a][bed]amix=inputs=2:duration=first:dropout_transition=0[mix]
  " \
  -map 0:v -map "[mix]" \
  -c:v copy -c:a aac -b:a 192k -shortest \
  "${DV}/monitor-miroshark-bags-FINAL.mp4"

echo
echo "=== DONE ==="
ffprobe -v error -show_entries format=duration:stream=width,height,r_frame_rate,codec_name -of default=nw=1 "${DV}/monitor-miroshark-bags-FINAL.mp4"
ls -lh "${DV}/monitor-miroshark-bags-FINAL.mp4"
