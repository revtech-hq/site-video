# Review: the gates, the review page and the independent reviewer

Three layers, in this order, before the owner sees a version: the gates (numbers), a look at phone size (you), an
independent reviewer (fresh eyes). Then the owner.

## 1. beats.json: what the eye must get

The film's own statement of its beats, written with the timeline and checked against the encoded file:

```json
{"format": "1x1", "fps": 60, "duration": 14.8, "page_box": [72, 221, 1008, 936], "cuts": [8.42],
 "beats": [
  {"name": "title over the blur", "role": "glance", "t0": 1.0, "t1": 2.1},
  {"name": "the scroll to the section", "role": "scroll", "t0": 2.45, "t1": 4.7},
  {"name": "the card's words and link", "role": "key", "t0": 6.9, "t1": 8.42, "focus": [200, 440, 880, 665]},
  {"name": "the end card", "role": "end", "t0": 12.3, "t1": 14.8}],
 "click": {"press": 8.12, "nav": 8.42}, "page_scale": 0.65}
```

- `role`: glance 0.7 s, read 1.0 s, key 1.0 s, end 2.0 s (settled time inside `t0..t1`); `scroll` is judged by its
  brake. A beat's window may be generous: the gate finds the longest settled run inside it.
- `focus`: the box (frame px) of the words the beat exists for; the gate measures their line band at the hold.
- `page_box`: where the page shows in the frame (speed and sharpness are measured there).
- `cuts`: the film's intended cuts (the click); any other spike is a jolt.
- `page_scale`: on-screen px per page px at zoom 1 (window width over viewport width), for the plan gate.
- `events` and `order`: named moments in seconds and pairs that must come in that order, for the plan gate, e.g.
  `"events": {"blur": 0.68, "title": 0.8}, "order": [["blur", "title"]]` (the title never arrives before its blur).
- `cursor_entry`: the cursor's first point in frame px; the plan gate checks it is inside `page_box`.
- `reactions`: the times the page answers an in-page click (when the real click lands, after any `lead`). The
  page's answer may leave rest at speed or change in one frame (a tab), so the rest gate and the cut gate skip the
  first 0.1 s after each. A click that loads another page is a `click` with its `nav`, never a reaction.
- `subject` (page px), `centre` (`"x"`, `"xy"` or `"none"`), `row` (`{"y": [y0, y1], "x": [[x0, x1], ...]}`) per beat,
  and `nav_h` (the page's fixed nav, css px): the plan's framing gates (centred, inside the window, clear of the nav,
  no sliver of a neighbouring card).
- `answers`: a failing gate answered, never silenced. By the owner, in their words with the date
  (`{"gate": "hold: the middle card", "by": "owner", "words": "...", "date": "..."}`), or
  by the maker, saying why the gate does not measure what it means here (`{"gate": "...", "by": "maker", "why":
  "..."}`). An answered gate prints ANSW and still counts as failed in `eval`; the sidecar lists it under
  `answered`. Taste is the owner's: a defect the owner has not been shown stays FAIL until they decide. An answer
  names one gate (one that matches two lines prints AMBIGUOUS and answers neither), takes `"check": "plan"` or
  `"file"` when it belongs to one check, and can sit on a WARN line as its "kept because". `tests/test_answers.py`
  holds these rules.

A beat that scrolls has the role `scroll` for its move; the hold that follows the stop is its own `glance` or `read`
beat. Write `beats.json` when the timeline is written, and correct its times on the encoded file.

## 2. The gates

```
sv check plan timeline.json --beats beats.json --stitch STITCH   # before capture
sv check map timeline.json --stitch STITCH --beats beats.json --out map.png   # the camera map
sv check motion timeline.json --beats beats.json --stitch STITCH  # every move: peak, kind, near-stops
sv check capture raw/capture.json --timeline timeline.json --expect-url 'example\.com/next'
sv check file OUT.mp4 --beats beats.json               # writes OUT.mp4.film_check.json
sv check cover --raw raw/00096-0.jpg --viewport 1440x1100 --page-area 936x715 \
     --cam 1.4674,720,520 --padx 200 --blur 9 --veil 0.5 --box 110,400,826,504 --box 280,184,640,310
sv check same A.mp4 B.mp4                              # decoded frames identical
```

The plan gates, from the timeline and the stitch, before any capture: blur follows speed, one brake per stop, the
cursor's entry, the motion standard (`motion.md` section 9: no harsh stop-and-go; a WARN for a fast camera move over
dense content), the framing (centred, inside, clear of the nav, no sliver) and no line of text cut by the window's
edge at a hold (the stitch lists every line; a hold of 0.5 s or more fails, a shorter stop warns). Each gate prints
PASS or FAIL with the number it measured; exit 0 all passed, 1 a gate failed, 2 a tool or input is missing. Read the verdict line, never a `tail` of the output. The instruments `speed`, `sheet` and `platform` print
numbers and files for a look; they never gate.

**A gate counts only once it has failed a known-bad render and passed a good one.** The first sharpness measure
could not tell the jumpy version from the fixed one; it was replaced, not trusted. The calibration set (each gate
proven on renders with known faults) runs with `sv check eval MANIFEST --root DIR`; add a case whenever a new
defect is found, with the render that has it.

## 3. Your own look

- The contact sheet every 0.25 s (`sv check sheet OUT.mp4`) at thumbnail size: rhythm, blank beats, variety.
- Each held beat at phone width: does the one thing it exists for read?
- The click, frame by frame across the cut; the end card at full size (it is held longest).
- Every string on screen against its owned source, character for character, and every claim against the captured
  page (a date on the end card must be the date the page shows).

## 4. The review page

One page, one section per version, newest first: the film (with a phone-width view), its key frames, the gate output,
and the owner's note it answers. Alternatives as stills side by side, one recommended. The owner reviews on a phone:
publish the page and send the film itself; never ask them to find files.

## 5. The independent reviewer

**On the exact cut that will leave, before it is called final, even after the owner's yes.** On one film the owner
approved the sixteenth version; the review that ran after it found the closing line shown twice for 13
frames, an FAQ question cut at the window's edge through the closing hold, a stray caret on the end card, a faint box
round the lifted line, the mark crossing the page's words as it lifted, a heading cut at two stops of a pan, and a
file too large to attach to an email. Run it on the candidate, fix, then show.

Its verdict goes into the film's sidecar, beside the gates': `sv check review FILM.mp4 --verdict pass|fix --by
film-reviewer --note "..."`. It needs the gates' sidecar for those exact bytes, and a later `file` run on the same bytes
keeps it. An upload copy takes the master's review with `sv check review COPY.mp4 --from MASTER.mp4`, which is refused unless
the copy's decoded frames are the master's; a re-encode (the email copy) is a new cut and gets its own review. A cut
with no review, or a review that says fix, is not final (`tests/test_review.py`).

A fresh-context reviewer (this plugin's film-reviewer agent, or any agent that did not build the film), read-only, starting
no servers, working from the files. When the owner has approved the art, say so in the brief and hunt only for
defects: "Do not propose new choreography, colours or pacing ideas." Classify each fix as camera only (a key, no
capture), compositing (the film's code, no capture) or capture (the page itself), so the next version's cost is
known. Brief:

```
Independent review of a [length] s [format] [platform] video, before it is called final. Read-only: never edit files.
Do not start any server; work from files on disk with ffmpeg and by reading frames you extract.

THE VIDEO: [path]. THE BRIEF: [the sentence, the beats with times]. THE OWNER'S NOTES SO FAR: [verbatim, by version].
THE WORDS: only these strings may appear: [list]; every other word comes from the captured page.

Measure on the encoded file, at full size and scaled to 390 px wide (a phone):
- every hold: how long the beat is settled, and whether its words read at phone size;
- every move: does it start and stop at rest; speed per frame through each scroll; any one-frame jump in sharpness;
- every cut: is it the intended one; does anything appear or vanish for a single frame;
- the end card: centring, spacing, baselines, sizes, measured in pixels;
- the colour tags; the first frame as a thumbnail.
Report defects ranked, each with the frames, the number, and a fix; then what you checked and found fine.
```

The reviewer measures; you decide. Check every proposed fix against the owner's notes: one review's zoom (1.05 on
the destination) cost the margins the owner then asked for back.

## 6. What the reviews caught

Before the owner saw them: holds of 0.27 to 0.4 s; card words at 7 px on a phone; end-card marks at 6.5% of the space above the rule,
too far apart; a handshake that jolted; a title arriving over sharp words; marks upscaled 1.4 to 1.7x; a cursor entering
off-frame; a seam under a pasted header; copy cut mid-word by a crop; a blank beat; missing colour tags; a faint
click ring on a same-coloured button. Each is now a gate or a rule above.

On one film, after the owner's yes: the items in section 5. The page's copy of a lifted line, a capture's
stray edge in a layer, cut text at a hold and a near-white box are now a gate or a rule (`learned.md`).
