"""Frame-by-frame capture of a live page with Python Playwright (sync API): the port of the old capture.mjs.

Per frame: the navigation click when the timeline says, the mouse move, then for each blur sample scrollTo (instant),
two animation frames, a screenshot. The page's CSS animations are paced to the capture with CDP
Animation.setPlaybackRate, set before EVERY frame to FRAME_MS / (samples in this frame x measured ms per sample),
clamped 0.02..1, so the page advances one frame per captured frame whatever the sample count (re-pacing only every 30
frames ran the page ~5.8x fast on 10-sample frames).

Config (a dict, the "capture" block of a film's film.json):
  viewport [w, h]; device_scale 2; reduced_motion 'no-preference'; fps 60
  block [regex ...]            requests aborted (analytics)
  count_block [regex ...]      requests aborted AND counted as "posts" (form posts the film must never send)
  pre [step ...]               run in order before the film; a step is one of
       {"goto": url, "wait_until": "networkidle", "timeout": ms, "settle_ms": ms}
       {"click_text": "Decline"} | {"click_selector": css} | {"click_xy": [x, y]} | {"eval": "js"}
       (+ "wait_ms", "shot": "name.png"; "optional": true skips a click whose target is absent)
       {"wait_ms": ms}
  after_nav [step ...]         the same steps, run on the new page after the click (its consent banner)
  warmup {"to": px, "step": px, "wait_ms": ms, "settle_ms": ms}   scroll the page through once so lazy images load
  rate0 0.12                   playback rate until the first measurement
  click {"x", "y", "url_pattern", "timeout"}   the navigation click's target and the URL expected after it
  after_nav_mouse [5, 5]       where the real mouse rests after the new page loads
  frame_clock true             performance.now() returns the frame clock the page's requestAnimationFrame callbacks get
                               (set once the rate is slowed, and again after a navigation): see FRAME_CLOCK
  media_rate true              every <video> plays at the capture's rate (set before every frame): see MEDIA_RATE
  media_rate "seek"            every visible <video> is paused and stepped one film frame per captured frame: see MEDIA_SEEK
A timeline frame may carry "act": [step ...], run on that frame before its samples: {"click": [x, y]} a real click that
stays on the page (a tab, a map city, a carousel arrow; viewport px), {"move": [x, y]} the real mouse, {"eval": "js"}
(e.g. an element hidden as it leaves the page). capture.json records every act and the URL at the end (url_end).
"""
import json
import os
import re
import time
from collections import deque
from contextlib import contextmanager


def _step(page, st, out_dir):
    if 'goto' in st:
        page.goto(st['goto'], wait_until=st.get('wait_until', 'load'), timeout=st.get('timeout', 30000))
        if st.get('settle_ms'):
            page.wait_for_timeout(st['settle_ms'])
        return
    if 'click_text' in st or 'click_selector' in st:
        loc = (page.locator('button, a, [role=button]').filter(has_text=re.compile('^' + re.escape(st['click_text']) + '$'))
               if 'click_text' in st else page.locator(st['click_selector']))
        if loc.count() == 0 and st.get('optional'):   # a banner that shows only in some regions or on some visits
            return
        loc.first.click()
    elif 'click_xy' in st:
        page.mouse.click(st['click_xy'][0], st['click_xy'][1])
    elif 'eval' in st:   # page script before the film: e.g. a link's target=_blank removed, a chat widget hidden
        page.evaluate(st['eval'])
    if st.get('wait_ms'):
        page.wait_for_timeout(st['wait_ms'])
    if st.get('shot'):
        page.screenshot(path=os.path.join(out_dir, st['shot']))


# Under Animation.setPlaybackRate the timestamps requestAnimationFrame hands the page (and document.timeline) slow down
# with the capture, but performance.now() keeps wall time. A script that starts an animation at performance.now() and
# steps it by the rAF timestamp then reads a time far in the past: measured on a map's 460 ms zoom, the scale jumped
# to -12 on the click frame and the land flew out of view. The bridge makes performance.now() read the same frame
# clock, so the page's own animation plays at its own curve and duration in the film. Date.now() and timers keep wall
# time.
FRAME_CLOCK = """() => { if (window.__wallNow) return; window.__wallNow = performance.now.bind(performance); let last = null;
  (function tick(ts) { last = ts; requestAnimationFrame(tick) })(document.timeline.currentTime);
  performance.now = () => (last == null ? window.__wallNow() : last) }"""

# A <video> keeps wall time too: under a capture rate of about 0.15 a background reel played 7x fast in the film and its
# own edits read as cuts. Its playbackRate follows the capture's rate before every frame. Chrome plays 0.0625 to 16, so
# on a frame paced below 0.0625 the video runs a little ahead (counted in the log).
MEDIA_RATE = """r => { for (const v of document.querySelectorAll('video')) { v.defaultPlaybackRate = r; v.playbackRate = r } }"""
MEDIA_MIN = 0.0625
# Slowed playback still stutters: at a rate near 0.12 a reel's frames arrived unevenly (frame differences from 0.1 to
# 2.2 a fifth of a second apart) and the owner saw it as not playing naturally, as it does on the website. "seek"
# pauses each visible video and sets its currentTime one film frame further before every captured frame, waiting for
# the seek: the video's own frames, at its own speed, exactly.
MEDIA_SEEK = """dt => Promise.all([...document.querySelectorAll('video')].filter(v => {
    const q = v.getBoundingClientRect(); return v.readyState >= 2 && q.width > 0 && q.bottom > 0 && q.top < innerHeight })
  .map(v => new Promise(res => {
    if (v.__ft === undefined) v.__ft = v.currentTime;
    v.pause(); v.__ft += dt; if (v.duration) v.__ft %= v.duration;
    const done = () => { v.removeEventListener('seeked', done); res() };
    v.addEventListener('seeked', done); v.currentTime = v.__ft; setTimeout(done, 500) })))"""


def _cdp(ctx, page, rate):
    cdp = ctx.new_cdp_session(page)
    cdp.send('Animation.enable')
    cdp.send('Animation.setPlaybackRate', {'playbackRate': rate})
    return cdp


DRAFT = {'device_scale': 1, 'settle_frames': 1, 'max_samples': 3}
RATE_MAX = 4.0   # a frame captured quicker than real time (a draft of a light page: 16 ms a frame at 30 fps) plays the page
                 # faster to keep up; capped at 1.0 the page ran at 0.50x of film time
GPU_ARGS = ['--use-angle=metal', '--enable-gpu-rasterization', '--ignore-gpu-blocklist', '--enable-zero-copy']


def _predict(recent, ns):
    """the wall ms a frame of `ns` samples will take: a fixed cost per frame (the page calls, the mouse) plus a cost per
    sample, fitted to the recent frames. A per-sample average alone misprices a frame when the fixed cost is large: a
    draft's page ran at 0.51x of film time with it"""
    n = len(recent); mx = sum(k for _, k in recent) / n; my = sum(m for m, _ in recent) / n
    vx = sum((k - mx) ** 2 for _, k in recent)
    if vx > 1e-9:
        per = sum((k - mx) * (m - my) for m, k in recent) / vx; fixed = my - per * mx
        if per > 0 and fixed >= 0:
            return fixed + per * ns
    return my * ns / mx             # one sample count so far: proportional


def _thin(ss, n):
    """at most n of a frame's blur samples, evenly spread, the first and last kept"""
    if not n or len(ss) <= n:
        return ss
    return [ss[round(k * (len(ss) - 1) / (n - 1))] for k in range(n)] if n > 1 else [ss[len(ss) // 2]]


def run(cfg, timeline_path, out_dir, limit=None, verbose=True):
    """Captures every frame of the timeline into out_dir (raw JPGs 00012-0.jpg ... and capture.json).
    limit = capture only the first N frames. Returns the capture.json dict.
    cfg['draft'] = True: the rough cut's capture, about twice as fast (a bench on an Apple M4 Pro: a 1x screenshot 33 ms against
    84 at 2x; one animation frame of settle gave the same pixels as two in the headless shell): 1x, one frame's settle,
    at most 3 blur samples. Into its own folder; never the final's. cfg['gpu'] = True: Chromium with Metal (66 ms a 2x
    screenshot against 84 in software), which needs settle_frames 2."""
    from playwright.sync_api import sync_playwright
    if cfg.get('draft'):
        cfg = {**cfg, **DRAFT}
    n_raf = cfg.get('settle_frames', 2)
    settle = '() => new Promise(r => ' + 'requestAnimationFrame(() => ' * n_raf + 'r()' + ')' * n_raf + ')'
    frames = json.load(open(timeline_path))
    if cfg.get('max_samples'):
        frames = [dict(f, s=_thin(f['s'], cfg['max_samples'])) for f in frames]
    if limit:
        frames = frames[:limit]
    os.makedirs(out_dir, exist_ok=True)
    vw, vh = cfg['viewport']
    fps = cfg.get('fps', 60)
    frame_ms = 1000 / fps
    posts = [0]
    log = []
    acts = []

    def count(route):
        posts[0] += 1
        route.abort()

    with sync_playwright() as pw:
        b = pw.chromium.launch(channel='chromium', args=GPU_ARGS) if cfg.get('gpu') else pw.chromium.launch()
        ctx = b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=cfg.get('device_scale', 2),
                            reduced_motion=cfg.get('reduced_motion', 'no-preference'))
        for pat in cfg.get('block', []):
            ctx.route(re.compile(pat), lambda r: r.abort())
        for pat in cfg.get('count_block', []):
            ctx.route(re.compile(pat), count)
        p = ctx.new_page()
        for st in cfg.get('pre', []):
            _step(p, st, out_dir)
        w = cfg.get('warmup')
        if w:
            s = 0
            while s <= w['to']:
                p.evaluate('s => window.scrollTo({top: s, behavior: "instant"})', s)
                p.wait_for_timeout(w.get('wait_ms', 250))
                s += w['step']
            p.evaluate('() => window.scrollTo({top: 0, behavior: "instant"})')
            p.wait_for_timeout(w.get('settle_ms', 1500))
        p.evaluate('() => document.fonts.ready')
        rest = cfg.get('after_nav_mouse', [5, 5])
        p.mouse.move(rest[0], rest[1])
        rate = cfg.get('rate0', 0.12)
        cdp = _cdp(ctx, p, rate)
        if cfg.get('frame_clock'):
            p.evaluate(FRAME_CLOCK)
        recent = deque(maxlen=30)   # (ms, samples) of the last 30 frames
        errs, raw = deque(maxlen=3), None   # the last three frames' actual over predicted time; their median corrects the
                                            # next prediction: a page that turns heavy is caught in two frames (a draft ran
                                            # 2.3x fast for 20 frames when a 3D scene came into view) and a one-frame stall
                                            # (692 ms after a click) moves nothing (a mean slowed the page to 0.07x)
        media_low = 0               # frames paced below the slowest rate a video plays
        pacing = []                 # per frame: [i, samples, wall ms, playback rate]; page time = wall ms x rate
        t0 = time.time()
        url0, url1 = p.url, None
        for n, f in enumerate(frames):
            a = time.time()
            if f.get('nav'):   # the real click: the drawn press plays over the last frames of the old page
                c = cfg['click']
                p.mouse.move(c['x'], c['y'])
                p.mouse.click(c['x'], c['y'])
                p.wait_for_url(re.compile(c['url_pattern']), timeout=c.get('timeout', 30000))
                p.wait_for_load_state('networkidle')
                p.evaluate('() => document.fonts.ready')
                for st in cfg.get('after_nav', []):   # the new page's own consent banner, if it has one
                    _step(p, st, out_dir)
                p.mouse.move(rest[0], rest[1])
                url1 = p.url
                log.append(f"frame {f['i']}: clicked, landed on {url1}")
                cdp = _cdp(ctx, p, rate)
                if cfg.get('frame_clock'):
                    p.evaluate(FRAME_CLOCK)
                recent.clear()
                errs.clear(); raw = None
                a = time.time()
            # pace BEFORE the frame: one frame of page time per captured frame, whatever the sample count
            ns = len(f['s'])
            raw = None
            if recent:
                ms = sum(m for m, _ in recent) / max(1, sum(k for _, k in recent))   # measured ms per sample (the log's)
                raw = _predict(recent, ns)
                corr = sorted(errs)[len(errs) // 2] if errs else 1.0
                rate = min(RATE_MAX, max(0.02, frame_ms / (raw * corr)))   # above 1 when a frame is quicker than real time
                cdp.send('Animation.setPlaybackRate', {'playbackRate': rate})
            if cfg.get('media_rate') == 'seek':
                p.evaluate(MEDIA_SEEK, 1 / fps)
            elif cfg.get('media_rate'):
                p.evaluate(MEDIA_RATE, max(MEDIA_MIN, rate))
                media_low += rate < MEDIA_MIN
            if n % 30 == 0 and recent:
                log.append(f"frame {f['i']}: {ms:.0f} ms per sample, {ns} samples, playback rate {rate:.3f}")
            if f.get('mouse'):
                p.mouse.move(f['mouse'][0], f['mouse'][1])
            for st in f.get('act', []):   # in-page actions on this frame, before its samples
                if 'click' in st:
                    p.mouse.click(st['click'][0], st['click'][1])
                elif 'move' in st:
                    p.mouse.move(st['move'][0], st['move'][1])
                elif 'eval' in st:
                    p.evaluate(st['eval'])
                acts.append(f['i'])
                log.append(f"frame {f['i']}: act {json.dumps(st)}")
            for k, s in enumerate(f['s']):   # one sample, or the shutter's samples for motion blur
                p.evaluate('s => window.scrollTo({top: s, behavior: "instant"})', s)
                p.evaluate(settle)
                p.screenshot(path=os.path.join(out_dir, f"{f['i']:05d}-{k}.jpg"), type='jpeg', quality=92, scale=f.get('scale', 'device'))
            recent.append(((time.time() - a) * 1000, ns))
            if raw:
                errs.append(recent[-1][0] / raw)
            pacing.append([f['i'], ns, round(recent[-1][0], 1), round(rate, 4)])
            if verbose and f['i'] % 100 == 0:
                print(f"frame {f['i']}, scrollY {p.evaluate('() => scrollY')}", flush=True)
        if cfg.get('media_rate') is True:
            log.append(f'media_rate: {media_low} frames paced below {MEDIA_MIN}, where a video ran up to {MEDIA_MIN} / rate ahead')
        res = {'frames': len(frames), 'seconds': time.time() - t0, 'posts': posts[0], 'url0': url0, 'url1': url1, 'log': log,
               'draft': bool(cfg.get('draft')), 'max_samples': cfg.get('max_samples'), 'device_scale': cfg.get('device_scale', 2),
               'fps': fps, 'pacing': pacing, 'acts': acts, 'url_end': p.url}
        b.close()
    with open(os.path.join(out_dir, 'capture.json'), 'w') as fh:
        json.dump(res, fh, indent=1)
    return res



# ------------------------------------------------------------------------- the stitch (for animatics)
FIXED = """() => { const out = []; for (const e of document.querySelectorAll('body *')) { const cs = getComputedStyle(e);
    if (cs.position !== 'fixed' && cs.position !== 'sticky') continue;
    const r = e.getBoundingClientRect(); if (r.width < 1 || r.height < 1 || cs.visibility === 'hidden' || cs.display === 'none') continue;
    e.setAttribute('data-filmkit-fixed', '1');
    out.push({tag: e.tagName, cls: (e.className || '').toString().slice(0, 60), pos: cs.position, x: r.x, y: r.y, w: r.width, h: r.height}) }
  return out }"""
HIDE = "[data-filmkit-fixed] { visibility: hidden !important }"
TEXT = """() => { const out = [], r = document.createRange();
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT,
    {acceptNode: n => n.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT});
  const clip = el => { let x0 = -1e9, y0 = -1e9, x1 = 1e9, y1 = 1e9;
    for (let a = el; a && a !== document.body; a = a.parentElement) { const cs = getComputedStyle(a);
      if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible' || cs.clipPath !== 'none') { const b = a.getBoundingClientRect();
        x0 = Math.max(x0, b.left); y0 = Math.max(y0, b.top); x1 = Math.min(x1, b.right); y1 = Math.min(y1, b.bottom) } }
    return [x0, y0, x1, y1] };
  let n; while ((n = tw.nextNode())) { const el = n.parentElement;
    if (!el || el.closest('[data-filmkit-fixed]') || el.closest('script,style,noscript,template')) continue;
    if (el.checkVisibility && !el.checkVisibility({opacityProperty: true, visibilityProperty: true, checkOpacity: true, checkVisibilityCSS: true})) continue;
    const c = clip(el); r.selectNodeContents(n);
    for (const b of r.getClientRects()) { const x0 = Math.max(b.left, c[0]), y0 = Math.max(b.top, c[1]), x1 = Math.min(b.right, c[2]), y1 = Math.min(b.bottom, c[3]);
      if (x1 - x0 < 2 || y1 - y0 < 4) continue;
      out.push([Math.round(x0), Math.round(y0 + scrollY), Math.round(x1), Math.round(y1 + scrollY), n.nodeValue.trim().replace(/\\s+/g, ' ').slice(0, 40)]) } }
  return out }"""


def stitch(cfg, out_dir, verbose=True):
    """The page whole, for an animatic: after the same pre steps and warmup as run(), one screenshot per viewport height
    with the page's fixed and sticky elements hidden (the content under them), and one with them shown, of which only
    the top band (the fixed nav, its height measured, or cfg['nav_h']) is kept, per scroll position: the nav's own look
    at that point of the page. sources.StitchedSource puts the page back together and draws the nav over it at its real
    height, so a heading under the nav is under it in the animatic too. The page does not move: videos, carousels and
    in-page clicks are frozen at the state the stitch saw. Writes out_dir/tile-NNNNN.jpg, nav-NNNNN.png, stitch.json, which
    also lists every visible line of text in page px ("text": [x0, y0, x1, y1, words]) for the plan's cut-text gate."""
    from playwright.sync_api import sync_playwright
    os.makedirs(out_dir, exist_ok=True)
    vw, vh = cfg['viewport']
    posts = [0]
    t0 = time.time()

    def count(route):
        posts[0] += 1
        route.abort()

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=cfg.get('device_scale', 2),
                            reduced_motion=cfg.get('reduced_motion', 'no-preference'))
        for pat in cfg.get('block', []):
            ctx.route(re.compile(pat), lambda r: r.abort())
        for pat in cfg.get('count_block', []):
            ctx.route(re.compile(pat), count)
        p = ctx.new_page()
        for st in cfg.get('pre', []):
            _step(p, st, out_dir)
        w = cfg.get('warmup')
        if w:
            s = 0
            while s <= w['to']:
                p.evaluate('s => window.scrollTo({top: s, behavior: "instant"})', s)
                p.wait_for_timeout(w.get('wait_ms', 250))
                s += w['step']
        p.evaluate('() => window.scrollTo({top: 0, behavior: "instant"})')
        p.wait_for_timeout((w or {}).get('settle_ms', 1500))
        p.evaluate('() => document.fonts.ready')
        rest = cfg.get('after_nav_mouse', [5, 5])
        p.mouse.move(rest[0], rest[1])
        fixed = p.evaluate(FIXED)
        text = p.evaluate(TEXT)   # every visible line of text, page px at rest, clipped by its clipping ancestors
        top = [f for f in fixed if f['y'] <= 2 and f['h'] < vh / 3]
        nav_h = cfg.get('nav_h', max([f['y'] + f['h'] for f in top], default=0))
        H = p.evaluate('() => document.documentElement.scrollHeight')
        tiles, y = [], 0
        settle = '() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))'
        while True:
            p.evaluate('s => window.scrollTo({top: s, behavior: "instant"})', y)
            p.evaluate(settle)
            p.wait_for_timeout(cfg.get('stitch_wait_ms', 150))
            real = p.evaluate('() => scrollY')
            nav = os.path.join(out_dir, f'nav-{real:05d}.png')
            p.screenshot(path=nav, clip={'x': 0, 'y': 0, 'width': vw, 'height': max(1, nav_h)}, scale='device') if nav_h else None
            h = p.add_style_tag(content=HIDE)
            p.evaluate(settle)
            tile = os.path.join(out_dir, f'tile-{real:05d}.jpg')
            p.screenshot(path=tile, type='jpeg', quality=92, scale='device')
            h.evaluate('e => e.remove()')
            tiles.append([real, os.path.basename(tile), os.path.basename(nav) if nav_h else None])
            if verbose:
                print(f'tile at {real}', flush=True)
            if real + vh >= H or (len(tiles) > 1 and real == tiles[-2][0]):
                break
            y = real + vh
        b.close()
    res = {'viewport': [vw, vh], 'scale': cfg.get('device_scale', 2), 'height': H, 'nav_h': nav_h, 'tiles': tiles,
           'fixed': fixed, 'text': text, 'posts': posts[0], 'seconds': round(time.time() - t0, 1)}
    with open(os.path.join(out_dir, 'stitch.json'), 'w') as fh:
        json.dump(res, fh, indent=1)
    return res

# ------------------------------------------------------------------------- a prepared page (recon, brand layers)
@contextmanager
def page(cfg, out_dir):
    """A page prepared the way run() and stitch() prepare one: the capture's viewport and scale, its blocked requests,
    the pre steps (consent), the warmup, back to the top, fonts loaded. Yields (browser, context, page) for a film's
    recon and brand-layer commands, and closes the browser on exit. Captures nothing."""
    from playwright.sync_api import sync_playwright
    os.makedirs(out_dir, exist_ok=True)
    vw, vh = cfg['viewport']
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        try:
            ctx = b.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=cfg.get('device_scale', 2),
                                reduced_motion=cfg.get('reduced_motion', 'no-preference'))
            for pat in cfg.get('block', []) + cfg.get('count_block', []):
                ctx.route(re.compile(pat), lambda r: r.abort())
            p = ctx.new_page()
            for st in cfg.get('pre', []):
                _step(p, st, out_dir)
            w = cfg.get('warmup')
            if w:
                s = 0
                while s <= w['to']:
                    p.evaluate('s => window.scrollTo({top: s, behavior: "instant"})', s)
                    p.wait_for_timeout(w.get('wait_ms', 250))
                    s += w['step']
            p.evaluate('() => window.scrollTo({top: 0, behavior: "instant"})')
            p.wait_for_timeout((w or {}).get('settle_ms', 1500))
            p.evaluate('() => document.fonts.ready')
            yield b, ctx, p
        finally:
            b.close()


if __name__ == '__main__':
    import sys
    film = json.load(open(sys.argv[1]))
    print(json.dumps({k: v for k, v in run(film['capture'], sys.argv[2], sys.argv[3]).items() if k != 'log'}))
