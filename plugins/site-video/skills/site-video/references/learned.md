# Learned: triggers from the films

Written as triggers: when this happens, do that, before editing anything. Each carries its evidence in brief, from
the films that taught it.

## Before the first frame

- **When the brief arrives**: ask the three questions (`story.md` section 5) in the first message, each with a proposed
  answer. On one film most of the owner's notes turned out to be their answers, given one round at a time.
- **When the choreography is written**: draw the camera map and render the animatic (about a minute in all) before any
  capture. On one film the first capture-backed version reached the owner 69 minutes after the brief, and its
  direction was turned down two minutes later.
- **When the owner asks to speed up**: the time is in captures (on one film, thirteen of 5.4 to 7.4 minutes each),
  not in renders (about 20 s). Move the camera without recapturing, judge direction on the draft
  capture, and capture the final once.

## Making the film

- **When the owner says a move jumps or feels clunky**: measure on-screen speed and phone-size sharpness frame by
  frame on the encoded file before changing anything. Two causes hid behind one note: a stop that braked twice and a
  blur that switched off mid-brake.
- **When a stop is a curve through keyframes**: replace it with one ease-out (`stop_scroll`). A monotone cubic
  through close keyframes brakes, crawls and brakes again.
- **When blur depends on speed**: let it fade with the speed and keep the capture scale constant; never switch either
  in the middle of a move.
- **When a title goes over a page**: blur first, fast; the title after. Over sharp words two wordmarks fight.
- **When an element moves toward something and back**: `sin^2`, from rest to rest.
- **When the camera arrives somewhere new after a cut**: give the new page its own framing; the old zoom carried over
  crops it badly.
- **When a subject sits near the page's edge**: extend the page's own ground past the edge (`padx`) and centre the
  subject; do not show the neighbour.
- **When a chart or drawing animates on the page**: zoom in first, then let it draw; arriving after the motion
  wastes it.
- **When marks go on an end card**: draw them at their largest size and shrink; measure the stack's space above and
  below and the gap against the locked lockup's proportions.
- **When choosing the capture viewport**: a normal desktop height (about 1440 x 1100 to 1150). Pinned sections are a
  screen high and centre their content, so a tall window shows bands of empty ground.
- **When the page slows the capture** (a backdrop blur took captures from 90 to 400 ms): per-frame pacing absorbs
  it; check the capture gate rather than trusting the page's motion.
- **When a cursor appears**: start it inside the window and fade it in; put its tip clear of the words it points to.
- **When the film clicks something that animates by script** (a map's zoom, a custom tween): click it in recon under
  a slowed rate and read the element's transform for a few frames before planning the beat. A zoom that started at
  `performance.now()` and stepped by the rAF timestamp jumped to scale -12 and emptied the map for the whole beat; a
  test at full speed had looked fine. `"frame_clock": true` fixes that kind (`capture.md` section 5,
  `tests/test_frame_clock.py`).
- **When the file gate finds cuts the film never made**: look for a `<video>` on the page first. A background reel
  played 7x fast under the slowed capture and its own edits were the cuts. `"media_rate": true`.
- **When a beat stays in motion for an interaction** (a carousel clicked twice): the last state still needs its hold.
  Two clicks 0.8 s apart left the cards 0.22 s still; one click left them 0.8 s.
- **When the owner says a camera move still jumps after it was made longer**: the curve is the cause, not the
  length. The in-out cubic (`io`) peaks at 3x a move's average speed, so a zoom flagged twice peaked at 22 px a frame
  however long it was given; `soft` (in-out quintic) peaks at 1.9x and took the same moves to 13 to 15. Profile the
  on-screen speed (zoom, pan and scroll together, the worst point of the window, px a frame) before and after.
- **When a zoom out leads into a scroll**: overlap them so the speed climbs in one curve. A zoom out that came to rest
  just as the scroll began read as too harsh (speed up, dip, speed up again); starting the scroll 0.4 s into the
  zoom out, on a longer ramp, made it one gesture.
- **When the page's own slider snaps**: read its transition in recon. A carousel slid half its move in 0.14 s on its
  own ease-out; an injected curve on that list only (a `pre` `eval` adding a scoped `!important` rule) slowed it to
  the camera's peak, with the same content and the same real click.
- **When the same check passes alone and fails in the capture**: change one ingredient of the capture at a time
  (mouse path, warmup, rate, screenshots) through filmkit's own `capture.run` on a short timeline. The difference was
  how long the rate had been slowed before the click, not anything the film did.

- **When the owner approves the film**: it is a candidate until the independent review has run on that exact cut. On
  one film a review after the owner's yes found the closing line doubled for 13 frames, text cut through the
  closing hold, a stray caret on the end card and a near-white box.
- **When a version goes out with a defect you know**: fix it first, or name it in the message with its fix. A known
  framing slip and a heading under the page's nav, both held back to mention only if asked, came back as the owner's
  notes, the second costing a 6.5 minute capture in the last round. A version the reviewer has failed never goes out
  as if it had passed.
- **When a line of the page is lifted out to move on its own**: paint the page's copy out under it from the moment it
  lifts. The page's copy showed under the moving one for 13 frames while the page faded.
- **When a lifted patch lands on the film's ground**: map its paper to the ground's exact value. A paper 1 to 3 levels
  off white drew a box on the end card.
- **When a layer is cut from a capture**: look at its edges at full size before using it. A caret the page drew after
  an address sat in the layer's last two columns and showed on the end card for 3.7 s.
- **When framing a hold**: keep the neighbouring section's last line of text and the next block's edge out of the
  window, or wholly in it (the plan's cut-text gate; the camera map draws the cut lines in red).
- **When a page turns heavy partway through a capture** (a 3D scene, a video wall): the pacing must catch the jump in
  a few frames and ignore a one-frame stall. A 30-frame average let a draft's page run 2.3x fast for 20 frames; a
  mean of the last errors then overreacted to a single 692 ms frame and slowed the page to 0.07x. The median of the
  last three does both.
- **When a scroll brakes to rest**: Chromium lands every `scrollTo` on a whole CSS pixel at any device scale (100.3
  gives 100, 100.5 gives 101), so a brake's last pixels arrive as 1 px steps. Shifting the crop by the remainder (not
  built) would smooth them where no fixed element is in view, and shake the page's nav by a third of a pixel where one
  is. Until it is built, accept the steps and say so.
- **When frames capture faster than real time** (a draft of a light page): let the playback rate rise above 1. Capped
  at 1, the page ran at half speed.

## Measuring

- **When writing a gate**: run it on a render known to have the fault and one known not to. The first sharpness
  measure could not tell them apart and was replaced. A gate that has not failed anything is a hope.
- **When a number disagrees with the eye**: the number is measuring the wrong thing. The first "abrupt start"
  measure (mean frame difference) flagged the scroll's last whole-pixel steps; the eye judges distance moved, so the
  gate now measures the first step in pixels.
- **When a speed measure says a stopped page still creeps**: it has a 1 px floor; use the sub-pixel fit.
- **When a diff box is bigger than expected**: prove what it is before explaining it. An end-card diff that looked
  like a layout change was compression noise: the composed frames differed by 0.
- **When measuring a card or a box the camera frames**: measure the bordered thing on the captured pixels, not an
  inner element in the DOM.
- **When the reviewer proposes a fix**: check it against the owner's notes first. A zoom that hid one problem cost
  the margins the owner had asked for.
- **When a motion gate flags a stop between two moves**: measure how long the near-stop lasts. A rest of 0.37 s or
  more was a hold the owner kept; the joins the owner flagged rested 0.07 to 0.12 s.
- **When a gate cannot measure something** (an edge test that failed on grey cards): report "not measured", never
  "fine". A message called the margins balanced after the measure failed and six stills were judged by eye.
- **When a summary says the owner accepted something**: find the owner's words before repeating it. A final message
  told the owner they had accepted a beat's small text in an earlier round; the only source was the session's own
  summary, and the owner's one note on that beat had asked for the wider view that made the text small.
- **When an approved film fails a gate**: answer the gate in `beats.json`, in the owner's words or with the maker's
  reason the gate does not apply here; never rename a film to pass a send gate, and never answer a question of taste
  for the owner.
- **When a note is quoted as the verdict on a move**: check what it was said about (the version, the screenshot sent
  with it, the sentence around it), not only that the words exist. A line praising a shot as sharp was cited for a
  night as approval of a fast dive; it had been said of the pull out, a move the same note called a bit too sharp.
- **When a check reads a page's moving part from the still stitch** (a drifting collage, a carousel): the stitch shows
  where the part rests, not where the film saw it. Look at the film's frames at that hold before answering, and
  answer with the reason the gate does not apply there.

## Files and records

- **When moving a final into an archive**: plain `mv`, then compare checksums. `git mv -k` skips an untracked file
  without an error, and a fallback written after it never runs: a record was overwritten that way.
- **When editing a long script by pattern**: anchor on text that occurs once, or rewrite the whole function. A
  patch matched a repeated line and deleted the wrong code.
- **When an alternative still needs a different camera or blur**: give the film a named variant in `film.json`, not an
  environment switch read deep in the compositor; switches drift out of the record.
- **When a capture or render folder lives in a temporary directory**: copy the instruments and the source that made a
  shipped file into the tracked film folder the same day. The reviewers' measuring scripts were rescued from a folder
  that is wiped.
- **When a film ships**: reproduce it from its folder and compare decoded frames with the shipped file. A film that
  reproduces is a film whose next version is safe.
- **When a capture is expected to reproduce**: it does not. Two captures of the fixture differed in 66 of 283 frames,
  all inside the page's own CSS animation, whose phase follows the wall clock until the pacing starts; static content
  was identical. The capture (`raw/` and `inputs.sha256`) is the film's source; the render from it reproduces to the
  frame (2,292 of 2,292 on one film, 888 of 888 on another).
