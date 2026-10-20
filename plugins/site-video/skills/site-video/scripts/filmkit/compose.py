"""Compositing primitives on Pillow, parameterised: nothing here holds a brand value (colours, sizes and boxes come in
as arguments). Layers (alpha-trimmed, padded PNGs), place/travel/place_scaled, the framed end card, the cursor and
its click ring, the glow around a box, and the window (a crop of a source with blur samples averaged)."""
import math
from PIL import Image, ImageDraw, ImageFilter
from .motion import ease_out

PAD = 24   # transparent margin around a layer: room for the resample box at any scale
UNSHARP = ImageFilter.UnsharpMask(radius=0.7, percent=70, threshold=2)


# ------------------------------------------------------------------------- layers
def load_layer(path, pad=None):
    """A PNG (a path, or an Image already cleaned) as a layer: alpha-trimmed, then padded by PAD. Returns (image,
    (ink_x, ink_y) in css px, (ink_w, ink_h) in css px); the PNG is at 2x."""
    pad = PAD if pad is None else pad
    im = (path if isinstance(path, Image.Image) else Image.open(path)).convert('RGBA')
    bb = im.getchannel('A').getbbox()
    im = im.crop(bb)
    out = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    out.paste(im, (pad, pad))
    return out, (bb[0] / 2, bb[1] / 2), (im.width / 2, im.height / 2)


def place(fr, lay, x, y, w, alpha=1.0):
    """the layer's ink with its top-left at (x, y) css px, w wide; sub-pixel exact (resampled from the 2x source)"""
    im, _, (lw, lh) = lay
    sc = w / lw
    h = lh * sc
    X0, Y0 = math.floor(x), math.floor(y)
    fx, fy = x - X0, y - Y0
    ow, oh = math.ceil(w + fx) + 1, math.ceil(h + fy) + 1
    src = 2 / sc
    r = im.resize((ow, oh), Image.LANCZOS, box=(PAD - fx * src, PAD - fy * src, PAD + (ow - fx) * src, PAD + (oh - fy) * src))
    if alpha < 1:
        r.putalpha(r.getchannel('A').point(lambda v: int(v * alpha)))
    fr.alpha_composite(r, (X0, Y0))


def travel(fr, lay, g_layer, g0, g1, u, alpha=1.0):
    """a layer (rendered in box g_layer) whose box goes from g0 to g1 (same shape), its ink kept in place inside the box"""
    (_, (lx, ly), (lw, _)) = lay
    bx, by, bw = g0[0] + (g1[0] - g0[0]) * u, g0[1] + (g1[1] - g0[1]) * u, g0[2] + (g1[2] - g0[2]) * u
    k = bw / g_layer[2]
    place(fr, lay, bx + (lx - g_layer[0]) * k, by + (ly - g_layer[1]) * k, lw * k, alpha)


def place_scaled(fr, lay, g_layer, box, s, alpha):
    """a layer rendered in box g_layer, put at `box` (same size) and scaled by s about the box's centre"""
    (_, (lx, ly), (lw, lh)) = lay
    cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
    ix, iy = box[0] + (lx - g_layer[0]), box[1] + (ly - g_layer[1])
    place(fr, lay, cx + (ix - cx) * s, cy + (iy - cy) * s, lw * s, alpha)


# ------------------------------------------------------------------------- the framed card
def framed_card(w, h, inset, radius, ground, card, hairline, hairline_w, shadow, S=2):
    """A full-frame RGBA: `ground` outside, a `card` colour rounded box inset by `inset` px, its hairline and soft shadow.
    hairline = (r, g, b, alpha 0..1); hairline_w in supersampled px; shadow = {dy, blur, colour, alpha}."""
    fr = Image.new('RGB', (w * S, h * S), tuple(ground))
    box = [inset * S, inset * S, (w - inset) * S - 1, (h - inset) * S - 1]
    if inset > 0.01:
        sh = Image.new('L', fr.size, 0)
        ImageDraw.Draw(sh).rounded_rectangle([box[0], box[1] + shadow['dy'] * S, box[2], box[3] + shadow['dy'] * S], radius * S,
                                             fill=int(255 * shadow['alpha']))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow['blur'] * S))
        fr.paste(Image.new('RGB', fr.size, tuple(shadow['colour'])), (0, 0), sh)
    m = Image.new('L', fr.size, 0)
    ImageDraw.Draw(m).rounded_rectangle(box, radius * S, fill=255)
    fr.paste(Image.new('RGB', fr.size, tuple(card)), (0, 0), m)
    if inset > 0.01:
        ov = Image.new('RGBA', fr.size, (0, 0, 0, 0))
        ImageDraw.Draw(ov).rounded_rectangle(box, radius * S, outline=(*hairline[:3], int(255 * hairline[3])), width=hairline_w)
        fr = Image.alpha_composite(fr.convert('RGBA'), ov).convert('RGB')
    return fr.resize((w, h), Image.LANCZOS).convert('RGBA')


# ------------------------------------------------------------------------- cursor and click ring
def cursor_sprite(k=8):
    """a black arrow with a white outline and a soft shadow, drawn at k x. Returns (image, tip, k)."""
    pts = [(0, 0), (0, 22), (5, 17.2), (8.6, 25.6), (11.8, 24.2), (8.3, 16), (14.8, 16)]
    big = Image.new('RGBA', (20 * k, 30 * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    P = [(x * k + 2 * k, y * k + 2 * k) for x, y in pts]
    d.polygon(P, fill=(255, 255, 255, 255), outline=(255, 255, 255, 255), width=int(3.2 * k))
    d.polygon(P, fill=(0, 0, 0, 255))
    sh = Image.new('RGBA', big.size, (0, 0, 0, 0))
    sh.putalpha(big.getchannel('A').point(lambda v: v * 0.35))
    sh = sh.filter(ImageFilter.GaussianBlur(1.6 * k))
    cur = Image.new('RGBA', big.size, (0, 0, 0, 0))
    cur.alpha_composite(sh, (int(0.6 * k), int(1.6 * k)))
    cur.alpha_composite(big)
    return cur, (2 * k, 2 * k), k


def draw_cursor(fr, sprite, X, Y, alpha=1.0, press=1.0, size=34):
    """the cursor with its tip at (X, Y); `press` < 1 shrinks it (the click)"""
    spr, tip, k = sprite
    sc = size * press / (30 * k)
    im = spr.resize((max(1, round(spr.width * sc)), max(1, round(spr.height * sc))), Image.LANCZOS)
    if alpha < 1:
        im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    fr.alpha_composite(im, (round(X - tip[0] * sc), round(Y - tip[1] * sc)))


def ring(fr, X, Y, u, col, width=7, r0=10, grow=30, fade_pow=1.2, S=4, margin=8):
    """the click: a ring growing from r0 by `grow` px and fading, u = 0..1 through its life (clamped: a frame time a hair
    past the ring's end made (1 - u) negative and the fade complex)"""
    u = min(1.0, max(0.0, u))
    r = r0 + grow * ease_out(u)
    a = int(255 * (1 - u) ** fade_pow)
    size = int(2 * (r + margin) * S)
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    c = size / 2
    ImageDraw.Draw(im).ellipse([c - r * S, c - r * S, c + r * S, c + r * S], outline=(*col, a), width=int(width * S))
    im = im.resize((size // S, size // S), Image.LANCZOS)
    fr.alpha_composite(im, (round(X - size / S / 2), round(Y - size / S / 2)))


# ------------------------------------------------------------------------- glow
def clip_to(lay, rect):
    """clears the layer's alpha outside rect = (x, y, w, h)"""
    clip = Image.new('L', lay.size, 0)
    ImageDraw.Draw(clip).rectangle([rect[0], rect[1], rect[0] + rect[2] - 1, rect[1] + rect[3] - 1], fill=255)
    lay.putalpha(Image.composite(lay.getchannel('A'), Image.new('L', lay.size, 0), clip))
    return lay


def glow(fr, box, radius, colour, alpha, blur, clip, pad=70, spread=3, line=9, gain=1.9, S=2):
    """A soft light round a rounded box, outside it only (as if behind it), clipped to `clip` = (x, y, w, h).
    box = (X0, Y0, X1, Y1) in frame px; alpha 0..1 and blur px are the light's strength now (see motion.breathe)."""
    X0, Y0, X1, Y1 = box
    L, T = math.floor(X0) - pad, math.floor(Y0) - pad
    w, h = math.ceil(X1) + pad - L, math.ceil(Y1) + pad - T
    m = Image.new('L', (w * S, h * S), 0)
    b = [(X0 - L) * S, (Y0 - T) * S, (X1 - L) * S, (Y1 - T) * S]
    ImageDraw.Draw(m).rounded_rectangle([b[0] - spread * S, b[1] - spread * S, b[2] + spread * S, b[3] + spread * S],
                                        (radius + spread) * S, outline=255, width=line * S)
    m = m.filter(ImageFilter.GaussianBlur(blur * S)).point(lambda v: int(min(255, v * gain) * alpha))
    inside = Image.new('L', m.size, 0)
    ImageDraw.Draw(inside).rounded_rectangle(b, radius * S, fill=255)
    m.paste(0, (0, 0), inside)
    m = m.resize((w, h), Image.LANCZOS)
    lay = Image.new('RGBA', fr.size, (0, 0, 0, 0))
    col = Image.new('RGBA', (w, h), tuple(colour) + (255,))
    col.putalpha(m)
    lay.alpha_composite(col, (L, T))
    fr.alpha_composite(clip_to(lay, clip))


# ------------------------------------------------------------------------- the window
def window(source, j, box, page_size, bar=None, bar_h=0, amount=0.0, blur=0.0, veil=0.0, ground=(255, 255, 255), unsharp=UNSHARP):
    """The window at capture frame j: `source` (a CaptureSource) cropped to box = (x0, y0, cw, ch) page px and resized
    to page_size, its blur samples averaged, unsharped (r .7 / 70% / thr 2); then, if amount > .001, a Gaussian blur of
    blur*amount px and a veil of `ground` at veil*amount. `bar` (an RGB image bar_h tall) is pasted on top of the page.
    Returns the window image (page_size wide, bar_h + page_size[1] tall)."""
    pg = source.crop(j, box, page_size).filter(unsharp)
    if amount > 0.001:
        pg = pg.filter(ImageFilter.GaussianBlur(blur * amount))
        pg = Image.blend(pg, Image.new('RGB', pg.size, tuple(ground)), veil * amount)
    win = Image.new('RGB', (page_size[0], page_size[1] + bar_h), tuple(ground))
    if bar is not None:
        win.paste(bar, (0, 0))
    win.paste(pg, (0, bar_h))
    return win
