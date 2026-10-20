# Choreography: a site film, beat by beat

A worked example, as shipped: a proof film of 14.8 s, 1080 x 1080, 60 fps, silent. A partner's hub page lists the
brand's programme among its schools; the film finds the listing and clicks through to the programme's page. Every
number is in the film's `film.json`; the reasons are here, because the numbers will change and the reasons will not.

## An overview film is a choreography, not a tour

One overview film (a whole community page, about 35 s) first went out as a scroll from section to section with the
same hold of about 1 s on each and gentle pushes. The owner sent it back asking for more zooming in and out: a
choreography, not an even tour. What the next version did instead, one move per section, varied:

- **Dive and pull out**: from the section whole, in close (2 to 2.6x) on its one thing (a card, a video wall), then
  back out to place it. The capture at 2x carries about 2.7x on a 960 px window before it upsamples.
- **Glide**: in close, then travel along a row (numbers, cards) and back out.
- **Reveal**: in tight on a detail (a trophy) as the section lands, then a slow pull out that reveals the whole.
- **Quick pass**: a short stop at 1x between big moves, so the big ones read as big.
- **Soft curves on the dives**: a dive, a glide or a pull out is a `soft` key (peak speed 1.9x the move's average),
  not `io` (3x). On one film a 1.4 s zoom on `io` was flagged as a jump twice; on `soft` it passed. Length did not
  fix it, the curve did.
- **A pull out flows into the next scroll**: start the scroll while the camera is still pulling back, on a ramp of
  about 1 s, so the speed climbs once. A click on the page's own slider starts the pull back: the slide and the camera
  move as one.
- **The longest beat goes to the most cinematic section**, not to the one with the most clicks.
- **Ground**: the opening is the page's hero, full bleed (its colour to the frame's bottom); once the page steps back
  into its window the ground is white, with a hairline and a soft shadow giving the window its edge. The mark above
  the window sits in a band with equal air above and below it, and the window's bottom margin equals its sides.

Write the beat list in this vocabulary and get the owner's yes before capturing (SKILL.md section 2, A1).

## The choreography sheet and the camera map

The sheet is one line per beat, in the order the viewer sees them:

| Time | Beat | Where on the page | Move | Curve and length | Holds on | Why |
|---|---|---|---|---|---|---|
| 5.2 to 5.8 | the numbers | the stats row | dive to 2.3x on the first two | `io` 0.6 s, sparse: a snap | 0.3 s, then glide | fast over sparse reads as energy; kept through every round |

The camera map is the same choreography drawn on the page: the whole page from the stitch (`sv film DIR stitch`,
about 20 seconds), every hold's window on it, numbered, the camera's path between them, and in red every line of text
a hold cuts (`sv check map timeline.json --stitch STITCH_DIR --beats beats.json --out map.png`). The owner reads where
the camera stops and what each stop shows in one picture, before a capture exists, and moves a stop with a word. Send
the map and the sheet together; then the animatic (A2).

## Framing a stop

- **A stop shows its section between its neighbours' words.** Measure the last line of text above the subject and
  the first below it (the stitch lists every line with its box) and keep both out of the window, or wholly in it. A
  cut word reads as a mistake on a still frame: on one film the closing hold showed an FAQ question cut at the
  window's top and left (the start of the line missing) for 2.2 s, and the plan gate now fails it.
- **When a section cannot be framed whole at the zoom**, frame it from its top edge and let the picture run off the
  bottom (a landscape, a photo), never the words. The closing line then sits in the upper third with its landscape
  below it, the section's own composition.
- **The page's fixed nav covers the top of every view**: a heading must sit clear under it (8 css px at least), or the
  stop moves. A view whose nav cut the top of a section header was flagged.
- **No sliver of a neighbour**: a card in a row shows whole, or at a quarter or more, or not at all.
- **Never hold on a competitor** on someone else's page, and never let a zoomed-out stop open on one. Lead with the
  owner's item and pass the others: a zoomed-out view that opened on a rival's card was flagged late and cost a round.
- **A moving page is not a framing fault.** A drifting collage's notes cross the window's edge as they float; the
  cut-text gate reads the page at rest, so answer those lines with that reason.

## Endings that worked

- The page fades while its key line stays, lifted out of the page in place (the page's own copy painted out under
  it the moment it lifts, or it shows twice); the line moves to the centre on the white ground, its paper turned
  exactly white (a 1 to 3 level box showed otherwise).
- A highlighter on that line in the brand's hero colour, swept left to right line by line and multiplied into the
  page, so the words stay ink.
- The mark from the top and the address from the bottom meet in the middle as the line leaves; then the click on the
  address: in fast, out softer, on a soft shadow, so the click reads as going in and coming back out.

## The frame

- A browser window, 936 x 751, at (72, 185) in the 1080 frame, with a 36 px address bar showing the real host. The
  page area is 936 x 715, the same shape as the 1440 x 1100 capture viewport (scale 0.65), so nothing is stretched.
- Outside the window: the brand's ground and a soft shadow. The marks sit in the frame's top corners, their outer
  edges on the window's edges (72 and 1008), their centres level.
- Every frame of the page is resampled once from the 2x capture (LANCZOS) and then sharpened lightly (unsharp
  r 0.7, 70%, threshold 2): resizing softens; the unsharp gives back what it took.

## The beats

| Time (s) | Beat | What moves | Why |
|---|---|---|---|
| 0.00 to 2.00 | hook | the host page's hero, zoom 1.45 on its headline, pushing 1.5% (linear) | a hold is never a freeze: a slow push keeps it alive |
| 0.68 to 0.98 | hook | blur 12 px and a white veil at 55% rise over the page, ease-out (fast first) | the title must never arrive over sharp words (review: two wordmarks overlapped in the first second) |
| 0.80 to 1.28 | hook | the stack comes in: partner mark, the x, the brand's mark, each 0.3 s, a fade with a scale from 0.94 about its own centre, staggered 0.1 s | the host of the news leads; a stagger reads as a sentence |
| 2.00 to 2.65 | context | the blur clears while the marks travel to the corners; the x leaves first (0.25 s) | the page returns as the brand steps aside: no beat is blank |
| 2.45 to 4.45 | context | the scroll: hold, a 0.35 s smooth start, a cruise, one 1.1 s ease-out, 6,258 px in all, 68 px a frame at its fastest | one motion, like a fling; an earlier two-stage curve braked twice and was flagged as jumpy |
| 2.00 to 2.70 | context | the camera pulls back from 1.45 to the whole page, eased | the zoom-out overlaps the scroll's start so the cut from hero to page is one gesture |
| 4.45 to 5.10 | context | the section held whole | 0.8 s settled with the brake's tail: a glance |
| 5.10 to 5.80 | proof | zoom to 1.9 on the listing card, eased, the card centred | centre the subject; past the page's left edge the page's own white continues (`padx`) rather than showing a neighbour's card |
| 5.72 on | proof | a light breathes round the card, outside it only, once a second | highlight with light, not lines: a stroke round the card was turned down for a pulsing light |
| 5.80 to 6.50 | proof | a 1% push in the light | |
| 6.50 to 7.10 | proof | a second push, to 3.0, onto the card's title, words and link | at 1.9 its words were 7 px on a phone; at 3.0 the body's line band is 29 px |
| 7.10 to 8.42 | proof | 1.5% push; the key hold, 1.35 s settled | the fact is read here or nowhere |
| 7.45 to 8.05 | action | the cursor enters inside the window (fade 0.2 s) and travels a quadratic bezier to the link, eased | it entered off-frame once and first appeared already moving 77 px a frame |
| 8.12 to 8.28 | action | the press: the cursor shrinks 14% and back (half a sine over 0.16 s) | |
| 8.12 to 8.52 | action | the ring grows from 10 to 40 px, 7 px wide, fully opaque on its first frame, fading | a faint ring reads as nothing (a launch review found the click read weakly) |
| 8.42 | destination | the cut: the real click's page; the address bar changes with it | the press shows 0.30 s before the page changes |
| 8.42 to 8.62 | destination | the cursor and ring stay where the click was and fade on the new page | they carry the eye across the cut |
| 8.42 to 9.15 | destination | the landing, zoom 2.0 on the headline, 1% push; framed to its own words (32 and 47 px clear above and below) | a new page gets its own camera, never the last page's zoom carried over |
| 9.15 to 9.90 | destination | pull back to the whole page at 1.0, eased | at 1.05 the page lost its side margins and the owner asked for them back |
| 9.90 to 11.00 | destination | the whole page held | |
| 11.00 to 11.40 | sign-off | the window fades and shrinks 3% | |
| 11.05 to 11.95 | sign-off | the marks travel from the corners into the stack, eased, already moving while the window fades | no blank white between scenes (a 0.15 s fade through white was flagged) |
| 11.15 to 11.75 | sign-off | the ground becomes a framed card: inset 0 to 22 px, radius 0 to 32 px, a hairline and a soft shadow | |
| 11.78 to 12.22 | sign-off | the handshake: the marks press 12 px toward each other and settle, 12 sin^2(pi u) | from rest to rest; a linear press read as a twitch |
| 11.95 to 12.13 | sign-off | the x lands on the frame they meet, from 1.4x | |
| 12.15 to 12.65 | sign-off | the foot row: a hairline, the title on the left, the link with its link icon on the right | |
| 12.65 to 14.80 | sign-off | held still, 2.2 s | the end card's floor is 2.0 s |

## The end card's geometry (measured on the encoded file)

- The stack is centred on the card (539.5); 262 px above it, 264 px below it to the hairline.
- The x sits evenly between the marks (78 and 75 px); the partner mark is centred by its ink weight, not its box
  (a descender pulls a box off centre: render 0, 8 and 15 px shifts at phone size and pick).
- The hairline runs 70 to 1009; the foot strings sit on one baseline, 34 px, their ends on the hairline's ends.
- Marks are drawn at their largest size and only ever shrunk: an upscaled mark is soft beside a sharp one.
- The opening stack is the end stack at 85%, centred on the window: smaller than the end card so it does not
  crowd the window's edges.

## What the timeline does not do

- No scene is a freeze: every hold has a 1 to 1.5% push.
- No element starts or stops at speed: ease, ease-out or sin^2 at every end.
- No blank beat: when one thing fades, the next is already moving.
- No cut without a cause: the only cut is the click's.
