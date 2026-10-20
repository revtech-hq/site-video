# Delivery: the export, the cover, the upload copy, the record

A film is delivered when the file that leaves has passed its gates, carries no tool traces, has its cover, and its
record says what the owner asked for in each round.

## 1. The export

`filmkit.encode.Writer` writes every film the same way: libx264, preset slow, crf 14, High profile level 4.2,
yuv420p, BT.709 primaries, transfer and matrix (set in the stream and in the container: all three, or players guess),
tv range, fast start, no audio track. Clean by default: no metadata, no encoder note in the stream (the x264 SEI is
removed), bitexact muxing, and only the film's title. Decoded frames are identical to an unclean encode.

| Platform | Frame | Rate | Notes |
|---|---|---|---|
| LinkedIn feed | 1080 x 1080 (1:1) or 1080 x 1350 (4:5) | 60 fps | the platform re-encodes every upload; see section 2. Silent: feeds autoplay muted |
| YouTube | 1920 x 1080 or 3840 x 2160 (16:9) | the source's rate | the platform's recommendations below |
| Stories, Reels, Shorts | 1080 x 1920 (9:16) | 30 or 60 | keep words out of the top and bottom 14% (the app's chrome) |

YouTube's recommended upload settings (its help page *Recommended upload encoding settings*, last verified 15 Oct
2026): MP4 with the moov atom at the front and no edit lists; H.264 High, progressive, 2 consecutive B-frames, a
closed GOP of half the frame rate (`-g 30 -bf 2` at 60 fps), CABAC, 4:2:0, variable bitrate with no cap; SDR at
BT.709 for all three colour fields; 1080p at 8 Mbps (24 to 30 fps) or 12 Mbps (48 to 60 fps), 2160p at 35 to 45 or 53
to 68 Mbps; audio AAC-LC (or Opus) at 48 kHz, stereo; upload at the frame rate recorded. crf 14 lands above those
bitrates, which is fine: they are floors for quality, not caps.

## 2. Will the platform ruin it?

Every platform re-encodes. Simulate it before the owner asks:

```
sv check platform OUT.mp4 --mbps 3
```

It writes the re-encoded copy and prints the SSIM per frame with the worst moments. Look at those moments in both
files side by side at full size and at phone size. On one film, a 3 Mbps re-encode held at 60 fps
(worst frames in the fastest scroll, SSIM 0.974); a 30 fps version showed every blurred frame's stacked copies twice
as far apart. Do not drop to 30 fps to save bits; keep 60 and crf 14.

## 3. The cover

A separate still, uploaded as the post's custom thumbnail: the first frame of a film is rarely the best still, and
the platform's own pick is random.

- Start from the hook's frame (the marks over the blurred page).
- A still can take less blur than motion (9 instead of 12): the eye has time.
- If a mark sits on dark page (photos, a black button), move the camera, not the blur: search the moments before
  the first scroll and small camera shifts for the least dark page under the title boxes. One film's cover
  moved the page 38 px: dark page under its lockup went from 12.9% to 0.6% (L under 215), and 6.9% to 0.0% under
  the gate's threshold.
- Gate: `sv check cover ...` (section 2 of `review.md`): under 1% of the page darker than L 200 under each title
  box, measured on the page layer as the film composes it.
- YouTube thumbnails (last verified 15 Oct 2026): 16:9, 3840 x 2160 recommended, at least 640 px wide, JPG or PNG,
  at most 2 MB when set from a phone and 50 MB from a desktop.

## 4. The upload copy

What leaves is a copy named for its title (`Title-In-Words.mp4`, the PNG cover beside it), with the owner's
metadata only and no tool or AI trace. With `encode.Writer` in its default clean mode the film already is that copy;
a file from elsewhere is remuxed without re-encoding:

```
ffmpeg -i IN.mp4 -map 0 -c copy -map_metadata -1 -fflags +bitexact -flags:v +bitexact \
       -bsf:v filter_units=remove_types=6 -metadata:s:v:0 encoder= -metadata title="The Title" -movflags +faststart OUT.mp4
```

Check it: `sv check file OUT.mp4 --beats beats.json` (the tool-traces gate reads the bytes, and `same` proves the
frames did not change). Every copy that leaves gets its own run: a sidecar holds the sha256 of one file's bytes, and a
remux or a re-encode is another file. Then carry the master's review: `sv check review OUT.mp4 --from
MASTER.mp4`, refused unless the decoded frames are the master's.

## 5. The email copy

A film the owner will attach to an email needs a second copy. An attachment travels encoded and grows by about a
third, and mail providers cap a message at 20 to 25 MB (Outlook, Gmail), so a 25 MB master arrives as a link or not
at all. One film's master was 25.0 MB; its email copy, two passes of x264 at 2.5 Mb/s from the master
(`scripts/email_copy.sh IN OUT 2500 "Title" PASSLOG`, in the skill folder), was 11.7 MB, SSIM 0.9965 against the master, the worst frame
0.987 in a blurred scroll, with no difference to see at 1:1. Keep 60 fps and the colour tags; gate it like the master
(`sv check file`), and name it for the title like the upload copy. It is a new encode, so its review is its own.

## 6. The record

- The PASS sidecar (`OUT.mp4.film_check.json`) holds the file's sha256 and every gate's number. A file without a
  PASS sidecar for its exact bytes does not reach the owner as final.
- Keep a record of each file that leaves: its checksum, the gates' sidecar and the review. Beside it, for each
  version, the owner's words, verbatim and dated, then what changed. That record is what makes the next film faster.
- The film folder keeps `film.json`, `brand.json`, `beats.json`, `film.py` and the capture's checksum manifest in
  git; the capture itself stays out (hundreds of MB). Reproduce before you trust: `sv film DIR all OUT.mp4` from the folder
  must give a file whose decoded frames equal the shipped one (`sv check same`).
