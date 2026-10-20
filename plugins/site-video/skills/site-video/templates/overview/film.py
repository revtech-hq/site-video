#!/usr/bin/env python3
"""An overview film of one web page: the page's hero plays; on the first scroll the page's own mark lifts out of the
page and docks above it while the page steps back into a browser window; the camera travels the page (dives, glides,
real clicks, a highlighted sentence) and the film ends on the mark and the page's address meeting on the ground.
The numbers are in film.json, the brand's values in brand.json, the mark and the address line in chrome_dir
(made by the chrome command, from the page itself). Run every command through the skill's launcher:

  sv film DIR recon                  measure the boxes the camera frames (recon.items in film.json) into recon.json
  sv film DIR chrome                 render the page's mark and its address line into chrome_dir
  sv film DIR timeline [OUT.json]    plan the timeline (default: timeline.json beside this file)
  sv film DIR stitch                 the whole page at rest, for the camera map and the animatic (seconds)
  sv film DIR animatic OUT.mp4       every frame from the stitch: the camera, timing and framing, no page motion
  sv film DIR draft                  the rough cut's capture (1x, one frame of settle, at most 3 samples);
                                     then FILM_SOURCE=draft sv film DIR all OUT.mp4
  sv film DIR capture                the final's capture, once the direction is agreed
  sv film DIR keys OUT [T,T,...]     storyboard frames
  sv film DIR all OUT.mp4            every frame, piped to the encoder, with the render record beside it
  sv film DIR cover OUT.png [T]      one frame as a still (the cover), default T: cover_t in film.json or 3.25 s
A relative "goto" in capture.pre is a page beside this file (a local demo), opened as a file:// URL."""
import json, math, os, sys
from multiprocessing import Pool
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get('FILMKIT'):                          # the launcher sets it; PYTHONPATH carries it too
    sys.path.insert(0, os.environ['FILMKIT'])
from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: E402
from filmkit import motion, timeline, compose as fk, sources, encode  # noqa: E402
from filmkit.motion import ease, ease_out, prog  # noqa: E402

F = json.load(open(os.environ.get('FILM_JSON') or f'{HERE}/film.json')); B = json.load(open(f'{HERE}/brand.json'))
RAW, CHR = os.path.normpath(f'{HERE}/{F["raw_dir"]}'), os.path.normpath(f'{HERE}/{F["chrome_dir"]}')
STITCH = os.path.normpath(f'{HERE}/{F.get("stitch_dir", F["raw_dir"] + "-stitch")}')
FPS, DUR, CAP_END = F['fps'], F['duration'], F['cap_end']
VW, VH = F['viewport']; N = round(FPS * DUR)
W, H = F['frame']['W'], F['frame']['H']
WX, WY, WW, WH = F['frame']['win']                     # the window once the page has stepped back
GROUND, WHITE = tuple(B['ground']), tuple(B['white'])
O = F['open']; E = F['end']

# ------------------------------------------------------------------------- the timeline
_segs = [(t0, t1, a, b, motion.stop_scroll(b - a, t0, r, d, t1)) for t0, t1, a, b, r, d in F['scroll']]
def scroll(t):
    y = _segs[0][2]
    for t0, t1, a, b, f in _segs:
        if t >= t0: y = a + f(t)
    return y

def step_u(t): return ease(prog(t, O['t_step']))
def win_box(t):
    """the window in the frame: the whole frame at the opening, stepping back to its inset box"""
    u = step_u(t); return (WX * u, WY * u, W + (WW - W) * u, H + (WH - H) * u)

_cam = F['camera']['keys']
NAV = F['nav_h']; ASPECT = WW / WH
def crop(t):
    """(zoom, x0, y0, cw, ch) page px: a square push on the hero (inside its ground: below the nav, above its bottom),
    the step back (the crop widens with the window and stays below the nav while the mark rises past it), then the
    camera keys, at the window's aspect"""
    if t < O['t_step'][1]:
        cx, cy, s0, s1 = O['square']; s = s0 + (s1 - s0) * prog(t, O['push'])
        u = step_u(t) if t >= O['t_step'][0] else 0.0
        ch_end = O.get('hero_bottom', VH) - NAV   # the window holds the hero's ground to its bottom edge
        ch = s + (ch_end - s) * u; cyy = cy + (NAV + ch_end / 2 - cy) * u
        x, y, w, h = win_box(t); cw = min(VW, ch * w / h)
        return VH / ch, VW / 2 - cw / 2, min(max(0.0, cyy - ch / 2), VH - ch), cw, ch
    z, cx, cy = motion.camera_at(_cam, t)
    ch = VH / z; cw = min(VW, ch * ASPECT)
    return z, min(max(cx - cw / 2, 0.0), VW - cw), min(max(cy - ch / 2, 0.0), VH - ch), cw, ch

def camera(t):
    z, x0, y0, cw, ch = crop(t); return (VH / ch, x0 + cw / 2, y0 + ch / 2)

CUR = [dict(c, fn=motion.bezier_cursor(c['p0'], c['pc'], c['p1'], c['span'], 1e9)) for c in F['cursors']]
REST = F['mouse_rest']
def cursor_at(t):
    """(x, y, segment) of the drawn cursor in page px of the viewport, or None: each segment travels, then rests at its
    target until the next segment or its hide"""
    cur = None
    for k, c in enumerate(CUR):
        if c['span'][0] <= t <= c['hide'][1]:
            nxt = CUR[k + 1]['span'][0] if k + 1 < len(CUR) else 1e9
            if t < nxt: cur = (*c['fn'](min(t, c['span'][1])), k)
    return cur

def real_mouse(t):
    """the real pointer: on the drawn cursor's path, then held where it clicked until the segment's release (an open card
    stays open under it), else at rest off the page's content"""
    for c in CUR:
        if c['span'][0] <= t <= c['release']: return c['fn'](min(t, c['span'][1]))
    return tuple(REST)

def acts():
    """the page's own copy of the mark is hidden as the lifted copy leaves it (open.mark_selector: a CSS selector without
    single quotes), then the clicks (each lands `lead` s after its drawn press: a page that answers in one frame answers
    as the press releases), then the mouse back to rest"""
    a = {}
    if O.get('mark_selector'):
        a[round(O['hide_at'] * FPS)] = [{'eval': "document.querySelector('" + O['mark_selector'] + "').style.visibility = 'hidden'"}]
    for c in CUR:
        for tc in c['clicks']:
            a.setdefault(round((tc + c.get('lead', 0)) * FPS), []).append({'click': c['p1']})
    for k, c in enumerate(CUR):   # back to rest after a release, unless the next segment carries on from there
        if k + 1 < len(CUR) and CUR[k + 1]['span'][0] - c['release'] < 0.1: continue
        a.setdefault(round(c['release'] * FPS) + 1, []).append({'move': REST})
    return a

def plan():
    frames, A = [], acts()
    for i in range(round(CAP_END * FPS) + 1):
        t = i / FPS; z, x0, y0, cw, ch = crop(t); wx, wy, ww, wh = win_box(t)
        ss = motion.plan_samples(scroll, t, FPS, 1.0, ww, cw)          # travel on screen = page px x window px / crop px
        m = real_mouse(t)
        f = {'i': i, 's': ss, 'scale': 'device', 'z': round(VH / ch, 3), 'site': F.get('site', 'page'), 'nav': False,
             'mouse': [round(m[0], 1), round(m[1], 1)],
             'view': [round(x0, 2), round(y0 + scroll(t), 2), round(cw, 2), round(ch, 2)]}   # the window's view of the page, page px
        if i in A: f['act'] = A[i]
        frames.append(f)
    return frames

def cap_cfg(**extra):
    """the capture block, a relative goto (a page beside this file) made a file:// URL"""
    cfg = json.loads(json.dumps(F['capture'])); cfg.update(extra)
    for st in cfg.get('pre', []) + cfg.get('after_nav', []):
        if 'goto' in st and '://' not in st['goto']:
            st['goto'] = Path(HERE, st['goto']).resolve().as_uri()
    return cfg

# ------------------------------------------------------------------------- layers
G = {}
def init():
    G['badge'] = fk.load_layer(f'{CHR}/badge.png'); G['line'] = fk.load_layer(line_image())
    G['cursor'] = fk.cursor_sprite(); G['head'] = header(WW); G['head_bar'] = header(WW, text=False)
    G['text_in'] = text_in()
    if os.environ.get('FILM_SOURCE') == 'animatic':   # the whole page from the stitch: camera, timing and framing only
        G['src'] = sources.StitchedSource(STITCH, f'{HERE}/timeline.json', ground=WHITE)
    elif os.environ.get('FILM_SOURCE') == 'draft':    # the rough cut's capture: soft (1x), the page's own motion real
        G['src'] = sources.CaptureSource(RAW + '-draft', (VW, VH), ground=WHITE)
    else:
        G['src'] = sources.CaptureSource(RAW, (VW, VH), ground=WHITE)
    im = G['badge'][0]; ls = B['lift_shadow']                         # the lift's shadow, from the mark's own alpha
    a = im.getchannel('A').point(lambda v: int(v * ls['alpha']))
    pad = ls['blur'] * 4; sh = Image.new('L', (im.width + 2 * pad, im.height + 2 * pad), 0); sh.paste(a, (pad, pad))
    G['badge_shadow'] = (sh.filter(ImageFilter.GaussianBlur(ls['blur'] * 2)), pad)   # the layer is 2x: blur doubled

INK = None
def ink_box():
    """the mark's ink in page px: the alpha's bounding box of chrome_dir/badge.png mapped onto badge_page, the element's
    box on the page (the image fills it)"""
    global INK
    if INK is None:
        bp = Image.open(f'{CHR}/badge.png'); ib = bp.getchannel('A').getbbox()
        ex, ey, ew, eh = F['badge_page']
        INK = (ex + ib[0] * ew / bp.width, ey + ib[1] * eh / bp.height, (ib[2] - ib[0]) * ew / bp.width, (ib[3] - ib[1]) * eh / bp.height)
    return INK

def line_image():
    """the address line. A capture can leave a caret at the line's right edge: from end.line_clean_x (2x px) on, the
    layer is painted with its own white"""
    im = Image.open(f'{CHR}/line.png').convert('RGBA'); x = E.get('line_clean_x')
    if x is not None: ImageDraw.Draw(im).rectangle([x, 0, im.width, im.height], fill=WHITE + (255,))
    return im

def badge_box(t):
    """(centre x, centre y, width, lift 0..1) of the mark's ink in the frame, or None before it leaves the page. From
    t_show it sits exactly where the page drew it (the page's copy is hidden at hide_at), then lifts, then docks"""
    if t < O['t_show']: return None
    t0 = O['t_show']
    z, x0, y0, cw, ch = crop(t0); wx, wy, ww, wh = win_box(t0); k = ww / cw
    bx, by, bw, bh = ink_box()
    c0 = (wx + (bx + bw / 2 - x0) * k, wy + (by + bh / 2 - y0) * k, bw * k)     # where the page drew it
    u = ease_out(prog(t, O['t_lift'])); s = 1 + (O['lift_scale'] - 1) * u
    c1 = (c0[0], c0[1] - O['lift_rise'] * u, c0[2] * s)
    d = F['frame']['badge_dock']; e = F['frame']['badge_end']
    if t < O['t_dock'][0]: return (*c1, u)
    ud = ease(prog(t, O['t_dock']))
    cd = tuple(c1[k2] + (d[k2] - c1[k2]) * ud for k2 in range(3))
    if t < E['t_badge'][0]: return (*cd, 1 - ud)
    ue = ease(prog(t, E['t_badge']))
    return (*(d[k2] + (e[k2] - d[k2]) * ue for k2 in range(3)), 0.0)

def draw_badge(fr, t):
    bb = badge_box(t)
    if not bb: return
    cx, cy, w, lift = bb
    lay = G['badge']; (_, _, (lw, lh)) = lay; h = lh * w / lw
    alpha = 1.0
    if lift > 0.01:
        sh, pad = G['badge_shadow']; k = w / lw / 2                      # the shadow image is at the layer's 2x
        sw, shh = round(sh.width * k), round(sh.height * k)
        s2 = sh.resize((sw, shh), Image.LANCZOS).point(lambda v: int(v * lift * alpha))
        col = Image.new('RGBA', (sw, shh), tuple(B['lift_shadow']['colour']) + (0,)); col.putalpha(s2)
        fr.alpha_composite(col, (round(cx - sw / 2), round(cy - shh / 2 + B['lift_shadow']['dy'] * lift)))
    fk.place(fr, lay, cx - w / 2, cy - h / 2, w, alpha)

HEAD = F['browser']['head']; S = 4
def ui_font(px):
    """the browser's interface face: browser.font (a font file on this machine) when the film names one, else
    Pillow's own scalable face"""
    from PIL import ImageFont
    path = F['browser'].get('font')
    return ImageFont.truetype(path, px) if path else ImageFont.load_default(px)

def header(w, text=True):
    """the browser's header, w px wide: three lights, the address field, a hairline; with text, the padlock and the
    address (and, with browser.caret, a caret after it: typed in, still focused)"""
    im = Image.new('RGB', (w * S, HEAD * S), (241, 243, 244)); d = ImageDraw.Draw(im)
    for k, col in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        cx, cy, r = (24 + 20 * k) * S, HEAD / 2 * S, 6 * S
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    fw, fh = 440 * S, 30 * S; fx, fy = (w * S - fw) // 2, (HEAD * S - fh) // 2
    d.rounded_rectangle([fx, fy, fx + fw, fy + fh], fh // 2, fill=(255, 255, 255))
    if text:
        f = ui_font(15 * S); url = F['browser']['url']
        tw = d.textlength(url, font=f); tx = (w * S - tw) / 2 + 8 * S; ty = HEAD / 2 * S
        lx, ly = tx - 18 * S, ty                                   # a small padlock before the address
        d.rounded_rectangle([lx - 4 * S, ly - 1 * S, lx + 4 * S, ly + 6 * S], 1.5 * S, fill=(95, 99, 104))
        d.arc([lx - 3 * S, ly - 7 * S, lx + 3 * S, ly + 3 * S], 180, 360, fill=(95, 99, 104), width=int(1.6 * S))
        d.text((tx, ty), url, font=f, fill=(32, 33, 36), anchor='lm')
        if F['browser'].get('caret'):
            cxp = tx + tw + 2.5 * S
            d.line([(cxp, ty - 9 * S), (cxp, ty + 9 * S)], fill=(32, 33, 36), width=int(1.4 * S))
    d.line([(0, HEAD * S - 1), (w * S, HEAD * S - 1)], fill=(218, 220, 224), width=S)
    return im.resize((w, HEAD), Image.LANCZOS)

def text_in():
    """(t0, t1): the address fades into the header once the lifted mark has cleared it. The header comes down as the
    window steps back while the mark rises to its dock, so the two cross; shown from the start, the mark's words lie
    across the address for a few frames. From the last frame they meet (plus one), and never before the header is 85%
    grown, over 0.15 s. None when browser.text_in is null: the address shows all the way (the header as one image)."""
    if F['browser'].get('text_in', 'auto') is None: return None
    f = ui_font(15); url = F['browser']['url']; tw = ImageDraw.Draw(Image.new('L', (1, 1))).textlength(url, font=f)
    tx = (WW - tw) / 2 + 8; ax0, ax1, ay0, ay1 = tx - 22, tx + tw + 4, HEAD / 2 - 9, HEAD / 2 + 9   # padlock to the end
    bp = Image.open(f'{CHR}/badge.png'); ib = bp.getchannel('A').getbbox(); asp = (ib[3] - ib[1]) / (ib[2] - ib[0])
    t_last, t_grown = None, None
    for i in range(round(O['t_step'][0] * FPS), round(O['t_step'][1] * FPS) + 1):
        t = i / FPS; u = step_u(t)
        if t_grown is None and u >= 0.85: t_grown = t
        bb = badge_box(t)
        if not bb or u <= 0: continue
        cx, cy, w, _ = bb; h = w * asp; wx, wy, ww, wh = win_box(t); hh = HEAD * u; k = ww / WW
        x0, x1, y0, y1 = wx + ax0 * k, wx + ax1 * k, wy - hh + ay0 * u, wy - hh + ay1 * u
        if cx + w / 2 > x0 and cx - w / 2 < x1 and cy + h / 2 > y0 and cy - h / 2 < y1: t_last = t
    t0 = max(t_grown if t_grown is not None else O['t_step'][1], (t_last + 1 / FPS) if t_last is not None else 0.0)
    return (t0, t0 + 0.15)



def rounded(size, r):
    m = Image.new('L', size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=255); return m

HL = F.get('highlight')
def highlight(pg, t, x0, y0, cw, ch, size):
    """a sentence highlighted: a band per line in the brand's ground colour, swept left to right, multiplied into the
    page so the words stay ink and only the paper takes the colour"""
    if not HL or t < HL['t']: return pg
    k = size[0] / cw; px, py = HL['pad']
    m = Image.new('L', size, 0); d = ImageDraw.Draw(m)
    for n, (a, b, c, e) in enumerate(HL['lines']):
        u = ease(prog(t, (HL['t'] + n * HL['gap'], HL['t'] + n * HL['gap'] + HL['sweep'])))
        if u <= 0: continue
        xa, xb = a - px, a - px + (c - a + 2 * px) * u
        d.rounded_rectangle([(xa - x0) * k, (b - py - y0) * k, (xb - x0) * k, (e + py - y0) * k], 4 * k, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1.2 * k))
    blue = ImageChops.multiply(pg, Image.new('RGB', size, GROUND))
    return Image.composite(blue, pg, m)

def window(fr, t, fade=0.0):
    """the page in its window: cropped by the camera, blur samples averaged, sharpened; rounded and shadowed as it
    steps back; fading and shrinking 3% at the end"""
    j = min(round(t * FPS), G['src'].last); tj = j / FPS
    z, x0, y0, cw, ch = crop(tj); wx, wy, ww, wh = win_box(tj)
    if fade: k = 1 - E.get('shrink', 0.03) * fade; wx, wy, ww, wh = wx + ww * (1 - k) / 2, wy + wh * (1 - k) / 2, ww * k, wh * k
    size = (round(ww), round(wh))
    pg = G['src'].crop(j, (x0, y0, cw, ch), size).filter(fk.UNSHARP)
    pg = highlight(pg, tj, x0, y0, cw, ch, size)
    if SE and SE.get('hide') and tj >= E['t_fade'][0]: pg = hide_sentence(pg, x0, y0, cw, ch, size)
    u = step_u(tj); r = B['window']['radius'] * u; hh = round(HEAD * u)    # the header grows in as the page steps back
    ox, oy, ow, oh = wx, wy - hh, ww, wh + hh
    outer = Image.new('RGB', (size[0], size[1] + hh), WHITE)
    if hh > 0:
        head = G['head'].resize((size[0], hh), Image.LANCZOS); ti = G['text_in']
        if ti and tj < ti[1]:   # the address fades in once the mark has cleared it (text_in)
            head = Image.blend(G['head_bar'].resize((size[0], hh), Image.LANCZOS), head, ease(prog(tj, ti)))
        outer.paste(head, (0, 0))
    outer.paste(pg, (0, hh))
    m = rounded(outer.size, r) if r > 0.5 else Image.new('L', outer.size, 255)
    if fade: m = m.point(lambda v: int(v * (1 - fade)))
    if u > 0:
        s = B['window']['shadow']; a = s['alpha'] * u * (1 - fade)
        sh = Image.new('L', (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle([ox, oy + s['dy'], ox + ow, oy + oh + s['dy']], r, fill=int(255 * a))
        sh = sh.filter(ImageFilter.GaussianBlur(s['blur']))   # outside the window only: inside it would show through a fading page
        ImageDraw.Draw(sh).rounded_rectangle([ox, oy, ox + ow, oy + oh], r, fill=0)
        lay = Image.new('RGBA', (W, H), tuple(s['colour']) + (0,)); lay.putalpha(sh)
        fr.alpha_composite(lay)
    p = outer.convert('RGBA'); p.putalpha(m); fr.alpha_composite(p, (round(ox), round(oy)))
    if u > 0:   # on a white ground the window needs an edge: a hairline in the page's ink
        ln = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ln).rounded_rectangle([round(ox), round(oy), round(ox + ow) - 1, round(oy + oh) - 1], r,
                                             outline=tuple(B['ink']) + (int(B['window']['line_alpha'] * 255 * u * (1 - fade)),), width=1)
        fr.alpha_composite(ln)
    return tj

def to_frame(t, vx, vy):
    z, x0, y0, cw, ch = crop(t); wx, wy, ww, wh = win_box(t)
    return wx + (vx - x0) * ww / cw, wy + (vy - y0) * wh / ch

def cursor(fr, tj):
    c = cursor_at(tj)
    if not c: return
    x, y, k = c; seg = CUR[k]; st = F['cursor_style']; X, Y = to_frame(tj, x, y)
    a = min(1.0, (tj - seg['span'][0]) / st['fade_in']) if k in F.get('cursor_fade_in', [0, 2]) else 1.0
    if tj > seg['hide'][0]: a *= 1 - ease(prog(tj, seg['hide']))
    press = 1.0
    for tc in seg['clicks']:
        if tc <= tj <= tc + st['press_len']: press = 1 - st['press_depth'] * math.sin(math.pi * (tj - tc) / st['press_len'])
        if tc <= tj <= tc + st['ring_len']: fk.ring(fr, X, Y, (tj - tc) / st['ring_len'], tuple(B['ring']['colour']), B['ring']['width'])
    fk.draw_cursor(fr, G['cursor'], X, Y, a, press)

SE = E.get('sentence')
def sentence_patch():
    """the highlighted sentence cut from the held closing frame (the camera and the page are still there), with a
    feathered edge: it stays while the page fades around it"""
    if 'sentence' in G: return G['sentence']
    th = SE['t_hold']; j = round(th * FPS); z, x0, y0, cw, ch = crop(th); wx, wy, ww, wh = win_box(th); k = ww / cw
    size = (round(ww), round(wh))
    pg = highlight(G['src'].crop(j, (x0, y0, cw, ch), size).filter(fk.UNSHARP), th, x0, y0, cw, ch, size)
    a, b, c, d = SE['box']; px, py = SE['pad']
    bx = (round((a - px - x0) * k), round((b - py - y0) * k), round((c + px - x0) * k), round((d + py - y0) * k))
    rgb = pg.crop(bx); f = SE['feather']
    paper = tuple(sorted(ch.getdata())[int(0.9 * rgb.width * rgb.height)] for ch in rgb.split())   # the page's paper
    lift = SE.get('white_lift', 0)   # paper this many levels under its 90th percentile turns exactly white (no faint box)
    white = Image.merge('RGB', [ch.point(lambda v, q=q: min(255, round(v * 255 / (q - lift)))) for ch, q in zip(rgb.split(), paper)])
    im = rgb.convert('RGBA')
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle([f, f, im.width - f, im.height - f], f, fill=255)
    im.putalpha(m.filter(ImageFilter.GaussianBlur(f / 2)))
    wim = white.convert('RGBA'); wim.putalpha(im.getchannel('A'))
    G['sentence'] = (im, wim, wx + bx[0], wy + bx[1], paper); return G['sentence']

def hide_sentence(pg, x0, y0, cw, ch, size):
    """the page's own copy of the sentence, painted out with its paper while the lifted copy covers it (from t_fade):
    left in place it shows under the moving copy"""
    paper = sentence_patch()[4]; k = size[0] / cw
    a, b, c, d = SE['box']; px, py = SE['pad']
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).rectangle([(a - px - x0) * k, (b - py - y0) * k, (c + px - x0) * k, (d + py - y0) * k], fill=255)
    return Image.composite(Image.new('RGB', size, paper), pg, m.filter(ImageFilter.GaussianBlur(1.5)))

def draw_sentence(fr, T):
    if not SE or T < E['t_fade'][0] or T >= SE['t_out'][1]: return
    im0, imw, px, py, _ = sentence_patch()
    im = Image.blend(im0, imw, ease(prog(T, E['t_fade'])))   # its paper turns white as the page around it fades
    u = ease(prog(T, SE['t_move'])); X = px + ((W - im.width) / 2 - px) * u; Y = py + ((H - im.height) / 2 - py) * u
    a = 1 - ease(prog(T, SE['t_out']))
    if a < 1: im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * a)))
    fr.alpha_composite(im, (round(X), round(Y)))

EC = E.get('cursor')
END_CUR = motion.bezier_cursor(EC['p0'], EC['pc'], EC['p1'], EC['span'], 1e9) if EC else None
def press_amt(T):
    """0..1: how far the final click is pressed in: in fast (0.09 s), out softer (0.26 s)"""
    if not EC or T < EC['click']: return 0.0
    u = T - EC['click']
    return ease(u / 0.09) if u < 0.09 else 1 - ease(min(1.0, (u - 0.09) / 0.26))

def end_cursor(fr, T):
    """the click on the address at the end, felt going in and out: the cursor floats over the ground on a soft shadow;
    pressed, it sinks onto it and shrinks, then springs back; a ring in the brand's accent opens from the press"""
    if not EC or T < EC['span'][0]: return
    X, Y = END_CUR(min(T, EC['span'][1])); st = F['cursor_style']
    a = min(1.0, (T - EC['span'][0]) / st['fade_in']); p = press_amt(T); press = 1 - 0.24 * p
    t_ring = EC['click'] + 0.09
    if t_ring <= T <= t_ring + st['ring_len']: fk.ring(fr, X, Y, (T - t_ring) / st['ring_len'], tuple(B['ring']['colour']), B['ring']['width'])
    spr, tip, k = G['cursor']; sh = EC['shadow']; size = EC.get('size', 34)
    if 'cursor_shadow' not in G:
        al = spr.getchannel('A'); pad = sh['blur'] * 4
        m = Image.new('L', (spr.width + 2 * pad, spr.height + 2 * pad), 0); m.paste(al, (pad, pad))
        G['cursor_shadow'] = (m.filter(ImageFilter.GaussianBlur(sh['blur'] * spr.width / 34)), pad)
    m, pad = G['cursor_shadow']; sc = size * press / (30 * k)
    mm = m.resize((max(1, round(m.width * sc)), max(1, round(m.height * sc))), Image.LANCZOS)
    mm = mm.point(lambda v: int(v * sh['alpha'] * a * (1 - 0.55 * p)))
    lay = Image.new('RGBA', mm.size, tuple(B['ink']) + (0,)); lay.putalpha(mm)
    off = 1 - 0.8 * p                                   # the shadow slides in under the cursor as it presses
    fr.alpha_composite(lay, (round(X - (tip[0] + pad) * sc + sh['dx'] * off), round(Y - (tip[1] + pad) * sc + sh['dy'] * off)))
    fk.draw_cursor(fr, G['cursor'], X, Y, a, press, size)

def frame(i):
    T = i / FPS
    fr = Image.new('RGBA', (W, H), WHITE + (255,))   # the white ground; the hero's own ground fills the opening
    if T < E['t_fade'][1]:
        tj = window(fr, min(T, CAP_END), ease(prog(T, E['t_fade'])) if T >= E['t_fade'][0] else 0.0)
        if T < E['t_fade'][0]: cursor(fr, tj)
    draw_sentence(fr, T)
    draw_badge(fr, T)
    if T >= E['t_line'][0]:   # the address comes up from the bottom to meet the mark in the middle
        u = ease(prog(T, E['t_line'])); lay = G['line']; (_, _, (lw, lh)) = lay
        cx, cy, w = F['frame']['line_end']; w = w * (1 - (EC or {}).get('dip', 0) * press_amt(T)); h = lh * w / lw   # dips as it is clicked
        y = (H + h) + (cy - (H + h)) * u
        fk.place(fr, lay, cx - w / 2, y - h / 2, w, 1.0)
    end_cursor(fr, T)
    return fr.convert('RGB')

def render(i):
    return i, frame(i).tobytes()

# ------------------------------------------------------------------------- the page: boxes and brand layers
def recon():
    """the boxes the choreography frames, measured on the live page at the capture's viewport after the capture's own
    preparation (blocked requests, consent, warmup): recon.items {name: css selector} -> recon.json beside this file,
    every box in page px of the document (y includes the scroll), with the page's sections and headings, its fixed
    elements and its height"""
    from filmkit import capture
    items = F.get('recon', {}).get('items', {})
    with capture.page(cap_cfg(), f'{HERE}/recon-shots') as (b, ctx, p):
        res = {'url': p.url, 'viewport': [VW, VH], 'height': p.evaluate('() => document.documentElement.scrollHeight'), 'items': {}}
        for name, sel in items.items():
            res['items'][name] = {'selector': sel, 'boxes': p.evaluate(BOXES, [sel, 8])}
        res['outline'] = p.evaluate(BOXES, ['section, h1, h2, h3', 200])
        res['fixed'] = p.evaluate(capture.FIXED)
        p.screenshot(path=f'{HERE}/recon-shots/top.png')
    json.dump(res, open(f'{HERE}/recon.json', 'w'), indent=1)
    return res

BOXES = """([s, n]) => [...document.querySelectorAll(s)].slice(0, n).map(e => { const r = e.getBoundingClientRect();
  return {tag: e.tagName.toLowerCase(), x: Math.round(r.x), y: Math.round(r.y + scrollY), w: Math.round(r.width), h: Math.round(r.height),
          text: (e.innerText || e.getAttribute('alt') || e.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ').slice(0, 60)} })
  .filter(o => o.w > 0 && o.h > 0)"""

def chrome():
    """the film's two brand layers, rendered by the browser from the page itself (nothing redrawn), into chrome_dir:
    badge.png, the page's mark (chrome.mark_selector) alone on a transparent ground, the whole of the element's box;
    line.png, chrome.line (the address) in the face and ink of chrome.font_selector, at 2x on the film's white;
    chrome.json, what was read. badge_page in film.json is the mark element's box from recon."""
    from filmkit import capture
    C = F['chrome']; os.makedirs(CHR, exist_ok=True)
    white = 'rgb(%d, %d, %d)' % WHITE[:3]
    with capture.page(cap_cfg(), CHR) as (b, ctx, p):
        mark = p.evaluate("""s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect();
            return {html: e.outerHTML, src: e.currentSrc || null, color: getComputedStyle(e).color, w: r.width, h: r.height} }""",
                          C['mark_selector'])
        if not mark:
            sys.exit(f"chrome: no element matches mark_selector {C['mark_selector']!r} on {p.url}")
        face = p.evaluate("s => { const e = document.querySelector(s); const cs = getComputedStyle(e); return {family: cs.fontFamily, color: cs.color} }",
                          C.get('font_selector', 'h1'))
        base = p.url
        p.evaluate("""([t, fam, ink, ground, wt, px]) => { const d = document.createElement('div'); d.id = '__line'; d.textContent = t;
            Object.assign(d.style, {position: 'fixed', left: '40px', top: '40px', font: wt + ' ' + px + 'px ' + fam, color: ink,
                                    background: ground, zIndex: 2147483647, padding: '6px 10px', whiteSpace: 'nowrap', lineHeight: '1.2'});
            document.body.appendChild(d);   // a box of whole pixels: a fractional edge lets the page behind show as a stroke
            const r = d.getBoundingClientRect(); d.style.width = Math.ceil(r.width) + 'px'; d.style.height = Math.ceil(r.height) + 'px';
            d.style.boxSizing = 'border-box' }""", [C['line'], face['family'], face['color'], white, C.get('line_weight', 500), C.get('line_px', 44)])
        p.wait_for_timeout(300); p.locator('#__line').screenshot(path=f'{CHR}/line.png')
        src = mark['src']
        if src and src.startswith('file://'):   # a blank page may not load a local file: the mark goes in as a data URI
            import base64, mimetypes
            from urllib.parse import unquote, urlparse
            fp = unquote(urlparse(src).path)
            src = f"data:{mimetypes.guess_type(fp)[0] or 'image/png'};base64," + base64.b64encode(open(fp, 'rb').read()).decode()
        raster = bool(src) and not src.split('?')[0].lower().endswith('.svg') and not src.startswith('data:image/svg')
        scale = 1 if raster else C.get('mark_scale', 3)   # a raster mark at its own pixels; a drawn one (svg) at 3x
        c1 = b.new_context(viewport={'width': 1600, 'height': 900}, device_scale_factor=scale); q = c1.new_page()
        if src:
            size = '' if raster else f'width:{mark["w"]}px;height:{mark["h"]}px;'   # an svg at its box on the page
            q.set_content(f'<html><body style="margin:0;background:transparent"><img id=m src="{src}" style="display:block;{size}"></body></html>')
        else:
            q.set_content(f'<html><head><base href="{base}"></head><body style="margin:0;background:transparent;color:{mark["color"]}">'
                          f'<div id=m style="display:inline-block;width:{mark["w"]}px;height:{mark["h"]}px">{mark["html"]}</div></body></html>')
        q.wait_for_load_state('networkidle'); q.locator('#m').screenshot(path=f'{CHR}/badge.png', omit_background=True)
    info = {'url': base, 'mark_selector': C['mark_selector'], 'mark_src': mark['src'], 'mark_box_css': [mark['w'], mark['h']],
            'font': face['family'], 'ink': face['color'], 'ground': white, 'line': C['line']}
    json.dump(info, open(f'{CHR}/chrome.json', 'w'), indent=1)
    return info

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'timeline':
        out = sys.argv[2] if len(sys.argv) > 2 else f'{HERE}/timeline.json'
        print(timeline.write(plan(), out))
    elif cmd == 'recon':
        r = recon(); print(json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()}))
    elif cmd == 'chrome':
        print(json.dumps(chrome()))
    elif cmd == 'capture':
        from filmkit import capture
        res = capture.run(cap_cfg(), f'{HERE}/timeline.json', RAW)
        print(json.dumps({k: v for k, v in res.items() if k not in ('log', 'pacing')}))
    elif cmd == 'draft':
        from filmkit import capture
        res = capture.run(cap_cfg(draft=True), f'{HERE}/timeline.json', RAW + '-draft')
        print(json.dumps({k: v for k, v in res.items() if k not in ('log', 'pacing')}))
    elif cmd == 'keys':
        out = sys.argv[2]; os.makedirs(out, exist_ok=True); init()
        ts = [float(x) for x in sys.argv[3].split(',')]
        for T in ts: frame(round(T * FPS)).save(f'{out}/{round(T * FPS):05d}.png')
        print('keys written', len(ts))
    elif cmd == 'cover':
        out = sys.argv[2]; T = float(sys.argv[3]) if len(sys.argv) > 3 else F.get('cover_t', 3.25)
        init(); frame(round(T * FPS)).save(out); print('wrote', out)
    elif cmd == 'stitch':
        from filmkit import capture
        res = capture.stitch(cap_cfg(), STITCH)
        print(json.dumps({k: v for k, v in res.items() if k not in ('fixed', 'tiles', 'text')}), len(res['tiles']), 'tiles')
    elif cmd in ('all', 'animatic'):
        if cmd == 'animatic':
            os.environ['FILM_SOURCE'] = 'animatic'
        mp4 = sys.argv[2]
        wr = encode.Writer(mp4, W, H, FPS, title=F['title'])
        with Pool(8, initializer=init) as pool:
            for k, (i, buf) in enumerate(pool.imap(render, range(N), chunksize=4)):
                wr.write(buf)
                if (k + 1) % 300 == 0: print(f'{k + 1}/{N}', flush=True)
        print('wrote', mp4, 'exit', wr.close())
        encode.record(mp4, HERE, F['name'], N)
    else:
        print(__doc__); sys.exit(2)
