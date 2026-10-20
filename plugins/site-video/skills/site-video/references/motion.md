# Motion: the maths that makes it feel physical

Everything here is in `filmkit/motion.py` as pure functions of time. The rule under all of it: **things start and
stop at rest, and nothing changes state while it moves.**

## 1. Easing

- `soft(u)`: in-out quintic (smootherstep), the default for every camera move the eye follows. Its peak speed is
  1.875x the move's average and its acceleration rises and falls without a jolt.
- `ease(u)`: in-out cubic, for a move that may snap: peak 3x the average, and its acceleration flips at the midpoint.
  Over dense content it read as a jump every time (section 9).
- `ease_out(u)`: out cubic, for arrivals (a title, a blur rising fast then settling).
- A press toward and back (a handshake): `d = A sin^2(pi u)`, which leaves and returns to rest. A linear press went
  from still to 2 px a frame in one frame and read as a twitch.

## 2. The stop scroll (one brake)

`stop_scroll(distance, t0, ramp, decel, t_end)`:

- speed rises as a smoothstep, `3x^2 - 2x^3`, over `ramp` seconds;
- cruises at `vmax`;
- falls as `vmax (1 - x)^3` over `decel` seconds, which reaches rest in one curve, like a fling;
- `vmax = distance / (ramp/2 + cruise + decel/4)`, so the distance is exact by `t_end`.

Why not a curve through keyframes: a monotone cubic through (2.95 s, 520), (3.85 s, 5750), (4.4 s, 6258) dropped
from 50 to 16 px a frame in 0.14 s, crawled at 15.7 for seven frames, then braked again. The owner flagged it as
clunky and jumping, and the measure showed why: deceleration that falls and rises again is two brakes. The gate: no
re-rise over 15%, no plateau inside the brake.

At its very end a stop creeps in whole-pixel steps (the browser rounds scroll positions): about 0.65 px each on
screen, invisible on a phone. The gates ignore steps under 2 px; do not chase them.

## 3. The camera

Keys are `(t, zoom, centre_x, centre_y, mode)`; between two keys the zoom is interpolated in log space (equal
ratios feel like equal speeds), the centre linearly, on `'soft'` between framings (`'io'` only for a snap the owner
wants, over sparse content), linear (`'lin'`) for the slow push inside a hold. Every hold pushes 1 to 1.5%: a hold
that is a freeze reads as a stall.

`crop_at(cam, t, vw, vh, padx)` keeps the crop inside the page, except that it may run `padx` px past the page's left
edge, where the compositor continues the page's own ground. Use it to centre a subject near the page's edge rather
than show a neighbour. On one film a zoom that showed part of the next card was flagged; the fix was white space on
the left so the subject sat centred.

Zoom limits: the capture is 2x, so text stays sharp to about 2.5x on a 936 px window; a 3x push is soft but readable
for a held beat. Never crop a destination page's own margins: at 1.05 the page lost its side margins and the owner
asked for them back.

## 4. Motion blur from samples

A 180-degree shutter: each frame averages captures spread over half a frame of the scroll, centred on its time.

```
travel = |scroll(t + 1/(4 fps)) - scroll(t - 1/(4 fps))| x window_width / (viewport_width / zoom)
n = 1 if travel < 1 else min(10, ceil(travel / 3) + 1)
```

- The blur fades with the speed. An early build switched blur off at 6 px of travel and the page sharpened by
  half in one frame (measured at phone size: 5.96 to 8.92 at 4.10 s).
- Every capture at 2x, always. A scale that switches while the page moves is the same pop by another route.
- No blur across a navigation: the window ends where the page changes.
- At 1080 the samples show as stacked copies about 3 px apart on the fastest frames; at phone size they blend.

## 5. The cursor and the click

- A quadratic bezier from an entry point to the target, eased (`bezier_cursor`). It enters inside the frame and
  fades in over 0.2 s: one that entered off-frame first appeared already moving 77 px a frame.
- The tip rests on the link's lower right (the arrow), never on its words.
- The press: the cursor shrinks 14% and back over 0.16 s (`1 - 0.14 sin(pi u)`).
- The ring: from 10 to 40 px radius (ease-out), 7 px wide, fully opaque on its first frame, fading as `(1-u)^1.2`
  over 0.4 s, in the accent colour, white on an accent-coloured button (a ring the colour of its button vanishes).
- The page changes 0.15 to 0.4 s after the press: the viewer must see the press first (0.30 s shipped).
- Across the cut the cursor and ring stay where the click was and fade over 0.2 s on the new page, carrying the eye.

## 6. Titles and light

- A title never arrives over sharp words: the blur and veil rise first, fast (ease-out over 0.3 s), and the title
  starts once the page is about 70% blurred.
- The opening blur kills the page's words and keeps its motion visible: 12 px in motion, 9 on a still cover; 6 and
  3 let the page's headline compete with the marks.
- A title enters as a fade with a scale from 0.94 about its own centre; a stack enters staggered by 0.1 s.
- Highlight with light, not lines: `breathe(u)` fades a glow in over 0.35 s, then pulses once a second (alpha 0.62 to
  1.0, blur 9 to 16 px), drawn outside the box only and clipped to the window, as if from behind it.

## 7. Transitions

- Cut only on an action (a click). Every other change is a move or a fade with the next element already moving.
- Never a blank beat: when the window fades, the marks are already travelling; a 0.15 s fade through white read as
  a gap.
- The end card forms from the scene: the ground becomes a framed card (inset 0 to 22 px, radius 0 to 32 px), the
  marks come home in the hook's order, the foot row last.

## 8. Measuring motion

- **Speed on screen** (`sv check speed`): the moving area split into 9 column bands, each squeezed to one value
  per row; consecutive profiles matched by shift with a sub-pixel parabolic fit. Without the fit the measure has a
  1 px floor and reports a stopped page as creeping.
- **Sharpness at phone size**: the mean vertical difference between neighbouring rows after scaling to 390 px. Judge
  a pop by its absolute rise and its relative rise together: at low levels a relative rise alone is noise.
- **First step from rest**: block matching on the blocks that changed; a step counts only when one integer shift
  explains the block, so a sub-pixel scroll step reads as rest and a kicked element as its kick.
- **The motion profile** (`filmkit.profile`, `sv check motion`): from the plan alone, before any capture, the
  on-screen speed of the worst of nine window points (corners, edge centres, centre) per frame, as zoom, pan and
  scroll move the page under the window. Every number in section 9 is this measure, in px per frame at 60 fps in
  the 1080 frame.

## 9. The motion standard: what the owner flagged, what was kept

Calibrated on sixteen versions of one overview film: every camera move the owner commented on, profiled through the
film's own maths, beside the moves that were kept. Content density is the mean edge strength of the destination's
page (FIND_EDGES on grey at 480 px wide, from the stitch); dense from 12.

| Move | Peak px/f | Peak over mean | Near-stop | Content | Verdict |
|---|---|---|---|---|---|
| a card, zoom in (`io`) | 45.2 | 2.7 | | dense, 14.3 | flagged: wanted smoother |
| the same, longer, same curve | 30.4 | 2.6 | | dense, 14.3 | flagged again: still jumped on the zoom in |
| the card, out and scroll | 47.7 | 3.3 | 4.1 px/f | dense | flagged: too harsh on the zoom out and the scroll |
| the map, zoom out | 60.2 | 3.5 | 2.5 px/f | | flagged: smoothen a touch |
| the numbers, pull out | 86.3 | 6.0 | 1.8 px/f | dense, 12.3 | flagged: the snap was liked, but a touch too sharp |
| the numbers, dive | 76.4 | 2.7 | | sparse, 7.9 | kept |
| a card on the map, dive | 54.9 | 2.6 | | sparse, 9.6 | kept |
| the numbers, pull out (`soft`) | 41.1 | 2.5 | | dense, 12.3 | kept |
| the closing zoom | 31.1 | 2.5 | | dense, 18.3 | kept |
| the map, zoom out (`soft`) | 26.6 | 1.8 | | | kept |
| the card, zoom in (`soft`) | 15.1 | 1.8 | | dense | kept |
| the card, zoom out (`soft`) | 18.8 | 1.7 | | dense | kept |

The settings of the version behind the second and third rows were not saved; those two rows are profiled from the
next version's settings, which changed only the ending (the decoded frames of the two versions are identical over
the moves concerned).

What it says:

1. **A near-stop between two moves is the loudest fault.** Three of the five flags had one: the speed falling under a
   quarter of the moves either side, for under 0.25 s, next to a move faster than 35 px a frame (the flagged ones
   rested 0.07 to 0.12 s). A rest of 0.37 s or more between two moves reads as a hold and was never flagged. The plan
   gate "moves join without a harsh stop-and-go" fails exactly the flagged versions.
2. **Over dense content the curve and the peak decide.** Each flagged move without a near-stop crossed dense content
   on the in-out cubic at 30 px a frame or more. The same moves on `soft` at 15 to 19 px a frame were kept. From 20
   to about 31 over dense content the owner sometimes kept a move: the plan prints a WARN, answered in the
   choreography sheet with a fix or a "kept because".
3. **Over sparse content, fast reads as energy.** A dive onto three big numbers at 76 px a frame was kept in every
   version without a note, and even the flagged pull out was half liked: the owner asked for a touch less, not for
   less snap (`soft` at 41 px a frame was kept). Speed is judged against what the eye is trying to read while it
   moves.
4. **Length alone never fixed a jump.** A zoom given more time on the same curve kept its 3x peak and was flagged
   again. Change the curve, then the length.

**The duration rule**, before a key is written:

```
T  >=  k x D / (P x fps)
```

- `D`: the worst window point's travel on screen, in px (a zoom moves the corners, a pan and a scroll move all).
  `sv check motion` prints it per move, or estimate it from the two framings.
- `k`: the curve's peak over its mean: 1.875 for `soft`, 3 for `io`, 1 for `lin`.
- `P`: the peak allowed: 20 px a frame over dense content, 60 over sparse.

A dive whose corners travel 600 px on screen needs 0.94 s on `soft` over a dense section, 0.31 s over three big
numbers. A pull out that leads into a scroll overlaps it, so the speed climbs once. `sv check plan` does the
sum for every fast move over dense content: its WARN line names the length the move needs at 20 px a frame, on its
own curve and on `soft`.
