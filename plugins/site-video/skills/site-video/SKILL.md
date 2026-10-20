---
name: site-video
description: >-
  How to make a video that looks produced: a film of a real website (scroll
  through the website, zoom in on a section, click through to the next page,
  the Screen Studio look, captured frame by frame with the site's own motion),
  a story film with motion design built from footage and stills, and the edit
  of a recorded workshop or talk for YouTube. Use whenever someone says "make a
  video", "video editing", "a video of the website", "a video of this page",
  "scroll through the website", "zoom in", "Screen Studio", "motion design for
  the video", "edit the workshop for YouTube", or asks for a LinkedIn or launch
  video, a video's cover or thumbnail, whether an export is right for LinkedIn
  or YouTube, or why a video looks jumpy, soft or compressed after upload.
  Covers the story (one sentence, six beats), the choreography, capture, motion
  physics, compositing, the measured gates and delivery. Not for adding
  animation to a web page's own code, and not for a short captioned clip of a
  call.
allowed-tools: Bash(${CLAUDE_PLUGIN_ROOT}/skills/site-video/scripts/sv doctor:*), Bash(${CLAUDE_PLUGIN_ROOT}/skills/site-video/scripts/sv check:*), Bash(${CLAUDE_PLUGIN_ROOT}/skills/site-video/scripts/sv film:*)
---

# Site video

A film here is made, not recorded. The real page is captured frame by frame as it plays; the camera, the cursor and
the titles are composed in code; every frame is measured before anyone sees it. Because a capture is reused by every
render, a round of changes costs seconds, not a new recording.

**The launcher.** Every command runs through `sv`: this skill's `scripts/sv`, under the base directory shown when the
skill loads (write the full path in each command). It runs the skill's own Python environment with the skill's code on
the path, so a film never needs a path to the code.

- First time on a machine: `sv setup` (makes `~/.site-video/venv` with exact versions of Pillow and Playwright, and
  downloads Playwright's Chromium: ask the owner before it runs), then `sv doctor`. Every line must be PASS; each
  FAIL prints its fix (Command Line Tools, Python 3.9 to 3.13, ffmpeg and ffprobe, about 5 GB free disk).
- `sv new DIR` starts a film folder from the overview template. `sv film DIR COMMAND` runs the film's commands
  (`references/film-folder.md`). `sv check COMMAND` runs the gates. `sv test` runs the skill's own tests.
- A capture takes minutes (5 to 7 for a 35 s film at 2x). Run captures and full renders in the background and wait for
  them to finish; a command's time limit is shorter.
- Pages behind a sign-in cannot be filmed: the capture's browser starts with no cookies. Consent banners are declined
  by their button text in the capture's steps.

## 0. Name the film

| Kind | What carries it | Length | Sources |
|---|---|---|---|
| **Site film** (a proof) | a real page shows one fact; the camera finds it; a real click carries the viewer to the destination | 10 to 20 s | `CaptureSource` |
| **Tour** | a whole page as it plays | 20 to 40 s | `CaptureSource` |
| **Overview** | one page's story: the hero, its key sections as dives and glides, a closing line, the mark and the address | 30 to 40 s | `CaptureSource`; the overview template |
| **Story film** | a person's story told with footage, stills and type, motion design between them | 30 to 90 s | `FootageSource`, `StillSource`, layers |
| **Edit** | a long recording cut to its best minutes (a workshop for YouTube) | 3 to 20 min | footage, a cut list, captions |

A proof beats a tour. A 30 s tour of a brand's own page was out-performed by a 15 s film that showed one fact on a
partner's page and clicked through to the brand: the story did it, not the length. If the brief is "show the page",
ask what the viewer must believe at the end, and film that.

Name the mode before work starts: studio (finding the film), build (executing a locked storyboard) or verify
(measuring). A round of notes from the owner is build; a new film is studio.

## 1. The sentence and the beats

Write the film as one sentence before anything else: what the viewer knows at the end that they did not know at the
start. Then cut it into beats, each with one job and a role that sets its floor:

1. **Hook** (0 to 2 s): the brand in the first second. A brand that appears only after five seconds is a brand most
   viewers never see.
2. **Context**: where we are (the partner's page, the event, the room).
3. **Proof**: the one fact, framed and held long enough to read.
4. **Action**: something happens because of it (a click, a handshake, a turn).
5. **Destination**: where the action lands, framed for that page, not the last page's camera carried over.
6. **Sign-off**: the bookend. The marks return in the order the hook used, so the end answers the opening.

`references/story.md` has the sentence, the beat sheet, the storyboard and the questions to ask the owner.

## 2. The order of work

Two phases, in this order. **Art first: the owner agrees the choreography, then sees a rough cut quickly. Only then
the refinement to a pixel-perfect film.** Captures, gates and an independent review spent on a direction the owner has
not seen are hours at risk: the first film made this way was refined for forty minutes in a direction its owner then
turned down.

**Phase A, the art (the owner in the loop at every step).** Each step costs less than the next, and none needs a gate
beyond "it plays and nothing is blank":

- **A0. Three questions**, in the first message, each with a proposed answer the owner can take with a yes
  (`references/story.md` section 5): who watches it, where, and whose brand leads; what they must remember and what
  the film must never dwell on; where the camera stops and how it ends.
- **A1. The choreography sheet and the camera map.** `sv new DIR`, then the page's recon (`sv film DIR recon`) and the
  whole page stitched (`sv film DIR stitch`, about 20 seconds). The sheet: one line per beat, what the frame shows,
  the move, its curve and length, where it holds (`references/choreography.md`). The map: the same choreography drawn
  on the whole page, every stop numbered, the path between them, and in red any line of text a stop cuts
  (`sv check map`). `sv check plan --stitch` runs here, on the plan alone: the motion standard and the framing. A film
  is a choreography of dives, glides, reveals and quick passes, never an even scroll from section to section.
- **A2. The animatic** (`sv film DIR animatic OUT.mp4`, about 20 seconds from the stitch): the camera, the timing and
  the framing in motion, without the page's own motion (videos, carousels and clicks are frozen). The owner judges the
  rhythm.
- **A3. The draft** (`sv film DIR draft`: a 1x capture, about 2.5x quicker than the final's; then
  `FILM_SOURCE=draft sv film DIR all OUT.mp4`): the page's own motion and the real clicks, soft, labelled rough. The
  owner's notes change the choreography; a camera or timing note re-renders from the same capture in seconds. Repeat
  until the direction is the owner's.

**Phase B, the refinement (pixel perfect), only after the owner's yes on the direction.** Each step ends at a gate;
nothing moves on with a failing gate or an unanswered WARN.

1. **Brief**: the owned words (every string on screen comes from the owner, character for character), the formats,
   the platform; the questions in `story.md` section 6, one at a time.
2. **Recon**: measure the real page at the capture viewport: section tops, the boxes the camera will frame, the link
   it will click, consent banners, what loads late (`sv film DIR recon`). Never guess a page position; the stitch
   lists every line of text. The brand layers come from the page itself (`sv film DIR chrome`): its own mark and its
   address in its own font, never redrawn.
3. **Timeline**: `film.json` (numbers), `film.py` (the film's own scenes), and `beats.json` (each beat's role, start,
   end, the box the eye must read, the subject it frames); `references/film-folder.md` has every file and key.
   `sv check plan --stitch` gates the motion design before a single frame exists (blur, capture scale, brakes, the
   motion standard, the framing, cut text, the click's lead); holds and text size are gated later, on the file.
4. **Capture**: `sv film DIR capture`, once. Gate: `sv check capture` (every frame on disk, no form sent, the click
   landed, the page's time paced to the film's).
5. **Keys**: render storyboard frames (`sv film DIR keys`), look at them at phone size, show alternatives as stills.
6. **Render**: `sv film DIR all OUT.mp4`. Gate: `sv check file OUT.mp4 --beats beats.json`, which writes the PASS
   sidecar. A failing gate is fixed or answered (`references/review.md` section 1), never renamed away.
7. **Independent review on the exact cut that will leave, before it is called final, even after the owner's yes**:
   this plugin's `film-reviewer` agent (or any agent that did not build the film) with the brief in
   `references/review.md`; its verdict goes into the sidecar (`sv check review OUT.mp4 --verdict pass|fix --by
   film-reviewer`). Fix, then show.
8. **The owner's round**: the note in the owner's words, the change, the measurement, recorded per version.
9. **Delivery**: the upload copy, the email copy when it will be attached, the cover (`sv film DIR cover`), the record
   (`references/delivery.md`). Every file that leaves has a PASS sidecar for its own bytes, with the review's pass in
   it.

## 3. The floors

Every floor is a gate in `film_check.py`, calibrated on renders whose faults were known: each gate fails its known-bad
file and passes the good one. Numbers are at 1080 px wide and 60 fps.

| Floor | Value | Why |
|---|---|---|
| Hold, glance | 0.7 s settled | a landing held 0.38 s read as a flash |
| Hold, read or key | 1.0 s settled | a price held 0.27 s was never read |
| Hold, end card | 2.0 s settled | an end card held 1.0 s went by too fast |
| Text on a held beat | median line band 24 px (provisional) | 13 to 18 px read as 7 px on a phone; 27 to 29 px passed |
| Every move starts from rest | first step under 2 px | a handshake that left rest at 2 px a frame read as a twitch |
| One brake per stop | deceleration never rises again by 15%, no plateau inside the brake | a stop that braked twice was called clunky and jumping |
| No sharpness pop | no one-frame rise of 1.5 and 30% in vertical sharpness at 390 px | blur switched off at 6 px: +50% in one frame |
| Cuts only where declared | no frame difference spike outside the film's cuts | |
| No blank beat | never under 0.5% ink in the centre for 0.1 s | a fade through white between scenes |
| Blur follows speed | no sharp frame moving over 3 px; capture scale constant while moving | |
| Moves join | no near-stop (under 25% of the moves either side, shorter than 0.25 s) next to a move over 35 px a frame | three of five motion notes on one film were such joins, called too harsh or too sharp |
| Camera speed | `soft` curves; over dense content a peak of 20 px a frame (a WARN to answer up to about 31) | `references/motion.md` section 9: every flagged move without a near-stop was the in-out cubic at 30 px a frame or more over dense content |
| Framing | the subject clear of the page's fixed nav by 8 css px; centred within 8 px or 2%; no neighbouring card as a sliver (under 25% or 40 px) | a section header cut under the nav, and uneven left and right margins, were both owner notes |
| No text cut at a hold | no line of text cut by the window's edge at a hold of 0.5 s (a WARN from 0.25 s) | an approved film's closing hold showed a question cut mid-word |
| The press shows first | 0.15 to 0.4 s between the click and the page change | |
| Capture paced | page time within 0.67x to 1.5x of film time, never off for 0.1 s | a capture re-paced every 30 frames ran the page 5.8x fast |
| Nothing sent | no form post during capture; the click landed on the expected URL | |
| Delivery | H.264 High, yuv420p, constant frame rate, BT.709 primaries, transfer and matrix, fast start, silent unless sound is wanted, no tool traces | early files lacked two of the three colour tags |
| Cover | under 1% of the page darker than L 200 under each title box | a mark sitting on dark photos: 6.9% failed, 0% passed |

The floors are the minimum, not the film. A film that passes every gate can still be dead: the story, the camera and
the timing are design work (`references/choreography.md`).

## 4. The tools

**The overview template** (`templates/overview/`, copied by `sv new DIR`): a whole film of one page, the hero playing,
the page stepping back into a browser window with its address, the page's own mark lifting out and docking above it,
dives and glides with real clicks, a highlighted sentence, and the mark and the address meeting at the end. Every
number is in `film.json`, every brand value in `brand.json`. Its settings film a small demo page inside the folder
(`demo-site/`), so a first film works offline; for a real film, point `capture.pre`'s first step at the page, run
`recon` and `chrome`, and choreograph from there (delete `demo-site/`). The demo film, start to finish (a 31.5 s
film; the capture takes a few minutes, so run it in the background):

```
sv new DIR
sv film DIR chrome                  # the demo page's mark and address, rendered by the browser
sv film DIR stitch                  # the page at rest: the camera map and the cut-text gate need it
sv film DIR timeline
sv check plan DIR/timeline.json --stitch DIR/raw-stitch --beats DIR/beats.json
sv film DIR capture
sv check capture DIR/raw/capture.json --timeline DIR/timeline.json
sv film DIR all DIR/out/demo.mp4
sv check file DIR/out/demo.mp4 --beats DIR/beats.json
```

Every gate passes on the demo as shipped. Its `film.json` shows how each framing was derived from the page's boxes
(`references/film-folder.md`, "From recon.json to the numbers").

**filmkit** (`scripts/filmkit/`), the library every film uses:

| Module | Holds |
|---|---|
| `motion` | ease, soft (the calmer in-out for camera moves the eye follows), ease_out, prog, the stop scroll (one ease-out), log-zoom camera keys (`io`, `soft`, `lin`), the crop, the bezier cursor, the blur-sample planner, breathe (a light that pulses) |
| `profile` | the motion profile from the plan alone: the worst window point's on-screen speed per frame, its moves, near-stops and kind (zoom, pan, scroll) |
| `timeline` | plans and writes `timeline.json` from the film's scroll, camera and cursor functions |
| `capture` | the frame-by-frame Playwright capture: motion on, consent steps, warm-up, per-frame pacing, the real click, blocked and counted requests; `draft` (1x, one frame of settle, three samples) and `gpu` (Chromium with Metal, macOS); `stitch`: the whole page at rest, its nav and every line of text; `page`: a page prepared the same way, for recon and the brand layers |
| `sources` | `CaptureSource` (blur samples averaged, any capture scale), `StitchedSource` (the animatic's page), `FootageSource` (any video, frame-exact; refuses variable frame rate), `StillSource` |
| `compose` | layers placed sub-pixel exact, travel, scale about a centre, the framed card, the cursor and its click ring, the glow, the window |
| `layers` | brand layers (logos, bars, foot rows) rendered from HTML at 2x with their measured boxes |
| `encode` | the ffmpeg writer: libx264 slow, crf 14, High 4.2, BT.709 tags, fast start, clean of tool traces by default; the render record (each input's checksum, the plugin version) |

**The gates** (`sv check`): `plan` (with `--stitch`: the motion standard, the framing, cut text), `capture`, `file`
(the gates and the sidecar; answers in `beats.json`), `review` (the reviewer's verdict in the sidecar), `cover`, `same`
(decoded frames identical), `path` (one plan's camera in two renders: the animatic against the final), `map` (the
camera map), and the instruments `motion`, `speed`, `sheet`, `platform` (a re-encode simulated), `eval` (a calibration
set: cases that must fail or pass). `scripts/email_copy.sh` writes the email copy.

**A film folder** (`references/film-folder.md`) holds `film.json` (every number), `brand.json` (the brand's values:
the plugin holds none), `beats.json`, `film.py` (the film's own scenes on filmkit), `chrome/` (its brand layers) and
`raw/` (the capture: large, kept out of git, with a checksum manifest in git). A film that is reproduced from its folder
frame for frame is a film whose next version is safe to make.

## 5. Rounds with the owner

- **Agree the choreography, then show a rough cut, then refine** (section 2). Hours of gates on a direction the owner
  has not seen are hours at risk.
- **Show renders, not questions.** Storyboard frames before a full render; alternatives as stills at the size they
  are seen (three to five, one recommended); the full film in a review page with a phone-width view.
- **Record each round**: the owner's words, the change, the measurement that proves it. A note like "it jumps" is a
  measurement to make (speed and sharpness per frame), not a parameter to nudge.
- **Two strikes**: the same note twice means the diagnosis is wrong. Measure the exact frames before a third change.
- **Review before the owner sees the final**: the independent reviewer catches what the maker cannot see (on two films
  about twenty defects: short holds, 7 px text, an under-scaled end card, a jolt, a title before its blur, upscaled
  logos, a cursor entering off-frame, missing colour tags, a blank beat).
- **A reviewer's fix is a proposal.** One reviewer's zoom cost the destination page its margins, which the owner then
  asked for back. Check every fix against what the owner has already said.
- **The owner's yes is not the review.** Run the independent review on the exact cut that will leave: on one film it
  found eight defects after the owner had called the film perfect.
- **The owner's words, or nothing.** Never tell the owner they accepted something without their words in the record: a
  summary is not a source.

## 6. Limits, stated

- Page motion driven by JavaScript (GSAP, Lenis, canvas, video) is not slowed by the capture's playback rate; only
  CSS animations, transitions and Web Animations are. For such a page, capture with a virtual-time clock instead and
  say so in the brief. `frame_clock` and `media_rate` (`references/capture.md`) cover the common cases.
- Two captures of the same page differ a little (the page's own animation follows the wall clock until the pacing
  starts); renders from one kept capture are identical. Keep the capture.
- Sound: the films so far are silent (feeds autoplay muted). A film with speech gets burned-in captions and loudness
  to -14 LUFS, -1 dBTP.
- The text floor is provisional: one known-bad and one known-good film calibrate it.
- macOS is the tested platform. Linux should work; Windows is not supported.

## References

| Read | When |
|---|---|
| `references/story.md` | before anything: the sentence, beats, storyboard, owner questions, the film kinds |
| `references/choreography.md` | designing the timeline: a worked film, beat by beat, with timing and reasons |
| `references/film-folder.md` | setting up a film: each file, film.json's keys, the coordinate spaces, the film's commands |
| `references/capture.md` | capturing a live site, taking in footage and stills, and where the time goes |
| `references/motion.md` | the maths: the stop scroll, the camera, blur samples, the cursor, the ring, rest to rest, the motion standard |
| `references/review.md` | the gates, beats.json, the review page, the independent reviewer's brief |
| `references/delivery.md` | the export per platform, the cover, the upload copy, the record |
| `references/editing.md` | story films from footage, and workshop edits for YouTube |
| `references/learned.md` | what went wrong while building, as triggers |
