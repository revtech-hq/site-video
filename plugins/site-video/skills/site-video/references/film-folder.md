# The film folder: what each file holds

A film lives in the project's own repo, in a tracked folder (`films/<name>/`), never in the plugin. The capture and
the renders are large and stay in an ignored working folder; the film folder points at them and keeps their
checksums. The minimal worked example is `tests/fixture/` (a film.json and a script that plans, captures, composes
and encodes); a full film adds the files below.

Once per machine: `sv setup`, then `sv doctor`. A new film starts with `sv new DIR`, which copies the overview
template (`templates/overview/`: `film.py`, `film.json`, `brand.json`, `beats.json`) into the film folder DIR.

| File | Holds | Written by |
|---|---|---|
| `film.json` | every number: timing, scroll, camera, cursor, compose timings, the capture block | the film's author |
| `brand.json` | the brand's values the compositor uses (colours, the end card's inset, radius, hairline and shadow, the ring) | from the project's brand source, never guessed |
| `beats.json` | what the eye must get: each beat's role, start, end, focus box; the click; the cuts | the author, with the timeline (`review.md` section 1) |
| `film.py` | the film's own scenes on filmkit, and its commands (below) | the author, from the template |
| `recon.json` | the boxes the recon measured on the live page, by the names in `recon.items` | `sv film DIR recon` |
| `chrome/` (`chrome_dir`) | brand layers rendered from HTML at 2x (`filmkit.layers`): marks, the address bar per site, the foot row, with `geo.json` boxes | `layers`; in the overview template, `sv film DIR chrome` |
| `raw/` | the capture (ignored by git) and `capture.json` | `filmkit.capture` |
| `raw-stitch/` | the whole page at rest, its fixed nav per scroll position and every visible line of text with its box (`stitch.json`), ignored by git | `filmkit.capture.stitch` |
| `raw-draft/` | the draft capture for the rough cut (1x, three samples at most), ignored by git; never the final's source | `filmkit.capture` with `draft` |
| `versions/` | `film-vN.json` (and the script when it changed) for every version shown, so any version replays; `by-sha/` keeps every render's `film.json`, `film.py` and `beats.json` under the checksum its record names | the author, before each change; `by-sha/` by `encode.record` at every render |
| `evals/` | each version's planned timeline and the cases that prove the gates on the owner's notes | `evals/build.py` |
| `inputs.sha256` | checksums of `raw/` and `chrome/`, so a later render can prove it used the same inputs | the author, after the capture |

## film.json keys: the overview template

What `templates/overview/film.py` reads. Page px are CSS px of the capture's viewport, y from the viewport's top at
the current scroll; document px include the scroll (recon.json and the stitch use them); frame px are px of the
1080 frame.

```
name, title, fps, duration, cap_end    cap_end: the last captured second, the end of end.t_fade (no page after it)
viewport [w, h]                         the capture's CSS viewport, 1440 x 1100 unless the page needs another
raw_dir, chrome_dir                     the capture and the brand layers, relative to the film folder
site                                    a short name for the page, written into every timeline frame
nav_h                                   the page's fixed nav in css px (recon.json "fixed"); 0 when it has none
frame {W, H, win, badge_dock, badge_end, line_end}
                                        frame px: the frame's size; the window once the page has stepped back
                                        [x, y, w, h]; the mark docked above the window, the mark on the end card and
                                        the address on the end card, each [centre x, centre y, ink width]
browser {head, url, font, caret, text_in}
                                        the window's header height, the address it shows, optionally a font file for
                                        it (otherwise Pillow's own face); caret true draws a caret after the address
                                        (off by default: held for the whole film it reads as a stray artifact);
                                        text_in null shows the address from the start, otherwise it fades in once the
                                        lifted mark has cleared it (the header comes down as the mark goes up)
badge_page [x, y, w, h]                 the mark element's box, document px (recon: the mark's selector)
open {...}                              the opening, below
scroll [[t0, t1, from, to, ramp, decel], ...]   the stops, document px, each a stop_scroll
camera {padx, keys: [[t, zoom, cx, cy, mode], ...]}   page px; the first key is the step back's last framing
cursors [{p0, pc, p1, span, clicks, lead, hide, release}, ...]
                                        page px: a curve from p0 through pc to p1 over span; a drawn press at each
                                        time in clicks and the real click lead s later (default 0; 0.15 when the page
                                        answers in one frame, as a tab does, so the press shows first); drawn until
                                        hide; the real mouse held at p1 until release
cursor_style {fade_in, press_len, press_depth, ring_len}
cursor_fade_in [k, ...]                 which cursor segments fade in (default [0, 2])
mouse_rest [x, y]                       where the real mouse waits between clicks: off the content, so nothing hovers
highlight {t, sweep, gap, pad, lines}   the closing sentence's highlight; lines in page px at the last stop, each the
                                        line's glyph ink from ascender to descender, one height for every line
end {...}                               the ending, below
capture {...}                           capture.md section 2; a relative goto is a page beside film.py (the demo)
chrome {mark_selector, font_selector, line, line_weight, line_px, mark_scale}   what the chrome command renders
recon {items: {name: css selector}}     what the recon command measures
cover_t                                 the cover's time (3.25 s: the page in its window, the mark docked)
```

The opening:

```
open.square [cx, cy, s0, s1]     a square push on the hero before the step back, centred at (cx, cy) page px, from
                                 s0 to s1 px wide over open.push; keep it inside the hero's ground, below the nav
open.push [t0, t1]
open.hero_bottom                 where the hero's ground ends; the step back ends framing nav_h to hero_bottom
open.t_show, open.hide_at        the lifted copy appears exactly where the page drew it, and the page's own copy
                                 (open.mark_selector, a selector without single quotes) is hidden in the same frame
open.t_lift, lift_scale, lift_rise   the lift: it grows and rises, eased out
open.t_step [t0, t1]             the page steps back into its window
open.t_dock [t0, t1]             the mark travels to frame.badge_dock
```

The first camera key sits at `t_step`'s end and must equal the step back's last framing: zoom
`VH / (hero_bottom - nav_h)`, centre `(VW / 2, nav_h + (hero_bottom - nav_h) / 2)`.

The ending:

```
end.t_fade [t0, t1]              the page fades out around the highlighted sentence
end.shrink                       how much the window shrinks as it fades (0 to 0.03)
end.sentence {t_hold, box, pad, feather, t_move, t_out, hide, white_lift}
                                 the sentence is cut from the frame at t_hold (the highlight complete), box in page
                                 px at the last stop; it travels to the frame's centre over t_move and fades over
                                 t_out; hide paints the page's own copy out under it; white_lift turns its paper white
end.t_badge, end.t_line          the mark (from its dock) and the address (from below) meet on the end card
end.line_clean_x                 optional: from this x (2x px of line.png) the address layer is painted white
end.cursor {p0, pc, p1, span, click, size, shadow, dip}
                                 frame px: the click on the address; dip is how much the address gives as it is pressed
```

The ending's times hold their shape from film to film. With `F0 = t_fade[0]`: the highlight at F0 - 1.3; `t_hold`
F0 - 0.1; `t_move` F0 + 0.2 to F0 + 1.0; `t_out` F0 + 2.0 to F0 + 3.0; `t_badge` and `t_line` F0 + 2.3 to F0 + 3.2;
the end cursor F0 + 3.5 to F0 + 4.0 and its click at F0 + 4.15; the film ends at least 2 s after the click.

### From recon.json to the numbers

1. `sv film DIR recon`, with `recon.items` naming every box a beat frames: each section's heading and lead, its
   cards, the text inside them, the button the film clicks. `sv film DIR stitch` adds every line of text on the page.
2. A held framing: take the subject's box (document px) and a margin `m` (40 to 70 px). With `ASPECT = win w / win
   h`, the zoom is `min(VH / (h + 2m), VH x ASPECT / (w + 2m))` and the centre is the box's centre, its y minus the
   stop's scroll.
3. Walk the crop's four edges against recon.json: no heading, lead or neighbouring card may cross one. Two cards a
   few px apart leave no clean framing at any zoom; on a page you own, add air; on a client's page, choose another
   subject (two whole cards, the whole row).
4. A hold at zoom 1.0 keeps the crop's top on the viewport's top (`cy = VH / (2 x zoom)`), so a fixed nav shows whole
   or not at all. A zoomed hold keeps its crop's top a few px below the nav (its bottom border shows as a line
   otherwise): choose that stop's scroll so the subject sits low enough to be centred there. Every hold pushes 1 to
   1.5% on `lin`.
5. A scroll stop puts a section's top at the viewport's top, so the section before it hides behind the nav.
6. Words a beat exists for must reach the text floor (24 px): a line shows at `css px x (win w / viewport w) x zoom`,
   0.667 x zoom on the default window, so 26 px text needs a zoom of 1.4 and 20 px text 1.8. A held subject that
   cannot be framed that tight is the wrong subject for a read beat.
7. `sv film DIR timeline`, `sv check plan timeline.json --stitch STITCH --beats beats.json`, and `sv check map`: the
   map draws every hold's window on the page and marks in red any line it cuts.

## film.json keys: a two-page film (the fixture's shape)

```
name, title, fps, duration, cap_end          cap_end: the last captured second (the end card needs no page)
viewport [w, h], window [w, h]               the capture's CSS viewport; the page area in the frame (same shape)
sites [before, after], nav_t                 the two pages and the click's time
scroll {distance, t0, ramp, decel, t_end}    motion.stop_scroll
camera {padx, keys: [[t, zoom, cx, cy, mode], ...]}
cursor {p0, pc, p1, span, t_click, fade_in, fade_out, press_len, press_depth, ring_len, hold_after_nav}
compose {t_veil, t_title, t_out, t_glow, t_fade, t_frame, t_move, t_meet, t_x, t_foot, open_scale, blur, veil, ...}
capture {...}                                capture.md section 2
raw_dir, chrome_dir                          where the capture and the brand layers live, relative to the film
recon {items: {name: css selector}}          the boxes the recon command measures into recon.json
cover_t                                      the cover's time in seconds
_recon {...}                                 what the recon measured, with its date (JSON has no comments)
```

A tour that stops at several sections gives `scroll` as a list of stops instead, `[t0, t_end, from, to, ramp, decel]`,
each one a `stop_scroll` from the previous stop, with the holds between them.

Key names in `compose` are the film's own: a story film has different scenes. Name each time span for the event it
times, as `[start, end]` in seconds.

## Coordinate spaces

- **Page px**: CSS px in the capture viewport at the current scroll. The camera's centres, the click point, the real
  mouse (`cursor` in `timeline.json`) and the boxes the recon measures are all in page px of the screenshot.
- **Frame px**: px of the 1080 frame. The window sits at `geo.json`'s `WIN`; a page point maps to the frame by the
  camera's crop: `X = PX + (vx - x0) * PW / cw`, `Y = PY + (vy - y0) * PH / ch` (`to_frame` in a film's script).
- **beats.json** boxes (`focus`, `page_box`) are in frame px, measured on the encoded film.
- A hard camera change at a cut is two camera keys with the same time: the first ends the old shot, the second
  starts the new one.

## film.py commands

Every command runs through the launcher, `sv film DIR COMMAND`, where DIR is the film folder:

```
sv film DIR recon                   measure the boxes named in film.json's recon.items into recon.json
sv film DIR chrome                  render the page's own mark and its address line into chrome_dir
sv film DIR timeline [OUT.json]     plan the timeline from film.json (default: timeline.json in DIR)
sv film DIR stitch                  the whole page at rest, for the camera map and the animatic (about 20 s)
sv film DIR animatic OUT.mp4        every frame from the stitch: camera, timing, framing; no page motion
sv film DIR draft                   the rough cut's capture (1x, about 2.5x quicker than the final's)
FILM_SOURCE=draft sv film DIR all OUT.mp4   the rough cut, from the draft capture
sv film DIR capture                 the final's capture, once the direction is the owner's
sv film DIR keys OUT t,t,...        storyboard frames at those seconds, as PNGs
sv film DIR all OUT.mp4             every frame, piped to encode.Writer (clean by default), with the render record
sv film DIR cover OUT.png [T]       one frame as a still (default T: cover_t in film.json)
```

`init()` picks the source: `StitchedSource` for the animatic, `CaptureSource` on `raw-draft/` for the draft, on
`raw/` otherwise. A camera, timing or overlay change re-renders from the same capture in seconds; only a change to the
scroll, a click or the page's own state needs a capture.

Films import filmkit through the launcher: `sv film` puts it on the path, so a film holds no paths to the plugin.
Scenes, layers and their timing stay in the film's own file. A function moves into filmkit once three films need it,
not before.
