#!/bin/bash
# usage: sheet.sh NAME t1 t2 ...  -> renders stills and a contact sheet into the scratchpad
S=${OUT:-/tmp/claude-0/-home-user-claude/79a4ee62-ea4e-436e-a828-605ac2f1b2d2/scratchpad/stills}
FF=$(python3 -c "import imageio_ffmpeg as i;print(i.get_ffmpeg_exe())")
N=$1; shift
OUT=$S node stills.mjs "$@" >/dev/null
args=(); f=""; i=0
for t in "$@"; do tt=$(printf "%.2f" $t); args+=(-i $S/f_$tt.png); f+="[$i]scale=405:-1[v$i];"; i=$((i+1)); done
chain=""; for j in $(seq 0 $((i-1))); do chain+="[v$j]"; done
$FF -loglevel error -y "${args[@]}" -filter_complex "${f}${chain}hstack=$i" $S/$N.png
