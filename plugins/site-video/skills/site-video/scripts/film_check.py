#!/usr/bin/env python3
"""film_check: the gates of a short social film.

Every gate prints PASS or FAIL with the number it measured. A gate that cannot measure fails. A run exits 0 when every
gate ran and passed, 1 when any failed, 2 when a tool or an input is missing. `file` writes a sidecar beside the film,
FILM.film_check.json, holding the film's sha256 and the verdict: a film reaches its owner only with a PASS sidecar for
those exact bytes.

  film_check.py file FILM.mp4 [--beats BEATS.json] [--format 1x1] [--fps 60] [--duration S] [--cuts T,T] [--audio] [--no-sidecar]
  film_check.py plan TIMELINE.json [--beats BEATS.json] [--stitch STITCH_DIR]
  film_check.py motion TIMELINE.json --beats BEATS.json [--stitch STITCH_DIR]   (an instrument: every move, printed)
  film_check.py map TIMELINE.json --stitch STITCH_DIR --out MAP.png [--beats BEATS.json]   (the camera map, for the owner)
  film_check.py capture CAPTURE.json [--timeline TIMELINE.json] [--expect-url REGEX]
  film_check.py speed FILM.mp4 --from S --to S [--box x0,y0,x1,y1]
  film_check.py cover --raw FRAME.jpg --viewport WxH --page-area WxH --cam Z,CX,CY [--padx PX] --blur B --veil V --box x0,y0,x1,y1 ...
  film_check.py sheet FILM.mp4 [--every 0.25]
  film_check.py platform FILM.mp4 [--mbps 3]           (an instrument: prints, never gates)
  film_check.py same A.mp4 B.mp4
  film_check.py review FILM.mp4 --verdict pass|fix --by NAME [--note TEXT] | --from MASTER.mp4   (the review, in the sidecar)
  film_check.py path A.mp4 B.mp4 --times T,T,... [--box x0,y0,x1,y1]   (one plan's camera in two renders: animatic, final)
  film_check.py eval MANIFEST.json --root DIR

The beats file (written by the film's timeline, or by hand for an old film) names what the eye must get:
  {"format": "1x1", "fps": 60, "duration": 14.8, "page_box": [x0, y0, x1, y1], "cuts": [8.42],
   "beats": [{"name": "...", "role": "glance|read|key|end|scroll", "t0": S, "t1": S, "focus": [x0, y0, x1, y1]}],
   "click": {"press": S, "nav": S}, "events": {"name": S}, "order": [["first", "then"]], "reactions": [S],
   "answers": [{"gate": "part of a gate's name", "by": "owner", "words": "...", "date": "..."},
               {"gate": "...", "by": "maker", "why": "...", "check": "plan|file (optional: only that check reads it)"}]}
Floors by role (seconds settled): glance 0.7, read 1.0, key 1.0, end 2.0. A scroll beat is judged by its brake.
A failing gate can be answered, never silenced: by the owner, in their words with the date ("hold it a little shorter",
with the day and time they said it), or by the maker, saying why the gate does not measure what it means here (a camera move that overlaps a brake by
design). An answered gate prints ANSW, still counts as failed in `eval`, and is listed in the sidecar under "answered";
the verdict is PASS when every failing gate is answered. An answer must match exactly one failing gate: one that matches
several prints AMBIGUOUS and answers none, one that matches none prints UNUSED. Taste is never the maker's to answer: a defect the owner has not seen stays FAIL until they decide.
A beat with "hold_on": "focus" is held when its focus box is still: for a page that plays its own motion around the words
(a background video, a drifting collage, a rotating quote). "reactions" are the times the page answers an in-page
click (when the click lands): its response may leave rest at speed (a UI ease-out does) or change in one frame (a tab),
so the rest gate and the cut gate skip the first 0.1 s after each.

The plan gates read each timeline frame's "view" (the window's view of the page in page px, written by the film's plan)
and, in beats.json, "page_box" (the window's page area in the frame) and per beat:
  "subject": [x0, y0, x1, y1]   the thing the beat shows, page px (document coordinates; measure its ink, not its box)
  "centre": "x" | "xy" | "none" "x" by default: left and right margins within max(8 px, 2% of the window)
  "row": {"y": [y0, y1], "x": [[x0, x1], ...]}   the cards of a row: none may show as a sliver (under 25% or 40 px)
and top-level "nav_h" (the page's fixed nav, viewport px; or --stitch, which measured it). The motion gate needs no
beats: a stop between two moves (speed under 25% of the moves either side) after a move faster than 35 px a frame is a
harsh stop-and-go, the join owners flag most often, unless the near-stop lasts 0.25 s or more (then it is a
hold). Camera moves faster than 20 px a frame print as WARN lines with the content density under their destination
(edge strength from --stitch, dense from 12): a WARN is answered with a fix, or in beats.json's "answers" with a "kept
because" (the line prints it, and the verdict counts only the WARNs still to answer), and in the message that shows the
cut.

Run through the skill's launcher: sv check COMMAND ... (Pillow, no numpy). ffmpeg and ffprobe must be on PATH.
"""
import hashlib, json, math, os, re, statistics, subprocess, sys, time
from PIL import Image, ImageChops, ImageFilter, ImageStat

FORMATS = {'1x1': (1080, 1080), '4x5': (1080, 1350), '9x16': (1080, 1920), '16x9': (1920, 1080)}
FLOOR = {'glance': 0.7, 'read': 1.0, 'key': 1.0, 'end': 2.0}
SETTLE = 0.35          # mean frame difference (levels, at 270 px) under which a frame counts as settled
TEXT_FLOOR = 24        # px at 1080: the median height of a text line's ink band in a focus box
POP_ABS, POP_REL = 1.5, 0.30     # a one-frame rise in phone-size vertical sharpness, absolute and relative
COVER_DARK, COVER_FLOOR = 200, 0.01   # a cover's title box: under 1% of its page darker than L 200 after the veil
KICK_PX = 2                      # px at 1080: an element leaving rest by this much in one frame was kicked, not eased
BLANK_SHARE, BLANK_FRAMES = 0.005, 6   # under 0.5% ink in the centre for 0.1 s at 60 fps is a blank beat
TRACE = re.compile(rb'(?i)(lav[fc]\d|x264 - core|videolan|ffmpeg|handbrake|davinci|premiere)')
HARSH_PEAK, HARSH_DIP, HARSH_WIN = 35.0, 0.25, 0.6   # px/f, share of the smaller neighbour, s: a stop-and-go join
HARSH_HOLD = 0.25      # s: a near-stop this long is a hold between two moves (flagged joins rested 0.07-0.12 s, accepted holds 0.37 s and more)
FAST_CAMERA, DENSE = 20.0, 12.0                       # px/f for a camera move's WARN; edge strength from which content is dense
NAV_AIR, CENTRE_TOL, SLIVER = 8.0, 0.02, (0.25, 40.0)  # px under the nav; share of the window; share of a card, px
STILL, CUT_HOLD = 0.5, (0.25, 0.5)   # px/f under which the view holds; s of hold from which a cut line WARNs, then FAILs


class Gates:
    def __init__(self, title, answers=None, check=None):
        self.title, self.rows, self.n, self.answers = title, [], 0, []
        for an in answers or []:        # an owner's answer quotes the owner; the maker's says why the gate does not apply
            if an.get('check', check) != check:
                continue                # an answer for the other check (plan or file)
            if an.get('gate') and ((an.get('by') == 'owner' and an.get('words') and an.get('date')) or (an.get('by') == 'maker' and an.get('why'))):
                self.answers.append(an)
            else:
                print(f"INVALID answer (needs gate, and by owner with words and date, or by maker with why): {an}", flush=True)

    def answer(self, row):
        """the one answer whose gate text is in this row's name, attached to the row; '' or the words it prints"""
        hits = [an for an in self.answers if an['gate'] in row['gate']]
        an = hits[0] if len(hits) == 1 else None
        if not an:
            return ''
        row['answered'] = an
        return f"  <- answered by the {an['by']}: " + (f"\"{an['words']}\" ({an['date']})" if an['by'] == 'owner' else an['why'])

    def add(self, name, ok, measured):
        self.n += 1
        row = {'n': self.n, 'gate': name, 'pass': bool(ok), 'measured': measured}
        said = '' if ok else self.answer(row)
        self.rows.append(row)
        print(f"{'PASS' if ok else 'ANSW' if said else 'FAIL'} {self.n:2d} {name}: {measured}{said}", flush=True)

    def warn(self, name, measured):
        row = {'n': None, 'gate': name, 'pass': True, 'warn': True, 'measured': measured}
        said = self.answer(row)
        self.rows.append(row)
        print(f"WARN    {name}: {measured}{said}", flush=True)

    def verdict(self):
        amb = []                        # an answer names one gate: one that matches several answers none of them
        for an in self.answers:
            rows = [r for r in self.rows if r.get('answered') is an]
            if len(rows) > 1:
                amb.append(an)
                for r in rows:
                    del r['answered']
                print(f"AMBIGUOUS answer (matches {len(rows)} lines, so it answers none; name one): {an['gate']}", flush=True)
        gates = [r for r in self.rows if not r.get('warn')]
        bad = [r for r in gates if not r['pass'] and not r.get('answered')]
        said = [r for r in gates if r.get('answered')]
        warns = [r for r in self.rows if r.get('warn')]
        open_w = sum(1 for r in warns if not r.get('answered'))
        by = {k: sum(1 for r in said if r['answered']['by'] == k) for k in ('owner', 'maker')}
        print(f"{self.title}: {'PASS' if not bad else 'FAIL'} {sum(1 for r in gates if r['pass'])}/{len(gates)} gates"
              + (f", {len(said)} failed and answered (owner {by['owner']}, maker {by['maker']})" if said else '')
              + (f", {len(warns) - open_w} WARN answered" if len(warns) - open_w else '')
              + (f", {open_w} WARN to answer" if open_w else ''), flush=True)
        used = [r['answered'] for r in self.rows if r.get('answered')]
        for an in self.answers:
            if not any(an is u for u in used + amb):
                print(f"UNUSED answer (no failing gate matches it): {an['gate']}", flush=True)
        return not bad


def need(tool):
    if subprocess.run(['which', tool], capture_output=True).returncode:
        print(f'MISSING {tool}: install it first'); sys.exit(2)


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', path], capture_output=True, text=True)
    if r.returncode:
        return None
    return json.loads(r.stdout)


def atoms(path):
    """the top-level MP4 boxes in order"""
    out = []
    with open(path, 'rb') as f:
        while True:
            h = f.read(8)
            if len(h) < 8:
                break
            size, kind = int.from_bytes(h[:4], 'big'), h[4:8].decode('latin-1')
            if size == 1:
                size = int.from_bytes(f.read(8), 'big'); f.seek(size - 16, 1)
            elif size == 0:
                out.append(kind); break
            else:
                f.seek(size - 8, 1)
            out.append(kind)
    return out


def frames(path, w, h):
    """every decoded frame as an RGB image (the pipe is closed quietly when the caller stops early)"""
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:v', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    n = w * h * 3
    try:
        while True:
            b = p.stdout.read(n)
            if len(b) < n:
                break
            yield Image.frombytes('RGB', (w, h), b)
    finally:
        p.stdout.close(); p.kill(); p.wait()


def frame_at(path, i, w, h):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'select=eq(n\\,{i})', '-fps_mode', 'passthrough', '-frames:v', '1',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True)
    return Image.frombytes('RGB', (w, h), r.stdout[:w * h * 3]) if len(r.stdout) >= w * h * 3 else None


# ------------------------------------------------------------------ the measures
def vgrad(im):
    """mean vertical difference between neighbouring rows: what motion blur along a scroll takes away"""
    return ImageStat.Stat(ImageChops.difference(im.crop((0, 1, im.width, im.height)), im.crop((0, 0, im.width, im.height - 1)))).mean[0]


def profile(L, box, nb=9):
    """the page area as nb column bands, each squeezed to one value per row (an nb x H 'L' image)"""
    c = L.crop(box)
    return c.resize((nb, c.height), Image.BOX)


def shift(P, Q, lo=-6, hi=140):
    """rows the content moved up between profile P and the next profile Q, to a tenth of a pixel"""
    H = P.height
    def cost(s):
        if s >= 0:
            a, b = P.crop((0, s, P.width, H)), Q.crop((0, 0, Q.width, H - s))
        else:
            a, b = P.crop((0, 0, P.width, H + s)), Q.crop((0, -s, Q.width, H))
        return ImageStat.Stat(ImageChops.difference(a, b)).mean[0]
    cs = {s: cost(s) for s in range(lo, min(hi, H - 20))}
    sb = min(cs, key=cs.get)
    if sb - 1 in cs and sb + 1 in cs:
        c0, c1, c2 = cs[sb - 1], cs[sb], cs[sb + 1]; den = c0 - 2 * c1 + c2
        return sb + (0.5 * (c0 - c2) / den if den else 0.0)
    return float(sb)


def moved_px(A, B, block=40, search=12, top=16):
    """how far the content moved between greyscale frames A and B (px): block matching on the most-changed textured
    blocks. A block counts only when one integer shift explains it (residual under a quarter of the unshifted one),
    so a sub-pixel scroll step (about 1 px, poor match) reads as rest and an element kicked into motion as its kick."""
    w, h = A.size
    d = ImageChops.difference(A, B).point(lambda v: 255 if v > 16 else 0)
    bb = d.getbbox()
    if not bb:
        return 0.0
    blocks = []
    for y in range(bb[1], bb[3], block):
        for x in range(bb[0], bb[2], block):
            blk = (x, y, min(x + block, w), min(y + block, h))
            ch = ImageStat.Stat(d.crop(blk)).mean[0] / 255
            if ch > 0.02 and ImageStat.Stat(B.crop(blk)).stddev[0] > 8:
                blocks.append((ch, blk))
    best = 0.0
    for ch, blk in sorted(blocks, reverse=True)[:top]:
        tb, costs = B.crop(blk), {}
        for dy in range(-search, search + 1):
            for dx in range(-search, search + 1):
                sb = (blk[0] - dx, blk[1] - dy, blk[2] - dx, blk[3] - dy)
                if sb[0] >= 0 and sb[1] >= 0 and sb[2] <= w and sb[3] <= h:
                    costs[(dx, dy)] = ImageStat.Stat(ImageChops.difference(tb, A.crop(sb))).mean[0]
        k = min(costs, key=costs.get)
        if costs[k] < 0.25 * costs.get((0, 0), 0):
            best = max(best, math.hypot(*k))
    return best


def ink_share(im, ground=None):
    """share of the centre 70% whose colour differs from that area's median colour by more than 8 levels"""
    w, h = im.size
    c = im.crop((int(w * .15), int(h * .15), int(w * .85), int(h * .85)))
    med = [int(statistics.median(ch.getdata())) for ch in c.split()]
    d = ImageChops.difference(c, Image.new('RGB', c.size, tuple(med))).convert('L').point(lambda v: 255 if v > 8 else 0)
    return ImageStat.Stat(d).mean[0] / 255


def text_band(im, box):
    """median height of the text lines' ink bands inside box (px), and the bands"""
    c = im.convert('L').crop(box)
    bg = statistics.median(c.getdata())
    ink = c.point(lambda v: 255 if abs(v - bg) > 60 else 0)
    w = c.width
    rows = [sum(1 for v in ink.crop((0, y, w, y + 1)).getdata() if v) for y in range(c.height)]
    bands, s = [], None
    for y, n in enumerate(rows + [0]):
        on = n > 2
        if on and s is None:
            s = y
        if not on and s is not None:
            if y - s >= 6:
                bands.append(y - s)
            s = None
    return (statistics.median(bands) if bands else 0), bands


# ------------------------------------------------------------------ file
def analyse(path, w, h, page_box, fps, boxes=()):
    """one pass over the decoded film: frame difference (of the frame, and inside each of `boxes`, film px), ink share,
    phone sharpness, scroll profiles, and how far the content moved on each frame that leaves rest"""
    mad, ink, sharp, prof, starts = [], [], [], [], []
    k270 = 270 / w
    sb = [tuple(round(v * k270) for v in b) for b in boxes]
    bmad = [[] for _ in sb]
    prev = prevL = None
    pw = 390 / w
    pb = [round(v * pw) for v in page_box]
    for i, im in enumerate(frames(path, w, h)):
        L = im.convert('L')
        small = L.resize((270, round(270 * h / w)), Image.BOX)
        mad.append(ImageStat.Stat(ImageChops.difference(small, prev)).mean[0] if prev is not None else 0.0)
        for k, b in enumerate(sb):
            bmad[k].append(ImageStat.Stat(ImageChops.difference(small.crop(b), prev.crop(b))).mean[0] if prev is not None else 0.0)
        if i >= 2 and mad[i - 1] < 0.05 and mad[i] > 0.8:
            starts.append((i, mad[i - 1], mad[i], moved_px(prevL, L)))
        prev, prevL = small, L
        ink.append(ink_share(im.resize((270, round(270 * h / w)), Image.BOX)))
        phone = L.resize((390, round(390 * h / w)), Image.LANCZOS).crop(tuple(pb))
        sharp.append(vgrad(phone))
        prof.append(profile(L, tuple(page_box)))
    return {'mad': mad, 'ink': ink, 'sharp': sharp, 'prof': prof, 'starts': starts, 'box_mad': dict(zip(boxes, bmad))}


def speeds(prof, a, b):
    """on-screen speed (px per frame) between frames a..b"""
    return [(i, shift(prof[i - 1], prof[i])) for i in range(max(1, a), min(b, len(prof) - 1) + 1)]


def brake(vs):
    """the shape of a stop: a plateau inside the brake, and how far the deceleration rises again after it first falls"""
    v = [x for _, x in vs]
    if len(v) < 12:
        return None
    sm = [statistics.mean(v[max(0, i - 2):i + 3]) for i in range(len(v))]
    p = max(range(len(sm)), key=lambda i: sm[i]); vp = sm[p]
    if vp < 3:
        return None
    dec = [sm[i - 1] - sm[i] for i in range(p + 1, len(sm))]
    dec = [statistics.mean(dec[max(0, i - 2):i + 3]) for i in range(len(dec))]
    live = [i for i in range(len(dec)) if sm[p + 1 + i] > 0.10 * vp]
    if len(live) < 6:
        return None
    d = [dec[i] for i in live]
    a1 = max(d)
    k = d.index(a1)
    lo = min(range(k, len(d)), key=lambda i: d[i])
    rerise = (max(d[lo:]) - d[lo]) / a1 if a1 > 0 else 0.0
    plate, run = 0, 0
    for i in live:
        ratio = sm[p + 1 + i] / vp
        if 0.15 < ratio < 0.85 and dec[i] < 0.15 * a1:
            run += 1; plate = max(plate, run)
        else:
            run = 0
    return {'peak_px_per_frame': round(vp, 1), 'rerise': round(rerise, 3), 'plateau_frames': plate}


def cmd_file(a):
    need('ffmpeg'); need('ffprobe')
    path = a['FILM']
    if not os.path.exists(path):
        print(f'MISSING {path}'); sys.exit(2)
    beats = json.load(open(a['--beats'])) if a.get('--beats') else {}
    fmt = a.get('--format') or beats.get('format', '1x1')
    W, H = FORMATS.get(fmt) or tuple(int(x) for x in fmt.split('x'))   # a named format or WxH
    fps = float(a.get('--fps') or beats.get('fps', 60))
    cuts = [float(x) for x in a['--cuts'].split(',')] if a.get('--cuts') else beats.get('cuts', [])
    g = Gates(os.path.basename(path), beats.get('answers'), 'file')
    pr = probe(path)
    g.add('playable', pr is not None and not subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'null', '-'],
                                                             capture_output=True, text=True).stderr.strip(), 'ffprobe and a full decode')
    if pr is None:
        g.verdict(); sys.exit(1)
    vs = [s for s in pr['streams'] if s.get('codec_type') == 'video']
    au = [s for s in pr['streams'] if s.get('codec_type') == 'audio']
    v = vs[0] if vs else {}
    nb = int(v.get('nb_frames', 0) or 0); dur = float(pr['format'].get('duration', 0))
    want = float(a.get('--duration') or beats.get('duration', 0) or 0)
    g.add('stream', v.get('codec_name') == 'h264' and v.get('profile') == 'High' and v.get('pix_fmt') == 'yuv420p'
          and (v.get('width'), v.get('height')) == (W, H),
          f"{v.get('codec_name')} {v.get('profile')} {v.get('pix_fmt')} {v.get('width')}x{v.get('height')} (want h264 High yuv420p {W}x{H})")
    rate = v.get('r_frame_rate'); avg = v.get('avg_frame_rate')
    g.add('frame rate', rate == f'{int(fps)}/1' and avg == rate and (not want or abs(nb - round(want * fps)) <= 1),
          f'{rate} (avg {avg}), {nb} frames' + (f' for {want} s' if want else ''))
    tags = (v.get('color_primaries'), v.get('color_transfer'), v.get('color_space'))
    g.add('colour tags', tags == ('bt709', 'bt709', 'bt709'), f'primaries {tags[0]}, transfer {tags[1]}, matrix {tags[2]}')
    at = atoms(path)
    g.add('fast start', 'moov' in at and 'mdat' in at and at.index('moov') < at.index('mdat'), ' '.join(at))
    g.add('audio', bool(au) if a.get('--audio') else not au, f'{len(au)} audio stream(s)' + (' (wanted)' if a.get('--audio') else ' (silent film)'))
    raw = open(path, 'rb').read()
    hits = sorted({m.group(0).decode('latin-1') for m in TRACE.finditer(raw)})
    tagtrace = [f'{k}={val}' for k, val in pr['format'].get('tags', {}).items() if TRACE.search(str(val).encode())]
    g.add('tool traces', not hits and not tagtrace, ', '.join(hits + tagtrace) or 'none')
    page_box = beats.get('page_box') or [0, 0, W, H]
    print(f'... decoding {nb} frames', flush=True)
    holds = [tuple(b['focus']) for b in beats.get('beats', []) if b.get('hold_on') == 'focus' and b.get('focus')]
    m = analyse(path, W, H, page_box, fps, holds)
    n = len(m['mad'])
    cutf = {round(c * fps) + k for c in cuts for k in (-1, 0, 1)}
    # blank beats
    runs, run = [], []
    for i, s in enumerate(m['ink']):
        if s < BLANK_SHARE:
            run.append(i)
        else:
            if len(run) >= BLANK_FRAMES:
                runs.append((run[0], run[-1]))
            run = []
    if len(run) >= BLANK_FRAMES and run[0] > 0:
        runs.append((run[0], run[-1]))
    g.add('no blank beat', not runs, ', '.join(f'{x / fps:.2f}-{y / fps:.2f} s' for x, y in runs) or 'none')
    # jumps and abrupt starts outside the declared cuts and the page's own reactions
    react = {round(t * fps) + k for t in beats.get('reactions', []) for k in range(-1, round(0.1 * fps) + 1)}
    jumps = []
    for i in range(1, n):
        if i in cutf or i in react:
            continue
        nbh = [m['mad'][j] for j in range(max(1, i - 6), min(n, i + 7)) if j != i]
        if m['mad'][i] > max(1.5, 6 * (statistics.median(nbh) if nbh else 0)):
            jumps.append(i)
    g.add('cuts only where declared', not jumps, (', '.join(f'{i / fps:.3f} s ({m["mad"][i]:.2f})' for i in jumps) or 'none') + f'; declared {cuts}')
    kicks = [s for s in m['starts'] if s[0] not in cutf and s[0] not in react and s[3] >= KICK_PX]
    g.add(f'every move starts from rest (first step under {KICK_PX} px)', not kicks,
          ', '.join(f'{i / fps:.3f} s ({px:.0f} px from rest)' for i, _, _, px in kicks)
          or f"none; {len(m['starts'])} departures from rest, the largest first step {max([s[3] for s in m['starts']] or [0]):.0f} px")
    # sharpness pops
    pops = []
    for i in range(1, n):
        if i in cutf:
            continue
        d = m['sharp'][i] - m['sharp'][i - 1]
        if d > POP_ABS and m['sharp'][i - 1] > 0 and d / m['sharp'][i - 1] > POP_REL:
            pops.append((i, m['sharp'][i - 1], m['sharp'][i]))
    g.add('no sharpness pop', not pops, ', '.join(f'{i / fps:.3f} s ({x:.2f} to {y:.2f})' for i, x, y in pops) or 'none')
    # beats: holds, brakes, text
    for b in beats.get('beats', []):
        f0, f1 = round(b['t0'] * fps), min(n - 1, round(b['t1'] * fps))
        if b['role'] == 'scroll':
            sh = brake(speeds(m['prof'], f0, f1))
            ok = sh is not None and sh['plateau_frames'] < 4 and sh['rerise'] < 0.15
            g.add(f"one brake: {b['name']}", ok, sh if sh else 'no stop measured in the window')
            continue
        best, run, start, bs = 0, 0, f0, f0
        series = m['box_mad'][tuple(b['focus'])] if b.get('hold_on') == 'focus' and b.get('focus') else m['mad']
        for i in range(f0, f1 + 1):
            if series[i] < SETTLE:
                run += 1
                if run == 1:
                    start = i
                if run > best:
                    best, bs = run, start
            else:
                run = 0
        secs = best / fps
        fl = FLOOR.get(b['role'], 0.7)
        on = ' in its focus box' if series is not m['mad'] else ''
        g.add(f"hold: {b['name']} ({b['role']}, floor {fl} s)", secs >= fl, f'{secs:.2f} s settled{on} from {bs / fps:.2f} s')
        if b.get('focus'):
            im = frame_at(path, bs + best // 2, W, H)
            med, bands = text_band(im, tuple(b['focus'])) if im else (0, [])
            g.add(f"text floor: {b['name']} (median line band {TEXT_FLOOR} px)", med >= TEXT_FLOOR,
                  f'median {med} px, bands {bands[:12]}' if im else f'no frame read at {(bs + best // 2) / fps:.2f} s (ffmpeg)')
    ok = g.verdict()
    side = {'film': os.path.basename(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'verdict': 'PASS' if ok else 'FAIL',
            'answered': [dict(r['answered'], n=r['n']) for r in g.rows if r.get('answered')], 'gates': g.rows, 'beats': a.get('--beats')}
    if not a.get('--no-sidecar'):
        old = _sidecar(path)
        if old.get('review', {}).get('sha256') == side['sha256']:
            side['review'] = old['review']          # the review stays with the bytes it saw
        json.dump(side, open(path + '.film_check.json', 'w'), indent=1)
        print(f'wrote {path}.film_check.json')
    return ok


# ------------------------------------------------------------------ plan
def cmd_plan(a):
    tl = json.load(open(a['TIMELINE']))
    beats = json.load(open(a['--beats'])) if a.get('--beats') else {}
    g = Gates(os.path.basename(a['TIMELINE']), beats.get('answers'), 'plan')
    k = beats.get('page_scale', 1.0)   # on-screen px per page px at zoom 1 (the window's width over the viewport's)
    pos = [f['s'][len(f['s']) // 2] for f in tl]
    sharp_moving, switches = [], []
    for i in range(1, len(tl)):
        f, p = tl[i], tl[i - 1]
        if f.get('nav') or f.get('site') != p.get('site'):
            continue
        if len(f['s']) == 1 and abs(pos[i] - pos[i - 1]) * f.get('z', 1) * k > 3:
            sharp_moving.append(i)
        if f.get('scale') != p.get('scale') and (len(f['s']) > 1 or len(p['s']) > 1):
            switches.append(i)
    g.add('blur follows the speed (no sharp frame moving over 3 px)', not sharp_moving,
          f'{len(sharp_moving)} sharp frames while moving' + (f', from {sharp_moving[0] / beats.get("fps", 60):.2f} s' if sharp_moving else ''))
    g.add('capture scale constant while moving', not switches, f'{len(switches)} switches' + (f' at frames {switches[:6]}' if switches else ''))
    fps = beats.get('fps', 60)
    for b in beats.get('beats', []):
        if b['role'] != 'scroll':
            continue
        f0, f1 = round(b['t0'] * fps), min(len(pos) - 1, round(b['t1'] * fps))
        vs = [(i, pos[i] - pos[i - 1]) for i in range(f0 + 1, f1 + 1)]
        sh = brake(vs)
        g.add(f"one brake (designed): {b['name']}", sh is not None and sh['plateau_frames'] < 4 and sh['rerise'] < 0.15, sh or 'no stop')
    ck = beats.get('click')
    if ck:
        lead = ck['nav'] - ck['press']
        g.add('the press shows before the page changes', 0.15 <= lead <= 0.4, f'{lead:.2f} s (0.15 to 0.4)')
    navs = [f['i'] for f in tl if f.get('nav')]
    if navs or ck or beats.get('cuts'):
        said = sorted([round(ck['nav'] * fps)] if ck else []) + sorted(round(c * fps) for c in beats.get('cuts', []))
        ok = bool(navs) and all(any(abs(n - x) <= 1 for x in said) for n in navs) and all(any(abs(n - x) <= 1 for n in navs) for x in said)
        g.add('beats agree with the timeline (click and cuts on its navigation)', ok, f'timeline nav frames {navs}, beats say {said}')
    ev = beats.get('events', {})
    for first, then in beats.get('order', []):
        g.add(f'{first} before {then}', first in ev and then in ev and ev[first] <= ev[then], f"{ev.get(first)} / {ev.get(then)}")
    cur = beats.get('cursor_entry')
    if cur:
        x, y = cur; bx = beats.get('page_box') or [0, 0, 1080, 1080]
        g.add('the cursor enters inside the frame', bx[0] <= x <= bx[2] and bx[1] <= y <= bx[3], f'({x}, {y}) in {bx}')
    if all('view' in f for f in tl):
        plan_motion(tl, beats, g, a.get('--stitch'))
        plan_framing(tl, beats, g, a.get('--stitch'))
        plan_text(tl, beats, g, a.get('--stitch'))
    return g.verdict()


# ------------------------------------------------------------------ plan: motion and framing, from the views
def _stitch_meta(stitch):
    return json.load(open(os.path.join(stitch, 'stitch.json'))) if stitch else {}


def _profile(tl, beats):
    """per frame: (t, worst on-screen speed px/f, zoom part, pan part, scroll part) from consecutive views"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from filmkit import profile as P
    fps = beats.get('fps', 60); bx = beats.get('page_box') or [0, 0, 1080, 1080]; win_w = bx[2] - bx[0]
    rows = []
    for i in range(len(tl) - 1):
        va, vb = tl[i]['view'], tl[i + 1]['view']
        if tl[i + 1].get('nav') or tl[i].get('site') != tl[i + 1].get('site'):
            rows.append((i / fps, 0.0, 0.0, 0.0, 0.0, 0.0)); continue
        v = P.travel(va, vb, win_w); zp, pp = P.parts(va, vb, win_w)
        sa, sb = tl[i]['s'][len(tl[i]['s']) // 2], tl[i + 1]['s'][len(tl[i + 1]['s']) // 2]
        sp = abs(sb - sa) * win_w / va[2]
        rows.append((i / fps, v, 0.0, zp, max(0.0, pp - sp), sp))
    return rows, P


def _density(stitch, view, cache={}):
    if not stitch:
        return None
    if 'src' not in cache:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from filmkit import sources
        cache['src'] = sources.StitchedSource(stitch, [{'s': [0]}])
    src = cache['src']; pg, sc = src.page, src.sc
    x0, y0, cw, ch = view
    im = pg.crop((round(max(0, x0) * sc), round(y0 * sc), round((x0 + cw) * sc), round((y0 + ch) * sc))).convert('L')
    im = im.resize((480, max(1, round(480 * ch / cw))), Image.LANCZOS)
    return round(ImageStat.Stat(im.filter(ImageFilter.FIND_EDGES)).mean[0], 2)


def plan_motion(tl, beats, g, stitch=None):
    rows, P = _profile(tl, beats)
    fps = beats.get('fps', 60); w = round(HARSH_WIN * fps)
    v = [r[1] for r in rows]
    harsh, k = [], 1
    while k < len(v) - 1:
        if not (v[k] <= v[k - 1] and v[k] <= v[k + 1]):
            k += 1; continue
        before, after = max(v[max(0, k - w):k]), max(v[k + 1:k + 1 + w])
        low = min(before, after)
        if not (low > 2.0 and v[k] < HARSH_DIP * low and max(before, after) > HARSH_PEAK):
            k += 1; continue
        a = b = k                                    # the near-stop: the frames under HARSH_DIP of the smaller neighbour
        while a > 0 and v[a - 1] < HARSH_DIP * low: a -= 1
        while b < len(v) - 1 and v[b + 1] < HARSH_DIP * low: b += 1
        if (b - a + 1) / fps < HARSH_HOLD:
            harsh.append((round(k / fps, 2), round(before, 1), round(v[k], 1), round(after, 1), round((b - a + 1) / fps, 2)))
        k = b + 1
    g.add('moves join without a harsh stop-and-go', not harsh,
          'none' if not harsh else '; '.join(f'{t:.2f} s: {b} -> {d} -> {a} px/f, near-stop {n} s' for t, b, d, a, n in harsh[:4]))
    labels = {round(b['t0'], 2): b for b in beats.get('beats', [])}
    for m in P.moves(rows, fps):
        cam = m['kind'].get('zoom', 0) + m['kind'].get('pan', 0)
        if cam < 0.6 or m['peak'] <= FAST_CAMERA:
            continue
        end = tl[min(len(tl) - 1, round(m['t1'] * fps))]['view']
        dens = _density(stitch, end)
        tag = 'unmeasured (no --stitch)' if dens is None else f"{dens} ({'dense' if dens >= DENSE else 'sparse'})"
        if dens is None or dens >= DENSE:
            need = m['peak'] * m['dur'] / FAST_CAMERA                 # the same curve, stretched until its peak is the floor
            soft = 1.875 * m['mean'] * m['dur'] / FAST_CAMERA         # T >= k D / (P fps) with soft's k, D = mean x frames
            g.warn(f"fast camera move {m['t0']:.2f}-{m['t1']:.2f} s", f"peak {m['peak']} px/f, density {tag}: at {FAST_CAMERA:.0f} px/f it "
                   f"needs {need:.1f} s on this curve or {soft:.1f} s on soft (it has {m['dur']:.2f} s), or say why it is kept")
    for b in beats.get('beats', []):
        if 'dense' in b and b.get('subject'):
            x0, y0, x1, y1 = b['subject']
            dens = _density(stitch, (x0, y0, x1 - x0, y1 - y0))
            if dens is not None and (dens >= DENSE) != bool(b['dense']):
                g.warn(f"density label: {b['name']}", f"labelled {'dense' if b['dense'] else 'sparse'}, measured {dens}")


def holds_of(tl, beats):
    """[(first frame, last frame)] of every stretch where the view holds still (under STILL px/f) for CUT_HOLD[0] s"""
    rows, _ = _profile(tl, beats); fps = beats.get('fps', 60); v = [r[1] for r in rows]; out, i = [], 0
    while i < len(v):
        if v[i] >= STILL:
            i += 1; continue
        j = i
        while j + 1 < len(v) and v[j + 1] < STILL: j += 1
        if (j - i + 1) / fps >= CUT_HOLD[0]: out.append((i, j))
        i = j + 1
    return out


def cut_lines(f, boxes, nav_h):
    """the lines of text a frame's window cuts: [(words, edges)]. The window's page area is the view; when the page's
    fixed nav is inside it, the nav covers the page down to its bottom edge, so that is the window's top for the words"""
    vx, vy, cw, ch = f['view']; s = f['s'][len(f['s']) // 2]
    top = max(vy, s + nav_h) if nav_h and vy < s + nav_h else vy
    x1, y1, out = vx + cw, vy + ch, []
    for bx0, by0, bx1, by1, words in boxes:
        if bx1 <= vx + 1 or bx0 >= x1 - 1 or by1 <= top + 1 or by0 >= y1 - 1:
            continue                                            # outside the window (or touching it by a pixel)
        edges = [e for e, c in (('left', bx0 < vx - 1), ('right', bx1 > x1 + 1), ('top', by0 < top - 1), ('bottom', by1 > y1 + 1)) if c]
        if edges: out.append((words, edges))
    return out


def plan_text(tl, beats, g, stitch=None):
    """No line of text cut by the window's edge while the view holds: the eye reads a still frame, and a word cut in
    half reads as a mistake (a question cut mid-word at the top of a closing hold; a heading cut to its first letters
    at a stop of a pan). From the stitch's text lines (page px); a hold of CUT_HOLD[1] s or more FAILs, a shorter stop WARNs"""
    meta = _stitch_meta(stitch); boxes = meta.get('text')
    if not boxes:
        return
    fps = beats.get('fps', 60); nav_h = beats.get('nav_h', meta.get('nav_h', 0)) or 0
    for i, j in holds_of(tl, beats):
        cut = cut_lines(tl[(i + j) // 2], boxes, nav_h)
        dur = (j - i + 1) / fps; name = f"no text cut by the window's edge: hold {i / fps:.2f}-{(j + 1) / fps:.2f} s"
        said = '; '.join(f'"{w}" ({"/".join(e)})' for w, e in cut[:4]) + (f' and {len(cut) - 4} more' if len(cut) > 4 else '')
        if dur >= CUT_HOLD[1]:
            g.add(name, not cut, said or 'none')
        elif cut:
            g.warn(name, f'a {dur:.2f} s stop: {said}')


def plan_framing(tl, beats, g, stitch=None):
    fps = beats.get('fps', 60); bx = beats.get('page_box') or [0, 0, 1080, 1080]; win_w = bx[2] - bx[0]
    nav_h = beats.get('nav_h', _stitch_meta(stitch).get('nav_h'))
    for b in beats.get('beats', []):
        if b.get('role') == 'scroll' or not (b.get('subject') or b.get('row')):
            continue
        fr = [tl[min(len(tl) - 1, round(t * fps))] for t in (b['t0'], (b['t0'] + b['t1']) / 2, b['t1'])]
        if b.get('subject'):
            x0, y0, x1, y1 = b['subject']
            worst_nav, worst_in, worst_c = None, None, None
            for f in fr:
                vx, vy, cw, ch = f['view']; k = win_w / cw; s = f['s'][len(f['s']) // 2]
                L, R = (x0 - vx) * k, win_w - (x1 - vx) * k
                T, B = (y0 - vy) * k, ch * k - (y1 - vy) * k
                if nav_h is not None and vy < s + nav_h:          # the nav is in the window: the subject must clear it
                    clear = (y0 - (s + nav_h)) * k
                    worst_nav = clear if worst_nav is None else min(worst_nav, clear)
                inside = min(L, R, T, B)
                worst_in = inside if worst_in is None else min(worst_in, inside)
                tol = max(8.0, CENTRE_TOL * win_w); mode = b.get('centre', 'x')
                off = max(abs(L - R) if mode in ('x', 'xy') else 0.0, abs(T - B) if mode == 'xy' else 0.0)
                worst_c = off if worst_c is None else max(worst_c, off)
            if worst_nav is not None:
                g.add(f"{b['name']}: subject clear of the page's fixed nav", worst_nav >= NAV_AIR * win_w / fr[0]['view'][2],
                      f"{worst_nav:.0f} px below the nav (at least {NAV_AIR:.0f} css px)")
            g.add(f"{b['name']}: subject inside the window", worst_in >= 0, f"tightest margin {worst_in:.0f} px")
            if b.get('centre', 'x') != 'none':
                g.add(f"{b['name']}: subject centred", worst_c <= max(8.0, CENTRE_TOL * win_w),
                      f"{worst_c:.0f} px off (at most {max(8.0, CENTRE_TOL * win_w):.0f})")
        if b.get('row'):
            ry0, ry1 = b['row']['y']; slivers = []
            for f in fr:
                vx, vy, cw, ch = f['view']; k = win_w / cw
                if ry1 < vy or ry0 > vy + ch:
                    continue
                for cx0, cx1 in b['row']['x']:
                    vis = max(0.0, min(cx1, vx + cw) - max(cx0, vx))
                    if 0 < vis and (vis / (cx1 - cx0) < SLIVER[0] or vis * k < SLIVER[1]):
                        slivers.append(f"card {cx0:.0f}-{cx1:.0f}: {vis * k:.0f} px")
            g.add(f"{b['name']}: no sliver of a neighbouring card", not slivers, '; '.join(sorted(set(slivers))) or 'none')


def cmd_map(a):
    """the camera map: the whole page (the stitch), every hold's window drawn on it and numbered, the window's centre as a
    path between them, and in red each line of text a hold cuts. The choreography at a glance, before a capture: the
    owner reads where the camera stops and what it shows, and says yes or moves a stop"""
    from PIL import ImageDraw, ImageFont
    tl = json.load(open(a['TIMELINE'])); beats = json.load(open(a['--beats'])) if a.get('--beats') else {}
    stitch = a.get('--stitch'); meta = _stitch_meta(stitch)
    if not meta:
        print('MISSING --stitch: the camera map draws on the stitched page'); sys.exit(2)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from filmkit import sources
    src = sources.StitchedSource(stitch, [{'s': [0]}]); vw = meta['viewport'][0]
    col_w = int(a.get('--width', 420)); k = col_w / vw; col_h = int(a.get('--column', 1500))
    page = src.page.resize((col_w, round(src.page.height * col_w / src.page.width)), Image.LANCZOS).convert('RGBA')
    over = Image.new('RGBA', page.size, (0, 0, 0, 0)); d = ImageDraw.Draw(over)
    font = ImageFont.load_default(15)   # Pillow's own scalable face: the same map on every machine
    fps = beats.get('fps', 60); nav_h = beats.get('nav_h', meta.get('nav_h', 0)) or 0; boxes = meta.get('text') or []
    path = [((f['view'][0] + f['view'][2] / 2) * k, (f['view'][1] + f['view'][3] / 2) * k) for f in tl[::3]]
    d.line(path, fill=(252, 119, 83, 150), width=2)
    names = {}
    for b in beats.get('beats', []):
        names[(b['t0'], b['t1'])] = b['name']
    legend = []
    for n, (i, j) in enumerate(holds_of(tl, beats), 1):
        f = tl[(i + j) // 2]; vx, vy, cw, ch = f['view']
        for words, edges in cut_lines(f, boxes, nav_h):
            for bx0, by0, bx1, by1, w in boxes:
                if w == words and bx1 > vx and bx0 < vx + cw and by1 > vy and by0 < vy + ch:
                    d.rectangle([bx0 * k, by0 * k, bx1 * k, by1 * k], fill=(220, 30, 30, 110))
        d.rectangle([vx * k, vy * k, (vx + cw) * k, (vy + ch) * k], outline=(26, 26, 26, 255), width=2)
        d.rectangle([vx * k, vy * k, vx * k + 22, vy * k + 20], fill=(26, 26, 26, 255))
        d.text((vx * k + 5, vy * k + 2), str(n), fill=(255, 255, 255, 255), font=font)
        t0, t1 = i / fps, (j + 1) / fps
        nm = next((v for (b0, b1), v in names.items() if b0 < t1 and b1 > t0), '')
        legend.append(f"{n}  {t0:5.2f}-{t1:5.2f} s  {nm}")
    page = Image.alpha_composite(page, over).convert('RGB')
    cols = [page.crop((0, y, col_w, min(page.height, y + col_h))) for y in range(0, page.height, col_h)]
    heads = ['the camera map: each hold numbered;', 'red: a line of text the hold cuts']
    meas = ImageDraw.Draw(Image.new('RGB', (1, 1)))     # the legend's column fits its longest line: no label is cut
    lw = 24 + int(max(meas.textlength(t, font=font) for t in heads + legend))
    out = Image.new('RGB', (len(cols) * (col_w + 12) + lw, max(max(c.height for c in cols), 64 + 20 * len(legend))), (255, 255, 255))
    for c, im in enumerate(cols):
        out.paste(im, (c * (col_w + 12), 0))
    dd = ImageDraw.Draw(out); x = len(cols) * (col_w + 12) + 8
    dd.text((x, 8), heads[0], fill=(26, 26, 26), font=font)
    dd.text((x, 26), heads[1], fill=(200, 30, 30), font=font)
    for n, line in enumerate(legend):
        dd.text((x, 56 + n * 20), line, fill=(26, 26, 26), font=font)
    out.save(a['--out']); print('wrote', a['--out'], out.size, len(legend), 'holds')


def cmd_motion(a):
    """the instrument: every move of the plan with its peak, mean, kind and dips; WARN lines as in the plan gates"""
    tl = json.load(open(a['TIMELINE'])); beats = json.load(open(a['--beats'])) if a.get('--beats') else {}
    rows, P = _profile(tl, beats)
    for m in P.moves(rows, beats.get('fps', 60)):
        k = max(m['kind'], key=m['kind'].get)
        travel = m['mean'] * (round(m['dur'] * beats.get('fps', 60)) + 1)     # D: the worst point's on-screen travel
        print(f"{m['t0']:6.2f}-{m['t1']:6.2f} s {k:6s} peak {m['peak']:5.1f} px/f, mean {m['mean']:5.1f}, travel {travel:5.0f} px"
              + (f", dips {m['dips']}" if m['dips'] else ''))
    return True


# ------------------------------------------------------------------ capture
def cmd_capture(a):
    cj = json.load(open(a['CAPTURE']))
    d = os.path.dirname(os.path.abspath(a['CAPTURE']))
    g = Gates(os.path.basename(a['CAPTURE']))
    nav = set()
    if a.get('--timeline'):
        tl = json.load(open(a['--timeline']))
        if cj.get('max_samples'):   # a draft capture thinned each frame's samples the same way (filmkit.capture._thin)
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from filmkit.capture import _thin
            tl = [dict(f, s=_thin(f['s'], cj['max_samples'])) for f in tl]
        nav = {f['i'] for f in tl if f.get('nav')}
        missing = [(f['i'], k) for f in tl for k in range(len(f['s'])) if not os.path.exists(f"{d}/{f['i']:05d}-{k}.jpg")]
        g.add('every capture on disk', not missing, f"{sum(len(f['s']) for f in tl) - len(missing)} of {sum(len(f['s']) for f in tl)}")
    g.add('no form was sent', cj.get('posts') == 0, f"posts {cj.get('posts')}")
    if a.get('--expect-url'):
        url = cj.get('url1') or cj.get('url_end') or ''   # a film without a navigation: where it ended
        g.add('the click landed' if cj.get('url1') else 'the page is the expected one', bool(re.search(a['--expect-url'], url)),
              f"url1 {cj.get('url1')}" if cj.get('url1') else f"url_end {url}")
    if cj.get('acts') and not cj.get('url1'):
        g.add('in-page clicks stayed on the page', cj.get('url_end') == cj.get('url0'), f"{len(cj['acts'])} acts, url_end {cj.get('url_end')}")
    fms = 1000 / cj.get('fps', 60)
    r = [(p[0], p[2] * p[3] / fms) for p in cj.get('pacing') or [] if p[0] not in nav]   # (frame, page time over film time)
    if not r:   # an older record: a line every 30 frames, the average ms per frame and the rate it set for the next 30
        prev = None
        for line in cj.get('log', []):
            mm = re.search(r'frame (\d+): (\d+) ms per capture, playback rate ([\d.]+)', line)
            if mm:
                if prev is not None:
                    r += [(int(mm.group(1)) - 29 + k, float(mm.group(2)) * prev / fms) for k in range(30)]
                prev = float(mm.group(3))
    if r:
        run, worst, at, cur = 0, 0, None, None
        for f, x in r:
            if 0.67 <= x <= 1.5:
                run = 0
                continue
            run, cur = run + 1, (f if run == 0 else cur)
            if run > worst:
                worst, at = run, cur
        xs = [x for _, x in r]
        g.add('page time paced to the film (no 0.1 s outside 0.67x to 1.5x)', worst < 6,
              f'median {statistics.median(xs):.2f}x, range {min(xs):.2f}x to {max(xs):.2f}x, '
              + (f'longest stretch off pace {worst} frames from frame {at}' if worst else 'never off pace'))
    else:
        g.add('page time paced to the film', False, 'no pacing record in capture.json')
    return g.verdict()


# ------------------------------------------------------------------ tools
def rate_of(v):
    n, d = v['r_frame_rate'].split('/')
    return int(n) / int(d)


def cmd_speed(a):
    pr = probe(a['FILM']); v = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]
    W, H, fps = v['width'], v['height'], rate_of(v)
    box = [int(x) for x in a['--box'].split(',')] if a.get('--box') else [0, 0, W, H]
    f0, f1 = round(float(a['--from']) * fps), round(float(a['--to']) * fps)
    prof = []
    for i, im in enumerate(frames(a['FILM'], W, H)):
        if i > f1:
            break
        prof.append(profile(im.convert('L'), tuple(box)) if i >= f0 - 1 else None)
    for i, s in speeds(prof, f0, f1):
        print(f'{i / fps:.3f} {s:7.2f}')
    print('brake:', brake(speeds(prof, f0, f1)))


def cmd_cover(a):
    """the cover's page layer as the film composes it (the raw frame, the camera, the blur, the veil), and the share of
    dark page under each title box (page-area px). Dark is L < COVER_DARK after the veil: photos and buttons, not the faint
    grey of blurred text."""
    z, cx, cy = (float(x) for x in a['--cam'].split(','))
    VW, VH = (int(x) for x in a['--viewport'].split('x')); PW, PH = (int(x) for x in a['--page-area'].split('x'))
    padx = float(a.get('--padx', 0))
    im = Image.open(a['--raw']).convert('RGB').resize((VW, VH), Image.LANCZOS)
    cw, ch = VW / z, VH / z
    x0, y0 = min(max(cx - cw / 2, -padx), VW - cw), min(max(cy - ch / 2, 0), VH - ch)
    if x0 < 0:   # past the page's left edge the page's own white continues
        pad = math.ceil(-x0); wide = Image.new('RGB', (VW + pad, VH), (255, 255, 255)); wide.paste(im, (pad, 0)); im = wide; x0 += pad
    pg = im.resize((PW, PH), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).filter(ImageFilter.GaussianBlur(float(a['--blur'])))
    L = Image.blend(pg, Image.new('RGB', pg.size, (255, 255, 255)), float(a['--veil'])).convert('L')
    g = Gates('cover')
    for bx in a['--box'] if isinstance(a['--box'], list) else [a['--box']]:
        box = tuple(int(x) for x in bx.split(','))
        px = list(L.crop(box).getdata()); share = sum(1 for v in px if v < COVER_DARK) / len(px)
        g.add(f'quiet ground under the title {box}', share <= COVER_FLOOR, f'{100 * share:.1f}% dark (L<{COVER_DARK}), floor {100 * COVER_FLOOR:g}%')
    return g.verdict()


def cmd_sheet(a):
    pr = probe(a['FILM']); v = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]
    W, H = v['width'], v['height']; every = float(a.get('--every', 0.25)); fps = rate_of(v)
    picks = []
    for i, im in enumerate(frames(a['FILM'], W, H)):
        if i % round(every * fps) == 0:
            picks.append((i, im.resize((216, round(216 * H / W)), Image.LANCZOS)))
    cols = 8; rows = math.ceil(len(picks) / cols); tw, th = picks[0][1].size
    sheet = Image.new('RGB', (cols * (tw + 6) + 6, rows * (th + 6) + 6), (240, 240, 240))
    for k, (i, t) in enumerate(picks):
        sheet.paste(t, (6 + (k % cols) * (tw + 6), 6 + (k // cols) * (th + 6)))
    out = a['FILM'] + '.sheet.png'; sheet.save(out); print('wrote', out)


def cmd_platform(a):
    """an instrument, not a gate: a platform's re-encode simulated (x264 at a capped bitrate), scored frame by frame
    with SSIM against the film. Look at the worst moment in both files before calling a film safe to post."""
    mbps = float(a.get('--mbps', 3)); out = a['FILM'] + f'.sim-{mbps:g}M.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a['FILM'], '-c:v', 'libx264', '-preset', 'medium', '-b:v', f'{mbps}M',
                    '-maxrate', f'{mbps * 1.5}M', '-bufsize', f'{mbps * 2}M', '-pix_fmt', 'yuv420p', '-an', out], check=True)
    log = out + '.ssim.txt'
    subprocess.run(['ffmpeg', '-v', 'error', '-i', out, '-i', a['FILM'], '-lavfi', f'ssim=stats_file={log}', '-f', 'null', '-'], check=True)
    rows = [l.split() for l in open(log)]
    vals = [(int(r[0].split(':')[1]) - 1, float(r[-2].split(':')[1])) for r in rows if r and r[0].startswith('n:')]
    fps = rate_of([s for s in probe(a['FILM'])['streams'] if s['codec_type'] == 'video'][0])
    worst = sorted(vals, key=lambda v: v[1])[:5]
    print(f'simulated {mbps:g} Mbps re-encode: {out}')
    print(f'SSIM mean {statistics.mean(v for _, v in vals):.4f}; worst frames: ' + ', '.join(f'{i / fps:.2f} s ({v:.4f})' for i, v in worst))
    return None


def fmd5(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-map', '0:v', '-f', 'framemd5', '-'], capture_output=True, text=True)
    return [line.split(',')[-1].strip() for line in r.stdout.splitlines() if line and not line.startswith('#')]


def _sidecar(path):
    try:
        return json.load(open(path + '.film_check.json'))
    except (OSError, ValueError):
        return {}


def cmd_review(a):
    """the independent review's verdict, kept in the sidecar beside the gates' verdict. The owner's yes is not the
    review: on one film a cut reached the owner a minute before the reviewer failed it, and a cut the owner called
    perfect had not been reviewed. The sidecar must hold the gates for these exact bytes; a later `file` run on the same
    bytes keeps the review. --from MASTER copies the master's review to a copy whose decoded frames are identical (an
    upload copy is a remux: new bytes, the same film)"""
    path = a['FILM']; sha = hashlib.sha256(open(path, 'rb').read()).hexdigest(); side = _sidecar(path)
    if side.get('sha256') != sha:
        print(f'MISSING the gates first: {path}.film_check.json is not for these bytes (run film_check.py file)'); sys.exit(2)
    if a.get('--from'):
        src = _sidecar(a['--from']).get('review')
        x, y = fmd5(a['--from']), fmd5(path)
        if not src or src.get('sha256') != hashlib.sha256(open(a['--from'], 'rb').read()).hexdigest():
            print(f"MISSING a review recorded on {a['--from']} for its bytes"); sys.exit(2)
        if not x or x != y:
            print(f"FAIL the copy's decoded frames differ from {a['--from']}: the review does not carry"); return False
        rv = dict(src, via=os.path.basename(a['--from']), sha256=sha)
    else:
        if a.get('--verdict') not in ('pass', 'fix') or not a.get('--by'):
            print('review needs --verdict pass|fix and --by (who reviewed), or --from MASTER.mp4'); sys.exit(2)
        rv = {'verdict': a['--verdict'], 'by': a['--by'], 'note': a.get('--note', ''),
              'date': time.strftime('%d %b %Y, %H:%M'), 'sha256': sha}
    side['review'] = rv
    json.dump(side, open(path + '.film_check.json', 'w'), indent=1)
    print(f"REVIEW {rv['verdict']} by {rv['by']}" + (f" (via {rv['via']})" if rv.get('via') else '')
          + f" recorded beside the gates' {side.get('verdict')}: {path}.film_check.json")
    return rv['verdict'] == 'pass'


def cmd_same(a):
    x, y = fmd5(a['A']), fmd5(a['B'])
    diff = [i for i, (p, q) in enumerate(zip(x, y)) if p != q]
    g = Gates('same')
    g.add('decoded frames identical', x and len(x) == len(y) and not diff,
          f'{len(x)} and {len(y)} frames, {len(diff)} differ' + (f' (first {diff[0]})' if diff else ''))
    return g.verdict()


PATH_DIFF = 8.0        # levels: the mean grey difference under which two frames show the same view of a still page


def cmd_path(a):
    """the same camera on two renders of one plan (an animatic against its final, a draft against the capture): at each
    time the page area of A is matched against B shifted up to 4 px each way, in grey. The framing agrees when the best
    shift is (0, 0) and the difference there is under PATH_DIFF. Pick times where the page itself holds still: its own
    motion (a video, a drifting collage) differs between an animatic and a capture by design"""
    W, H = FORMATS[a.get('--format', '1x1')]; fps = float(a.get('--fps', 60))
    box = tuple(int(v) for v in a['--box'].split(',')) if a.get('--box') else (100, 300, W - 100, H - 100)
    g = Gates('path'); off, seen = [], []
    for t in [float(v) for v in a['--times'].split(',')]:
        fa, fb = frame_at(a['A'], round(t * fps), W, H), frame_at(a['B'], round(t * fps), W, H)
        if fa is None or fb is None:
            off.append(f'{t:.2f} s: no frame'); continue
        la, lb = fa.convert('L').crop(box), fb.convert('L')
        d, dx, dy = min((ImageStat.Stat(ImageChops.difference(la, lb.crop((box[0] + x, box[1] + y, box[2] + x, box[3] + y)))).mean[0], x, y)
                        for x in range(-4, 5) for y in range(-4, 5))
        seen.append(f'{t:.2f} s {d:.1f}')
        if (dx, dy) != (0, 0) or d >= PATH_DIFF:
            off.append(f'{t:.2f} s: best at ({dx:+d}, {dy:+d}), difference {d:.1f}')
    g.add(f'camera path: the same framing at every time (best shift 0, 0; difference under {PATH_DIFF:.0f})', not off,
          '; '.join(off) if off else 'differences ' + ', '.join(seen))
    return g.verdict()


def cmd_eval(a):
    """the gates proven on renders whose faults are known: each case names the verdict each gate must give. In a case's
    args a value starting with @ is a path under --root. Eval runs write no sidecars."""
    import tempfile
    man = json.load(open(a['MANIFEST'])); root = a['--root']; me = os.path.abspath(__file__)
    tmpd = tempfile.mkdtemp(prefix='film_check_eval_'); bad = checked = 0
    for n, c in enumerate(man['cases']):
        args = [sys.executable, me, c['command']] + [os.path.join(root, x[1:]) if x.startswith('@') else x for x in c['args']]
        if c['command'] == 'file':
            args.append('--no-sidecar')
        if c.get('beats'):
            bt = man['beats'][c['beats']] if isinstance(c['beats'], str) else c['beats']
            tmp = os.path.join(tmpd, f'{n}.beats.json'); json.dump(bt, open(tmp, 'w')); args += ['--beats', tmp]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode == 2:
            bad += len(c['expect']); print(f"MISS {c['name']}: could not run ({(r.stdout + r.stderr).strip().splitlines()[-1:]})"); continue
        got = [('FAIL' if v == 'ANSW' else v, rest) for v, rest in (mm.groups() for mm in (re.match(r'(PASS|FAIL|ANSW)\s+\d+\s+(.*)$', line)
               for line in r.stdout.splitlines()) if mm)]   # an answered gate failed: eval judges the gate, not the answer
        for gate, want in c['expect'].items():
            hit = [v for v, rest in got if rest.startswith(gate)]
            ok = bool(hit) and all(v == want for v in hit)
            bad += not ok; checked += 1
            print(f"{'OK  ' if ok else 'MISS'} {c['name']}: {gate} expected {want}, got {', '.join(hit) or 'not run'}", flush=True)
    print(f"eval: {'PASS' if not bad else 'FAIL'} ({checked} expectations, {bad} unexpected)")
    return not bad


def parse(argv):
    pos, opts, i = [], {}, 0
    while i < len(argv):
        if argv[i].startswith('--'):
            k = argv[i]
            if i + 1 < len(argv) and not argv[i + 1].startswith('--'):
                if k in opts:
                    opts[k] = (opts[k] if isinstance(opts[k], list) else [opts[k]]) + [argv[i + 1]]
                else:
                    opts[k] = argv[i + 1]
                i += 2
            else:
                opts[k] = True; i += 1
        else:
            pos.append(argv[i]); i += 1
    return pos, opts


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    cmd, (pos, opts) = sys.argv[1], parse(sys.argv[2:])
    names = {'file': ['FILM'], 'plan': ['TIMELINE'], 'motion': ['TIMELINE'], 'capture': ['CAPTURE'], 'speed': ['FILM'], 'sheet': ['FILM'],
             'platform': ['FILM'], 'same': ['A', 'B'], 'path': ['A', 'B'], 'review': ['FILM'], 'eval': ['MANIFEST'], 'cover': [], 'map': ['TIMELINE']}
    if cmd not in names:
        print(__doc__); sys.exit(2)
    a = dict(zip(names[cmd], pos)); a.update(opts)
    fn = {'file': cmd_file, 'plan': cmd_plan, 'motion': cmd_motion, 'capture': cmd_capture, 'speed': cmd_speed, 'sheet': cmd_sheet,
          'platform': cmd_platform, 'same': cmd_same, 'path': cmd_path, 'review': cmd_review, 'eval': cmd_eval, 'cover': cmd_cover, 'map': cmd_map}[cmd]
    ok = fn(a)
    sys.exit(0 if ok in (None, True) else 1)
