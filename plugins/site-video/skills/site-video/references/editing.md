# Editing: story films from footage, and workshop edits for YouTube

The site film is proven: its gates were calibrated on renders with known faults. The two forms here use the same method and
the same tools, but no film of either kind has been made yet: the first of each proves or corrects this page.
Record what it teaches in `learned.md`.

## 1. A story film (footage, stills, type)

A person's story told in 30 to 90 seconds: a member who became a teacher, a founder's road to a launch. Footage
carries what happened, stills carry who and where, type carries what it meant.

**Before building**

1. The sentence and the beats (`story.md`). The story's words are the person's own, or copy the owner approved,
   character for character; the film never invents a line, a number or a date.
2. The inventory: every source probed (duration, size, frame rate, variable rate, HDR, audio). Originals untouched;
   working copies at a constant rate and SDR BT.709 (`capture.md` section 6), each with the command that made it.
3. The selects: for each source, the moments worth using, with in, out, what it shows and why, written into
   `film.json`. Show them as a contact sheet before building: the owner picks moments, not renders.

**Building**

- `FootageSource(path).at(t)` gives the frame at any time; a select plays at its own speed, or ramps (eased, never a
  step) when the beat needs it. A camera on footage is the same camera keys as on a page: a crop of the frame, pushing
  slowly through a hold.
- Type is a layer (`filmkit.layers` renders it from HTML at 2x), in the brand's faces and sizes from `brand.json`.
  One motion language for the whole film: one easing family, one direction of travel, one way type enters and leaves.
- Cut on movement or on a match (a shape, a direction, a colour continuing across the cut). Declare every cut in
  `beats.json`; the gates then treat any other jump as a jolt.
- Every line of type is held long enough to be read twice at phone size; until a story film calibrates a number, the
  read floor (1.0 s) and the text floor (24 px line band at 1080) apply.
- Sound is decided at the start, not the end: silent with burned-in words (feeds autoplay muted), music the owner
  holds the rights to, or the person's voice with captions timed to the verified words. With sound: loudness -14 LUFS
  integrated, -1 dBTP; a 10 to 30 ms fade at every audio cut (a hard cut clicks).

**Gates**: `sv check file OUT.mp4 --beats beats.json` (add `--audio` when the film has sound). Holds, rest to
rest, declared cuts, blank beats and the text floor apply unchanged.

## 2. A workshop edit for YouTube

A recorded workshop or talk cut to its best minutes, with chapters and captions.

**Where the moments come from**: the recording's transcript, coded line by line, each line with a use label that
says what it may be used for. Use only moments whose label allows this use; transcripts and
private material never leave the library; every quote shown on screen is checked word for word against the
recording.

**The cut list** lives in the film folder, one entry per segment, in the order the edit plays:

```json
[{"src": "workshop-2.mp4", "in": 754.20, "out": 812.85, "chapter": "Why the pipeline stalled",
  "why": "the clearest statement of the problem", "label": "public"}]
```

- Every in and out sits on a word boundary from the speech model's word times, with a handle of 0.15 to 0.3 s. The
  speech model supplies times, never words: caption text comes from the verified transcript.
- Show the owner the cut list as a page (each segment's quote, duration and reason) before rendering: approving cuts
  is cheap, approving renders is not.

**Assembly**: video cuts on the list; audio faded 10 to 30 ms either side of every join (or a J or L cut where speech
runs over); loudness two-pass to -14 LUFS, -1 dBTP; exported to YouTube's settings (`delivery.md` section 1).

**Chapters** come from the cut list's `chapter` fields, in the video's description. YouTube's rules (last verified 15
Oct 2026): the first timestamp is 00:00, at least three timestamps in ascending order, each chapter at least 10 s.

**Captions**: an SRT or VTT built from the verified words and their times, uploaded as captions (not burned in) so
they can be corrected and searched.

**Short clips from the same recording** (a 30 to 60 s quote, captioned and reframed for 9:16 or 4:5) are a
captioning tool's job: one that aligns a verified quote to the speech, reframes on the speaker and levels the audio.

**The tool still to build**: filmkit has no cut-list assembler yet. The first workshop edit builds one (`edit.py`: a
cut list in, the assembled video with faded joins and levelled audio out), proven first on a synthetic recording
(a test pattern and a generated voice) and gated by `sv check file --audio` plus a check that every join sits in
silence.
