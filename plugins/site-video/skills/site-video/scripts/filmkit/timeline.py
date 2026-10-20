"""Writes a film's timeline.json: per frame the scroll samples for capture.py, the mouse position, the zoom, the site
and the navigation flag. A film supplies scroll/camera/cursor functions (see motion.py) and the navigation time."""
import json
from . import motion


def plan(fps, cap_end, scroll, camera, cursor, nav_t, view_w, win_w, sites=('a', 'b'), shutter=0.5, acts=None, crop=None):
    """One entry per frame 0..round(cap_end*fps). Video time = capture time. `camera(t)` -> (zoom, cx, cy);
    `cursor(t)` -> (x, y) | None; `sites` names the page before and from the navigation; `acts` {frame: [step, ...]}
    in-page actions for capture.py (a click that stays on the page, a mouse move, a script). `crop(t)` -> (zoom, x0, y0,
    cw, ch), the film's crop of the viewport: given, each frame also carries `view`, the window's view of the page in
    page px [x0, y0 + scroll, cw, ch], which film_check's plan gates read (motion and framing before any capture)."""
    frames = []
    for i in range(round(cap_end * fps) + 1):
        t = i / fps
        c = cursor(t)
        z = camera(t)[0]
        ss = motion.plan_samples(scroll, t, fps, z, win_w, view_w, nav_t, shutter)
        frames.append({'i': i, 's': ss, 'scale': 'device', 'z': round(z, 3),
                       'site': sites[0] if t < nav_t else sites[1], 'nav': t >= nav_t > (i - 1) / fps,
                       'mouse': [round(c[0], 1), round(c[1], 1)] if c else None})
        if acts and i in acts:
            frames[-1]['act'] = acts[i]
        if crop:
            _, x0, y0, cw, ch = crop(t)
            frames[-1]['view'] = [round(x0, 2), round(y0 + scroll(t), 2), round(cw, 2), round(ch, 2)]
    return frames


def write(frames, path):
    """Writes the plan as JSON (json.dump defaults, no trailing newline) and returns a one-line summary."""
    with open(path, 'w') as fh:
        json.dump(frames, fh)
    return (f"{len(frames)} frames; {sum(len(f['s']) for f in frames)} captures "
            f"({sum(1 for f in frames if len(f['s']) > 1)} blurred); "
            f"navs {sum(f['nav'] for f in frames)}; max zoom {max(f['z'] for f in frames)}")
