#!/bin/bash
# A two-pass email copy of a film master: H.264 High 4.2, the BT.709 tags of the master, no tool traces, fast start.
# email_copy.sh IN.mp4 OUT.mp4 KBPS "Title" PASSLOG   (2500 kb/s puts a 38 s 1080 square film at 11.7 MB)
# Then: film_check.py file OUT.mp4 --beats beats.json (its own sidecar: these bytes are not the master's).
set -e
IN="$1"; OUT="$2"; K="$3"; TITLE="$4"; LOG="$5"
C=(-c:v libx264 -preset slower -b:v "${K}k" -maxrate "$((K * 8 / 5))k" -bufsize "$((K * 2))k" -profile:v high -level 4.2 -pix_fmt yuv420p
   -x264-params colorprim=bt709:transfer=bt709:colormatrix=bt709 -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -an)
ffmpeg -hide_banner -loglevel error -y -i "$IN" "${C[@]}" -pass 1 -passlogfile "$LOG" -f null /dev/null
ffmpeg -hide_banner -loglevel error -y -i "$IN" "${C[@]}" -pass 2 -passlogfile "$LOG" -movflags +faststart -map_metadata -1 -fflags +bitexact \
  -flags:v +bitexact -bsf:v filter_units=remove_types=6 -metadata:s:v:0 encoder= -metadata title="$TITLE" "$OUT"
