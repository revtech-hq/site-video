# Capture: a live site frame by frame, and footage and stills

A screen recording is a video of whatever the machine managed to draw. A capture here is one screenshot per film
frame (several for a blurred frame), taken at exactly the scroll position and the page time the timeline asks for.
That is why a capture is deterministic, sharp at any zoom, and reusable by every render.

## 1. Recon first

Open the page at the capture viewport in a throwaway script and measure, never guess:

- the top of every section the film passes, and the box of everything the camera frames (the bordered card itself,
  measured on captured pixels, not an inner element: an inner box put the first zoom off centre);
- the link the cursor clicks, and the URL it lands on;
- consent banners and their buttons; what loads late (lazy images, fonts, embeds);
- the page's own motion: CSS animations and transitions slow down with the capture, JavaScript-driven motion (GSAP,
  Lenis, canvas, video) does not (see section 5);
- how the click travels: a link that opens a new tab (remove its target in a `pre` `eval` step), a redirect or a
  second hop (give `click.url_pattern` the final URL), the new page's own consent banner (`after_nav`);
- what hides the item: a directory behind filters, tabs or infinite scroll (load it in `warmup` or `pre` steps);
- permission: a partner's page and mark are theirs. Film them for a joint announcement or with their yes.

Record the numbers with the date in `film.json` under `_recon` (JSON has no comments): pages change.

## 2. The capture block (film.json)

`filmkit.capture.run(cfg, timeline.json, raw_dir)` reads:

| Key | Use |
|---|---|
| `viewport` | a normal desktop shape with the window's proportions (1440 x 1100 for a 936 x 715 page area); never a tall one: pinned sections are a screen high and centre their content, so a tall window shows empty bands |
| `device_scale` | 2, always, for every frame: a scale switched mid-move shows as a sharpness pop |
| `reduced_motion` | `no-preference`: the page plays as its visitors see it |
| `block` | regexes aborted silently: analytics, ads, chat widgets |
| `count_block` | regexes aborted and counted as `posts`: form endpoints. A film never submits anything; the gate wants 0 |
| `pre` | steps before the film: `goto`, then decline the consent banner (`click_text` its decline button; the most private choice, always), optional screenshots of the banner as a record; `eval` runs page script; `"optional": true` skips a click whose target is absent (banners that show only in some regions) |
| `after_nav` | the same steps on the new page, after the click (its own consent banner) |
| `warmup` | scroll the page through once so lazy images and fonts are in before frame 0 |
| `rate0` | the playback rate until the first measurement |
| `click` | the real click's point, the URL pattern it must land on, a timeout |
| `after_nav_mouse` | where the real mouse rests on the new page (out of the way of hover states) |

A frame of the timeline may also carry `act`: steps run on that frame before its samples. `{"click": [x, y]}` is a
real click that stays on the page (a filter tab, a map's city, a carousel arrow), at the drawn cursor's tip, in
viewport px; `{"move": [x, y]}` moves the real mouse; `{"eval": "js"}` changes the page (an element hidden as it
leaves the page). `timeline.plan(..., acts={frame: [step, ...]})` writes them; `capture.json` records each act and the
URL at the end, and the capture gate checks that in-page clicks left the URL where it was. Keep the real mouse on
what it clicked while the film looks at the result (an open card may close when the pointer leaves), then send it to
rest off the content.

**An element that leaves the page** (a logo lifting out of the hero): draw it as a layer at exactly the page's place
and size, then hide the page's own copy one or two frames later (`eval` act). Order matters, and the plan gate checks
it through `events` and `order` in beats.json: the layer first, the hide after, never a frame with neither.

Per frame the capture moves the real mouse (so hover states are real), scrolls instantly to each blur sample (never
smooth scrolling: a probe that animates its own scroll measures the wrong place), waits two animation frames, and
takes a JPEG at quality 92. On the navigation frame it clicks for real, waits for the URL and the network to settle
and for fonts, and records where it landed.

## 3. Pacing: the page's time must match the film's

Capturing a frame takes 40 to 970 ms of wall time depending on its blur samples; the film shows each frame for
16.7 ms. CDP `Animation.setPlaybackRate` slows the page's animations to match, set before every frame from that
frame's sample count and the measured time per sample: `rate = frame_ms / (samples x ms_per_sample)`, clamped
0.02 to 1. The capture records `[frame, samples, wall ms, rate]` for every frame; `sv check capture` checks
that page time stayed within 0.67x to 1.5x of film time and was never off for 0.1 s.

One film's capture re-paced only every 30 frames, so on its ten-sample frames the page ran 5.8x fast, then 0.5x
and 0.2x as the average caught up. It was invisible under that film's motion blur and would not be under a slower
move.

The prediction is a fixed cost per frame plus a cost per sample, fitted to the last 30 frames, then corrected by the
median of the last three frames' actual over predicted time. A page that turns heavy is caught in two frames (a 3D
scene coming into view took frames from 80 to 188 ms at once; the average alone let the page run 2.3x fast for 20
frames), and a one-frame stall moves nothing (a 692 ms frame after a click; a mean of the errors slowed the page to
0.07x for five frames after it). The rate
may rise above 1 (to 4) when frames capture quicker than real time, as a draft of a light page does; capped at 1,
that page ran at half speed.

## 4. Gates and costs

```
sv check capture raw/capture.json --timeline timeline.json --expect-url 'example\.com/next'
```

Every capture on disk, posts 0, the click landed, pacing in band. A 685-frame capture with 1,296 screenshots took
about two minutes; a full render from it about ten seconds on ten cores. So capture once and compose many times:
on one film, eight versions came from four captures (one per change to the scroll or the blur), and the last four
versions, rendered over 19 minutes, from one.

Recapture only when the page itself must change in the film (a new scroll path, a new zoom past the 2x capture's
sharpness, about 2.5x on a 936 px window), never for a camera, timing or overlay change.

## 5. Pages that move by script

The playback rate governs CSS animations, transitions and Web Animations, and the timestamps
`requestAnimationFrame` hands its callbacks (and `document.timeline.currentTime`) slow down with it. Three kinds of
script motion follow from that:

- **Steps by the rAF timestamp only**: paced with the capture, nothing to do.
- **Reads `performance.now()` or `Date.now()` every frame, or runs on timers**: keeps wall time and plays fast
  relative to the film.
- **Mixes them** (starts at `performance.now()`, steps by the rAF timestamp): the most common hand-written tween, and
  the worst case. The first frame reads a time far in the past and the animation jumps backwards. On a map's 460 ms
  zoom the scale went to -12 on the click frame and the land left the view for the rest of the beat.

Set `"frame_clock": true` in the capture block for the second and third kinds: `performance.now()` then reads the
frame clock, so the page's own animation plays at its own curve and duration in the film (verified: the map's zoom
eased 1 → 2 over its 460 ms). Find which kind a page uses in recon: click it under a slowed rate and read the
animated element's transform for a few frames, or read the page's script for `performance.now`. `Date.now()` and
timers still keep wall time; for those, frame the motion out or capture with a virtual-time clock (a Playwright clock
installed before the page's scripts, advanced one film frame per capture). Say which in the brief.

**Videos keep wall time too.** A background reel under a capture rate of about 0.15 played 7x fast in the film, and
its own edits read as cuts in the file gate. Set `"media_rate": true`: every `<video>` plays at the capture's rate,
set before every frame (`tests/test_media_rate.py`: 1.30 s of video in 1.30 s of film, against 7.83 s without). In
recon, list the page's videos with their boxes (`document.querySelectorAll('video')`): a page can hold hundreds, of
which only the visible ones matter. Slowed playback can still stutter (a reel's frames arrived unevenly at a rate near
0.12, and the owner wanted the video to play as it does on the website): `"media_rate": "seek"` pauses
each visible video and steps it one film frame per captured frame, waiting for the seek, so the film shows the video's
own frames at its own speed.

**The page's own motion and the holds.** A hold is measured on the whole frame, so a page that keeps moving around
the words (a drifting collage, a background video, a rotating quote) never reads as settled. Give that beat a focus box
on the words and `"hold_on": "focus"` in `beats.json`. List the times of in-page clicks as `"reactions"`: a UI's
ease-out leaves rest at speed by design, and the rest gate skips the first 0.1 s after each.

## 6. Footage

`FootageSource(path)` gives frame-exact access (`frame(n)`, `at(t)`) through one ffmpeg pipe, and refuses two kinds
of file that would silently break a composite:

- **Variable frame rate** (phone and screen recordings usually are): make a constant-rate copy first,
  `ffmpeg -i IN -fps_mode cfr -r 60 -c:v libx264 -crf 12 -pix_fmt yuv420p OUT.mp4`, and use the copy.
- **HDR** (PQ or HLG transfer, common on phones): convert to SDR BT.709 first and compare one frame of the copy with
  the original by eye before using it. Composited as is, HDR footage looks washed out.

Keep the original untouched beside its working copy, with the command that made the copy. Probe every file first:
duration, size, rate, colour tags, audio streams.

## 7. Stills and marks

- Use the largest source of every image and mark, and only ever shrink it. An upscaled mark was soft (3 px edges
  against 2 px) beside a sharp one on the end card.
- Marks come from the owner's brand kit, never redrawn; the brand's layers (marks, the address bar, the foot row)
  are rendered from HTML at 2x by `filmkit.layers` with their boxes measured, so positions come from the render.
- Never paste a region from one capture into another. A header pasted from older captures made a sharp band that
  jumped every 40 px over a blurred scroll.

## 8. Where the time goes, and how to go faster

The wait is in the capture, not the render. On one 38 s film made in twelve rounds, from the brief to the owner's
yes in just under four hours, captures were the largest single wait. The session's 231 minutes split:

| Where | Minutes | What it is |
|---|---|---|
| Captures | 52 waited on, 23 more in the background | thirteen captures of 5.4 to 7.4 minutes: a real browser driven through every one of 1,951 frames, the page's own animations paced to film time, 3,143 screenshots at 2x (blurred frames take several) |
| The model | 72 | reading, deciding, writing code, gates and messages |
| The owner | 62 | watching each version and writing notes |
| Other tools | 15 | recon, measures, files |
| Renders | 7 | compositing all 2,292 frames on ten cores takes about 20 s |

So "rendering" was capturing. A capture costs about 52 ms per frame plus 91 ms per screenshot; a render is a rounding
error. As a benchmark (measured on an Apple M4 Pro laptop, 14 cores, 20-core GPU, October 2026):

| Setup | One 2x screenshot |
|---|---|
| headless shell, software rendering (the default) | 84 ms |
| the same through raw CDP | 90 ms (no gain) |
| a 1x screenshot | 33 ms |
| new headless, no flags | 262 ms |
| Chromium with Metal (`"gpu": true`) | 66 to 69 ms; it needs two animation frames of settle |
| one animation frame of settle instead of two, in the shell | the same pixels, 64 ms against 74 |
| two capture processes side by side | 96 to 97 ms each: 1.74x the throughput |

What to do with it, in order of payoff:

1. **Do not capture to judge a camera.** The camera map and the animatic come from the stitch (about 20 s once; the
   animatic renders in about 20 s): the camera, the timing and the framing, with the page frozen. On one film the
   animatic showed a heading under the page's nav exactly where the capture later did, on the same camera path.
2. **Judge direction on a draft capture** (`"draft": true`, `sv film DIR draft`): 1x, one frame of settle, at most
   three blur samples. On one film the draft took 2.4 minutes against the final capture's 6.5, and the whole film
   rendered from it in 14 s; the test fixture's took 4.8 s against 12.2. At half size the draft and the final are
   hard to tell apart; at full size, zoomed text shows stepped edges. For direction only, in its own folder.
3. **Capture the final once**, after the direction is the owner's; every camera, timing or overlay change after it
   re-renders in seconds.
4. **The GPU** (`"gpu": true`) takes a fifth off each screenshot. It is off by default: it needs Chromium's own
   channel, and its frames need two animation frames of settle.
5. **Shards** (not built yet): two processes gave 1.74x the throughput, so a capture split by time ranges could take
   about half the time. Each shard must rebuild the page's state at its first frame (the scroll, and every click and
   act before it), which is simple before the first in-page click and needs a replay after it.

The model running the session does not change the capture or the render time: they are bound by the browser and the
machine. A faster model only shortens the session's own work (the 72 minutes above). Keep the strongest model for the
choreography and the review, and hand mechanical side work (strips, diffs, checks) to sub-agents in parallel. The loop
itself (capture, render, look, the owner) is serial: each step needs the one before.
